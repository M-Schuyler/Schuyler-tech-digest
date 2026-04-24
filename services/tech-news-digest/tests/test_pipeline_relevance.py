from __future__ import annotations

from datetime import datetime, timezone

from news_digest.models import ArticleSeed
from news_digest import pipeline


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
