from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from news_digest.alerts.close import CloseAlertService
from news_digest.alerts.intraday import IntradayAlertService
from news_digest.config import load_runtime_settings
from news_digest.market.symbol_scope import pick_symbol_scope
from news_digest.models import BriefRecord, MarketBar, WatchSignal
from news_digest.scheduling.calendar import NYSECalendar
from news_digest.state.store import StateStore


NY = ZoneInfo("America/New_York")


class FakeDispatcher:
    def __init__(self) -> None:
        self.intraday_events = []
        self.close_summaries = []

    def send_intraday_alert(self, event, *, card_path: Path, text: str) -> None:
        self.intraday_events.append((event, card_path, text))

    def send_close_summary(self, summary, *, card_path: Path, text: str) -> None:
        self.close_summaries.append((summary, card_path, text))


class FakeIntradayProvider:
    def __init__(self) -> None:
        self.requested_batches: list[tuple[str, ...]] = []

    def get_recent_bars_batch(self, symbols, interval: str, lookback_days: int):
        normalized = tuple(symbols)
        self.requested_batches.append(normalized)
        window_end = datetime(2026, 4, 23, 10, 0, tzinfo=NY)
        window_start = window_end - timedelta(minutes=15)
        return {
            symbol: [
                MarketBar(
                    symbol=symbol,
                    ts_ny=window_start,
                    open=100.0,
                    high=100.2,
                    low=99.8,
                    close=100.0,
                    volume=1000,
                ),
                MarketBar(
                    symbol=symbol,
                    ts_ny=window_end,
                    open=100.0,
                    high=100.1,
                    low=99.9,
                    close=100.05,
                    volume=1100,
                ),
            ]
            for symbol in normalized
        }

    def get_intraday_bars(self, symbol: str, lookback_days: int = 10):
        return self.get_recent_bars_batch((symbol,), interval="15m", lookback_days=lookback_days).get(symbol, [])

    def get_daily_bars(self, symbol: str, lookback_days: int = 30):
        return []

    def get_recent_bars(self, symbol: str, interval: str, lookback_days: int):
        return self.get_recent_bars_batch((symbol,), interval=interval, lookback_days=lookback_days).get(symbol, [])

    def compute_volume_baseline(self, symbol: str, bars, lookback_days: int = 20):
        return None


class FailingCloseProvider:
    def get_intraday_bars(self, symbol: str, lookback_days: int = 10):
        raise AssertionError("Close summary should reuse stored market bars before hitting provider")

    def get_daily_bars(self, symbol: str, lookback_days: int = 30):
        raise AssertionError("Close summary should not need fresh daily market bars")

    def get_recent_bars(self, symbol: str, interval: str, lookback_days: int):
        raise AssertionError("Close summary should not issue ad-hoc market fetches")

    def get_recent_bars_batch(self, symbols, interval: str, lookback_days: int):
        raise AssertionError("Close summary should not batch-fetch market bars")

    def compute_volume_baseline(self, symbol: str, bars, lookback_days: int = 20):
        return None


def test_pick_symbol_scope_respects_budget_and_prioritized_watchlist() -> None:
    scoped = pick_symbol_scope(budget=3, prioritized=("TSLA",))

    assert scoped == ("TSLA", "QQQ", "NVDA")


def test_intraday_scan_limits_requested_symbols_to_budget(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MARKET_SYMBOL_BUDGET", "3")
    settings = load_runtime_settings()
    store = StateStore(sqlite_path=tmp_path / "state.db", market_timezone=settings.market_timezone)
    store.record_brief(
        BriefRecord(
            brief_date_sh=date(2026, 4, 23),
            reference_trade_date_ny=date(2026, 4, 22),
            top_three=["AI主线仍在", "市场风险偏好回暖", "BTC继续强于ETH"],
            ai_section="AI",
            tech_section="Tech",
            market_section="Market",
            cross_section="Cross",
            watchlist=[WatchSignal(symbol="TSLA", reason="watchlist bump", priority=7)],
            chart_paths=[],
            generated_at=datetime(2026, 4, 23, 8, 0, tzinfo=ZoneInfo(settings.brief_timezone)),
        )
    )
    provider = FakeIntradayProvider()
    dispatcher = FakeDispatcher()
    service = IntradayAlertService(
        settings=settings,
        provider=provider,
        state_store=store,
        calendar=NYSECalendar(settings),
        dispatcher=dispatcher,
    )

    result = service.run(now=datetime(2026, 4, 23, 10, 0, tzinfo=NY))

    assert provider.requested_batches == [("TSLA", "QQQ", "NVDA")]
    assert result.evaluated_symbols == ["TSLA", "QQQ", "NVDA"]


def test_close_summary_reuses_stored_market_bars_before_provider(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MARKET_SYMBOL_BUDGET", "3")
    settings = load_runtime_settings()
    store = StateStore(sqlite_path=tmp_path / "state.db", market_timezone=settings.market_timezone)
    dispatcher = FakeDispatcher()
    service = CloseAlertService(
        settings=settings,
        provider=FailingCloseProvider(),
        state_store=store,
        calendar=NYSECalendar(settings),
        dispatcher=dispatcher,
    )

    close_time = datetime(2026, 4, 23, 16, 30, tzinfo=NY)
    qqq_open = datetime(2026, 4, 23, 9, 45, tzinfo=NY)
    qqq_close = datetime(2026, 4, 23, 16, 0, tzinfo=NY)
    store.upsert_market_bars(
        "QQQ",
        "15m",
        [
            MarketBar("QQQ", ts_ny=qqq_open, open=100.0, high=101.0, low=99.8, close=100.5, volume=1200),
            MarketBar("QQQ", ts_ny=qqq_close, open=100.5, high=102.0, low=100.2, close=101.8, volume=2400),
        ],
    )
    store.upsert_market_bars(
        "BTC",
        "15m",
        [
            MarketBar("BTC", ts_ny=qqq_open, open=90000.0, high=90500.0, low=89800.0, close=90200.0, volume=100),
            MarketBar("BTC", ts_ny=qqq_close, open=90200.0, high=91000.0, low=90100.0, close=90900.0, volume=120),
        ],
    )

    summary = service.run(now=close_time)

    assert summary is not None
    assert "QQQ" in summary.strongest_assets
    assert dispatcher.close_summaries
