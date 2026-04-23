from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import RuntimeSettings
from ..market.cooldown import AlertCooldownPolicy
from ..market.provider import MarketProvider
from ..market.signals import aggregate_normals, classify_extreme, classify_normal
from ..market.symbol_scope import pick_symbol_scope
from ..models import AlertEvent, IntradayScanResult
from ..routing.dispatcher import TelegramDispatcher
from ..scheduling.calendar import NYSECalendar
from ..state.store import StateStore
from .render_alert_card import AlertCardRenderer


class IntradayAlertService:
    def __init__(
        self,
        *,
        settings: RuntimeSettings,
        provider: MarketProvider,
        state_store: StateStore,
        calendar: NYSECalendar,
        dispatcher: TelegramDispatcher,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.state_store = state_store
        self.calendar = calendar
        self.dispatcher = dispatcher
        self.policy = AlertCooldownPolicy(max_daily_alerts=settings.max_intraday_alerts_per_day)
        self.card_renderer = AlertCardRenderer(settings)
        self.market_tz = ZoneInfo(settings.market_timezone)

    def run(self, now: datetime | None = None) -> IntradayScanResult:
        moment = self.calendar.now_ny(now)
        if not self.calendar.is_intraday_window(moment):
            return IntradayScanResult(
                trade_date_ny=moment.date(),
                evaluated_symbols=[],
                dispatched_events=[],
                stored_events=[],
                skipped_reason="outside_intraday_window",
            )

        trade_date = moment.date()
        prior_events = self.state_store.list_alerts(trade_date_ny=trade_date)
        previous_window_normals = self.state_store.list_alerts(
            trade_date_ny=trade_date,
            kind="normal",
            since_ny=moment - timedelta(minutes=self.settings.intraday_interval_minutes * 2),
            until_ny=moment - timedelta(minutes=self.settings.intraday_interval_minutes),
            include_suppressed=True,
        )

        latest_brief = self.state_store.get_latest_brief()
        watchlist_symbols = {item.symbol for item in latest_brief.watchlist} if latest_brief else set()
        scoped_symbols = pick_symbol_scope(
            budget=self.settings.market_symbol_budget,
            prioritized=[item.symbol for item in latest_brief.watchlist] if latest_brief else (),
        )
        bars_by_symbol = self.provider.get_recent_bars_batch(
            scoped_symbols,
            interval="15m",
            lookback_days=max(10, self.settings.volume_baseline_lookback_days + 5),
        )
        evaluated: list[str] = []
        stored_events: list[AlertEvent] = []
        dispatched_events: list[AlertEvent] = []
        allowed_normals: list[AlertEvent] = []

        for symbol in scoped_symbols:
            bars = list(bars_by_symbol.get(symbol, []))
            if len(bars) < 2:
                continue

            evaluated.append(symbol)
            self.state_store.upsert_market_bars(symbol, "15m", bars)
            baseline = self.provider.compute_volume_baseline(
                symbol,
                bars,
                lookback_days=self.settings.volume_baseline_lookback_days,
            )

            combined_events = [*prior_events, *stored_events, *dispatched_events]
            extreme = classify_extreme(
                symbol,
                bars,
                volume_baseline=baseline,
                volume_multiplier=self.settings.volume_baseline_multiplier,
            )
            if extreme:
                if symbol in watchlist_symbols:
                    extreme.metadata["watchlist_hit"] = True
                decision = self.policy.evaluate(extreme, combined_events)
                extreme.suppressed_reason = decision.suppressed_reason
                if decision.allowed:
                    extreme.dispatched_at_ny = moment
                    card_path = self.card_renderer.render_intraday(extreme)
                    self.dispatcher.send_intraday_alert(
                        extreme,
                        card_path=card_path,
                        text=_format_intraday_text(extreme),
                    )
                    dispatched_events.append(extreme)
                self.state_store.record_alert(extreme)
                stored_events.append(extreme)
                continue

            normal = classify_normal(symbol, bars)
            if not normal:
                continue
            if symbol in watchlist_symbols:
                normal.metadata["watchlist_hit"] = True

            decision = self.policy.evaluate(normal, combined_events)
            normal.suppressed_reason = decision.suppressed_reason
            self.state_store.record_alert(normal)
            stored_events.append(normal)
            if decision.allowed:
                allowed_normals.append(normal)

        aggregate = aggregate_normals(allowed_normals, previous_window_normals)
        if aggregate:
            decision = self.policy.evaluate(aggregate, [*prior_events, *stored_events, *dispatched_events])
            aggregate.suppressed_reason = decision.suppressed_reason
            if decision.allowed:
                aggregate.dispatched_at_ny = moment
                card_path = self.card_renderer.render_intraday(aggregate)
                self.dispatcher.send_intraday_alert(
                    aggregate,
                    card_path=card_path,
                    text=_format_intraday_text(aggregate),
                )
                dispatched_events.append(aggregate)
            self.state_store.record_alert(aggregate)
            stored_events.append(aggregate)

        return IntradayScanResult(
            trade_date_ny=trade_date,
            evaluated_symbols=evaluated,
            dispatched_events=dispatched_events,
            stored_events=stored_events,
        )


def _format_intraday_text(event: AlertEvent) -> str:
    direction_zh = "拉升" if event.direction == "up" else "回落"
    related = f"；联动 {', '.join(event.related_symbols)}" if event.related_symbols else ""
    focus = "；命中早报 watchlist" if event.metadata.get("watchlist_hit") else ""
    return f"⚡️【盘中异动】{event.symbol} {direction_zh} {event.magnitude_pct:+.2f}%{related}{focus}"
