from __future__ import annotations

from datetime import datetime, timezone

from news_digest.monitoring.models import (
    MonitorEvent,
    MonitorSignal,
    SignalLevel,
    SourceKind,
)


def test_monitor_event_carries_dedupe_hash_entities_and_symbols() -> None:
    event = MonitorEvent(
        source_key="openai-news",
        source_kind=SourceKind.RSS.value,
        title="OpenAI launches workplace agents",
        url="https://openai.com/news/workplace-agents",
        published_at=datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc),
        first_seen_at=datetime(2026, 4, 24, 0, 5, tzinfo=timezone.utc),
        content_hint="Agent controls for enterprise workflows",
        event_hash="abc123",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        trust_tier=1,
    )

    assert event.event_hash == "abc123"
    assert event.entities == ("openai",)
    assert event.symbols == ("MSFT", "NVDA")


def test_monitor_signal_has_explicit_level_not_boolean_importance() -> None:
    signal = MonitorSignal(
        event_id=12,
        level=SignalLevel.INTERRUPT,
        score=92,
        reason="Official OpenAI agent update maps to MSFT/NVDA watchlist.",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        created_at=datetime(2026, 4, 24, 0, 10, tzinfo=timezone.utc),
    )

    assert signal.level is SignalLevel.INTERRUPT
    assert signal.score == 92
