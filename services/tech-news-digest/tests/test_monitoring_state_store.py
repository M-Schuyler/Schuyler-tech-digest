from __future__ import annotations

from datetime import datetime, timezone

from news_digest.monitoring.models import MonitorEvent, MonitorSignal, SignalLevel
from news_digest.state.store import StateStore


def test_state_store_records_monitor_event_once_by_hash(tmp_path) -> None:
    store = StateStore(sqlite_path=tmp_path / "state.db")
    event = MonitorEvent(
        source_key="openai-news",
        source_kind="rss",
        title="OpenAI launches workplace agents",
        url="https://openai.com/news/workplace-agents",
        published_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        first_seen_at=datetime(2026, 4, 24, 0, 5, tzinfo=timezone.utc),
        content_hint="Agent controls",
        event_hash="hash-1",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        trust_tier=1,
    )

    first = store.record_monitor_event(event)
    second = store.record_monitor_event(event)
    events = store.list_monitor_events(since_utc=datetime(2026, 4, 23, tzinfo=timezone.utc))

    assert first.id == second.id
    assert len(events) == 1
    assert events[0].entities == ("openai",)
    assert store.get_monitor_event_by_hash("hash-1").id == first.id


def test_state_store_records_and_lists_digest_candidate_signals(tmp_path) -> None:
    store = StateStore(sqlite_path=tmp_path / "state.db")
    event = store.record_monitor_event(
        MonitorEvent(
            source_key="openai-news",
            source_kind="rss",
            title="OpenAI launches workplace agents",
            url="https://openai.com/news/workplace-agents",
            published_at=None,
            first_seen_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            content_hint="Agent controls",
            event_hash="hash-1",
            entities=("openai",),
            symbols=("MSFT", "NVDA"),
            tags=("ai", "agent"),
            trust_tier=1,
        )
    )
    store.record_monitor_signal(
        MonitorSignal(
            event_id=event.id,
            level=SignalLevel.DIGEST_CANDIDATE,
            score=75,
            reason="Official AI agent update matched OpenAI watchlist.",
            entities=("openai",),
            symbols=("MSFT", "NVDA"),
            tags=("ai", "agent"),
            created_at=datetime(2026, 4, 24, 0, 10, tzinfo=timezone.utc),
        )
    )

    signals = store.list_monitor_signals(level=SignalLevel.DIGEST_CANDIDATE)

    assert len(signals) == 1
    assert signals[0].score == 75
    assert signals[0].symbols == ("MSFT", "NVDA")


def test_state_store_marks_monitor_signal_dispatched(tmp_path) -> None:
    store = StateStore(sqlite_path=tmp_path / "state.db")
    event = store.record_monitor_event(
        MonitorEvent(
            source_key="openai-news",
            source_kind="rss",
            title="OpenAI launches workplace agents",
            url="https://openai.com/news/workplace-agents",
            published_at=None,
            first_seen_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            content_hint="Agent controls",
            event_hash="hash-1",
            entities=("openai",),
            symbols=("MSFT", "NVDA"),
            tags=("ai", "agent"),
            trust_tier=1,
        )
    )
    signal = store.record_monitor_signal(
        MonitorSignal(
            event_id=event.id,
            level=SignalLevel.INTERRUPT,
            score=91,
            reason="Official source + watched entity.",
            entities=("openai",),
            symbols=("MSFT", "NVDA"),
            tags=("ai", "agent"),
            created_at=datetime(2026, 4, 24, 0, 10, tzinfo=timezone.utc),
        )
    )

    store.mark_monitor_signal_dispatched(signal.id, datetime(2026, 4, 24, 0, 11, tzinfo=timezone.utc))

    stored = store.list_monitor_signals(level=SignalLevel.INTERRUPT)[0]
    assert stored.dispatched_at == datetime(2026, 4, 24, 0, 11, tzinfo=timezone.utc)
