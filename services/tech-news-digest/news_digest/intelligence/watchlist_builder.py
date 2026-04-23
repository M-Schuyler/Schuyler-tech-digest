from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from ..config import MARKET_SYMBOLS
from ..models import CloseSummary, WatchSignal
from ..report import BriefingItem

KEYWORD_TO_SYMBOLS: dict[str, tuple[str, ...]] = {
    "nvidia": ("NVDA", "AMD"),
    "gpu": ("NVDA", "AMD"),
    "chip": ("NVDA", "AMD"),
    "semiconductor": ("NVDA", "AMD"),
    "openai": ("MSFT", "NVDA"),
    "microsoft": ("MSFT",),
    "azure": ("MSFT",),
    "google": ("GOOGL",),
    "deepmind": ("GOOGL",),
    "meta": ("META",),
    "apple": ("AAPL",),
    "iphone": ("AAPL",),
    "tesla": ("TSLA",),
    "robot": ("TSLA",),
    "bitcoin": ("BTC",),
    "btc": ("BTC",),
    "ethereum": ("ETH",),
    "eth": ("ETH",),
    "crypto": ("BTC", "ETH"),
    "cloud": ("MSFT", "GOOGL"),
}
CATEGORY_TO_SYMBOLS: dict[str, tuple[str, ...]] = {
    "AI": ("NVDA", "MSFT", "GOOGL"),
    "Chips": ("NVDA", "AMD"),
    "Big Tech": ("MSFT", "GOOGL", "META", "AAPL", "TSLA"),
    "Robotics": ("TSLA",),
    "Startups": ("QQQ",),
}


class WatchlistBuilder:
    def build(
        self,
        items: Sequence[BriefingItem],
        close_summary: CloseSummary | None = None,
    ) -> list[WatchSignal]:
        scores: dict[str, int] = defaultdict(int)
        reasons: dict[str, list[str]] = defaultdict(list)

        for item in items:
            text = " ".join(
                [item.title, item.category, *(item.summary_en or []), *(item.summary_zh or [])]
            ).lower()
            matched_symbols = set(CATEGORY_TO_SYMBOLS.get(item.category, ()))

            for keyword, symbols in KEYWORD_TO_SYMBOLS.items():
                if keyword in text:
                    matched_symbols.update(symbols)

            if not matched_symbols:
                continue

            for symbol in matched_symbols:
                scores[symbol] += max(4, item.importance_score // 20)
                reasons[symbol].append(_reason_for_item(item))

        if close_summary:
            for symbol in close_summary.strongest_assets[:2]:
                scores[symbol] += 3
                reasons[symbol].append("昨夜已经是最先响应主线的资产之一")
            for symbol in close_summary.weakest_assets[:1]:
                scores[symbol] += 1
                reasons[symbol].append("昨夜偏弱，今天更需要观察是否继续承压")

        ranked = sorted(
            scores.items(),
            key=lambda item: (item[1], MARKET_SYMBOLS[item[0]].watchlist_priority),
            reverse=True,
        )
        watchlist: list[WatchSignal] = []
        for symbol, score in ranked:
            if symbol not in MARKET_SYMBOLS:
                continue
            watchlist.append(
                WatchSignal(
                    symbol=symbol,
                    reason=_merge_reasons(reasons[symbol]),
                    priority=score,
                )
            )
            if len(watchlist) == 3:
                break

        if not watchlist:
            watchlist = [
                WatchSignal(symbol="QQQ", reason="没有足够强的单点催化时，先看科技风险偏好", priority=5),
                WatchSignal(symbol="NVDA", reason="AI 与算力叙事如果继续扩散，NVDA 最容易先给反馈", priority=4),
                WatchSignal(symbol="BTC", reason="风险偏好回暖或退潮时，BTC 往往先动", priority=3),
            ]

        return watchlist


def _reason_for_item(item: BriefingItem) -> str:
    if item.category == "AI":
        return "AI 相关更新还在堆积"
    if item.category == "Chips":
        return "算力和芯片叙事继续发酵"
    if item.category == "Big Tech":
        return "大厂动作在重塑市场预期"
    if item.category == "Robotics":
        return "机器人与自动化落地在往产业链传导"
    if item.category == "Startups":
        return "融资方向反映资金押注的赛道"
    return "主线新闻还在积累"


def _merge_reasons(reasons: Sequence[str]) -> str:
    unique: list[str] = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return "；".join(unique[:2])
