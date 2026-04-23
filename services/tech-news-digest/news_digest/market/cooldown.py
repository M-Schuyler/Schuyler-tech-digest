from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from ..models import AlertEvent


@dataclass(frozen=True)
class CooldownDecision:
    allowed: bool
    suppressed_reason: str | None = None


class AlertCooldownPolicy:
    def __init__(
        self,
        *,
        extreme_cooldown_minutes: int = 45,
        normal_cooldown_minutes: int = 90,
        max_daily_alerts: int = 5,
    ) -> None:
        self.extreme_cooldown = timedelta(minutes=extreme_cooldown_minutes)
        self.normal_cooldown = timedelta(minutes=normal_cooldown_minutes)
        self.max_daily_alerts = max_daily_alerts

    def evaluate(
        self,
        candidate: AlertEvent,
        previous_events: Sequence[AlertEvent],
    ) -> CooldownDecision:
        if self._daily_limit_reached(candidate.trading_date_ny, previous_events):
            return CooldownDecision(False, "daily_limit_reached")

        if candidate.kind == "aggregated":
            return CooldownDecision(True, None)

        symbol_events = sorted(
            [event for event in previous_events if event.symbol == candidate.symbol and event.was_dispatched],
            key=lambda event: event.triggered_at_ny,
            reverse=True,
        )
        if not symbol_events:
            return CooldownDecision(True, None)

        latest_extreme = next((event for event in symbol_events if event.kind == "extreme"), None)
        if latest_extreme and candidate.triggered_at_ny - latest_extreme.triggered_at_ny < self.extreme_cooldown:
            if candidate.kind == "extreme":
                return CooldownDecision(False, "in_extreme_cooldown")
            return CooldownDecision(False, "in_extreme_cooldown")

        if candidate.kind == "extreme":
            return CooldownDecision(True, None)

        latest_normal = next(
            (
                event
                for event in symbol_events
                if event.kind in {"normal", "aggregated"} and candidate.symbol in event.symbols
            ),
            None,
        )
        if latest_normal and candidate.triggered_at_ny - latest_normal.triggered_at_ny < self.normal_cooldown:
            return CooldownDecision(False, "in_normal_cooldown")

        return CooldownDecision(True, None)

    def _daily_limit_reached(self, trade_date_ny: date, previous_events: Sequence[AlertEvent]) -> bool:
        dispatched = [
            event
            for event in previous_events
            if event.trading_date_ny == trade_date_ny and event.was_dispatched
        ]
        return len(dispatched) >= self.max_daily_alerts
