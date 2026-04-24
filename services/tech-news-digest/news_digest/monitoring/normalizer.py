from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import MonitorEvent, RawSourceItem, SourceKind, SourceSpec, WatchEntity
from .watchlist import MonitoringWatchlist

TRACKING_QUERY_KEYS = {"ref", "ref_src", "fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_item(raw: RawSourceItem, watchlist: MonitoringWatchlist, *, now: datetime) -> MonitorEvent:
    source = _source_for(raw.source_key, watchlist)
    canonical_url = canonicalize_url(raw.url)
    matched_entities = _match_entities(f"{raw.title}\n{raw.content_hint}", watchlist.entities)
    entities = tuple(entity.key for entity in matched_entities)
    symbols = _dedupe(value for entity in matched_entities for value in entity.symbols)
    entity_tags = _dedupe(value for entity in matched_entities for value in entity.tags)
    source_tags = source.tags if source else tuple(raw.metadata.get("source_tags", ()))
    tags = _dedupe((*entity_tags, *source_tags))
    normalized_title = _normalize_title(raw.title)
    event_hash = hashlib.sha256(
        f"{raw.source_key}|{canonical_url}|{normalized_title}".encode("utf-8")
    ).hexdigest()
    metadata = dict(raw.metadata)
    metadata["entity_priorities"] = {entity.key: entity.priority for entity in matched_entities}

    return MonitorEvent(
        source_key=raw.source_key,
        source_kind=_source_kind_value(raw.source_kind),
        title=raw.title.strip(),
        url=canonical_url,
        published_at=raw.published_at,
        first_seen_at=now,
        content_hint=raw.content_hint.strip(),
        event_hash=event_hash,
        entities=entities,
        symbols=symbols,
        tags=tags,
        trust_tier=source.trust_tier if source else 3,
        raw_metadata=metadata,
    )


def canonicalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = "https" if parsed.scheme.lower() == "http" else parsed.scheme.lower()
    if not scheme:
        scheme = "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not _is_tracking_query_key(key)
        ],
        doseq=True,
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def _match_entities(text: str, entities: tuple[WatchEntity, ...]) -> list[WatchEntity]:
    candidates: list[tuple[str, WatchEntity]] = []
    for entity in entities:
        aliases = entity.aliases or (entity.label,)
        candidates.extend((alias, entity) for alias in aliases if alias)

    matched: list[WatchEntity] = []
    occupied_spans: list[tuple[int, int]] = []
    for alias, entity in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
        span = _find_alias_span(text, alias)
        if span is None:
            continue
        if _overlaps(span, occupied_spans):
            continue
        occupied_spans.append(span)
        if entity.key not in {item.key for item in matched}:
            matched.append(entity)
    return matched


def _find_alias_span(text: str, alias: str) -> tuple[int, int] | None:
    if _contains_cjk(alias):
        start = text.find(alias)
        if start < 0:
            return None
        return start, start + len(alias)

    lower_text = text.lower()
    lower_alias = alias.lower()
    start = 0
    while True:
        idx = lower_text.find(lower_alias, start)
        if idx < 0:
            return None
        end = idx + len(lower_alias)
        if _english_boundary(lower_text, idx, end):
            return idx, end
        start = idx + 1


def _english_boundary(text: str, start: int, end: int) -> bool:
    previous_ok = start == 0 or not _is_ascii_word_or_hyphen(text[start - 1])
    next_ok = end >= len(text) or not _is_ascii_word_or_hyphen(text[end])
    return previous_ok and next_ok


def _is_ascii_word_or_hyphen(char: str) -> bool:
    return char == "-" or char.isascii() and char.isalnum()


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(span[0] < existing[1] and existing[0] < span[1] for existing in spans)


def _source_for(source_key: str, watchlist: MonitoringWatchlist) -> SourceSpec | None:
    for source in watchlist.sources:
        if source.key == source_key:
            return source
    return None


def _source_kind_value(kind: SourceKind | str) -> str:
    if isinstance(kind, SourceKind):
        return kind.value
    return str(kind)


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def _is_tracking_query_key(key: str) -> bool:
    normalized = key.lower()
    return normalized.startswith("utm_") or normalized in TRACKING_QUERY_KEYS


def _dedupe(values) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return tuple(result)
