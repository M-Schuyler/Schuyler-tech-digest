from __future__ import annotations

from datetime import datetime, timezone

from news_digest.monitoring.models import MonitorEvent, SignalLevel
from news_digest.monitoring.signal_engine import classify_signal


def event(
    *,
    trust_tier: int,
    entities=("openai",),
    symbols=("MSFT", "NVDA"),
    tags=("ai", "agent"),
    entity_priorities=None,
):
    priorities = entity_priorities
    if priorities is None:
        priorities = {entity: 5 for entity in entities}
    return MonitorEvent(
        source_key="openai-news",
        source_kind="rss",
        title="OpenAI launches workplace agents",
        url="https://openai.com/news/workplace-agents",
        published_at=None,
        first_seen_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        content_hint="Agent controls",
        event_hash="hash-1",
        entities=entities,
        symbols=symbols,
        tags=tags,
        trust_tier=trust_tier,
        raw_metadata={"entity_priorities": priorities},
    )


def test_official_watchlist_event_becomes_interrupt_signal() -> None:
    signal = classify_signal(event(trust_tier=1))

    assert signal.level is SignalLevel.INTERRUPT
    assert signal.score >= 85
    assert "official" in signal.reason.lower()


def test_low_trust_unmapped_event_is_archive_only() -> None:
    signal = classify_signal(event(trust_tier=4, entities=(), symbols=(), tags=("general",)))

    assert signal.level is SignalLevel.ARCHIVE_ONLY
    assert signal.score < 50


def test_official_focus_tag_without_entity_or_symbol_stays_archive_only() -> None:
    signal = classify_signal(event(trust_tier=1, entities=(), symbols=(), tags=("ai", "official")))

    assert signal.level is SignalLevel.ARCHIVE_ONLY
    assert signal.score < 50


def test_mapped_non_official_event_becomes_digest_candidate() -> None:
    signal = classify_signal(
        event(
            trust_tier=3,
            entities=("low-priority-entity",),
            tags=("ai", "agent"),
            entity_priorities={"low-priority-entity": 1},
        )
    )

    assert signal.level is SignalLevel.DIGEST_CANDIDATE
    assert 50 <= signal.score < 85


def test_higher_priority_entity_scores_above_lower_priority_entity() -> None:
    low = event(
        trust_tier=3,
        entities=("low",),
        symbols=("QQQ",),
        entity_priorities={"low": 1},
    )
    high = event(
        trust_tier=3,
        entities=("high",),
        symbols=("QQQ",),
        entity_priorities={"high": 5},
    )

    assert classify_signal(high).score > classify_signal(low).score
