from __future__ import annotations

from .models import MonitorEvent, MonitorSignal, SignalLevel

FOCUS_TAGS = {"ai", "agent", "compute", "crypto", "risk"}
TRUST_TIER_POINTS = {
    1: 35,
    2: 25,
    3: 10,
}


def classify_signal(event: MonitorEvent) -> MonitorSignal:
    score = 20
    reasons: list[str] = []

    trust_points = TRUST_TIER_POINTS.get(event.trust_tier, 0)
    score += trust_points
    if event.trust_tier == 1:
        reasons.append("Official source")
    elif trust_points:
        reasons.append(f"tier {event.trust_tier} source")

    if event.entities:
        max_priority = _max_matched_entity_priority(event)
        score += 20 + (max_priority * 2)
        reasons.append(f"watched entity {'/'.join(event.entities)}")

    if event.symbols:
        score += 15
        reasons.append(f"mapped symbols {'/'.join(event.symbols)}")

    focus_tags = sorted(set(event.tags).intersection(FOCUS_TAGS))
    if focus_tags:
        score += 10
        reasons.append(f"focus tags {'/'.join(focus_tags)}")

    if not event.entities and not event.symbols:
        score = min(score, 45)

    score = min(score, 100)
    if score >= 85:
        level = SignalLevel.INTERRUPT
    elif score >= 50:
        level = SignalLevel.DIGEST_CANDIDATE
    else:
        level = SignalLevel.ARCHIVE_ONLY

    return MonitorSignal(
        event_id=event.id or 0,
        level=level,
        score=score,
        reason=" + ".join(reasons) + "." if reasons else "No strong watchlist or source signal.",
        entities=event.entities,
        symbols=event.symbols,
        tags=event.tags,
        created_at=event.first_seen_at,
    )


def _max_matched_entity_priority(event: MonitorEvent) -> int:
    raw_priorities = event.raw_metadata.get("entity_priorities") or {}
    max_priority = 0
    for entity in event.entities:
        if entity not in raw_priorities:
            continue
        try:
            priority = int(raw_priorities[entity])
        except (TypeError, ValueError):
            continue
        max_priority = max(max_priority, min(max(priority, 1), 5))
    return max_priority
