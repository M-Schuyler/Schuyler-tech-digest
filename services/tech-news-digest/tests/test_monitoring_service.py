from __future__ import annotations

from datetime import datetime, timezone

from news_digest.monitoring.models import RawSourceItem, SignalLevel, SourceKind, SourceSpec, WatchEntity
from news_digest.monitoring.service import MonitoringService
from news_digest.monitoring.watchlist import MonitoringWatchlist
from news_digest.state.store import StateStore


class FakeAdapter:
    def __init__(self, source):
        self.source = source

    def fetch(self):
        return [
            RawSourceItem(
                source_key=self.source.key,
                source_kind=self.source.kind,
                title="OpenAI launches workplace agents",
                url="https://openai.com/news/workplace-agents",
                published_at=None,
                content_hint="Agent controls",
            )
        ]


class FakeDispatcher:
    def __init__(self):
        self.sent = []

    def send_monitor_signal(self, signal, event):
        self.sent.append((signal, event))


def test_monitoring_service_records_event_signal_and_dispatches_interrupt(tmp_path) -> None:
    watchlist = MonitoringWatchlist(
        entities=(
            WatchEntity(
                key="openai",
                label="OpenAI",
                aliases=("OpenAI",),
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
    store = StateStore(sqlite_path=tmp_path / "state.db")
    dispatcher = FakeDispatcher()
    service = MonitoringService(
        watchlist=watchlist,
        state_store=store,
        dispatcher=dispatcher,
        adapter_factory=lambda source: FakeAdapter(source),
    )

    result = service.run(now=datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc))

    assert result.fetched_count == 1
    assert result.new_event_count == 1
    assert result.signal_count == 1
    assert result.dispatched_count == 1
    assert dispatcher.sent[0][0].level is SignalLevel.INTERRUPT


def test_monitoring_service_enforces_run_interrupt_budget_and_records_suppressed(tmp_path) -> None:
    watchlist = MonitoringWatchlist(
        entities=(
            WatchEntity(
                key="openai",
                label="OpenAI",
                aliases=("OpenAI",),
                symbols=("MSFT", "NVDA"),
                tags=("ai", "agent"),
                priority=5,
            ),
        ),
        sources=tuple(
            SourceSpec(
                key=f"openai-news-{idx}",
                kind=SourceKind.RSS,
                url=f"https://openai.com/news/rss-{idx}.xml",
                trust_tier=1,
                tags=("official", "ai"),
            )
            for idx in range(5)
        ),
    )

    class ManySignalAdapter:
        def __init__(self, source):
            self.source = source

        def fetch(self):
            return [
                RawSourceItem(
                    source_key=self.source.key,
                    source_kind=self.source.kind,
                    title=f"OpenAI launches workplace agents {self.source.key}",
                    url=f"https://openai.com/news/{self.source.key}",
                    published_at=None,
                    content_hint="Agent controls",
                )
            ]

    store = StateStore(sqlite_path=tmp_path / "state.db")
    dispatcher = FakeDispatcher()
    service = MonitoringService(
        watchlist=watchlist,
        state_store=store,
        dispatcher=dispatcher,
        adapter_factory=lambda source: ManySignalAdapter(source),
    )

    result = service.run(now=datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc))
    signals = store.list_monitor_signals()

    assert result.signal_count == 5
    assert result.dispatched_count == 3
    assert len(dispatcher.sent) == 3
    assert [item.level for item in signals].count(SignalLevel.INTERRUPT) == 3
    assert [item.suppressed_reason for item in signals].count("run_budget_exceeded") == 2
