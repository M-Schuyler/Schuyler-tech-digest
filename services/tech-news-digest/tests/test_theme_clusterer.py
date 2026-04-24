from __future__ import annotations

from news_digest.briefs.composer import DailyBriefComposer
from news_digest.intelligence.theme_clusterer import ThemeClusterer
from news_digest.report import BriefingItem


def _item(
    title: str,
    *,
    category: str = "AI",
    score: int = 80,
    summary: str = "This is a relevant update.",
    url: str = "https://example.com/news",
) -> BriefingItem:
    return BriefingItem(
        title=title,
        category=category,
        summary_en=[summary],
        summary_zh=[summary],
        url=url,
        importance_score=score,
    )


def test_clusterer_promotes_repeated_agent_theme_over_single_high_score_headline() -> None:
    items = [
        _item(
            "OpenAI launches workplace agent controls",
            score=88,
            summary="OpenAI is pushing agents deeper into enterprise workflows.",
            url="https://openai.com/news/workplace-agents",
        ),
        _item(
            "Microsoft adds Copilot agents across Office",
            score=84,
            summary="Microsoft is making Copilot agents a default office workflow layer.",
            url="https://blogs.microsoft.com/copilot-agents",
        ),
        _item(
            "Tesla previews a new charging adapter",
            category="Big Tech",
            score=96,
            summary="A single company hardware update.",
            url="https://tesla.com/blog/adapter",
        ),
    ]

    themes = ThemeClusterer().cluster(items)

    assert themes[0].name == "Agent / 办公 AI"
    assert "工作流入口" in themes[0].judgment
    assert [item.title for item in themes[0].items] == [
        "OpenAI launches workplace agent controls",
        "Microsoft adds Copilot agents across Office",
    ]


def test_clusterer_keeps_traceable_evidence_titles_and_source_domains() -> None:
    theme = ThemeClusterer().cluster(
        [
            _item(
                "Nvidia and TSMC expand AI compute capacity",
                category="Chips",
                score=90,
                summary="GPU supply remains the hard constraint for AI scaling.",
                url="https://nvidia.com/en-us/data-center/news",
            ),
            _item(
                "AMD updates inference chip roadmap",
                category="Chips",
                score=82,
                summary="Inference chips are moving faster as AI workloads spread.",
                url="https://amd.com/en/newsroom",
            ),
        ]
    )[0]

    assert theme.name == "算力 / 芯片链"
    assert theme.evidence == [
        "Nvidia and TSMC expand AI compute capacity（nvidia.com）",
        "AMD updates inference chip roadmap（amd.com）",
    ]


def test_clusterer_uses_theme_category_for_compute_even_when_article_is_tagged_ai() -> None:
    theme = ThemeClusterer().cluster(
        [
            _item(
                "Nvidia expands GPUs for AI inference",
                category="AI",
                score=86,
                summary="The article was categorized as AI, but the signal is compute supply.",
                url="https://nvidia.com/en-us/data-center/news",
            )
        ]
    )[0]

    assert theme.name == "算力 / 芯片链"
    assert theme.category == "Chips"


def test_daily_brief_routes_compute_theme_to_tech_section_even_when_article_is_tagged_ai() -> None:
    items = [
        _item(
            "Nvidia expands GPUs for AI inference",
            category="AI",
            score=86,
            summary="The article was categorized as AI, but the signal is compute supply.",
            url="https://nvidia.com/en-us/data-center/news",
        )
    ]
    themes = ThemeClusterer().cluster(items)
    composer = object.__new__(DailyBriefComposer)

    ai_section = composer._build_ai_section(items, themes)
    tech_section = composer._build_tech_section(items, themes)

    assert "算力 / 芯片链" not in ai_section
    assert "主线：算力 / 芯片链" in tech_section


def test_daily_brief_ai_section_uses_theme_evidence_instead_of_item_by_item_summaries() -> None:
    items = [
        _item(
            "OpenAI launches workplace agents",
            score=88,
            summary="OpenAI is pushing agents deeper into enterprise workflows.",
            url="https://openai.com/news/workplace-agents",
        ),
        _item(
            "Microsoft adds Copilot agents to Office",
            score=84,
            summary="Copilot agents are becoming an office workflow layer.",
            url="https://blogs.microsoft.com/copilot-agents",
        ),
    ]
    themes = ThemeClusterer().cluster(items)
    composer = object.__new__(DailyBriefComposer)

    section = composer._build_ai_section(items, themes)

    assert "主线：Agent / 办公 AI" in section
    assert "判断：" in section
    assert "证据：" in section
    assert "OpenAI launches workplace agents（openai.com）" in section
    assert "Microsoft adds Copilot agents to Office（blogs.microsoft.com）" in section
    assert "OpenAI launches workplace agents：" not in section


def test_daily_brief_top_three_uses_theme_judgments_before_legacy_title_ranker() -> None:
    items = [
        _item("OpenAI launches workplace agents", score=88),
        _item("Microsoft adds Copilot agents to Office", score=84, url="https://blogs.microsoft.com/copilot-agents"),
    ]
    themes = ThemeClusterer().cluster(items)
    composer = object.__new__(DailyBriefComposer)
    composer.topic_ranker = _LegacyRanker()

    top_three = composer._build_top_three(items, themes)

    assert top_three[0] == "Agent / 办公 AI：多条更新都在争夺工作流入口，不是单点功能发布。"
    assert "OpenAI launches workplace agents 是今天最值得盯的落点" not in top_three[0]


class _LegacyRanker:
    def rank(self, _items: list[BriefingItem]) -> list[str]:
        return [
            "OpenAI launches workplace agents 是今天最值得盯的落点。",
            "市场风险偏好回暖。",
            "BTC 继续强于 ETH。",
        ]
