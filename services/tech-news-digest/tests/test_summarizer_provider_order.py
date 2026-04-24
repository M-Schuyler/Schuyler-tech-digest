from __future__ import annotations

import sys
import types

from news_digest.config import Settings
from news_digest.models import ArticleAssessment, ArticleRaw
from news_digest.summarizer import NewsSummarizer


def _article() -> ArticleRaw:
    return ArticleRaw(
        title="OpenAI launches new agent platform for enterprise workflows",
        source="OpenAI",
        url="https://openai.com/news/agents",
        published_at=None,
        content="OpenAI launched a new AI agent platform for enterprise workflows and automation.",
    )


def _assessment(title: str = "OpenAI launches agent platform") -> ArticleAssessment:
    return ArticleAssessment(
        keep=True,
        category="AI",
        importance_score=90,
        title=title,
        summary_en=[
            "OpenAI launched a new agent platform for enterprise workflows.",
            "The release expands automation capabilities for business users.",
        ],
        summary_zh=[
            "OpenAI 发布了面向企业工作流的新 agent 平台。",
            "这次发布扩展了企业用户的自动化能力。",
        ],
    )


def _settings() -> Settings:
    return Settings(rss_sources={}, openai_model="gpt-5.4-mini", gemini_model="3.1-flash-preview")


def test_summarizer_tries_openai_before_gemini_when_both_are_configured(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    summarizer = NewsSummarizer(_settings())
    calls: list[str] = []

    monkeypatch.setattr(
        summarizer,
        "_assess_with_openai",
        lambda article: calls.append("openai") or _assessment(),
    )
    monkeypatch.setattr(
        summarizer,
        "_assess_with_gemini",
        lambda article: calls.append("gemini") or _assessment("Gemini should not run"),
    )

    result = summarizer.assess(_article())

    assert result is not None
    assert calls == ["openai"]


def test_summarizer_falls_back_to_gemini_after_openai_failure(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    summarizer = NewsSummarizer(_settings())
    calls: list[str] = []

    def openai_failure(article):
        calls.append("openai")
        raise TimeoutError("openai timeout")

    monkeypatch.setattr(summarizer, "_assess_with_openai", openai_failure)
    monkeypatch.setattr(
        summarizer,
        "_assess_with_gemini",
        lambda article: calls.append("gemini") or _assessment("Gemini fallback"),
    )

    result = summarizer.assess(_article())

    assert result is not None
    assert result.title == "Gemini fallback"
    assert calls == ["openai", "gemini"]


def test_summarizer_uses_heuristic_after_openai_and_gemini_fail(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    summarizer = NewsSummarizer(_settings())
    calls: list[str] = []

    def openai_failure(article):
        calls.append("openai")
        raise RuntimeError("openai failed")

    def gemini_failure(article):
        calls.append("gemini")
        raise RuntimeError("gemini failed")

    monkeypatch.setattr(summarizer, "_assess_with_openai", openai_failure)
    monkeypatch.setattr(summarizer, "_assess_with_gemini", gemini_failure)
    monkeypatch.setattr(
        summarizer,
        "_assess_with_heuristic",
        lambda article: calls.append("heuristic") or _assessment("Heuristic fallback"),
    )

    result = summarizer.assess(_article())

    assert result is not None
    assert result.title == "Heuristic fallback"
    assert calls == ["openai", "gemini", "heuristic"]


def test_summarizer_initializes_openai_client_with_base_url(monkeypatch) -> None:
    captured_kwargs: dict[str, str] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_API_KEY", "cliproxy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8317/v1")

    NewsSummarizer(_settings())

    assert captured_kwargs == {
        "api_key": "cliproxy-key",
        "base_url": "http://127.0.0.1:8317/v1",
        "timeout": 20,
    }
