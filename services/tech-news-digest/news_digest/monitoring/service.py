from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from ..state.store import StateStore
from .adapters import SourceAdapter, create_adapter
from .models import SignalLevel, SourceSpec
from .normalizer import normalize_item
from .policies import enforce_run_interrupt_budget, should_dispatch_interrupt
from .signal_engine import classify_signal
from .watchlist import MonitoringWatchlist

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitoringRunResult:
    fetched_count: int
    new_event_count: int
    signal_count: int
    dispatched_count: int
    skipped_sources: list[str]


class MonitoringService:
    def __init__(
        self,
        *,
        watchlist: MonitoringWatchlist,
        state_store: StateStore,
        dispatcher,
        adapter_factory: Callable[[SourceSpec], SourceAdapter] = create_adapter,
        max_interrupts_per_run: int = 3,
    ) -> None:
        self.watchlist = watchlist
        self.state_store = state_store
        self.dispatcher = dispatcher
        self.adapter_factory = adapter_factory
        self.max_interrupts_per_run = max_interrupts_per_run

    def run(self, now: datetime | None = None) -> MonitoringRunResult:
        run_at = now or datetime.now(tz=timezone.utc)
        fetched_count = 0
        new_event_count = 0
        skipped_sources: list[str] = []
        run_records = []

        for source in self.watchlist.sources:
            if not source.enabled:
                skipped_sources.append(source.key)
                continue
            try:
                adapter = self.adapter_factory(source)
                raw_items = adapter.fetch()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Monitoring source fetch failed for %s: %s", source.key, exc)
                skipped_sources.append(source.key)
                continue

            fetched_count += len(raw_items)
            for raw in raw_items:
                event = normalize_item(raw, self.watchlist, now=run_at)
                existing = self.state_store.get_monitor_event_by_hash(event.event_hash)
                persisted_event = self.state_store.record_monitor_event(event)
                if existing is not None:
                    continue
                new_event_count += 1
                run_records.append((classify_signal(persisted_event), persisted_event))

        budgeted_signals = enforce_run_interrupt_budget(
            [signal for signal, _event in run_records],
            max_per_run=self.max_interrupts_per_run,
        )
        events_by_id = {event.id: event for _signal, event in run_records}
        recent_dispatched = [
            signal
            for signal in self.state_store.list_monitor_signals(level=SignalLevel.INTERRUPT)
            if signal.dispatched_at is not None
        ]

        dispatched_count = 0
        for signal in budgeted_signals:
            persisted_signal = self.state_store.record_monitor_signal(signal)
            if should_dispatch_interrupt(persisted_signal, recent_dispatched=recent_dispatched):
                event_to_send = events_by_id[persisted_signal.event_id]
                sent = self.dispatcher.send_monitor_signal(persisted_signal, event_to_send)
                if sent is False:
                    continue
                self.state_store.mark_monitor_signal_dispatched(persisted_signal.id, run_at)
                dispatched_count += 1

        return MonitoringRunResult(
            fetched_count=fetched_count,
            new_event_count=new_event_count,
            signal_count=len(budgeted_signals),
            dispatched_count=dispatched_count,
            skipped_sources=skipped_sources,
        )
