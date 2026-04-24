from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .config import DEFAULT_SETTINGS, Settings
from .extractor import ArticleExtractor
from .fetchers import RSSFetcher
from .models import ArticleRaw, ArticleSeed
from .report import BriefingItem
from .summarizer import NewsSummarizer

logger = logging.getLogger(__name__)

TITLE_INCLUDE_PATTERNS = [
    r"\b(ai|llm|model|agent|gpt|chatgpt|claude|gemini|deepseek)\b",
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
        default_attempts = max(30, settings.max_briefing_items * 6)
        default_pool = max(settings.max_briefing_items * 3, settings.max_briefing_items)
        self.max_extraction_attempts = int(os.getenv("MAX_EXTRACTION_ATTEMPTS", str(default_attempts)))
        self.target_candidate_pool = int(os.getenv("TARGET_CANDIDATE_POOL", str(default_pool)))

    def collect_selected(
        self,
        report_date: date | None = None,
    ) -> tuple[list[tuple[BriefingItem, ArticleRaw]], int, int]:
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
                x[0].importance_score + _source_weight(x[1]) + _recentness_weight(x[1]),
                _published_sort_key(x[1].published_at),
            ),
            reverse=True,
        )
        selected = candidates[: self.settings.max_briefing_items]
        logger.info(
            "Collected digest candidates (selected=%s, extraction_attempts=%s, candidates=%s)",
            len(selected),
            extraction_attempts,
            len(candidates),
        )
        return selected, extraction_attempts, len(candidates)


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


def _source_weight(item: ArticleRaw | ArticleSeed) -> int:
    source = (item.source or "").lower()
    url = (item.url or "").lower()
    if "openai" in source or "openai.com" in url:
        return 18
    if "hacker news" in source or "hnrss.org" in url:
        return 8
    return 0


def _recentness_weight(item: ArticleRaw | ArticleSeed, *, now: datetime | None = None) -> int:
    published_at = item.published_at
    if not published_at:
        return 0

    reference = now or datetime.now(tz=timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    else:
        reference = reference.astimezone(timezone.utc)

    if published_at.tzinfo is None:
        normalized = published_at.replace(tzinfo=timezone.utc)
    else:
        normalized = published_at.astimezone(timezone.utc)

    age_hours = (reference - normalized).total_seconds() / 3600
    if age_hours < 0:
        return 20
    if age_hours <= 12:
        return 24
    if age_hours <= 24:
        return 18
    if age_hours <= 72:
        return 8
    return 0
