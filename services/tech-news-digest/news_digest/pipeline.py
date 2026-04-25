from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rapidfuzz import fuzz

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
                        story_key=assessment.story_key,
                        entities=assessment.entities,
                        symbols=assessment.symbols,
                    ),
                    raw,
                )
            )

            if len(candidates) >= self.target_candidate_pool:
                logger.info("Reached candidate pool target (%s)", self.target_candidate_pool)
                break

        candidates = _dedupe_story_candidates(candidates)
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


def _dedupe_story_candidates(
    candidates: list[tuple[BriefingItem, ArticleRaw]],
) -> list[tuple[BriefingItem, ArticleRaw]]:
    unique: list[tuple[BriefingItem, ArticleRaw]] = []

    for candidate in candidates:
        match_idx = next(
            (
                idx
                for idx, existing in enumerate(unique)
                if _is_same_story(candidate, existing)
            ),
            None,
        )
        if match_idx is None:
            unique.append(candidate)
            continue

        if _candidate_rank_value(candidate) > _candidate_rank_value(unique[match_idx]):
            unique[match_idx] = candidate

    return unique


def _is_same_story(
    left: tuple[BriefingItem, ArticleRaw],
    right: tuple[BriefingItem, ArticleRaw],
) -> bool:
    left_item, _left_raw = left
    right_item, _right_raw = right

    if left_item.story_key and right_item.story_key and left_item.story_key == right_item.story_key:
        return True

    left_models = _model_tokens(left_item)
    right_models = _model_tokens(right_item)
    if left_models and right_models and left_models != right_models:
        return False

    left_money = _money_tokens(left_item)
    right_money = _money_tokens(right_item)
    if left_money and right_money and left_money != right_money:
        return False

    left_entities = set(left_item.entities) or _entity_tokens(left_item)
    right_entities = set(right_item.entities) or _entity_tokens(right_item)
    if left_entities and right_entities and left_entities.isdisjoint(right_entities):
        return False

    similarity = fuzz.token_set_ratio(_story_text(left_item), _story_text(right_item))
    if similarity >= 90:
        return True

    has_shared_entities = bool(left_entities and right_entities and not left_entities.isdisjoint(right_entities))
    has_shared_event_tokens = bool((left_money and left_money == right_money) or (left_models and left_models == right_models))
    return similarity >= 84 and has_shared_entities and has_shared_event_tokens


def _candidate_rank_value(candidate: tuple[BriefingItem, ArticleRaw]) -> tuple[int, float]:
    item, raw = candidate
    return (
        item.importance_score + _source_weight(raw) + _recentness_weight(raw),
        _published_sort_key(raw.published_at),
    )


def _story_text(item: BriefingItem) -> str:
    return " ".join([item.title, item.story_key, *(item.summary_en or []), *(item.summary_zh or [])]).lower()


def _model_tokens(item: BriefingItem) -> set[str]:
    text = _story_text(item)
    return set(re.findall(r"\b(?:gpt|claude|gemini|deepseek|llama|mistral)[-\s]?\d+(?:\.\d+)?\b", text))


def _money_tokens(item: BriefingItem) -> set[str]:
    text = _story_text(item)
    tokens = set()
    for amount, unit in re.findall(r"\$?\b(\d+(?:\.\d+)?)\s?(billion|million|bn|m|b)\b", text):
        normalized_unit = "b" if unit in {"billion", "bn", "b"} else "m"
        tokens.add(f"{amount}{normalized_unit}")
    if "billions" in text:
        tokens.add("billions")
    return tokens


def _entity_tokens(item: BriefingItem) -> set[str]:
    text = _story_text(item)
    known_entities = {
        "openai",
        "anthropic",
        "google",
        "alphabet",
        "amazon",
        "microsoft",
        "meta",
        "nvidia",
        "apple",
        "deepmind",
    }
    return {entity for entity in known_entities if re.search(rf"\b{re.escape(entity)}\b", text)}


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
