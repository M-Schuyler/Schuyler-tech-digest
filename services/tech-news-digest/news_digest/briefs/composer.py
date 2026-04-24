from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from ..config import RuntimeSettings
from ..intelligence.cross_correlator import CrossCorrelator
from ..intelligence.theme_clusterer import BriefTheme, ThemeClusterer
from ..intelligence.topic_ranker import TopicRanker
from ..intelligence.watchlist_builder import WatchlistBuilder
from ..market.provider import MarketProvider
from ..models import BriefRecord, CloseSummary, DailyBrief
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
        self.theme_clusterer = ThemeClusterer()
        self.watchlist_builder = WatchlistBuilder()
        self.cross_correlator = CrossCorrelator()
        self._brief_tz = ZoneInfo(settings.brief_timezone)

    def compose(self, report_date_sh: date | None = None) -> DailyBrief:
        brief_date = report_date_sh or datetime.now(tz=self._brief_tz).date()
        reference_trade_date = self.calendar.reference_trade_date_for_brief(brief_date)
        close_summary = self.state_store.get_close_summary(reference_trade_date)
        selected, _, _ = self.pipeline.collect_selected(report_date=brief_date)
        items = [item for item, _ in selected]

        themes = self.theme_clusterer.cluster(items)
        top_three = self._build_top_three(items, themes)
        watchlist = self.watchlist_builder.build(items, close_summary)
        ai_section = self._build_ai_section(items, themes)
        tech_section = self._build_tech_section(items, themes)
        market_section = self._build_market_section(reference_trade_date, close_summary)
        cross_section = self.cross_correlator.compose(
            top_three=top_three,
            close_summary=close_summary,
            watchlist=watchlist,
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

    def _build_top_three(self, items: list[BriefingItem], themes: list[BriefTheme]) -> list[str]:
        top_three = [theme.judgment for theme in themes[:3]]
        if len(top_three) >= 3:
            return top_three[:3]

        for fallback in self.topic_ranker.rank(items):
            if fallback not in top_three:
                top_three.append(fallback)
            if len(top_three) == 3:
                break
        return top_three[:3]

    def _build_ai_section(self, items: list[BriefingItem], themes: list[BriefTheme]) -> str:
        ai_themes = [theme for theme in themes if theme.category == "AI"]
        if not ai_themes:
            return "• 今天没有新的重锤 AI 新闻进来，先看昨夜主线是否继续被价格确认。"
        return "\n".join(_format_theme_block(theme) for theme in ai_themes[:2])

    def _build_tech_section(self, items: list[BriefingItem], themes: list[BriefTheme]) -> str:
        tech_themes = [theme for theme in themes if theme.category != "AI"]
        if not tech_themes:
            return "• 科技与公司层面没有比 AI 主线更强的新增变量，今天先看核心资产承接。"
        return "\n".join(_format_theme_block(theme) for theme in tech_themes[:2])

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


def _format_theme_block(theme: BriefTheme) -> str:
    evidence = "；".join(theme.evidence[:2]) or "暂无可追溯来源"
    return "\n".join(
        [
            f"• 主线：{theme.name}",
            f"  判断：{_strip_theme_name(theme.judgment, theme.name)}",
            f"  证据：{evidence}",
        ]
    )


def _strip_theme_name(judgment: str, theme_name: str) -> str:
    prefix = f"{theme_name}："
    if judgment.startswith(prefix):
        return judgment[len(prefix):]
    return judgment
