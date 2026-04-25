from __future__ import annotations

from datetime import date, datetime, timezone

from news_digest.briefs.composer import _format_monitoring_signal_line
from news_digest.models import DailyBrief, WatchSignal
from news_digest.monitoring.models import MonitorEvent, MonitorSignal, SignalLevel
from news_digest.routing.dispatcher import format_daily_brief, format_monitor_signal


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
    event = MonitorEvent(
        id=1,
        source_key="openai-news",
        source_kind="rss",
        title="OpenAI launches workplace agents",
        url="https://openai.com/news/workplace-agents",
        published_at=None,
        first_seen_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        content_hint="",
        event_hash="hash-1",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        trust_tier=1,
    )

    line = _format_monitoring_signal_line(signal, event)

    assert "MSFT / NVDA" in line
    assert "openai" in line
    assert "OpenAI launches workplace agents" in line
    assert "Official source" not in line
    assert "focus tags" not in line


def test_format_monitoring_signal_line_drops_unmapped_unnamed_noise() -> None:
    signal = MonitorSignal(
        event_id=2,
        level=SignalLevel.DIGEST_CANDIDATE,
        score=65,
        reason="Official source + focus tags ai.",
        entities=(),
        symbols=(),
        tags=("ai", "official"),
        created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )

    assert _format_monitoring_signal_line(signal) is None


def test_format_daily_brief_removes_internal_metadata_lines() -> None:
    brief = DailyBrief(
        brief_date_sh=date(2026, 4, 25),
        reference_trade_date_ny=date(2026, 4, 24),
        top_three=["AI 主线继续看商业落点。"],
        ai_section="• OpenAI 发布新模型：这是可读摘要。",
        tech_section="• MSFT：Official source + focus tags ai.",
        market_section="• QQQ：上一日变化 +0.8%",
        cross_section="• MSFT：openai - tier 3 source + mapped symbols MSFT.\n• NVDA：价格确认仍是关键。",
        watchlist=[WatchSignal(symbol="NVDA", reason="看价格确认", priority=5)],
        chart_symbols=["NVDA", "QQQ"],
        generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
    )

    text = format_daily_brief(brief)

    assert "Official source" not in text
    assert "focus tags" not in text
    assert "tier 3 source" not in text
    assert "mapped symbols" not in text
    assert "价格确认仍是关键" in text


def test_format_monitor_signal_uses_public_reason_not_internal_score_reason() -> None:
    signal = MonitorSignal(
        event_id=1,
        level=SignalLevel.INTERRUPT,
        score=92,
        reason="Official source + watched entity openai + mapped symbols MSFT/NVDA + focus tags ai.",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )
    event = MonitorEvent(
        id=1,
        source_key="openai-news",
        source_kind="rss",
        title="OpenAI launches workplace agents",
        url="https://openai.com/news/workplace-agents",
        published_at=None,
        first_seen_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        content_hint="Agent controls for enterprise workflows",
        event_hash="hash-1",
        entities=("openai",),
        symbols=("MSFT", "NVDA"),
        tags=("ai", "agent"),
        trust_tier=1,
    )

    text = format_monitor_signal(signal, event)

    assert "Official source" not in text
    assert "watched entity" not in text
    assert "mapped symbols" not in text
    assert "focus tags" not in text
    assert "OpenAI launches workplace agents" in text
    assert "MSFT / NVDA" in text
