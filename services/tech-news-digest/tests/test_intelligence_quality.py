from __future__ import annotations

from datetime import date, datetime

from news_digest.config import load_runtime_settings
from news_digest.intelligence.cross_correlator import CrossCorrelator
from news_digest.intelligence.topic_ranker import TopicRanker
from news_digest.intelligence.watchlist_builder import WatchlistBuilder
from news_digest.models import CloseSummary, WatchSignal
from news_digest.report import BriefingItem


def _item(
    *,
    title: str,
    category: str = "Chips",
    summary_zh: list[str] | None = None,
    importance_score: int = 88,
) -> BriefingItem:
    return BriefingItem(
        title=title,
        category=category,
        summary_en=[],
        summary_zh=summary_zh or [],
        url="https://example.com/story",
        importance_score=importance_score,
    )


def _close_summary() -> CloseSummary:
    return CloseSummary(
        trade_date_ny=date(2026, 4, 23),
        closing_verdict="NVDA 最弱，QQQ 小幅走强，资金没有无差别追 AI。",
        strongest_assets=["QQQ", "META"],
        weakest_assets=["NVDA"],
        ai_tech_thread="算力链条分化。",
        crypto_mood="中性",
        tomorrow_watch=[],
        generated_at=datetime(2026, 4, 23, 17, 0),
    )


def test_topic_ranker_treats_meta_graviton_and_weak_nvda_as_compute_divergence() -> None:
    ranker = TopicRanker(load_runtime_settings())
    item = _item(
        title="Meta moves part of its AI workload to AWS Graviton CPUs",
        summary_zh=["Meta 把部分 AI 负载转到 AWS Graviton CPU，以降低昂贵 GPU 算力成本。"],
    )

    [line] = ranker.rank([item], close_summary=_close_summary())[:1]

    assert "升温" not in line
    assert "GPU" in line
    assert "NVDA" in line
    assert any(word in line for word in ("分化", "降本", "承压"))


def test_watchlist_reasons_are_symbol_specific_not_template_repeats() -> None:
    builder = WatchlistBuilder()
    items = [
        _item(title="Microsoft adds OpenAI model routing to Azure", category="AI"),
        _item(title="Google releases Gemini agent tooling for Workspace", category="AI"),
        _item(title="NVIDIA demand cools as hyperscalers test CPU inference", category="Chips"),
    ]

    watchlist = builder.build(items, _close_summary())
    reasons = [item.reason for item in watchlist]

    assert len(set(reasons)) == len(reasons)
    assert "AI 相关更新还在堆积" not in " ".join(reasons)
    assert "算力和芯片叙事继续发酵" not in " ".join(reasons)


def test_cross_correlator_marks_weak_watchlist_symbol_as_risk_validation_not_chase() -> None:
    section = CrossCorrelator().compose(
        top_three=["算力链条在分化：Meta 转向 CPU 降本；NVDA 同时偏弱。"],
        close_summary=_close_summary(),
        watchlist=[WatchSignal(symbol="NVDA", reason="GPU 成本压力验证点", priority=10)],
    )

    assert "不是追涨" in section
    assert "约束" in section
