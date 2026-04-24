from __future__ import annotations

from datetime import datetime, timezone

from news_digest.monitoring.models import RawSourceItem, SourceKind, SourceSpec, WatchEntity
from news_digest.monitoring.normalizer import normalize_item
from news_digest.monitoring.watchlist import MonitoringWatchlist


def test_normalizer_extracts_entities_symbols_tags_and_stable_hash() -> None:
    watchlist = MonitoringWatchlist(
        entities=(
            WatchEntity(
                key="openai",
                label="OpenAI",
                aliases=("OpenAI", "ChatGPT"),
                symbols=("MSFT", "NVDA"),
                tags=("ai", "agent"),
                priority=5,
            ),
        ),
        sources=(
            SourceSpec(
                key="openai-news",
                kind=SourceKind.RSS,
                url="https://openai.com/news/rss.xml",
                trust_tier=1,
                tags=("official", "ai"),
            ),
        ),
    )
    raw = RawSourceItem(
        source_key="openai-news",
        source_kind=SourceKind.RSS,
        title="OpenAI launches workplace agents",
        url="https://openai.com/news/workplace-agents?utm_source=x",
        published_at=datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc),
        content_hint="Agent controls",
    )

    event = normalize_item(raw, watchlist, now=datetime(2026, 4, 24, 0, 5, tzinfo=timezone.utc))

    assert event.entities == ("openai",)
    assert event.symbols == ("MSFT", "NVDA")
    assert event.tags == ("ai", "agent", "official")
    assert event.url == "https://openai.com/news/workplace-agents"
    assert len(event.event_hash) == 64


def test_normalizer_does_not_match_partial_alias_words() -> None:
    watchlist = MonitoringWatchlist(
        entities=(WatchEntity(key="ai", label="AI", aliases=("AI",), symbols=("QQQ",), tags=("ai",)),),
        sources=(),
    )
    raw = RawSourceItem(
        source_key="example",
        source_kind=SourceKind.RSS,
        title="Said another way",
        url="https://example.com/a",
        published_at=None,
    )

    event = normalize_item(raw, watchlist, now=datetime(2026, 4, 24, tzinfo=timezone.utc))

    assert event.entities == ()
    assert event.symbols == ()


def test_normalizer_hash_is_stable_across_tracking_params_case_and_trailing_slash() -> None:
    watchlist = MonitoringWatchlist(
        entities=(),
        sources=(
            SourceSpec(
                key="example",
                kind=SourceKind.RSS,
                url="https://example.com/feed",
                trust_tier=3,
            ),
        ),
    )
    first = RawSourceItem(
        source_key="example",
        source_kind=SourceKind.RSS,
        title="Same Article",
        url="HTTP://Example.COM/path/article/?utm_source=x&ref=twitter&keep=1#section",
        published_at=None,
    )
    second = RawSourceItem(
        source_key="example",
        source_kind=SourceKind.RSS,
        title="Same Article",
        url="https://example.com/path/article?keep=1",
        published_at=None,
    )

    first_event = normalize_item(first, watchlist, now=datetime(2026, 4, 24, tzinfo=timezone.utc))
    second_event = normalize_item(second, watchlist, now=datetime(2026, 4, 24, tzinfo=timezone.utc))

    assert first_event.url == "https://example.com/path/article?keep=1"
    assert first_event.event_hash == second_event.event_hash


def test_normalizer_prefers_longer_alias_and_supports_chinese_aliases() -> None:
    watchlist = MonitoringWatchlist(
        entities=(
            WatchEntity(key="gpt", label="GPT", aliases=("GPT",), symbols=("MSFT",), tags=("ai",)),
            WatchEntity(key="gpt-5", label="GPT-5", aliases=("GPT-5",), symbols=("MSFT",), tags=("ai",)),
            WatchEntity(key="nvidia", label="NVIDIA", aliases=("英伟达",), symbols=("NVDA",), tags=("chips",)),
        ),
        sources=(),
    )

    gpt_event = normalize_item(
        RawSourceItem(
            source_key="example",
            source_kind=SourceKind.RSS,
            title="GPT-5 发布",
            url="https://example.com/gpt-5",
            published_at=None,
        ),
        watchlist,
        now=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )
    nvidia_event = normalize_item(
        RawSourceItem(
            source_key="example",
            source_kind=SourceKind.RSS,
            title="英伟达发布新品",
            url="https://example.com/nvidia",
            published_at=None,
        ),
        watchlist,
        now=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )

    assert gpt_event.entities == ("gpt-5",)
    assert nvidia_event.entities == ("nvidia",)
