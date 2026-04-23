from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from ..alerts.close import CloseAlertService
from ..alerts.intraday import IntradayAlertService
from ..briefs.composer import DailyBriefComposer
from ..briefs.render_card import DailyBriefCardRenderer
from ..briefs.render_trend import TrendChartRenderer
from ..config import load_runtime_settings
from ..market.provider import create_market_provider
from ..pipeline import NewsPipeline
from ..routing.dispatcher import TelegramDispatcher
from ..scheduling.calendar import NYSECalendar
from ..state.store import create_state_store


def run_daily_brief(report_date_sh: date | None = None):
    settings = load_runtime_settings()
    provider = create_market_provider(settings)
    store = create_state_store(settings)
    calendar = NYSECalendar(settings)
    dispatcher = TelegramDispatcher(settings)
    pipeline = NewsPipeline()
    composer = DailyBriefComposer(
        settings=settings,
        pipeline=pipeline,
        market_provider=provider,
        state_store=store,
        calendar=calendar,
    )
    brief = composer.compose(report_date_sh=report_date_sh)
    card_renderer = DailyBriefCardRenderer(settings)
    trend_renderer = TrendChartRenderer(settings, provider)
    card_path = card_renderer.render(brief)
    trend_paths = trend_renderer.render(
        brief_date=brief.brief_date_sh.isoformat(),
        symbols=brief.chart_symbols,
    )
    dispatcher.send_daily_brief(brief, card_path=card_path, trend_paths=trend_paths)
    composer.persist(
        brief,
        chart_paths=[str(card_path), *[str(path) for path in trend_paths]],
        published_at=datetime.now(tz=ZoneInfo(settings.brief_timezone)),
    )
    return brief


def run_intraday_scan(now: datetime | None = None):
    settings = load_runtime_settings()
    provider = create_market_provider(settings)
    store = create_state_store(settings)
    calendar = NYSECalendar(settings)
    dispatcher = TelegramDispatcher(settings)
    service = IntradayAlertService(
        settings=settings,
        provider=provider,
        state_store=store,
        calendar=calendar,
        dispatcher=dispatcher,
    )
    return service.run(now=now)


def run_close_alert(now: datetime | None = None):
    settings = load_runtime_settings()
    provider = create_market_provider(settings)
    store = create_state_store(settings)
    calendar = NYSECalendar(settings)
    dispatcher = TelegramDispatcher(settings)
    service = CloseAlertService(
        settings=settings,
        provider=provider,
        state_store=store,
        calendar=calendar,
        dispatcher=dispatcher,
    )
    return service.run(now=now)
