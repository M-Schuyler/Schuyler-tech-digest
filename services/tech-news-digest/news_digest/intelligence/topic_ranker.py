from __future__ import annotations

from collections.abc import Sequence

from ..config import RuntimeSettings
from ..models import CloseSummary
from ..report import BriefingItem

OFFICIAL_SOURCE_HINTS = ("openai", "anthropic", "deepmind", "meta", "microsoft", "nvidia", "google")
GPU_SUBSTITUTION_TERMS = ("graviton", "cpu", "arm")


class TopicRanker:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings

    def rank(
        self,
        items: Sequence[BriefingItem],
        close_summary: CloseSummary | None = None,
    ) -> list[str]:
        if not items:
            return [
                "隔夜没有足够强的新信号，今天先按既有主线观察市场承接。",
                "AI 与大厂动态偏平，优先看价格是否先于叙事行动。",
                "没有新的重锤消息时，更要看主线资产有没有继续扩散。",
            ]

        ranked = sorted(items, key=self._score, reverse=True)
        results: list[str] = []
        seen_titles: set[str] = set()
        seen_categories: set[str] = set()

        for item in ranked:
            normalized = item.title.strip().lower()
            if normalized in seen_titles:
                continue
            if item.category in seen_categories and len(ranked) > 3:
                continue
            results.append(self._judgment_line(item, close_summary))
            seen_titles.add(normalized)
            seen_categories.add(item.category)
            if len(results) == 3:
                break

        if len(results) < 3:
            for item in ranked:
                normalized = item.title.strip().lower()
                if normalized in seen_titles:
                    continue
                results.append(self._judgment_line(item, close_summary))
                seen_titles.add(normalized)
                if len(results) == 3:
                    break

        return results[:3]

    def _score(self, item: BriefingItem) -> int:
        base = item.importance_score
        source_bonus = self.settings.min_official_source_weight if item.url and any(
            hint in item.url.lower() or hint in item.title.lower() for hint in OFFICIAL_SOURCE_HINTS
        ) else 0
        return base + source_bonus

    def _judgment_line(self, item: BriefingItem, close_summary: CloseSummary | None) -> str:
        headline = _trim_title(item.title)
        text = _item_text(item)

        if _is_gpu_substitution_story(text):
            line = f"算力链条在分化：{headline} 更像用 CPU/ARM 做 AI 降本，不是简单的 GPU 需求扩张"
            if _is_weak("NVDA", close_summary):
                line += "；NVDA 同时偏弱，先按 GPU 定价压力和算力替代交易处理"
            return line + "。"

        market_note = _market_note_for_item(item, close_summary)
        if item.category == "Chips":
            line = f"芯片新闻先拆成需求增量还是替代降本：{headline}"
        elif item.category == "AI":
            line = f"AI 新闻先看商业落点和成本承担方：{headline}"
        elif item.category == "Big Tech":
            line = f"大厂动作要落到云、广告或设备收入：{headline}"
        elif item.category == "Robotics":
            line = f"机器人信号只看是否进入真实采购和供应链：{headline}"
        elif item.category == "Startups":
            line = f"融资新闻要看资金押注的具体环节：{headline}"
        else:
            line = headline

        if market_note:
            line += f"；{market_note}"
        return line + "。"


def _trim_title(title: str, limit: int = 36) -> str:
    clean = " ".join((title or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _item_text(item: BriefingItem) -> str:
    return " ".join([item.title, item.category, *(item.summary_en or []), *(item.summary_zh or [])]).lower()


def _is_gpu_substitution_story(text: str) -> bool:
    mentions_gpu_stack = "gpu" in text or "nvidia" in text or "nvda" in text or "ai workload" in text
    mentions_cpu_arm = any(term in text for term in GPU_SUBSTITUTION_TERMS)
    return mentions_gpu_stack and mentions_cpu_arm and ("meta" in text or "aws" in text or "hyperscaler" in text)


def _market_note_for_item(item: BriefingItem, close_summary: CloseSummary | None) -> str:
    if close_summary is None:
        return ""

    text = _item_text(item)
    watched_symbols = {
        "NVDA": ("nvidia", "gpu", "chip", "semiconductor", "compute", "算力"),
        "AMD": ("amd", "gpu", "chip", "semiconductor"),
        "MSFT": ("microsoft", "azure", "openai"),
        "GOOGL": ("google", "gemini", "deepmind"),
        "AMZN": ("amazon", "aws", "graviton"),
        "META": ("meta",),
        "AAPL": ("apple", "iphone"),
        "BTC": ("bitcoin", "btc", "crypto"),
    }

    weak_hits = [
        symbol
        for symbol, keywords in watched_symbols.items()
        if symbol in close_summary.weakest_assets and any(keyword in text for keyword in keywords)
    ]
    if weak_hits:
        return f"{' / '.join(weak_hits)} 已在弱势名单里，结论必须先写成验证/承压而不是追涨"

    strong_hits = [
        symbol
        for symbol, keywords in watched_symbols.items()
        if symbol in close_summary.strongest_assets and any(keyword in text for keyword in keywords)
    ]
    if strong_hits:
        return f"{' / '.join(strong_hits)} 已有承接，今天看能否延续而不是只看新闻热度"

    return ""


def _is_weak(symbol: str, close_summary: CloseSummary | None) -> bool:
    return close_summary is not None and symbol in close_summary.weakest_assets
