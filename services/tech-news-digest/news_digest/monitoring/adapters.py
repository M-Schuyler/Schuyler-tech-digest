from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from .models import RawSourceItem, SourceKind, SourceSpec


class SourceAdapter:
    def __init__(self, source: SourceSpec) -> None:
        self.source = source

    def fetch(self) -> list[RawSourceItem]:
        raise NotImplementedError


class UnsupportedSourceAdapter(SourceAdapter):
    def fetch(self) -> list[RawSourceItem]:
        return []


class RSSSourceAdapter(SourceAdapter):
    def fetch(self) -> list[RawSourceItem]:
        feed = feedparser.parse(self.source.url)
        items: list[RawSourceItem] = []
        max_items = _max_items_per_source()
        for entry in getattr(feed, "entries", [])[:max_items]:
            title = str(entry.get("title", "")).strip()
            url = str(entry.get("link", "")).strip()
            if not title or not url:
                continue
            items.append(
                RawSourceItem(
                    source_key=self.source.key,
                    source_kind=self.source.kind,
                    title=title,
                    url=url,
                    published_at=_entry_time(entry),
                    content_hint=str(entry.get("summary", "")).strip(),
                    metadata={"source_tags": list(self.source.tags)},
                )
            )
        return items


def create_adapter(source: SourceSpec) -> SourceAdapter:
    if source.kind is SourceKind.RSS:
        return RSSSourceAdapter(source)
    return UnsupportedSourceAdapter(source)


def _entry_time(entry) -> datetime | None:
    if entry.get("published_parsed"):
        return datetime(*entry["published_parsed"][:6], tzinfo=timezone.utc)
    if entry.get("published"):
        parsed = parsedate_to_datetime(str(entry["published"]))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _max_items_per_source() -> int:
    raw = os.getenv("MONITORING_MAX_ITEMS_PER_SOURCE", "20").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 20
