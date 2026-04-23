from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..config import RuntimeSettings
from ..models import MarketBar


class MarketProvider(Protocol):
    def get_intraday_bars(self, symbol: str, lookback_days: int = 10) -> list[MarketBar]:
        ...

    def get_daily_bars(self, symbol: str, lookback_days: int = 30) -> list[MarketBar]:
        ...

    def get_recent_bars(self, symbol: str, interval: str, lookback_days: int) -> list[MarketBar]:
        ...

    def compute_volume_baseline(
        self,
        symbol: str,
        bars: Sequence[MarketBar],
        lookback_days: int = 20,
    ) -> float | None:
        ...


def create_market_provider(settings: RuntimeSettings) -> MarketProvider:
    if settings.market_provider == "yahoo":
        from .yahoo_provider import YahooProvider

        return YahooProvider(settings)

    if settings.market_provider == "twelvedata":
        from .twelvedata_provider import TwelveDataProvider

        return TwelveDataProvider(settings)

    raise ValueError(f"Unsupported MARKET_PROVIDER: {settings.market_provider}")
