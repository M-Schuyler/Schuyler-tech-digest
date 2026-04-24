from __future__ import annotations

from datetime import timedelta

from .models import MonitorSignal, SignalLevel


def should_dispatch_interrupt(
    signal: MonitorSignal,
    recent_dispatched: list[MonitorSignal],
    cooldown_minutes: int = 90,
) -> bool:
    if signal.level is not SignalLevel.INTERRUPT:
        return False

    cutoff = signal.created_at - timedelta(minutes=cooldown_minutes)
    signal_keys = set(signal.symbols) or set(signal.entities)
    if not signal_keys:
        return True

    for recent in recent_dispatched:
        recent_time = recent.dispatched_at or recent.created_at
        if recent_time < cutoff:
            continue
        recent_keys = set(recent.symbols) or set(recent.entities)
        if signal_keys.intersection(recent_keys):
            return False
    return True


def enforce_run_interrupt_budget(
    signals: list[MonitorSignal],
    max_per_run: int = 3,
) -> list[MonitorSignal]:
    used = 0
    budgeted: list[MonitorSignal] = []
    for signal in signals:
        if signal.level is not SignalLevel.INTERRUPT:
            budgeted.append(signal)
            continue
        if used < max_per_run:
            used += 1
            budgeted.append(signal)
            continue
        signal.level = SignalLevel.DIGEST_CANDIDATE
        signal.suppressed_reason = "run_budget_exceeded"
        budgeted.append(signal)
    return budgeted
