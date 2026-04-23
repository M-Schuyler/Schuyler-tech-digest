from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from news_digest.models import AlertEvent, BriefRecord, MarketBar, WatchSignal
from news_digest.state.store import StateStore


NY = ZoneInfo("America/New_York")


def test_state_store_persists_alerts_briefs_and_market_bars(tmp_path) -> None:
    store = StateStore(sqlite_path=tmp_path / "state.db", market_timezone="America/New_York")
    moment = datetime(2026, 4, 22, 10, 15, tzinfo=NY)
    alert = AlertEvent(
        symbol="QQQ",
        window_start_ny=moment.replace(minute=0),
        window_end_ny=moment,
        triggered_at_ny=moment,
        trading_date_ny=moment.date(),
        kind="extreme",
        direction="up",
        magnitude_pct=1.3,
        reason="15m move",
        dispatched_at_ny=moment,
    )
    store.record_alert(alert)

    alerts = store.list_alerts(trade_date_ny=moment.date())
    assert len(alerts) == 1
    assert alerts[0].symbol == "QQQ"

    bars = [
        MarketBar("QQQ", ts_ny=moment, open=100.0, high=101.0, low=99.8, close=100.9, volume=1000),
    ]
    store.upsert_market_bars("QQQ", "15m", bars)
    stored_bars = store.list_market_bars(symbol="QQQ", interval="15m")
    assert len(stored_bars) == 1
    assert stored_bars[0].close == 100.9

    brief = BriefRecord(
        brief_date_sh=date(2026, 4, 23),
        reference_trade_date_ny=date(2026, 4, 22),
        top_three=["AI 仍是主线", "芯片链条继续升温", "BTC 风险偏好抬头"],
        ai_section="AI section",
        tech_section="Tech section",
        market_section="Market section",
        cross_section="Cross section",
        watchlist=[WatchSignal(symbol="NVDA", reason="chip follow-through", priority=10)],
        chart_paths=["/tmp/card.png"],
        generated_at=moment,
    )
    store.record_brief(brief)

    latest = store.get_latest_brief()
    assert latest is not None
    assert latest.reference_trade_date_ny == date(2026, 4, 22)
    assert latest.watchlist[0].symbol == "NVDA"
