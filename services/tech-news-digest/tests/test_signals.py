from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from news_digest.market.signals import aggregate_normals, classify_extreme, classify_normal
from news_digest.models import AlertEvent, MarketBar


NY = ZoneInfo("America/New_York")


def make_bar(
    symbol: str,
    *,
    minute_offset: int,
    close: float,
    open_price: float | None = None,
    volume: float | None = None,
    base: datetime | None = None,
) -> MarketBar:
    start = base or datetime(2026, 4, 22, 9, 30, tzinfo=NY)
    ts = start + timedelta(minutes=minute_offset)
    opening = open_price if open_price is not None else close
    return MarketBar(
        symbol=symbol,
        ts_ny=ts,
        open=opening,
        high=max(opening, close),
        low=min(opening, close),
        close=close,
        volume=volume,
    )


def test_index_extreme_on_15_min_threshold() -> None:
    bars = [
        make_bar("QQQ", minute_offset=0, close=100.0, open_price=100.0, volume=1000),
        make_bar("QQQ", minute_offset=15, close=101.3, open_price=100.1, volume=1200),
    ]

    event = classify_extreme("QQQ", bars, volume_baseline=800)

    assert event is not None
    assert event.kind == "extreme"
    assert event.direction == "up"
    assert event.metadata["trigger"] == "fifteen_min"


def test_stock_extreme_on_daily_move_with_volume() -> None:
    base = datetime(2026, 4, 22, 9, 30, tzinfo=NY)
    bars = [
        make_bar("NVDA", minute_offset=0, close=100.0, open_price=100.0, volume=1000, base=base),
        make_bar("NVDA", minute_offset=15, close=101.3, open_price=100.5, volume=1100, base=base),
        make_bar("NVDA", minute_offset=30, close=102.6, open_price=101.7, volume=1500, base=base),
        make_bar("NVDA", minute_offset=45, close=104.2, open_price=103.2, volume=2500, base=base),
    ]

    event = classify_extreme("NVDA", bars, volume_baseline=1000)

    assert event is not None
    assert event.kind == "extreme"
    assert event.metadata["trigger"] == "daily_with_volume"


def test_crypto_extreme_on_hour_move() -> None:
    base = datetime(2026, 4, 22, 9, 30, tzinfo=NY)
    bars = [
        make_bar("BTC", minute_offset=0, close=100.0, open_price=100.0, base=base),
        make_bar("BTC", minute_offset=15, close=100.8, open_price=100.1, base=base),
        make_bar("BTC", minute_offset=30, close=101.6, open_price=100.9, base=base),
        make_bar("BTC", minute_offset=45, close=102.4, open_price=101.7, base=base),
        make_bar("BTC", minute_offset=60, close=104.1, open_price=103.0, base=base),
    ]

    event = classify_extreme("BTC", bars)

    assert event is not None
    assert event.metadata["trigger"] == "hour"


def test_volume_branch_degrades_when_baseline_missing() -> None:
    base = datetime(2026, 4, 22, 9, 30, tzinfo=NY)
    bars = [
        make_bar("AMD", minute_offset=0, close=100.0, open_price=100.0, volume=1000, base=base),
        make_bar("AMD", minute_offset=15, close=101.5, open_price=100.6, volume=1300, base=base),
        make_bar("AMD", minute_offset=30, close=103.0, open_price=101.8, volume=1600, base=base),
        make_bar("AMD", minute_offset=45, close=104.6, open_price=103.4, volume=2200, base=base),
    ]

    event = classify_extreme("AMD", bars, volume_baseline=None)

    assert event is None


def test_normal_threshold_and_resonance_aggregation() -> None:
    qqq_bars = [
        make_bar("QQQ", minute_offset=0, close=100.0, open_price=100.0, volume=900),
        make_bar("QQQ", minute_offset=15, close=100.9, open_price=100.1, volume=950),
    ]
    nvda_bars = [
        make_bar("NVDA", minute_offset=0, close=100.0, open_price=100.0, volume=1200),
        make_bar("NVDA", minute_offset=15, close=101.5, open_price=100.7, volume=1500),
    ]
    msft_bars = [
        make_bar("MSFT", minute_offset=0, close=100.0, open_price=100.0, volume=1100),
        make_bar("MSFT", minute_offset=15, close=101.6, open_price=100.4, volume=1350),
    ]

    current = [
        classify_normal("QQQ", qqq_bars),
        classify_normal("NVDA", nvda_bars),
        classify_normal("MSFT", msft_bars),
    ]
    current = [event for event in current if event is not None]

    aggregated = aggregate_normals(current)

    assert aggregated is not None
    assert aggregated.kind == "aggregated"
    assert "market_resonance" in aggregated.metadata["reasons"]
    assert set(aggregated.metadata["symbols"]) == {"QQQ", "NVDA", "MSFT"}


def test_two_window_continuation_aggregates_single_symbol() -> None:
    previous = [
        AlertEvent(
            symbol="ETH",
            window_start_ny=datetime(2026, 4, 22, 10, 0, tzinfo=NY),
            window_end_ny=datetime(2026, 4, 22, 10, 15, tzinfo=NY),
            triggered_at_ny=datetime(2026, 4, 22, 10, 15, tzinfo=NY),
            trading_date_ny=datetime(2026, 4, 22, 10, 15, tzinfo=NY).date(),
            kind="normal",
            direction="up",
            magnitude_pct=1.9,
            reason="prior normal",
        )
    ]
    current = [
        AlertEvent(
            symbol="ETH",
            window_start_ny=datetime(2026, 4, 22, 10, 15, tzinfo=NY),
            window_end_ny=datetime(2026, 4, 22, 10, 30, tzinfo=NY),
            triggered_at_ny=datetime(2026, 4, 22, 10, 30, tzinfo=NY),
            trading_date_ny=datetime(2026, 4, 22, 10, 30, tzinfo=NY).date(),
            kind="normal",
            direction="up",
            magnitude_pct=2.0,
            reason="current normal",
        )
    ]

    aggregated = aggregate_normals(current, previous)

    assert aggregated is not None
    assert "two_window_continuation" in aggregated.metadata["reasons"]
