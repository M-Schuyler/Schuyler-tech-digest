from __future__ import annotations

import re
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
    "amazon": ("AMZN",),
    "aws": ("AMZN",),
    "graviton": ("AMZN", "META", "NVDA"),
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
    "cloud": ("MSFT", "GOOGL", "AMZN"),
}
CATEGORY_TO_SYMBOLS: dict[str, tuple[str, ...]] = {
    "AI": ("NVDA", "MSFT", "GOOGL"),
    "Chips": ("NVDA", "AMD"),
    "Big Tech": ("MSFT", "GOOGL", "AMZN", "META", "AAPL", "TSLA"),
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
            matched_symbols: set[str] = set()

            for keyword, symbols in KEYWORD_TO_SYMBOLS.items():
                if keyword in text:
                    matched_symbols.update(symbols)

            if not matched_symbols:
                matched_symbols.update(CATEGORY_TO_SYMBOLS.get(item.category, ()))

            if not matched_symbols:
                continue

            for symbol in matched_symbols:
                if symbol not in MARKET_SYMBOLS:
                    continue
                scores[symbol] += max(4, item.importance_score // 20)
                reasons[symbol].append(_reason_for_symbol(item, symbol))

        if close_summary:
            for symbol in close_summary.strongest_assets[:2]:
                if symbol not in MARKET_SYMBOLS:
                    continue
                scores[symbol] += 3
                reasons[symbol].append(f"{symbol} 昨夜已有承接，今天看延续而不是只看新闻热度")
            for symbol in close_summary.weakest_assets[:1]:
                if symbol not in MARKET_SYMBOLS:
                    continue
                scores[symbol] += 1
                reasons[symbol].append(f"{symbol} 昨夜偏弱，今天更需要观察是否继续承压")

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
                WatchSignal(symbol="QQQ", reason="没有足够强的单点催化时，先用 QQQ 验证科技风险偏好", priority=5),
                WatchSignal(symbol="NVDA", reason="若 AI 新闻继续扩散但 NVDA 不跟，说明算力交易在降温", priority=4),
                WatchSignal(symbol="BTC", reason="风险偏好回暖或退潮时，BTC 往往先动", priority=3),
            ]

        return watchlist


def _reason_for_symbol(item: BriefingItem, symbol: str) -> str:
    text = " ".join([item.title, item.category, *(item.summary_en or []), *(item.summary_zh or [])]).lower()
    headline = _trim_title(item.title)

    if _is_gpu_substitution_story(text):
        if symbol == "NVDA":
            return f"{headline} 指向 GPU 成本压力，NVDA 是承压验证点"
        if symbol == "AMD":
            return f"{headline} 指向推理算力分层，AMD 跟随看 GPU 需求弹性"
        if symbol in {"META", "AMZN"}:
            return f"{headline} 体现云/大厂用自研 CPU 降本，{symbol} 看成本改善"

    if symbol == "MSFT" and ("microsoft" in text or "azure" in text or "openai" in text):
        return f"{headline} 先落到 Azure/OpenAI 分发和企业云收入"
    if symbol == "GOOGL" and ("google" in text or "gemini" in text or "deepmind" in text):
        return f"{headline} 先落到 Gemini/搜索/Workspace 的产品承接"
    if symbol == "NVDA" and ("nvidia" in text or "gpu" in text or "openai" in text):
        return f"{headline} 只在新增推理需求被价格确认时才利好 NVDA"
    if symbol == "META" and "meta" in text:
        return f"{headline} 先看 META 的成本结构和广告/AI 资本开支"
    if symbol == "AAPL" and ("apple" in text or "iphone" in text):
        return f"{headline} 先看 AAPL 设备生态是否真的形成增量"
    if symbol in {"BTC", "ETH"}:
        return f"{headline} 用 {symbol} 验证风险偏好是否扩散到币圈"
    if symbol == "TSLA":
        return f"{headline} 用 TSLA 验证机器人/自动驾驶叙事承接"
    if symbol == "QQQ":
        return f"{headline} 用 QQQ 验证科技风险偏好是否扩散"

    return f"{headline} 与 {symbol} 直接相关，等价格确认"


def _merge_reasons(reasons: Sequence[str]) -> str:
    unique: list[str] = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return "；".join(unique[:2])


def _is_gpu_substitution_story(text: str) -> bool:
    mentions_gpu_stack = "gpu" in text or "nvidia" in text or "nvda" in text or "ai workload" in text
    mentions_cpu_arm = any(term in text for term in ("graviton", "cpu", "arm"))
    return mentions_gpu_stack and mentions_cpu_arm


def _trim_title(title: str, limit: int = 26) -> str:
    clean = re.sub(r"\s+", " ", (title or "").strip())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "..."
