from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class ArticleSeed:
    title: str
    source: str
    url: str
    published_at: datetime | None


@dataclass
class ArticleRaw:
    title: str
    source: str
    url: str
    published_at: datetime | None
    content: str


@dataclass
class ArticleSummary:
    sentences_en: list[str]
    sentences_zh: list[str]
    keywords: list[str]

    @property
    def summary_text(self) -> str:
        pairs = self.bilingual_pairs
        return "\n".join(f"{en}\n{zh}" for en, zh in pairs)

    @property
    def bilingual_pairs(self) -> list[tuple[str, str]]:
        max_len = max(len(self.sentences_en), len(self.sentences_zh))
        pairs: list[tuple[str, str]] = []
        for idx in range(max_len):
            en = self.sentences_en[idx] if idx < len(self.sentences_en) else ""
            zh = self.sentences_zh[idx] if idx < len(self.sentences_zh) else ""
            pairs.append((en, zh))
        return pairs


@dataclass
class ArticleAssessment:
    keep: bool
    category: str
    importance_score: int
    title: str
    summary_en: list[str]
    summary_zh: list[str]
    rejection_reason: str = ""
    story_key: str = ""
    entities: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    ts_ny: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    interval: str = "15m"
    source: str = "yahoo"

    @property
    def trading_date_ny(self) -> date:
        return self.ts_ny.date()


@dataclass
class WatchSignal:
    symbol: str
    reason: str
    priority: int = 0


@dataclass
class AlertEvent:
    symbol: str
    window_start_ny: datetime
    window_end_ny: datetime
    triggered_at_ny: datetime
    trading_date_ny: date
    kind: str
    direction: str
    magnitude_pct: float
    reason: str
    source: str = "yahoo"
    related_symbols: tuple[str, ...] = ()
    suppressed_reason: str | None = None
    dispatched_at_ny: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None

    @property
    def symbols(self) -> tuple[str, ...]:
        if self.related_symbols:
            ordered = [self.symbol, *self.related_symbols]
            deduped: list[str] = []
            for item in ordered:
                if item and item not in deduped:
                    deduped.append(item)
            return tuple(deduped)
        return (self.symbol,)

    @property
    def was_dispatched(self) -> bool:
        return self.dispatched_at_ny is not None and self.suppressed_reason is None


@dataclass
class CloseSummary:
    trade_date_ny: date
    closing_verdict: str
    strongest_assets: list[str]
    weakest_assets: list[str]
    ai_tech_thread: str
    crypto_mood: str
    tomorrow_watch: list[WatchSignal]
    generated_at: datetime
    published_at: datetime | None = None


@dataclass
class BriefRecord:
    brief_date_sh: date
    reference_trade_date_ny: date
    top_three: list[str]
    ai_section: str
    tech_section: str
    market_section: str
    cross_section: str
    watchlist: list[WatchSignal]
    chart_paths: list[str]
    generated_at: datetime
    published_at: datetime | None = None


@dataclass
class DailyBrief:
    brief_date_sh: date
    reference_trade_date_ny: date
    top_three: list[str]
    ai_section: str
    tech_section: str
    market_section: str
    cross_section: str
    watchlist: list[WatchSignal]
    chart_symbols: list[str]
    generated_at: datetime


@dataclass
class IntradayScanResult:
    trade_date_ny: date | None
    evaluated_symbols: list[str]
    dispatched_events: list[AlertEvent]
    stored_events: list[AlertEvent]
    skipped_reason: str | None = None
