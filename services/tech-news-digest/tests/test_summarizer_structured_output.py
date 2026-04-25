from __future__ import annotations

from types import SimpleNamespace

from news_digest.config import Settings
from news_digest.models import ArticleRaw
from news_digest.summarizer import NewsSummarizer


def _settings() -> Settings:
    return Settings(rss_sources={}, openai_model="gpt-5.4-mini", gemini_model="3.1-flash-preview")


def _article() -> ArticleRaw:
    return ArticleRaw(
        title="OpenAI launches GPT-5.5 model routing for enterprise agents",
        source="OpenAI News",
        url="https://openai.com/news/gpt-5-5-routing",
        published_at=None,
        content=(
            "OpenAI launched GPT-5.5 model routing for enterprise agents. "
            "The release changes how developers route tasks across models."
        ),
    )


class _FakeOpenAIClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.responses.pop(0)
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


def test_openai_assessment_uses_json_schema_and_repairs_bad_structured_output(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "local-key")
    summarizer = NewsSummarizer(_settings())
    summarizer._openai_client = _FakeOpenAIClient(
        [
            """
            {
              "keep": true,
              "category": "AI",
              "importance_score": 95,
              "title": "Project Maven...",
              "summary_en": ["Project Maven Project Maven Project Maven Project Maven."],
              "summary_zh": ["focus tags ai Project Maven Project Maven."],
              "story_key": "openai-gpt-5-5-routing",
              "entities": ["openai"],
              "symbols": ["MSFT"]
            }
            """,
            """
            {
              "keep": true,
              "category": "AI",
              "importance_score": 95,
              "title": "OpenAI launches GPT-5.5 model routing",
              "summary_en": [
                "OpenAI launched GPT-5.5 routing for enterprise agents.",
                "The release changes how developers assign work across models."
              ],
              "summary_zh": [
                "OpenAI 发布面向企业 agent 的 GPT-5.5 路由能力。",
                "这次发布改变开发者在模型之间分配任务的方式。"
              ],
              "rejection_reason": "",
              "story_key": "openai-gpt-5-5-routing",
              "entities": ["openai"],
              "symbols": ["MSFT", "NVDA"]
            }
            """,
        ]
    )

    assessment = summarizer._assess_with_openai(_article())

    assert assessment.title == "OpenAI launches GPT-5.5 model routing"
    assert assessment.story_key == "openai-gpt-5-5-routing"
    assert assessment.entities == ("openai",)
    assert assessment.symbols == ("MSFT", "NVDA")
    assert len(summarizer._openai_client.calls) == 2
    assert summarizer._openai_client.calls[0]["response_format"]["type"] == "json_schema"
    assert "Previous output failed validation" in summarizer._openai_client.calls[1]["messages"][-1]["content"]


def test_bad_openai_output_falls_back_to_heuristic_after_repair_failure(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "local-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    summarizer = NewsSummarizer(_settings())
    summarizer._openai_client = _FakeOpenAIClient(
        [
            '{"keep": true, "category": "AI", "importance_score": 90, "title": "Project Maven..."}',
            '{"keep": true, "category": "AI", "importance_score": 90, "title": "Project Maven..."}',
        ]
    )

    assessment = summarizer.assess(_article())

    assert assessment is not None
    assert assessment.title == _article().title
    assert assessment.story_key == "openai-gpt-5-5-routing-enterprise-agents"
