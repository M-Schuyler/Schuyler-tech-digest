from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from news_digest.market.cooldown import AlertCooldownPolicy
from news_digest.models import AlertEvent


NY = ZoneInfo("America/New_York")


def make_event(
    symbol: str,
    *,
    minute_offset: int,
    kind: str,
    dispatched: bool = True,
) -> AlertEvent:
    base = datetime(2026, 4, 22, 10, 0, tzinfo=NY)
    moment = base + timedelta(minutes=minute_offset)
    return AlertEvent(
        symbol=symbol,
        window_start_ny=moment - timedelta(minutes=15),
        window_end_ny=moment,
        triggered_at_ny=moment,
        trading_date_ny=moment.date(),
        kind=kind,
        direction="up",
        magnitude_pct=2.0,
        reason=f"{kind} event",
        dispatched_at_ny=moment if dispatched else None,
    )


def test_extreme_punches_through_normal_cooldown() -> None:
    policy = AlertCooldownPolicy()
    previous = [make_event("NVDA", minute_offset=0, kind="normal")]
    candidate = make_event("NVDA", minute_offset=30, kind="extreme", dispatched=False)

    decision = policy.evaluate(candidate, previous)

    assert decision.allowed is True


def test_normal_is_suppressed_inside_extreme_cooldown() -> None:
    policy = AlertCooldownPolicy()
    previous = [make_event("NVDA", minute_offset=0, kind="extreme")]
    candidate = make_event("NVDA", minute_offset=20, kind="normal", dispatched=False)

    decision = policy.evaluate(candidate, previous)

    assert decision.allowed is False
    assert decision.suppressed_reason == "in_extreme_cooldown"


def test_daily_limit_is_global() -> None:
    policy = AlertCooldownPolicy(max_daily_alerts=5)
    previous = [
        make_event("QQQ", minute_offset=0, kind="extreme"),
        make_event("SPY", minute_offset=30, kind="extreme"),
        make_event("NVDA", minute_offset=60, kind="aggregated"),
        make_event("AAPL", minute_offset=90, kind="extreme"),
        make_event("BTC", minute_offset=120, kind="aggregated"),
    ]
    candidate = make_event("ETH", minute_offset=150, kind="extreme", dispatched=False)

    decision = policy.evaluate(candidate, previous)

    assert decision.allowed is False
    assert decision.suppressed_reason == "daily_limit_reached"


def test_aggregate_still_counts_as_one_dispatched_event() -> None:
    policy = AlertCooldownPolicy(max_daily_alerts=5)
    previous = [
        make_event("QQQ", minute_offset=0, kind="extreme"),
        make_event("SPY", minute_offset=30, kind="extreme"),
        make_event("NVDA", minute_offset=60, kind="aggregated"),
        make_event("AAPL", minute_offset=90, kind="extreme"),
    ]
    candidate = make_event("MSFT", minute_offset=120, kind="aggregated", dispatched=False)

    decision = policy.evaluate(candidate, previous)

    assert decision.allowed is True
