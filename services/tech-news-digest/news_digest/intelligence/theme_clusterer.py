from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from ..report import BriefingItem


@dataclass(frozen=True)
class ThemeDefinition:
    key: str
    name: str
    category: str
    keywords: tuple[str, ...]
    judgment: str
    why_it_matters: str


@dataclass
class BriefTheme:
    key: str
    name: str
    category: str
    judgment: str
    why_it_matters: str
    items: list[BriefingItem]
    score: int

    @property
    def evidence(self) -> list[str]:
        return [_evidence_label(item) for item in self.items[:3]]


THEME_DEFINITIONS: tuple[ThemeDefinition, ...] = (
    ThemeDefinition(
        key="agents",
        name="Agent / 办公 AI",
        category="AI",
        keywords=(
            "agent",
            "agents",
            "copilot",
            "operator",
            "workspace",
            "office",
            "enterprise workflow",
        ),
        judgment="Agent / 办公 AI：多条更新都在争夺工作流入口，不是单点功能发布。",
        why_it_matters="这条线如果成立，后续要看 MSFT、GOOGL、NVDA 和 QQQ 是否一起给出价格确认。",
    ),
    ThemeDefinition(
        key="models",
        name="模型 / 基础设施",
        category="AI",
        keywords=(
            "model",
            "llm",
            "foundation model",
            "claude",
            "chatgpt",
            "gemini",
            "openai",
            "anthropic",
            "deepmind",
        ),
        judgment="模型 / 基础设施：竞争焦点还在能力、成本和分发入口，单次发布只是表层。",
        why_it_matters="模型层新闻要和云、芯片、应用入口一起看，孤立追发布会容易误判强弱。",
    ),
    ThemeDefinition(
        key="compute",
        name="算力 / 芯片链",
        category="Chips",
        keywords=(
            "nvidia",
            "gpu",
            "tsmc",
            "semiconductor",
            "chip",
            "foundry",
            "amd",
            "inference",
            "datacenter",
            "compute",
        ),
        judgment="算力 / 芯片链：AI 交易的硬约束仍在供给端，芯片新闻比普通产品更新更能影响主线。",
        why_it_matters="如果算力链继续扩散，优先观察 NVDA、AMD、TSM、QQQ 的强弱排序。",
    ),
    ThemeDefinition(
        key="platforms",
        name="大厂平台 / 生态入口",
        category="Big Tech",
        keywords=(
            "microsoft",
            "google",
            "meta",
            "apple",
            "amazon",
            "tesla",
            "platform",
            "ecosystem",
            "cloud",
        ),
        judgment="大厂平台 / 生态入口：竞争重点是把用户、开发者和算力锁进自己的系统。",
        why_it_matters="这类新闻真正有用的部分，是判断大厂资本开支和生态份额会不会继续重估。",
    ),
    ThemeDefinition(
        key="robotics",
        name="机器人 / 自动化",
        category="Robotics",
        keywords=("robot", "robotics", "humanoid", "autonomous", "drone"),
        judgment="机器人 / 自动化：落地节奏比概念更重要，重点看量产、成本和真实场景。",
        why_it_matters="机器人线容易被情绪放大，只有和订单、产能或核心供应链绑定时才值得提高权重。",
    ),
    ThemeDefinition(
        key="funding",
        name="创业融资 / 估值",
        category="Startups",
        keywords=(
            "startup",
            "funding",
            "raised",
            "series a",
            "series b",
            "series c",
            "seed",
            "valuation",
            "venture",
            "ipo",
        ),
        judgment="创业融资 / 估值：资金还在挑方向，但热钱和真实需求需要分开看。",
        why_it_matters="融资新闻更像风险偏好温度计，单条融资不能直接当产业趋势。",
    ),
)

CATEGORY_FALLBACKS: dict[str, ThemeDefinition] = {
    "AI": THEME_DEFINITIONS[1],
    "Chips": THEME_DEFINITIONS[2],
    "Big Tech": THEME_DEFINITIONS[3],
    "Robotics": THEME_DEFINITIONS[4],
    "Startups": THEME_DEFINITIONS[5],
}


class ThemeClusterer:
    def cluster(self, items: list[BriefingItem]) -> list[BriefTheme]:
        buckets: dict[str, list[BriefingItem]] = {}
        definitions: dict[str, ThemeDefinition] = {}

        for item in items:
            definition = _match_definition(item)
            buckets.setdefault(definition.key, []).append(item)
            definitions[definition.key] = definition

        themes = [
            _build_theme(key, definitions[key], bucket)
            for key, bucket in buckets.items()
        ]
        return sorted(themes, key=lambda theme: (theme.score, len(theme.items)), reverse=True)


def _match_definition(item: BriefingItem) -> ThemeDefinition:
    text = _searchable_text(item)
    for definition in THEME_DEFINITIONS:
        if any(_contains_keyword(text, keyword) for keyword in definition.keywords):
            return definition
    return CATEGORY_FALLBACKS.get(item.category, _category_definition(item.category))


def _build_theme(key: str, definition: ThemeDefinition, items: list[BriefingItem]) -> BriefTheme:
    ranked_items = sorted(items, key=lambda item: item.importance_score, reverse=True)
    return BriefTheme(
        key=key,
        name=definition.name,
        category=definition.category,
        judgment=definition.judgment,
        why_it_matters=definition.why_it_matters,
        items=ranked_items,
        score=_theme_score(ranked_items),
    )


def _theme_score(items: list[BriefingItem]) -> int:
    if not items:
        return 0
    score_total = sum(item.importance_score for item in items)
    repeated_signal_bonus = max(0, len(items) - 1) * 30
    high_confidence_bonus = 12 if any(_is_primary_source(item) for item in items) else 0
    return score_total + repeated_signal_bonus + high_confidence_bonus


def _category_definition(category: str) -> ThemeDefinition:
    name = category or "其他科技变量"
    return ThemeDefinition(
        key=f"category:{name}",
        name=name,
        category=name,
        keywords=(),
        judgment=f"{name}：今天有新增变量，但还不足以单独升级成主线。",
        why_it_matters="先把它当作候选信号，等价格或更多消息确认后再提高权重。",
    )


def _searchable_text(item: BriefingItem) -> str:
    parts = [
        item.title,
        item.category,
        item.url,
        *(item.summary_en or []),
        *(item.summary_zh or []),
    ]
    return " ".join(part for part in parts if part).lower()


def _contains_keyword(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword.lower() in text
    escaped = re.escape(keyword.lower())
    return re.search(rf"\b{escaped}\b", text) is not None


def _is_primary_source(item: BriefingItem) -> bool:
    domain = _domain(item.url)
    primary_domains = (
        "openai.com",
        "anthropic.com",
        "deepmind.google",
        "googleblog.com",
        "microsoft.com",
        "nvidia.com",
        "amd.com",
    )
    return any(domain == primary or domain.endswith(f".{primary}") for primary in primary_domains)


def _evidence_label(item: BriefingItem) -> str:
    domain = _domain(item.url)
    if domain:
        return f"{item.title}（{domain}）"
    return item.title


def _domain(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host
