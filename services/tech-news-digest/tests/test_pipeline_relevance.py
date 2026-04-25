from __future__ import annotations

from datetime import datetime, timezone

from news_digest.config import Settings
from news_digest.models import ArticleAssessment, ArticleRaw, ArticleSeed
from news_digest import pipeline
from news_digest.pipeline import NewsPipeline


def test_title_gate_keeps_gpt_version_launches_even_without_generic_ai_words() -> None:
    assert pipeline._seed_passes_title_gate("GPT-5.5 sparks a new model-routing race")


def test_recentness_weight_prioritizes_same_day_items() -> None:
    now = datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc)
    fresh = ArticleSeed(
        title="GPT-5.5 sparks a new model-routing race",
        source="OpenAI News",
        url="https://openai.com/news/gpt-5-5",
        published_at=datetime(2026, 4, 24, 1, 0, tzinfo=timezone.utc),
    )
    stale = ArticleSeed(
        title="Apple fixes Signal vulnerability",
        source="Example",
        url="https://example.com/apple-signal",
        published_at=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
    )

    assert pipeline._recentness_weight(fresh, now=now) > pipeline._recentness_weight(stale, now=now)


def test_collect_selected_semantically_dedupes_rewritten_funding_story() -> None:
    news_pipeline = NewsPipeline(Settings(rss_sources={}, max_briefing_items=10))
    seeds = [
        ArticleSeed(
            title="Anthropic is raising billions from Alphabet and Amazon",
            source="TechCrunch",
            url="https://techcrunch.com/anthropic-alphabet-amazon-funding?utm_source=rss",
            published_at=datetime(2026, 4, 25, 1, 0, tzinfo=timezone.utc),
        ),
        ArticleSeed(
            title="Google and Amazon commit billions to Anthropic AI expansion",
            source="Hacker News Frontpage",
            url="https://news.ycombinator.com/item?id=anthropic-funding",
            published_at=datetime(2026, 4, 25, 2, 0, tzinfo=timezone.utc),
        ),
        ArticleSeed(
            title="OpenAI launches GPT-5.5 model routing for developers",
            source="OpenAI News",
            url="https://openai.com/news/gpt-5-5-routing",
            published_at=datetime(2026, 4, 25, 3, 0, tzinfo=timezone.utc),
        ),
    ]
    raw_by_url = {}
    for seed in seeds:
        raw = ArticleRaw(
            title=seed.title,
            source=seed.source,
            url=seed.url,
            published_at=seed.published_at,
            content=seed.title,
        )
        raw_by_url[seed.url] = raw
        raw_by_url[pipeline._canonicalize_url(seed.url)] = raw
    assessment_by_url = {
        seeds[0].url: ArticleAssessment(
            keep=True,
            category="Startups",
            importance_score=84,
            title="Anthropic raises billions from Alphabet and Amazon",
            summary_en=["Anthropic secured new funding from Alphabet and Amazon.", "The round backs model infrastructure."],
            summary_zh=["Anthropic 获得 Alphabet 和 Amazon 的新增融资。", "这笔资金继续押注模型基础设施。"],
            story_key="anthropic-funding-alphabet-amazon",
            entities=("anthropic", "alphabet", "amazon"),
            symbols=("GOOGL", "AMZN"),
        ),
        seeds[1].url: ArticleAssessment(
            keep=True,
            category="Startups",
            importance_score=91,
            title="Google and Amazon commit billions to Anthropic AI expansion",
            summary_en=["Google and Amazon committed more capital to Anthropic.", "The investment supports AI expansion."],
            summary_zh=["Google 和 Amazon 向 Anthropic 追加资本。", "这笔投资支持 Anthropic 的 AI 扩张。"],
            story_key="anthropic-funding-alphabet-amazon",
            entities=("anthropic", "google", "amazon"),
            symbols=("GOOGL", "AMZN"),
        ),
        seeds[2].url: ArticleAssessment(
            keep=True,
            category="AI",
            importance_score=93,
            title="OpenAI launches GPT-5.5 model routing for developers",
            summary_en=["OpenAI launched GPT-5.5 routing for developers.", "The release changes model selection workflows."],
            summary_zh=["OpenAI 发布面向开发者的 GPT-5.5 路由能力。", "这次更新改变模型选择工作流。"],
            story_key="openai-gpt-5-5-routing",
            entities=("openai",),
            symbols=("MSFT", "NVDA"),
        ),
    }

    news_pipeline.fetcher.fetch = lambda: seeds
    news_pipeline.extractor.extract = lambda seed: raw_by_url[seed.url]
    news_pipeline.summarizer.assess = lambda raw: assessment_by_url[raw.url]

    selected, _attempts, _candidate_count = news_pipeline.collect_selected()
    titles = [item.title for item, _raw in selected]

    assert sum("Anthropic" in title for title in titles) == 1
    assert "Google and Amazon commit billions to Anthropic AI expansion" in titles
    assert "OpenAI launches GPT-5.5 model routing for developers" in titles


def test_semantic_dedupe_keeps_distinct_model_versions() -> None:
    news_pipeline = NewsPipeline(Settings(rss_sources={}, max_briefing_items=10))
    seeds = [
        ArticleSeed(
            title="OpenAI launches GPT-5.5 for enterprise agents",
            source="OpenAI News",
            url="https://openai.com/news/gpt-5-5",
            published_at=datetime(2026, 4, 25, 1, 0, tzinfo=timezone.utc),
        ),
        ArticleSeed(
            title="OpenAI launches GPT-6 preview for enterprise agents",
            source="OpenAI News",
            url="https://openai.com/news/gpt-6",
            published_at=datetime(2026, 4, 25, 2, 0, tzinfo=timezone.utc),
        ),
    ]
    raw_by_url = {
        seed.url: ArticleRaw(
            title=seed.title,
            source=seed.source,
            url=seed.url,
            published_at=seed.published_at,
            content=seed.title,
        )
        for seed in seeds
    }
    assessment_by_url = {
        seeds[0].url: ArticleAssessment(
            keep=True,
            category="AI",
            importance_score=91,
            title=seeds[0].title,
            summary_en=["OpenAI launched GPT-5.5 for enterprise agents.", "The release updates model routing."],
            summary_zh=["OpenAI 发布面向企业 agent 的 GPT-5.5。", "这次发布更新模型路由。"],
            story_key="openai-gpt-5-5-enterprise-agents",
            entities=("openai",),
            symbols=("MSFT",),
        ),
        seeds[1].url: ArticleAssessment(
            keep=True,
            category="AI",
            importance_score=92,
            title=seeds[1].title,
            summary_en=["OpenAI launched a GPT-6 preview for enterprise agents.", "The preview is a separate model release."],
            summary_zh=["OpenAI 发布面向企业 agent 的 GPT-6 预览。", "这属于另一条模型发布。"],
            story_key="openai-gpt-6-enterprise-agents",
            entities=("openai",),
            symbols=("MSFT",),
        ),
    }

    news_pipeline.fetcher.fetch = lambda: seeds
    news_pipeline.extractor.extract = lambda seed: raw_by_url[seed.url]
    news_pipeline.summarizer.assess = lambda raw: assessment_by_url[raw.url]

    selected, _attempts, _candidate_count = news_pipeline.collect_selected()

    assert {item.story_key for item, _raw in selected} == {
        "openai-gpt-5-5-enterprise-agents",
        "openai-gpt-6-enterprise-agents",
    }
