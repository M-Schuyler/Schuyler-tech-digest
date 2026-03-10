from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

from .config import Settings
from .models import ArticleAssessment, ArticleRaw

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {"AI", "Robotics", "Chips", "Big Tech", "Startups"}

EXCLUDED_TITLE_PATTERNS = [
    r"\breview\b",
    r"\bhands[- ]on\b",
    r"\bopinion\b",
    r"\bop-ed\b",
    r"\beditorial\b",
    r"\bgaming\b",
    r"\bgame\b",
    r"\bgadget\b",
    r"\bsmartphone\b",
    r"\biphone\b",
    r"\bandroid phones?\b",
    r"\bbest .*?(phone|laptop|tablet|headphones?)\b",
    r"\btrailer\b",
    r"\bmovie\b",
    r"\bseries\b",
]

FOCUS_PATTERNS = [
    r"\b(ai|llm|language model|foundation model|agentic|generative ai)\b",
    r"\b(robot|robotics|humanoid|autonomous system|drone)\b",
    r"\b(chip|semiconductor|gpu|cpu|foundry|tsmc|nvidia)\b",
    r"\b(apple|google|microsoft|amazon|meta|tesla|openai|anthropic)\b",
    r"\b(startup|funding|raised|series [abcde]|seed round|valuation)\b",
    r"\b(breakthrough|quantum|fusion|new material|novel architecture)\b",
]

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Robotics", ["robot", "robotics", "humanoid", "drone", "autonomous vehicle", "autonomous system"]),
    ("Chips", ["chip", "semiconductor", "gpu", "cpu", "foundry", "fabrication", "wafer", "tsmc", "nvidia"]),
    (
        "Big Tech",
        [
            "apple",
            "google",
            "microsoft",
            "amazon",
            "meta",
            "tesla",
            "alphabet",
            "bytedance",
        ],
    ),
    ("Startups", ["startup", "funding", "raised", "series a", "series b", "series c", "valuation", "venture"]),
    ("AI", ["ai", "llm", "language model", "foundation model", "openai", "anthropic", "chatbot", "agent"]),
]


class NewsSummarizer:
    """Assess, filter and summarize articles for Daily Tech Briefing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._openai_client = None
        self._gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._gemini_model = settings.gemini_model
        self._translation_target = os.getenv("FREE_TRANSLATION_TARGET", "zh-CN")
        self._translation_timeout = int(os.getenv("FREE_TRANSLATION_TIMEOUT", "8"))
        self._min_importance = int(os.getenv("MIN_IMPORTANCE_SCORE", "55"))
        self._google_available = True
        self._mymemory_available = True

        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_api_key:
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(api_key=openai_api_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI client init failed: %s", exc)

    def assess(self, article: ArticleRaw) -> ArticleAssessment | None:
        if _is_obvious_excluded(article.title) and not _matches_focus_topic(article.title):
            return None

        assessment: ArticleAssessment | None = None

        if self._gemini_api_key:
            try:
                assessment = self._assess_with_gemini(article)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Gemini assess failed for %s: %s", article.url, exc)

        if not assessment and self._openai_client:
            try:
                assessment = self._assess_with_openai(article)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI assess failed for %s: %s", article.url, exc)

        if not assessment:
            assessment = self._assess_with_heuristic(article)

        normalized = self._normalize_assessment(article, assessment)
        if not normalized.keep:
            return None
        if normalized.category not in ALLOWED_CATEGORIES:
            return None
        if normalized.importance_score < self._min_importance:
            return None
        return normalized

    def _assess_with_gemini(self, article: ArticleRaw) -> ArticleAssessment:
        prompt = _editor_prompt(article)
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._gemini_model}:generateContent",
            params={"key": self._gemini_api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.15,
                    "responseMimeType": "application/json",
                },
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        raw_text = (
            ((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [{}]
        )[0].get("text", "{}")
        data = _parse_json_object(raw_text)
        return _assessment_from_dict(data, article.title)

    def _assess_with_openai(self, article: ArticleRaw) -> ArticleAssessment:
        response = self._openai_client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.15,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _editor_system_prompt()},
                {"role": "user", "content": _editor_user_prompt(article)},
            ],
        )
        raw_content = response.choices[0].message.content or "{}"
        data = _parse_json_object(raw_content)
        return _assessment_from_dict(data, article.title)

    def _assess_with_heuristic(self, article: ArticleRaw) -> ArticleAssessment:
        text = f"{article.title}\n{article.content}".lower()
        category = _categorize_heuristic(text)

        if _is_obvious_excluded(article.title) and not _matches_focus_topic(text):
            return ArticleAssessment(
                keep=False,
                category="Other",
                importance_score=0,
                title=article.title,
                summary_en=[],
                summary_zh=[],
                rejection_reason="Excluded consumer/gaming/review content",
            )

        if not category:
            return ArticleAssessment(
                keep=False,
                category="Other",
                importance_score=0,
                title=article.title,
                summary_en=[],
                summary_zh=[],
                rejection_reason="Not in key tech focus topics",
            )

        importance_score = _heuristic_importance(text)
        if importance_score < self._min_importance:
            return ArticleAssessment(
                keep=False,
                category=category,
                importance_score=importance_score,
                title=article.title,
                summary_en=[],
                summary_zh=[],
                rejection_reason="Below importance threshold",
            )

        summary_en = _extract_sentences(article.content, 2)
        if len(summary_en) < 2:
            summary_en = _normalize_two_sentences(summary_en, article.content or article.title)

        summary_zh = [self._translate_free(sentence) or _fallback_zh(sentence) for sentence in summary_en]

        return ArticleAssessment(
            keep=True,
            category=category,
            importance_score=importance_score,
            title=article.title,
            summary_en=summary_en[:2],
            summary_zh=summary_zh[:2],
        )

    def _normalize_assessment(self, article: ArticleRaw, assessment: ArticleAssessment) -> ArticleAssessment:
        title = (assessment.title or article.title).strip() or article.title
        keep = bool(assessment.keep)
        category = assessment.category.strip() if assessment.category else "Other"
        if category not in ALLOWED_CATEGORIES:
            category = _categorize_heuristic(f"{title}\n{article.content}".lower()) or category

        summary_en = _normalize_two_sentences(assessment.summary_en, article.content or title)
        summary_zh = _normalize_two_sentences_zh(assessment.summary_zh)
        if len(summary_zh) < 2:
            summary_zh = [self._translate_free(s) or _fallback_zh(s) for s in summary_en]
        else:
            repaired: list[str] = []
            for idx, zh in enumerate(summary_zh[:2]):
                if _contains_cjk(zh):
                    repaired.append(zh)
                else:
                    repaired.append(self._translate_free(summary_en[idx]) or _fallback_zh(summary_en[idx]))
            summary_zh = repaired

        if _is_obvious_excluded(title) and not _matches_focus_topic(f"{title}\n{article.content}"):
            keep = False

        importance = max(0, min(100, int(assessment.importance_score or 0)))
        if importance == 0:
            importance = _heuristic_importance(f"{title}\n{article.content}".lower())

        return ArticleAssessment(
            keep=keep,
            category=category,
            importance_score=importance,
            title=title,
            summary_en=summary_en[:2],
            summary_zh=summary_zh[:2],
            rejection_reason=assessment.rejection_reason,
        )

    def _translate_free(self, text: str) -> str | None:
        clean_text = text.strip()
        if not clean_text:
            return None

        google = self._translate_with_google(clean_text)
        if google:
            return google

        memory = self._translate_with_mymemory(clean_text)
        if memory:
            return memory

        return None

    def _translate_with_google(self, text: str) -> str | None:
        if not self._google_available:
            return None

        endpoint = "https://translate.googleapis.com/translate_a/single"
        try:
            response = requests.get(
                endpoint,
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": self._translation_target,
                    "dt": "t",
                    "q": text,
                },
                timeout=self._translation_timeout,
            )
            response.raise_for_status()
            data = response.json()
            chunks = data[0] if isinstance(data, list) and data else []
            merged = "".join(chunk[0] for chunk in chunks if isinstance(chunk, list) and chunk)
            return merged.strip() or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google free translation failed: %s", exc)
            self._google_available = False
            return None

    def _translate_with_mymemory(self, text: str) -> str | None:
        if not self._mymemory_available:
            return None

        endpoint = "https://api.mymemory.translated.net/get"
        langpair_target = self._translation_target.split("-")[0]
        try:
            response = requests.get(
                endpoint,
                params={"q": text, "langpair": f"en|{langpair_target}"},
                timeout=self._translation_timeout,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
            translated = (data.get("responseData") or {}).get("translatedText")
            return str(translated).strip() if translated else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("MyMemory free translation failed: %s", exc)
            self._mymemory_available = False
            return None


def _editor_system_prompt() -> str:
    return (
        "You are an expert tech editor for an executive daily briefing. "
        "Filter and summarize only high-impact technology news."
    )


def _editor_user_prompt(article: ArticleRaw) -> str:
    return _editor_prompt(article)


def _editor_prompt(article: ArticleRaw) -> str:
    return (
        "Task:\n"
        "1) Decide whether this article should be kept for a high-signal Daily Tech Briefing.\n"
        "2) If keep, output category and concise bilingual summaries.\n\n"
        "Keep ONLY if related to:\n"
        "- AI / LLM\n"
        "- Robotics\n"
        "- Semiconductor / chips\n"
        "- Major tech company announcements\n"
        "- Startup funding\n"
        "- Breakthrough technology\n\n"
        "Remove if mainly about:\n"
        "- phone reviews\n"
        "- gaming\n"
        "- gadget reviews\n"
        "- entertainment\n"
        "- opinion/editorial\n\n"
        "Return strict JSON only, with keys:\n"
        "keep (boolean),\n"
        "category (one of: AI, Robotics, Chips, Big Tech, Startups, Other),\n"
        "importance_score (0-100 integer),\n"
        "title (concise title),\n"
        "summary_en (array of exactly 2 concise English sentences),\n"
        "summary_zh (array of exactly 2 concise Simplified Chinese sentences),\n"
        "rejection_reason (string; empty if keep=true).\n\n"
        f"Article title: {article.title}\n"
        f"Article content:\n{article.content[:9000]}"
    )


def _assessment_from_dict(data: dict[str, Any], default_title: str) -> ArticleAssessment:
    return ArticleAssessment(
        keep=bool(data.get("keep", False)),
        category=str(data.get("category") or "Other"),
        importance_score=_to_int(data.get("importance_score"), 0),
        title=str(data.get("title") or default_title),
        summary_en=[str(x).strip() for x in (data.get("summary_en") or []) if str(x).strip()],
        summary_zh=[str(x).strip() for x in (data.get("summary_zh") or []) if str(x).strip()],
        rejection_reason=str(data.get("rejection_reason") or ""),
    )


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        return {}

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _normalize_two_sentences(items: list[str], fallback_text: str) -> list[str]:
    clean = [s.strip() for s in items if s and s.strip()]
    if len(clean) >= 2:
        return [_ensure_terminal_punct(clean[0]), _ensure_terminal_punct(clean[1])]

    extracted = _extract_sentences(fallback_text, 2)
    for sentence in extracted:
        if len(clean) >= 2:
            break
        clean.append(sentence)

    while len(clean) < 2:
        clean.append(clean[0] if clean else "No key update available.")

    return [_ensure_terminal_punct(clean[0]), _ensure_terminal_punct(clean[1])]


def _normalize_two_sentences_zh(items: list[str]) -> list[str]:
    clean = [s.strip() for s in items if s and s.strip()]
    return clean[:2]


def _extract_sentences(text: str, limit: int) -> list[str]:
    chunks = re.split(r"(?<=[.!?。！？])\s+", (text or "").strip())
    out: list[str] = []
    for chunk in chunks:
        sentence = re.sub(r"\s+", " ", chunk).strip()
        if len(sentence) < 35:
            continue
        out.append(_ensure_terminal_punct(sentence))
        if len(out) >= limit:
            break
    return out


def _ensure_terminal_punct(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    if stripped[-1] in ".!?。！？":
        return stripped
    return stripped + "."


def _is_obvious_excluded(text: str) -> bool:
    lower = (text or "").lower()
    return any(re.search(pattern, lower) for pattern in EXCLUDED_TITLE_PATTERNS)


def _matches_focus_topic(text: str) -> bool:
    lower = (text or "").lower()
    return any(re.search(pattern, lower) for pattern in FOCUS_PATTERNS)


def _categorize_heuristic(text: str) -> str | None:
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                return category
    return None


def _heuristic_importance(text: str) -> int:
    score = 45
    boosts = [
        r"\b(announced|launch|released|partnership|acquire|acquisition)\b",
        r"\b(funding|raised|series [abcde]|valuation|billion|million)\b",
        r"\b(breakthrough|first|new model|new chip|new architecture)\b",
        r"\b(regulation|court|policy|department)\b",
    ]
    for pattern in boosts:
        if re.search(pattern, text):
            score += 12

    if _matches_focus_topic(text):
        score += 10

    if _is_obvious_excluded(text):
        score -= 25

    return max(0, min(100, score))


def _contains_cjk(text: str) -> bool:
    return re.search(r"[\u4e00-\u9fff]", text) is not None


def _fallback_zh(english_sentence: str) -> str:
    return f"（中文翻译暂不可用）{english_sentence}"
