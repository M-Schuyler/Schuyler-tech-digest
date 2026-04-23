from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import CRYPTO_SYMBOLS, MARKET_SYMBOLS, RuntimeSettings
from ..market.provider import MarketProvider
from ..models import CloseSummary, WatchSignal
from ..routing.dispatcher import TelegramDispatcher, format_close_summary
from ..scheduling.calendar import NYSECalendar
from ..state.store import StateStore
from .render_alert_card import AlertCardRenderer


class CloseAlertService:
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
        self.card_renderer = AlertCardRenderer(settings)
        self.market_tz = ZoneInfo(settings.market_timezone)

    def run(self, now: datetime | None = None) -> CloseSummary | None:
        moment = self.calendar.now_ny(now)
        if not self.calendar.is_close_alert_window(moment):
            return None

        trade_date = moment.date()
        alerts = self.state_store.list_alerts(trade_date_ny=trade_date)
        daily_changes = _collect_daily_changes(self.provider)
        strongest = [symbol for symbol, _ in sorted(daily_changes.items(), key=lambda item: item[1], reverse=True)[:3]]
        weakest = [symbol for symbol, _ in sorted(daily_changes.items(), key=lambda item: item[1])[:3]]
        latest_brief = self.state_store.get_latest_brief()
        watchlist = latest_brief.watchlist if latest_brief else [
            WatchSignal(symbol="QQQ", reason="先看科技风险偏好", priority=5)
        ]

        summary = CloseSummary(
            trade_date_ny=trade_date,
            closing_verdict=_build_closing_verdict(daily_changes, alerts),
            strongest_assets=strongest,
            weakest_assets=weakest,
            ai_tech_thread=_build_ai_thread(alerts, strongest),
            crypto_mood=_build_crypto_mood(daily_changes),
            tomorrow_watch=watchlist[:3],
            generated_at=moment,
            published_at=moment,
        )
        self.state_store.record_close_summary(summary)
        card_path = self.card_renderer.render_close(summary)
        self.dispatcher.send_close_summary(summary, card_path=card_path, text=format_close_summary(summary))
        return summary


def _collect_daily_changes(provider: MarketProvider) -> dict[str, float]:
    changes: dict[str, float] = {}
    for symbol in MARKET_SYMBOLS:
        bars = provider.get_intraday_bars(symbol, lookback_days=3)
        if len(bars) < 2:
            continue
        today_bars = [bar for bar in bars if bar.trading_date_ny == bars[-1].trading_date_ny]
        if len(today_bars) < 2:
            continue
        open_price = today_bars[0].open
        close_price = today_bars[-1].close
        changes[symbol] = ((close_price - open_price) / open_price) * 100
    return changes


def _build_closing_verdict(daily_changes: dict[str, float], alerts) -> str:
    qqq = daily_changes.get("QQQ", 0.0)
    spy = daily_changes.get("SPY", 0.0)
    btc = daily_changes.get("BTC", 0.0)
    alert_count = len([event for event in alerts if event.was_dispatched])

    if qqq > 1.0 and btc > 1.0:
        return f"今天更像一次风险偏好回暖，QQQ 和 BTC 同向走强，盘中一共触发了 {alert_count} 次有效提醒。"
    if qqq < -1.0 and btc < -1.0:
        return f"今天是明显的风险偏好回落日，科技与加密同步承压，盘中一共触发了 {alert_count} 次有效提醒。"
    if qqq > spy:
        return f"科技相对更强，资金还在往成长和 AI 链条里挤，盘中触发 {alert_count} 次有效提醒。"
    return f"市场没有给出特别干净的一致方向，更多是结构分化，盘中触发 {alert_count} 次有效提醒。"


def _build_ai_thread(alerts, strongest: list[str]) -> str:
    tech_alerts = [event for event in alerts if event.symbol in {"NVDA", "AMD", "MSFT", "GOOGL", "META", "AAPL", "TSLA"}]
    if tech_alerts:
        lead = tech_alerts[-1]
        return f"科技主线里最值得回看的是 {lead.symbol}，因为 {lead.reason.lower()}。"
    if strongest:
        return f"今天没有太多单点新闻驱动，但 {strongest[0]} 代表的主线资产仍然最强。"
    return "今天没有新的 AI/科技异动主角，先把节奏留给下一交易日。"


def _build_crypto_mood(daily_changes: dict[str, float]) -> str:
    crypto_changes = {symbol: daily_changes.get(symbol, 0.0) for symbol in CRYPTO_SYMBOLS}
    if all(change > 0.8 for change in crypto_changes.values()):
        return "BTC 和 ETH 同步回暖，风险偏好明显抬头。"
    if all(change < -0.8 for change in crypto_changes.values()):
        return "BTC 和 ETH 同步走弱，币圈情绪偏冷。"
    return "BTC / ETH 没有形成共振，币圈情绪更多是跟随盘面。"
