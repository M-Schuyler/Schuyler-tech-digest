from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
import time
from zoneinfo import ZoneInfo

import requests

from ..config import RuntimeSettings, get_symbol_profile
from ..models import MarketBar

logger = logging.getLogger(__name__)

YAHOO_CHART_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_CHART_FALLBACK_ENDPOINT = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"


class YahooProvider:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._market_tz = ZoneInfo(settings.market_timezone)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
        )

    def get_recent_bars_batch(
        self,
        symbols: Sequence[str],
        interval: str,
        lookback_days: int,
    ) -> dict[str, list[MarketBar]]:
        return {
            symbol: self.get_recent_bars(symbol, interval=interval, lookback_days=lookback_days)
            for symbol in symbols
        }

    def get_intraday_bars(self, symbol: str, lookback_days: int = 10) -> list[MarketBar]:
        return self.get_recent_bars(symbol, interval="15m", lookback_days=lookback_days)

    def get_daily_bars(self, symbol: str, lookback_days: int = 30) -> list[MarketBar]:
        range_hint = f"{max(lookback_days, 5)}d"
        return self._fetch_bars(symbol, interval="1d", range_hint=range_hint)

    def get_recent_bars(self, symbol: str, interval: str, lookback_days: int) -> list[MarketBar]:
        range_hint = f"{max(lookback_days, 1)}d"
        return self._fetch_bars(symbol, interval=interval, range_hint=range_hint)

    def compute_volume_baseline(
        self,
        symbol: str,
        bars: Sequence[MarketBar],
        lookback_days: int = 20,
    ) -> float | None:
        profile = get_symbol_profile(symbol)
        if profile.bucket == "crypto":
            return None

        usable = sorted([bar for bar in bars if bar.volume is not None], key=lambda bar: bar.ts_ny)
        if len(usable) < 3:
            return None

        current_slot = usable[-1].ts_ny.strftime("%H:%M")
        current_trade_date = usable[-1].trading_date_ny
        slot_samples: dict[str, float] = {}

        for bar in reversed(usable[:-1]):
            if bar.trading_date_ny >= current_trade_date:
                continue
            if bar.ts_ny.strftime("%H:%M") != current_slot:
                continue
            slot_key = bar.trading_date_ny.isoformat()
            if slot_key in slot_samples:
                continue
            slot_samples[slot_key] = float(bar.volume or 0.0)
            if len(slot_samples) >= lookback_days:
                break

        if len(slot_samples) < 10:
            return None

        return sum(slot_samples.values()) / len(slot_samples)

    def _fetch_bars(self, symbol: str, interval: str, range_hint: str) -> list[MarketBar]:
        profile = get_symbol_profile(symbol)
        params = {
            "interval": interval,
            "range": range_hint,
            "includePrePost": "false",
            "events": "div,splits",
        }
        payload = None
        last_error: Exception | None = None

        for endpoint in (YAHOO_CHART_ENDPOINT, YAHOO_CHART_FALLBACK_ENDPOINT):
            url = endpoint.format(symbol=profile.yahoo_symbol)
            for attempt in range(3):
                try:
                    response = self._session.get(url, params=params, timeout=30)
                    if response.status_code == 429:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    break
                except requests.RequestException as exc:
                    last_error = exc
                    time.sleep(0.75 * (attempt + 1))
            if payload is not None:
                break

        if payload is None:
            logger.warning(
                "Yahoo request failed for %s interval=%s range=%s: %s",
                symbol,
                interval,
                range_hint,
                last_error,
            )
            return []

        chart = (payload.get("chart") or {}).get("result") or []
        if not chart:
            logger.warning("Yahoo returned no chart payload for %s", symbol)
            return []

        result = chart[0]
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        bars: list[MarketBar] = []
        for idx, raw_ts in enumerate(timestamps):
            if idx >= len(opens) or idx >= len(highs) or idx >= len(lows) or idx >= len(closes):
                continue
            raw_open = opens[idx]
            raw_high = highs[idx]
            raw_low = lows[idx]
            raw_close = closes[idx]
            if raw_open is None or raw_high is None or raw_low is None or raw_close is None:
                continue

            ts_ny = datetime.fromtimestamp(raw_ts, tz=ZoneInfo("UTC")).astimezone(self._market_tz)
            volume = volumes[idx] if idx < len(volumes) else None
            bars.append(
                MarketBar(
                    symbol=symbol,
                    ts_ny=ts_ny,
                    open=float(raw_open),
                    high=float(raw_high),
                    low=float(raw_low),
                    close=float(raw_close),
                    volume=float(volume) if volume is not None else None,
                    interval=interval,
                    source="yahoo",
                )
            )

        return sorted(bars, key=lambda bar: bar.ts_ny)
