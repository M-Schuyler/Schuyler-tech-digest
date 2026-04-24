from __future__ import annotations

from datetime import datetime

from news_digest.monitoring.adapters import RSSSourceAdapter, UnsupportedSourceAdapter, create_adapter
from news_digest.monitoring.models import SourceKind, SourceSpec


def test_create_adapter_returns_rss_adapter_for_rss_sources() -> None:
    source = SourceSpec(
        key="hn",
        kind=SourceKind.RSS,
        url="https://hnrss.org/frontpage",
        trust_tier=3,
    )

    adapter = create_adapter(source)

    assert isinstance(adapter, RSSSourceAdapter)


def test_create_adapter_returns_unsupported_adapter_for_web_v1() -> None:
    source = SourceSpec(
        key="custom-web",
        kind=SourceKind.WEB,
        url="https://example.com",
        trust_tier=3,
    )

    adapter = create_adapter(source)

    assert isinstance(adapter, UnsupportedSourceAdapter)
    assert adapter.fetch() == []


def test_rss_adapter_converts_feed_entries_to_raw_items(monkeypatch) -> None:
    class Feed:
        entries = [
            {
                "title": "OpenAI launches workplace agents",
                "link": "https://openai.com/news/workplace-agents",
                "summary": "Agent controls for enterprise workflows",
                "published_parsed": datetime(2026, 4, 24).timetuple(),
            }
        ]

    monkeypatch.setattr("feedparser.parse", lambda _url: Feed())
    source = SourceSpec(
        key="openai-news",
        kind=SourceKind.RSS,
        url="https://openai.com/news/rss.xml",
        trust_tier=1,
    )

    items = RSSSourceAdapter(source).fetch()

    assert len(items) == 1
    assert items[0].source_key == "openai-news"
    assert items[0].title == "OpenAI launches workplace agents"
    assert items[0].content_hint == "Agent controls for enterprise workflows"
