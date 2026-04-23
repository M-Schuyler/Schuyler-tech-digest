from __future__ import annotations

from collections.abc import Sequence

from ..config import RuntimeSettings
from ..report import BriefingItem

OFFICIAL_SOURCE_HINTS = ("openai", "anthropic", "deepmind", "meta", "microsoft", "nvidia", "google")
CATEGORY_TEMPLATES = {
    "AI": "AI 进展还在加速，{headline} 是今天最值得盯的落点。",
    "Chips": "算力和芯片链条仍在升温，{headline} 强化了这条主线。",
    "Big Tech": "大厂动作继续改写竞争格局，{headline} 不该只当成普通更新看。",
    "Robotics": "机器人和自动化落地继续推进，{headline} 更像产业信号，不只是热闹。",
    "Startups": "创业与融资端还在分化，{headline} 透露了资金在押什么方向。",
}


class TopicRanker:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings

    def rank(self, items: Sequence[BriefingItem]) -> list[str]:
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
            results.append(self._judgment_line(item))
            seen_titles.add(normalized)
            seen_categories.add(item.category)
            if len(results) == 3:
                break

        if len(results) < 3:
            for item in ranked:
                normalized = item.title.strip().lower()
                if normalized in seen_titles:
                    continue
                results.append(self._judgment_line(item))
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

    def _judgment_line(self, item: BriefingItem) -> str:
        headline = _trim_title(item.title)
        template = CATEGORY_TEMPLATES.get(item.category, "{headline}")
        return template.format(headline=headline)


def _trim_title(title: str, limit: int = 36) -> str:
    clean = " ".join((title or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"
