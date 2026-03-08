from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .config import DEFAULT_SETTINGS, Settings
from .db import NewsRepository, StoredArticle
from .extractor import ArticleExtractor
from .fetchers import RSSFetcher
from .models import ArticleRaw, ArticleSeed
from .notifier import TelegramNotifier
from .report import BriefingItem, MarkdownReportWriter
from .summarizer import NewsSummarizer

logger = logging.getLogger(__name__)

TITLE_INCLUDE_PATTERNS = [
    r"\b(ai|llm|model|agent)\b",
    r"\b(robot|robotics|humanoid|autonomous|drone)\b",
    r"\b(chip|semiconductor|gpu|cpu|foundry|tsmc|nvidia|amd|intel)\b",
    r"\b(openai|anthropic|google|microsoft|amazon|meta|apple|tesla|bytedance)\b",
    r"\b(startup|funding|raised|series [abcde]|seed|venture|valuation|ipo)\b",
    r"\b(acquisition|acquire|merger|antitrust|regulation|lawsuit)\b",
    r"\b(quantum|fusion|battery|biotech|breakthrough|datacenter|cloud)\b",
]

TITLE_EXCLUDE_PATTERNS = [
    r"\breview\b",
    r"\bhands[- ]on\b",
    r"\bgaming\b",
    r"\bgame\b",
    r"\bgadget\b",
    r"\bsmartphone\b",
    r"\biphone\b",
    r"\bandroid phones?\b",
    r"\bmovie\b",
    r"\bseries\b",
    r"\bopinion\b",
    r"\bop-ed\b",
    r"\beditorial\b",
]


class NewsPipeline:
    def __init__(self, settings: Settings = DEFAULT_SETTINGS) -> None:
        self.settings = settings
        self.fetcher = RSSFetcher(settings)
        self.extractor = ArticleExtractor(settings)
        self.summarizer = NewsSummarizer(settings)
        self.repository = NewsRepository()
        self.report_writer = MarkdownReportWriter(max_items=settings.max_briefing_items)
        self.notifier = TelegramNotifier()
        default_attempts = max(30, settings.max_briefing_items * 6)
        default_pool = max(settings.max_briefing_items * 3, settings.max_briefing_items)
        self.max_extraction_attempts = int(os.getenv("MAX_EXTRACTION_ATTEMPTS", str(default_attempts)))
        self.target_candidate_pool = int(os.getenv("TARGET_CANDIDATE_POOL", str(default_pool)))

    def run(self, report_date: date | None = None) -> tuple[str, int]:
        run_day = report_date or date.today()

        seeds = _dedupe_seeds(self.fetcher.fetch())
        logger.info("After dedupe, %s article seeds remain", len(seeds))

        candidates: list[tuple[BriefingItem, ArticleRaw]] = []
        seen_titles: set[str] = set()
        extraction_attempts = 0

        for seed in seeds:
            if not _seed_passes_title_gate(seed.title):
                continue
            if extraction_attempts >= self.max_extraction_attempts:
                logger.info("Reached extraction attempt cap (%s)", self.max_extraction_attempts)
                break

            extraction_attempts += 1
            raw = self.extractor.extract(seed)
            if not raw:
                continue

            assessment = self.summarizer.assess(raw)
            if not assessment:
                continue

            title_key = _normalize_title(assessment.title)
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            candidates.append(
                (
                    BriefingItem(
                        title=assessment.title,
                        category=assessment.category,
                        summary_en=assessment.summary_en,
                        summary_zh=assessment.summary_zh,
                        url=raw.url,
                        importance_score=assessment.importance_score,
                    ),
                    raw,
                )
            )

            if len(candidates) >= self.target_candidate_pool:
                logger.info("Reached candidate pool target (%s)", self.target_candidate_pool)
                break

        candidates.sort(
            key=lambda x: (
                x[0].importance_score,
                _published_sort_key(x[1].published_at),
            ),
            reverse=True,
        )
        selected = candidates[: self.settings.max_briefing_items]

        for briefing, raw in selected:
            article_day = raw.published_at.date().isoformat() if raw.published_at else run_day.isoformat()
            self.repository.upsert(
                StoredArticle(
                    title=briefing.title,
                    source=raw.source,
                    summary=_format_summary_for_storage(briefing),
                    keywords=briefing.category,
                    url=briefing.url,
                    date=article_day,
                )
            )

        report_items = [item for item, _ in selected]
        report_path = self.report_writer.write(run_day, report_items)
        self.notifier.send_report(run_day, report_path, len(report_items))
        logger.info(
            "Report generated: %s (items=%s, extraction_attempts=%s, candidates=%s)",
            report_path,
            len(report_items),
            extraction_attempts,
            len(candidates),
        )

        return str(report_path), len(report_items)


def _dedupe_seeds(seeds: list[ArticleSeed]) -> list[ArticleSeed]:
    unique: list[ArticleSeed] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for seed in seeds:
        canonical_url = _canonicalize_url(seed.url)
        title_key = _normalize_title(seed.title)

        if canonical_url in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue

        seen_urls.add(canonical_url)
        if title_key:
            seen_titles.add(title_key)

        unique.append(
            ArticleSeed(
                title=seed.title,
                source=seed.source,
                url=canonical_url,
                published_at=seed.published_at,
            )
        )

    return unique


def _canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    filtered_qs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lower_key = key.lower()
        if lower_key.startswith("utm_"):
            continue
        if lower_key in {"gclid", "fbclid", "mc_cid", "mc_eid", "igshid"}:
            continue
        filtered_qs.append((key, value))

    clean_query = urlencode(filtered_qs, doseq=True)
    clean_path = parsed.path.rstrip("/") or "/"

    return urlunparse(
        (
            parsed.scheme.lower() or "https",
            parsed.netloc.lower(),
            clean_path,
            "",
            clean_query,
            "",
        )
    )


def _normalize_title(title: str) -> str:
    text = re.sub(r"\s+", " ", title.lower()).strip()
    return re.sub(r"[^a-z0-9]+", "", text)


def _format_summary_for_storage(item: BriefingItem) -> str:
    en_1 = item.summary_en[0] if item.summary_en else ""
    en_2 = item.summary_en[1] if len(item.summary_en) > 1 else ""
    zh_1 = item.summary_zh[0] if item.summary_zh else ""
    zh_2 = item.summary_zh[1] if len(item.summary_zh) > 1 else ""
    return "\n".join(
        [
            f"Category: {item.category}",
            f"EN1: {en_1}",
            f"EN2: {en_2}",
            f"ZH1: {zh_1}",
            f"ZH2: {zh_2}",
            f"Score: {item.importance_score}",
        ]
    )


def _seed_passes_title_gate(title: str) -> bool:
    lower = (title or "").lower()
    has_excluded = any(re.search(pattern, lower) for pattern in TITLE_EXCLUDE_PATTERNS)
    has_included = any(re.search(pattern, lower) for pattern in TITLE_INCLUDE_PATTERNS)
    if has_excluded and not has_included:
        return False
    return has_included


def _published_sort_key(published_at: datetime | None) -> float:
    if not published_at:
        return 0.0
    if published_at.tzinfo is None:
        normalized = published_at.replace(tzinfo=timezone.utc)
    else:
        normalized = published_at.astimezone(timezone.utc)
    return normalized.timestamp()
