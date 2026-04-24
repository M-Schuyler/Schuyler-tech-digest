from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from ..config import RuntimeSettings
from ..intelligence.cross_correlator import CrossCorrelator
from ..intelligence.topic_ranker import TopicRanker
from ..intelligence.watchlist_builder import WatchlistBuilder
from ..market.provider import MarketProvider
from ..models import BriefRecord, CloseSummary, DailyBrief
from ..monitoring.models import MonitorSignal, SignalLevel
from ..pipeline import NewsPipeline
from ..report import BriefingItem
from ..scheduling.calendar import NYSECalendar
from ..state.store import StateStore


class DailyBriefComposer:
    def __init__(
        self,
        *,
        settings: RuntimeSettings,
        pipeline: NewsPipeline,
        market_provider: MarketProvider,
        state_store: StateStore,
        calendar: NYSECalendar,
    ) -> None:
        self.settings = settings
        self.pipeline = pipeline
        self.market_provider = market_provider
        self.state_store = state_store
        self.calendar = calendar
        self.topic_ranker = TopicRanker(settings)
        self.watchlist_builder = WatchlistBuilder()
        self.cross_correlator = CrossCorrelator()
        self._brief_tz = ZoneInfo(settings.brief_timezone)

    def compose(self, report_date_sh: date | None = None) -> DailyBrief:
        brief_date = report_date_sh or datetime.now(tz=self._brief_tz).date()
        reference_trade_date = self.calendar.reference_trade_date_for_brief(brief_date)
        close_summary = self.state_store.get_close_summary(reference_trade_date)
        selected, _, _ = self.pipeline.collect_selected(report_date=brief_date)
        items = [item for item, _ in selected]

        top_three = self.topic_ranker.rank(items, close_summary=close_summary)
        watchlist = self.watchlist_builder.build(items, close_summary)
        ai_section = self._build_ai_section(items)
        tech_section = self._build_tech_section(items)
        market_section = self._build_market_section(reference_trade_date, close_summary)
        cross_section = self.cross_correlator.compose(
            top_three=top_three,
            close_summary=close_summary,
            watchlist=watchlist,
        )
        monitoring_signal_lines = self._monitoring_signal_lines(brief_date)
        if monitoring_signal_lines:
            cross_section = "\n".join(
                [
                    cross_section,
                    "【监控信号】",
                    *monitoring_signal_lines,
                ]
            )

        return DailyBrief(
            brief_date_sh=brief_date,
            reference_trade_date_ny=reference_trade_date,
            top_three=top_three,
            ai_section=ai_section,
            tech_section=tech_section,
            market_section=market_section,
            cross_section=cross_section,
            watchlist=watchlist,
            chart_symbols=self._pick_chart_symbols(watchlist),
            generated_at=datetime.now(tz=self._brief_tz),
        )

    def persist(
        self,
        brief: DailyBrief,
        *,
        chart_paths: list[str],
        published_at: datetime | None = None,
    ) -> BriefRecord:
        record = BriefRecord(
            brief_date_sh=brief.brief_date_sh,
            reference_trade_date_ny=brief.reference_trade_date_ny,
            top_three=brief.top_three,
            ai_section=brief.ai_section,
            tech_section=brief.tech_section,
            market_section=brief.market_section,
            cross_section=brief.cross_section,
            watchlist=brief.watchlist,
            chart_paths=chart_paths,
            generated_at=brief.generated_at,
            published_at=published_at,
        )
        self.state_store.record_brief(record)
        return record

    def _build_ai_section(self, items: list[BriefingItem]) -> str:
        ai_items = [item for item in items if item.category == "AI"][:3]
        if not ai_items:
            return "• 今天没有新的重锤 AI 新闻进来，先看昨夜主线是否继续被价格确认。"
        return "\n".join(
            f"• {item.title}：{_primary_summary(item)}"
            for item in ai_items
        )

    def _build_tech_section(self, items: list[BriefingItem]) -> str:
        sections: dict[str, list[BriefingItem]] = defaultdict(list)
        for item in items:
            if item.category != "AI":
                sections[item.category].append(item)

        selected: list[BriefingItem] = []
        for category in ("Big Tech", "Chips", "Robotics", "Startups"):
            selected.extend(sections.get(category, [])[:1])

        if not selected:
            return "• 科技与公司层面没有比 AI 主线更强的新增变量，今天先看核心资产承接。"
        return "\n".join(
            f"• {item.title}：{_primary_summary(item)}"
            for item in selected[:3]
        )

    def _build_market_section(
        self,
        reference_trade_date_ny: date,
        close_summary: CloseSummary | None,
    ) -> str:
        if close_summary:
            strongest = " / ".join(close_summary.strongest_assets[:2]) or "暂无明显领涨"
            weakest = " / ".join(close_summary.weakest_assets[:2]) or "暂无明显领跌"
            return "\n".join(
                [
                    f"• 前一纽约交易日结论：{close_summary.closing_verdict}",
                    f"• 最强资产：{strongest}",
                    f"• 最弱资产：{weakest}",
                    f"• 币圈情绪：{close_summary.crypto_mood}",
                ]
            )

        fallback_symbols = list(self.settings.chart_default_symbols)
        lines = ["• 前一交易日还没有现成收盘结案，先用核心资产涨跌幅补齐盘感。"]
        for symbol in fallback_symbols[:3]:
            bars = self.market_provider.get_daily_bars(symbol, lookback_days=5)
            if len(bars) < 2:
                continue
            change_pct = ((bars[-1].close - bars[-2].close) / bars[-2].close) * 100
            lines.append(f"• {symbol}：上一日变化 {change_pct:+.2f}%")
        return "\n".join(lines)

    def _pick_chart_symbols(self, watchlist) -> list[str]:
        chosen = [item.symbol for item in watchlist[:2]]
        if not chosen:
            chosen = list(self.settings.chart_default_symbols[:2])
        while len(chosen) < 2 and len(self.settings.chart_default_symbols) > len(chosen):
            fallback = self.settings.chart_default_symbols[len(chosen)]
            if fallback not in chosen:
                chosen.append(fallback)
        return chosen[:2]

    def _monitoring_signal_lines(self, brief_date: date) -> list[str]:
        since_utc = datetime.combine(brief_date, time.min, tzinfo=self._brief_tz).astimezone(timezone.utc)
        signals = self.state_store.list_monitor_signals(
            level=SignalLevel.DIGEST_CANDIDATE,
            since_utc=since_utc,
            limit=8,
        )
        ranked = sorted(signals, key=lambda signal: signal.score, reverse=True)
        lines: list[str] = []
        for signal in ranked:
            line = _format_monitoring_signal_line(signal)
            if line:
                lines.append(line)
            if len(lines) == 3:
                break
        return lines


def _primary_summary(item: BriefingItem) -> str:
    if item.summary_zh:
        return item.summary_zh[0]
    if item.summary_en:
        return item.summary_en[0]
    return "暂无摘要。"


def _format_monitoring_signal_line(signal: MonitorSignal) -> str | None:
    if not signal.symbols and not signal.entities:
        return None
    symbols = " / ".join(signal.symbols) or "未映射"
    entities = " / ".join(signal.entities) or "未命名"
    return f"• {symbols}：{entities} - {signal.reason}"
