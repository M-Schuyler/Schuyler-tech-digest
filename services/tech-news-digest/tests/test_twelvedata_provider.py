from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from news_digest.config import load_runtime_settings
from news_digest.market.provider import create_market_provider


NY = ZoneInfo("America/New_York")


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def test_twelvedata_provider_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_PROVIDER", "twelvedata")
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)

    settings = load_runtime_settings()

    with pytest.raises(ValueError, match="TWELVEDATA_API_KEY"):
        create_market_provider(settings)


def test_twelvedata_provider_batches_symbols_and_caches_intraday_calls(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_PROVIDER", "twelvedata")
    monkeypatch.setenv("TWELVEDATA_API_KEY", "test-key")

    settings = load_runtime_settings()
    provider = create_market_provider(settings)

    calls: list[dict[str, str]] = []

    def fake_get(url: str, params: dict[str, str], timeout: int):
        calls.append({"url": url, **params, "timeout": str(timeout)})
        return FakeResponse(
            {
                "QQQ": {
                    "meta": {
                        "symbol": "QQQ",
                        "interval": "15min",
                        "exchange_timezone": "America/New_York",
                        "type": "ETF",
                    },
                    "values": [
                        {
                            "datetime": "2026-04-22 10:00:00",
                            "open": "100.0",
                            "high": "101.0",
                            "low": "99.8",
                            "close": "100.8",
                            "volume": "1200",
                        },
                        {
                            "datetime": "2026-04-22 09:45:00",
                            "open": "99.6",
                            "high": "100.2",
                            "low": "99.5",
                            "close": "100.0",
                            "volume": "1000",
                        },
                    ],
                    "status": "ok",
                },
                "BTC/USD": {
                    "meta": {
                        "symbol": "BTC/USD",
                        "interval": "15min",
                        "exchange_timezone": "UTC",
                        "type": "Digital Currency",
                    },
                    "values": [
                        {
                            "datetime": "2026-04-22 14:00:00",
                            "open": "88000.0",
                            "high": "88500.0",
                            "low": "87900.0",
                            "close": "88300.0",
                            "volume": "42",
                        },
                        {
                            "datetime": "2026-04-22 13:45:00",
                            "open": "87800.0",
                            "high": "88150.0",
                            "low": "87700.0",
                            "close": "88000.0",
                            "volume": "40",
                        },
                    ],
                    "status": "ok",
                },
            }
        )

    monkeypatch.setattr(provider._session, "get", fake_get)

    qqq_bars = provider.get_intraday_bars("QQQ", lookback_days=25)
    btc_bars = provider.get_intraday_bars("BTC", lookback_days=25)

    assert len(calls) == 1
    assert calls[0]["interval"] == "15min"
    assert calls[0]["apikey"] == "test-key"
    assert "QQQ" in calls[0]["symbol"]
    assert "BTC/USD" in calls[0]["symbol"]
    assert qqq_bars[-1].close == 100.8
    assert qqq_bars[-1].ts_ny.tzinfo == NY
    assert btc_bars[-1].symbol == "BTC"
    assert btc_bars[-1].ts_ny.tzinfo == NY
    assert btc_bars[-1].trading_date_ny == date(2026, 4, 22)
