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

TWELVEDATA_ENDPOINT = "https://api.twelvedata.com/time_series"
INTERVAL_MAP = {
    "15m": "15min",
    "1d": "1day",
}


class TwelveDataProvider:
    def __init__(self, settings: RuntimeSettings) -> None:
        if not settings.twelvedata_api_key:
            raise ValueError("TWELVEDATA_API_KEY is required when MARKET_PROVIDER=twelvedata")

        self.settings = settings
        self._market_tz = ZoneInfo(settings.market_timezone)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "daily-news/1.0 (+https://github.com/M-Schuyler/Schuyler-tech-digest)"
                )
            }
        )
        self._batch_cache: dict[tuple[str, int, tuple[str, ...]], dict[str, list[MarketBar]]] = {}

    def get_recent_bars_batch(
        self,
        symbols: Sequence[str],
        interval: str,
        lookback_days: int,
    ) -> dict[str, list[MarketBar]]:
        normalized_symbols = tuple(
            dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip())
        )
        if not normalized_symbols:
            return {}

        batch = self._load_batch(
            symbols=normalized_symbols,
            interval=interval,
            lookback_days=lookback_days,
        )
        return {symbol: list(batch.get(symbol, [])) for symbol in normalized_symbols}

    def get_intraday_bars(self, symbol: str, lookback_days: int = 10) -> list[MarketBar]:
        return self.get_recent_bars(symbol, interval="15m", lookback_days=lookback_days)

    def get_daily_bars(self, symbol: str, lookback_days: int = 30) -> list[MarketBar]:
        return self.get_recent_bars(symbol, interval="1d", lookback_days=lookback_days)

    def get_recent_bars(self, symbol: str, interval: str, lookback_days: int) -> list[MarketBar]:
        batch = self.get_recent_bars_batch((symbol,), interval=interval, lookback_days=lookback_days)
        return list(batch.get(symbol, []))

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

    def _load_batch(
        self,
        *,
        symbols: Sequence[str],
        interval: str,
        lookback_days: int,
    ) -> dict[str, list[MarketBar]]:
        cache_key = (interval, lookback_days, tuple(symbols))
        cached = self._batch_cache.get(cache_key)
        if cached is not None:
            return cached

        batch = self._fetch_batch(symbols=symbols, interval=interval, lookback_days=lookback_days)
        self._batch_cache[cache_key] = batch
        return batch

    def _fetch_batch(
        self,
        *,
        symbols: Sequence[str],
        interval: str,
        lookback_days: int,
    ) -> dict[str, list[MarketBar]]:
        td_interval = INTERVAL_MAP.get(interval, interval)
        params = {
            "apikey": self.settings.twelvedata_api_key,
            "symbol": ",".join(self._provider_symbol(symbol) for symbol in symbols),
            "interval": td_interval,
            "outputsize": str(self._output_size(interval, lookback_days)),
            "format": "JSON",
        }
        payload: dict[str, object] | None = None
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = self._session.get(TWELVEDATA_ENDPOINT, params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(0.75 * (attempt + 1))

        if payload is None:
            logger.warning(
                "Twelve Data request failed interval=%s lookback_days=%s: %s",
                interval,
                lookback_days,
                last_error,
            )
            return {}

        if payload.get("status") == "error":
            logger.warning(
                "Twelve Data returned error for interval=%s lookback_days=%s: %s",
                interval,
                lookback_days,
                payload.get("message") or payload,
            )
            return {}

        parsed: dict[str, list[MarketBar]] = {}
        for key, item in payload.items():
            if not isinstance(item, dict):
                continue
            series_payload = item.get("data") if isinstance(item.get("data"), dict) else item
            if not isinstance(series_payload, dict) or "values" not in series_payload:
                continue

            meta = series_payload.get("meta") or {}
            raw_symbol = str(meta.get("symbol") or key)
            internal_symbol = self._internal_symbol(raw_symbol)
            if internal_symbol not in symbols:
                continue
            parsed[internal_symbol] = self._parse_series(internal_symbol, series_payload, interval)

        return parsed

    def _parse_series(
        self,
        symbol: str,
        series_payload: dict[str, object],
        requested_interval: str,
    ) -> list[MarketBar]:
        meta = series_payload.get("meta") or {}
        values = series_payload.get("values") or []
        if not isinstance(values, list):
            return []

        timezone_name = str(meta.get("exchange_timezone") or "UTC")
        try:
            source_tz = ZoneInfo(timezone_name)
        except Exception:
            source_tz = ZoneInfo("UTC")

        bars: list[MarketBar] = []
        for item in values:
            if not isinstance(item, dict):
                continue
            raw_dt = item.get("datetime")
            raw_open = item.get("open")
            raw_high = item.get("high")
            raw_low = item.get("low")
            raw_close = item.get("close")
            if not raw_dt or raw_open is None or raw_high is None or raw_low is None or raw_close is None:
                continue

            ts_source = datetime.fromisoformat(str(raw_dt).replace(" ", "T"))
            if ts_source.tzinfo is None:
                ts_source = ts_source.replace(tzinfo=source_tz)
            ts_ny = ts_source.astimezone(self._market_tz)

            raw_volume = item.get("volume")
            bars.append(
                MarketBar(
                    symbol=symbol,
                    ts_ny=ts_ny,
                    open=float(raw_open),
                    high=float(raw_high),
                    low=float(raw_low),
                    close=float(raw_close),
                    volume=float(raw_volume) if raw_volume not in (None, "") else None,
                    interval=requested_interval,
                    source="twelvedata",
                )
            )

        return sorted(bars, key=lambda bar: bar.ts_ny)

    def _provider_symbol(self, symbol: str) -> str:
        profile = get_symbol_profile(symbol)
        if profile.bucket == "crypto":
            return f"{symbol}/USD"
        return symbol

    def _internal_symbol(self, provider_symbol: str) -> str:
        normalized = provider_symbol.strip().upper()
        if normalized.endswith("/USD"):
            return normalized.split("/", 1)[0]
        return normalized.split(":")[-1]

    def _output_size(self, interval: str, lookback_days: int) -> int:
        if interval == "1d":
            return max(lookback_days + 5, 30)

        max_points_per_day = 96
        return max(lookback_days * max_points_per_day, 600)
