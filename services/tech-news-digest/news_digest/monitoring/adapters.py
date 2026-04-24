from __future__ import annotations

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
        for entry in getattr(feed, "entries", []):
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
