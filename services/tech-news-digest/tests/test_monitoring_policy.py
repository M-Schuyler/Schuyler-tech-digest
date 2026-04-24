from __future__ import annotations

from datetime import datetime, timedelta, timezone

from news_digest.monitoring.models import MonitorSignal, SignalLevel
from news_digest.monitoring.policies import enforce_run_interrupt_budget, should_dispatch_interrupt


def signal(symbols=("MSFT",), created_at=datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)):
    return MonitorSignal(
        event_id=1,
        level=SignalLevel.INTERRUPT,
        score=90,
        reason="Official source + watched entity.",
        entities=("openai",),
        symbols=symbols,
        tags=("ai", "agent"),
        created_at=created_at,
    )


def test_interrupt_signal_dispatches_when_not_recently_sent() -> None:
    assert should_dispatch_interrupt(signal(), recent_dispatched=[]) is True


def test_interrupt_signal_suppressed_by_same_symbol_cooldown() -> None:
    now = datetime(2026, 4, 24, 0, 30, tzinfo=timezone.utc)
    recent = [signal(created_at=now - timedelta(minutes=30))]

    assert should_dispatch_interrupt(signal(created_at=now), recent_dispatched=recent) is False


def test_run_interrupt_budget_downgrades_excess_interrupts() -> None:
    signals = [
        signal(symbols=(f"SYM{idx}",), created_at=datetime(2026, 4, 24, 0, idx, tzinfo=timezone.utc))
        for idx in range(5)
    ]

    budgeted = enforce_run_interrupt_budget(signals, max_per_run=3)

    assert [item.level for item in budgeted].count(SignalLevel.INTERRUPT) == 3
    assert [item.level for item in budgeted].count(SignalLevel.DIGEST_CANDIDATE) == 2
    assert [item.suppressed_reason for item in budgeted[-2:]] == [
        "run_budget_exceeded",
        "run_budget_exceeded",
    ]
