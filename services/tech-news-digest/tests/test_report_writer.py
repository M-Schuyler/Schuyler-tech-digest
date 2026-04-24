from __future__ import annotations

from news_digest.report import BriefingItem, _overall_takeaway


def test_overall_takeaway_avoids_generic_chip_heat_language() -> None:
    takeaway = _overall_takeaway(
        [
            BriefingItem(
                title="Meta moves part of its AI workload to AWS Graviton CPUs",
                category="Chips",
                summary_en=[],
                summary_zh=["Meta 把部分 AI 负载转到 AWS Graviton CPU。"],
                url="https://example.com/meta-graviton",
                importance_score=90,
            )
        ]
    )

    assert "持续升温" not in takeaway
    assert "价格确认" in takeaway
