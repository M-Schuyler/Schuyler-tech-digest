from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import timedelta

from ..config import CRYPTO_SYMBOLS, INDEX_SYMBOLS, MARKET_SYMBOLS, TECH_STOCK_SYMBOLS
from ..models import AlertEvent, MarketBar

EXTREME_THRESHOLDS = {
    "index": {"fifteen_min": 1.2, "daily": 2.0},
    "tech_stock": {"fifteen_min": 2.0, "daily": 4.0},
    "crypto": {"fifteen_min": 2.5, "hour": 4.0},
}
NORMAL_THRESHOLDS = {
    "index": 0.8,
    "tech_stock": 1.2,
    "crypto": 1.8,
}


def classify_extreme(
    symbol: str,
    bars: Sequence[MarketBar],
    volume_baseline: float | None = None,
    volume_multiplier: float = 1.8,
) -> AlertEvent | None:
    ordered = sorted(bars, key=lambda bar: bar.ts_ny)
    if len(ordered) < 2:
        return None

    bucket = MARKET_SYMBOLS[symbol].bucket
    latest = ordered[-1]
    previous = ordered[-2]
    fifteen_min_pct = pct_change(latest.close, previous.close)
    day_change_pct = intraday_change_pct(ordered)
    direction = direction_for_change(fifteen_min_pct or day_change_pct)

    if abs(fifteen_min_pct) >= EXTREME_THRESHOLDS[bucket]["fifteen_min"]:
        return build_event(
            symbol=symbol,
            kind="extreme",
            direction=direction,
            magnitude_pct=fifteen_min_pct,
            latest=latest,
            reason=f"15m change reached {fifteen_min_pct:.2f}%",
            metadata={"trigger": "fifteen_min"},
        )

    if bucket == "crypto":
        hour_change = hourly_change_pct(ordered)
        if hour_change is not None and abs(hour_change) >= EXTREME_THRESHOLDS[bucket]["hour"]:
            return build_event(
                symbol=symbol,
                kind="extreme",
                direction=direction_for_change(hour_change),
                magnitude_pct=hour_change,
                latest=latest,
                reason=f"1h change reached {hour_change:.2f}%",
                metadata={"trigger": "hour"},
            )
        return None

    volume_ratio = None
    if volume_baseline and latest.volume is not None and volume_baseline > 0:
        volume_ratio = latest.volume / volume_baseline

    if (
        volume_ratio is not None
        and volume_ratio >= volume_multiplier
        and abs(day_change_pct) >= EXTREME_THRESHOLDS[bucket]["daily"]
    ):
        return build_event(
            symbol=symbol,
            kind="extreme",
            direction=direction_for_change(day_change_pct),
            magnitude_pct=day_change_pct,
            latest=latest,
            reason=(
                f"Daily change reached {day_change_pct:.2f}% with "
                f"volume ratio {volume_ratio:.2f}x"
            ),
            metadata={"trigger": "daily_with_volume", "volume_ratio": round(volume_ratio, 4)},
        )

    return None


def classify_normal(symbol: str, bars: Sequence[MarketBar]) -> AlertEvent | None:
    ordered = sorted(bars, key=lambda bar: bar.ts_ny)
    if len(ordered) < 2:
        return None

    latest = ordered[-1]
    previous = ordered[-2]
    change_pct = pct_change(latest.close, previous.close)
    bucket = MARKET_SYMBOLS[symbol].bucket
    threshold = NORMAL_THRESHOLDS[bucket]
    if abs(change_pct) < threshold:
        return None

    return build_event(
        symbol=symbol,
        kind="normal",
        direction=direction_for_change(change_pct),
        magnitude_pct=change_pct,
        latest=latest,
        reason=f"15m change crossed normal threshold at {change_pct:.2f}%",
        metadata={"trigger": "normal_threshold"},
    )


def aggregate_normals(
    current_window: Sequence[AlertEvent],
    previous_window: Sequence[AlertEvent] | None = None,
) -> AlertEvent | None:
    current = [event for event in current_window if event.kind == "normal" and event.suppressed_reason is None]
    if not current:
        return None

    previous = previous_window or []
    by_symbol = {event.symbol: event for event in current}
    direction = current[0].direction
    same_direction = [event for event in current if event.direction == direction]

    reasons: list[str] = []
    if len(current) >= 2:
        reasons.append("multiple_symbols")

    if _has_continuation(current, previous):
        reasons.append("two_window_continuation")

    if _has_market_resonance(same_direction):
        reasons.append("market_resonance")

    if not reasons:
        return None

    anchor = sorted(current, key=lambda item: abs(item.magnitude_pct), reverse=True)[0]
    related = tuple(symbol for symbol in by_symbol if symbol != anchor.symbol)
    return AlertEvent(
        symbol=anchor.symbol,
        related_symbols=related,
        window_start_ny=anchor.window_start_ny,
        window_end_ny=anchor.window_end_ny,
        triggered_at_ny=anchor.triggered_at_ny,
        trading_date_ny=anchor.trading_date_ny,
        kind="aggregated",
        direction=anchor.direction,
        magnitude_pct=anchor.magnitude_pct,
        reason=f"Aggregated window trigger: {', '.join(reasons)}",
        metadata={"reasons": reasons, "symbols": sorted(by_symbol)},
    )


def pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def intraday_change_pct(bars: Sequence[MarketBar]) -> float:
    if not bars:
        return 0.0

    latest = bars[-1]
    same_day = [bar for bar in bars if bar.trading_date_ny == latest.trading_date_ny]
    if not same_day:
        return 0.0

    first_bar = same_day[0]
    return pct_change(latest.close, first_bar.open)


def hourly_change_pct(bars: Sequence[MarketBar]) -> float | None:
    if len(bars) < 5:
        return None
    latest = bars[-1]
    comparison = bars[-5]
    if latest.ts_ny - comparison.ts_ny < timedelta(minutes=45):
        return None
    return pct_change(latest.close, comparison.close)


def direction_for_change(change_pct: float) -> str:
    return "up" if change_pct >= 0 else "down"


def build_event(
    *,
    symbol: str,
    kind: str,
    direction: str,
    magnitude_pct: float,
    latest: MarketBar,
    reason: str,
    metadata: dict[str, object] | None = None,
) -> AlertEvent:
    return AlertEvent(
        symbol=symbol,
        window_start_ny=latest.ts_ny - timedelta(minutes=15),
        window_end_ny=latest.ts_ny,
        triggered_at_ny=latest.ts_ny,
        trading_date_ny=latest.trading_date_ny,
        kind=kind,
        direction=direction,
        magnitude_pct=magnitude_pct,
        reason=reason,
        metadata=metadata or {},
    )


def _has_continuation(current: Sequence[AlertEvent], previous: Sequence[AlertEvent]) -> bool:
    prev_map = {(event.symbol, event.direction) for event in previous if event.kind == "normal"}
    return any((event.symbol, event.direction) in prev_map for event in current)


def _has_market_resonance(current: Sequence[AlertEvent]) -> bool:
    symbols = [event.symbol for event in current]
    counts = Counter(
        "index"
        if symbol in INDEX_SYMBOLS
        else "tech_stock"
        if symbol in TECH_STOCK_SYMBOLS
        else "crypto"
        for symbol in symbols
    )
    if counts["index"] >= 1 and counts["tech_stock"] >= 2:
        return True
    if counts["index"] >= 1 and counts["crypto"] >= 1:
        return True
    return False
