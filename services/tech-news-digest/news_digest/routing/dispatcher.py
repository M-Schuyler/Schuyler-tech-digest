from __future__ import annotations

from pathlib import Path

from ..config import RuntimeSettings
from ..models import AlertEvent, CloseSummary, DailyBrief
from ..monitoring.models import MonitorEvent, MonitorSignal
from ..public_text import sanitize_public_section
from .telegram_client import TelegramBotClient, split_text


class TelegramDispatcher:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.main_bot = TelegramBotClient(settings.main_bot)
        self.side_bot = TelegramBotClient(settings.side_bot)

    def send_daily_brief(self, brief: DailyBrief, *, card_path: Path, trend_paths: list[Path]) -> None:
        image_paths = [card_path, *trend_paths]
        self.main_bot.send_media_group(image_paths)
        for chunk in split_text(format_daily_brief(brief)):
            self.main_bot.send_message(chunk)

    def send_intraday_alert(self, event: AlertEvent, *, card_path: Path, text: str) -> None:
        self.side_bot.send_photo(card_path, caption=text)

    def send_close_summary(self, summary: CloseSummary, *, card_path: Path, text: str) -> None:
        self.side_bot.send_photo(card_path, caption="收盘总结")
        for chunk in split_text(text):
            self.side_bot.send_message(chunk)

    def send_monitor_signal(self, signal: MonitorSignal, event: MonitorEvent) -> bool:
        return self.side_bot.send_message(format_monitor_signal(signal, event))


def format_daily_brief(brief: DailyBrief) -> str:
    top_lines = [line for line in (sanitize_public_section(line) for line in brief.top_three) if line]
    top = "\n".join(f"{idx}. {line}" for idx, line in enumerate(top_lines, start=1))
    return "\n\n".join(
        [
            "🧭【今天只看这 3 件事】\n" + top,
            "🤖【AI 主线】\n" + sanitize_public_section(brief.ai_section),
            "🏢【科技与公司】\n" + sanitize_public_section(brief.tech_section),
            "📈【市场与价格】\n" + sanitize_public_section(brief.market_section),
            "🔗【交叉情报】\n" + sanitize_public_section(brief.cross_section),
        ]
    )


def format_close_summary(summary: CloseSummary) -> str:
    watch = "\n".join(f"• {item.symbol}：{item.reason}" for item in summary.tomorrow_watch[:3])
    return "\n\n".join(
        [
            f"📌【收盘结论】\n{summary.closing_verdict}",
            f"⚖️【今天最强 / 最弱】\n强：{' / '.join(summary.strongest_assets[:3])}\n弱：{' / '.join(summary.weakest_assets[:3])}",
            f"🤖【AI / 科技主线】\n{summary.ai_tech_thread}",
            f"₿【币圈情绪】\n{summary.crypto_mood}",
            f"👀【明天继续盯什么】\n{watch or '• 暂无新的优先观察标的。'}",
        ]
    )


def format_monitor_signal(signal: MonitorSignal, event: MonitorEvent) -> str:
    symbols = " / ".join(signal.symbols) or "无映射标的"
    title = sanitize_public_section(event.title) or "新情报信号"
    return "\n".join(
        [
            "🛰️【实时情报信号】",
            f"{title}",
            f"标的：{symbols}",
            f"理由：{_public_monitor_signal_reason(signal, event)}",
            f"来源：{event.url}",
        ]
    )


def _public_monitor_signal_reason(signal: MonitorSignal, event: MonitorEvent) -> str:
    if signal.symbols:
        return "相关标的已进入观察名单，先看价格是否确认消息强度"
    if signal.entities:
        return "关注实体出现新动态，等待后续新闻和市场反应确认"
    if event.content_hint:
        return "新事件进入候选池，等待更多证据确认"
    return "候选信号需要继续观察"
