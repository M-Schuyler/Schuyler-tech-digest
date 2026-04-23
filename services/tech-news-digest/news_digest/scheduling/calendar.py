from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

from ..config import RuntimeSettings


@dataclass(frozen=True)
class ScheduleWindow:
    now_ny: datetime
    is_trading_day: bool
    intraday_open: bool
    close_window_open: bool


class NYSECalendar:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.market_tz = ZoneInfo(settings.market_timezone)
        self.brief_tz = ZoneInfo(settings.brief_timezone)
        self._calendar = mcal.get_calendar("NYSE")

    def now_ny(self, now: datetime | None = None) -> datetime:
        moment = now or datetime.now(tz=self.market_tz)
        return moment.astimezone(self.market_tz)

    def is_trading_day(self, day: date) -> bool:
        schedule = self._calendar.schedule(start_date=day, end_date=day)
        return not schedule.empty

    def is_intraday_window(self, now: datetime | None = None) -> bool:
        moment = self.now_ny(now)
        if not self.is_trading_day(moment.date()):
            return False
        current_time = moment.timetz().replace(tzinfo=None)
        return self.settings.intraday_start_ny <= current_time <= self.settings.intraday_end_ny

    def is_close_alert_window(self, now: datetime | None = None, tolerance_minutes: int = 10) -> bool:
        moment = self.now_ny(now)
        if not self.is_trading_day(moment.date()):
            return False
        close_dt = datetime.combine(moment.date(), self.settings.close_alert_time_ny, tzinfo=self.market_tz)
        delta = abs(moment - close_dt)
        return delta <= timedelta(minutes=tolerance_minutes)

    def previous_trading_day(self, day: date) -> date:
        probe = day
        while not self.is_trading_day(probe):
            probe -= timedelta(days=1)
        return probe

    def reference_trade_date_for_brief(self, brief_date_sh: date) -> date:
        candidate = brief_date_sh - timedelta(days=1)
        return self.previous_trading_day(candidate)

    def describe(self, now: datetime | None = None) -> ScheduleWindow:
        moment = self.now_ny(now)
        return ScheduleWindow(
            now_ny=moment,
            is_trading_day=self.is_trading_day(moment.date()),
            intraday_open=self.is_intraday_window(moment),
            close_window_open=self.is_close_alert_window(moment),
        )
