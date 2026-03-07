from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from .config import Settings
from .models import ArticleSeed

logger = logging.getLogger(__name__)


class RSSFetcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch(self) -> list[ArticleSeed]:
        items: list[ArticleSeed] = []

        for source, url in self.settings.rss_sources.items():
            logger.info("Fetching RSS from %s (%s)", source, url)
            feed = feedparser.parse(url)

            if feed.bozo:
                logger.warning("RSS parse warning for %s: %s", source, feed.bozo_exception)

            for entry in feed.entries[: self.settings.max_articles_per_source]:
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                if not title or not link:
                    continue

                items.append(
                    ArticleSeed(
                        title=title,
                        source=source,
                        url=link,
                        published_at=_parse_published(entry),
                    )
                )

        logger.info("Collected %s article seeds", len(items))
        return items


def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("pubDate"),
    ]

    for value in candidates:
        if not value:
            continue
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            continue

    if "published_parsed" in entry and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (TypeError, ValueError):
            return None

    return None
