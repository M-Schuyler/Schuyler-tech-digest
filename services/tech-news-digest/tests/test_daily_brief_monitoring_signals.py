from __future__ import annotations

from datetime import datetime, timezone

from news_digest.briefs.composer import _format_monitoring_signal_line
from news_digest.monitoring.models import MonitorSignal, SignalLevel


def test_format_monitoring_signal_line_keeps_reason_symbols_and_entities() -> None:
    signal = MonitorSignal(
        event_id=1,
        level=SignalLevel.DIGEST_CANDIDATE,
        score=76,
        reason="Official source + watched entity openai + mapped symbols MSFT/NVDA.",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )

    line = _format_monitoring_signal_line(signal)

    assert "MSFT / NVDA" in line
    assert "openai" in line
    assert "Official source" in line
