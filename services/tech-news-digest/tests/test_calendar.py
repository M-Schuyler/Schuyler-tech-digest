from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from news_digest.config import load_runtime_settings
from news_digest.scheduling.calendar import NYSECalendar


NY = ZoneInfo("America/New_York")


def test_reference_trade_date_for_monday_brief_jumps_to_previous_friday(monkeypatch) -> None:
    monkeypatch.delenv("STATE_DB_URL", raising=False)
    settings = load_runtime_settings()
    calendar = NYSECalendar(settings)

    reference = calendar.reference_trade_date_for_brief(date(2026, 4, 27))

    assert reference == date(2026, 4, 24)


def test_intraday_window_respects_trading_day() -> None:
    settings = load_runtime_settings()
    calendar = NYSECalendar(settings)

    trading_moment = datetime(2026, 4, 22, 10, 0, tzinfo=NY)
    weekend_moment = datetime(2026, 4, 25, 10, 0, tzinfo=NY)

    assert calendar.is_intraday_window(trading_moment) is True
    assert calendar.is_intraday_window(weekend_moment) is False


def test_close_alert_window_tracks_new_york_wall_clock() -> None:
    settings = load_runtime_settings()
    calendar = NYSECalendar(settings)

    dst_moment = datetime(2026, 6, 1, 16, 30, tzinfo=NY)
    standard_moment = datetime(2026, 12, 1, 16, 30, tzinfo=NY)

    assert calendar.is_close_alert_window(dst_moment) is True
    assert calendar.is_close_alert_window(standard_moment) is True
