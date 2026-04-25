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
SCHEMA_CATEGORIES = sorted([*ALLOWED_CATEGORIES, "Other"])

ARTICLE_ASSESSMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "keep",
        "category",
        "importance_score",
        "title",
        "summary_en",
        "summary_zh",
        "rejection_reason",
        "story_key",
        "entities",
        "symbols",
    ],
    "properties": {
        "keep": {"type": "boolean"},
        "category": {"type": "string", "enum": SCHEMA_CATEGORIES},
        "importance_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "title": {"type": "string", "minLength": 1, "maxLength": 120},
        "summary_en": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {"type": "string", "minLength": 20, "maxLength": 220},
        },
        "summary_zh": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {"type": "string", "minLength": 8, "maxLength": 160},
        },
        "rejection_reason": {"type": "string", "maxLength": 160},
        "story_key": {"type": "string", "minLength": 1, "maxLength": 90},
        "entities": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string", "minLength": 1, "maxLength": 40},
        },
        "symbols": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string", "minLength": 1, "maxLength": 12},
        },
    },
}

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

INTERNAL_METADATA_PATTERNS = [
    "focus tags",
    "tier 1 source",
    "tier 2 source",
    "tier 3 source",
    "tier source",
    "mapped symbols",
    "official source",
    "watched entity",
    "source signal",
]


class AssessmentValidationError(ValueError):
    pass


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
        openai_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        if openai_api_key:
            try:
                from openai import OpenAI

                openai_kwargs = {"api_key": openai_api_key, "timeout": settings.request_timeout}
                if openai_base_url:
                    openai_kwargs["base_url"] = openai_base_url
                self._openai_client = OpenAI(**openai_kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI client init failed: %s", exc)

    def assess(self, article: ArticleRaw) -> ArticleAssessment | None:
        if _is_obvious_excluded(article.title) and not _matches_focus_topic(article.title):
            return None

        assessment: ArticleAssessment | None = None

        if self._openai_client:
            try:
                assessment = self._assess_with_openai(article)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI assess failed for %s: %s", article.url, exc)

        if not assessment and self._gemini_api_key:
            try:
                assessment = self._assess_with_gemini(article)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Gemini assess failed for %s: %s", article.url, exc)

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
        validation_error = ""
        for _attempt in range(2):
            prompt = _editor_prompt(article, validation_error=validation_error)
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
            try:
                return _validated_assessment_from_dict(data, article)
            except AssessmentValidationError as exc:
                validation_error = str(exc)
        raise AssessmentValidationError(validation_error or "Gemini output failed validation")

    def _assess_with_openai(self, article: ArticleRaw) -> ArticleAssessment:
        validation_error = ""
        for _attempt in range(2):
            response = self._openai_client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=0.15,
                response_format=_openai_json_schema_response_format(),
                messages=[
                    {"role": "system", "content": _editor_system_prompt()},
                    {"role": "user", "content": _editor_user_prompt(article, validation_error=validation_error)},
                ],
            )
            raw_content = response.choices[0].message.content or "{}"
            data = _parse_json_object(raw_content)
            try:
                return _validated_assessment_from_dict(data, article)
            except AssessmentValidationError as exc:
                validation_error = str(exc)
        raise AssessmentValidationError(validation_error or "OpenAI output failed validation")

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
            story_key=_build_story_key(article.title),
            entities=_extract_entities(f"{article.title}\n{article.content}"),
            symbols=_extract_symbols(f"{article.title}\n{article.content}"),
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
            story_key=assessment.story_key or _build_story_key(title),
            entities=assessment.entities or _extract_entities(f"{title}\n{article.content}"),
            symbols=assessment.symbols or _extract_symbols(f"{title}\n{article.content}"),
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
        "Filter and summarize only high-impact technology news. "
        "Never expose internal scoring metadata such as focus tags, source tiers, or mapped symbols."
    )


def _editor_user_prompt(article: ArticleRaw, *, validation_error: str = "") -> str:
    return _editor_prompt(article, validation_error=validation_error)


def _editor_prompt(article: ArticleRaw, *, validation_error: str = "") -> str:
    repair_instruction = ""
    if validation_error:
        repair_instruction = (
            "Previous output failed validation: "
            f"{validation_error}\nReturn a corrected JSON object only.\n\n"
        )

    return (
        repair_instruction +
        "Task:\n"
        "1) Decide whether this article should be kept for a high-signal Daily Tech Briefing.\n"
        "2) If keep, output category, compact bilingual summaries, story key, entities and symbols.\n\n"
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
        "Do not include internal phrases such as focus tags, tier source, mapped symbols, "
        "Official source or watched entity in any user-facing field.\n"
        "Do not repeat the same phrase. Do not end any field with ellipses.\n\n"
        "Return strict JSON only matching this JSON Schema:\n"
        f"{json.dumps(ARTICLE_ASSESSMENT_SCHEMA, ensure_ascii=False)}\n\n"
        f"Article title: {article.title}\n"
        f"Article content:\n{article.content[:9000]}"
    )


def _openai_json_schema_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "article_assessment",
            "strict": True,
            "schema": ARTICLE_ASSESSMENT_SCHEMA,
        },
    }


def _assessment_from_dict(data: dict[str, Any], default_title: str) -> ArticleAssessment:
    return ArticleAssessment(
        keep=bool(data.get("keep", False)),
        category=str(data.get("category") or "Other"),
        importance_score=_to_int(data.get("importance_score"), 0),
        title=str(data.get("title") or default_title),
        summary_en=[str(x).strip() for x in (data.get("summary_en") or []) if str(x).strip()],
        summary_zh=[str(x).strip() for x in (data.get("summary_zh") or []) if str(x).strip()],
        rejection_reason=str(data.get("rejection_reason") or ""),
        story_key=_normalize_story_key(str(data.get("story_key") or default_title)),
        entities=_normalize_tuple(data.get("entities")),
        symbols=tuple(symbol.upper() for symbol in _normalize_tuple(data.get("symbols"))),
    )


def _validated_assessment_from_dict(data: dict[str, Any], article: ArticleRaw) -> ArticleAssessment:
    if not isinstance(data, dict) or not data:
        raise AssessmentValidationError("empty or non-object JSON")

    missing = [key for key in ARTICLE_ASSESSMENT_SCHEMA["required"] if key not in data]
    if missing:
        raise AssessmentValidationError(f"missing required fields: {', '.join(missing)}")

    assessment = _assessment_from_dict(data, article.title)
    if assessment.category not in SCHEMA_CATEGORIES:
        raise AssessmentValidationError(f"unsupported category: {assessment.category}")
    if not 0 <= assessment.importance_score <= 100:
        raise AssessmentValidationError("importance_score must be 0-100")

    if assessment.keep:
        _validate_public_text("title", assessment.title, max_len=120)
        _validate_story_key(assessment.story_key)
        _validate_list("summary_en", assessment.summary_en, expected_len=2, max_len=220, require_cjk=False)
        _validate_list("summary_zh", assessment.summary_zh, expected_len=2, max_len=160, require_cjk=True)
    return assessment


def _validate_story_key(value: str) -> None:
    if not value or len(value) > 90:
        raise AssessmentValidationError("story_key must be 1-90 chars")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise AssessmentValidationError("story_key must be lowercase slug text")


def _validate_list(
    field: str,
    values: list[str],
    *,
    expected_len: int,
    max_len: int,
    require_cjk: bool,
) -> None:
    if len(values) != expected_len:
        raise AssessmentValidationError(f"{field} must contain exactly {expected_len} items")
    for value in values:
        _validate_public_text(field, value, max_len=max_len)
        if require_cjk and not _contains_cjk(value):
            raise AssessmentValidationError(f"{field} must be Simplified Chinese")


def _validate_public_text(field: str, value: str, *, max_len: int) -> None:
    text = (value or "").strip()
    if not text:
        raise AssessmentValidationError(f"{field} cannot be empty")
    if len(text) > max_len:
        raise AssessmentValidationError(f"{field} too long")
    if text.endswith(("...", "…")):
        raise AssessmentValidationError(f"{field} appears truncated")
    lower = text.lower()
    if any(pattern in lower for pattern in INTERNAL_METADATA_PATTERNS):
        raise AssessmentValidationError(f"{field} leaks internal metadata")
    if _has_repetitive_loop(text):
        raise AssessmentValidationError(f"{field} appears repetitive")


def _has_repetitive_loop(text: str) -> bool:
    words = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text.lower())
    if len(words) < 4:
        return False
    for width in (1, 2, 3):
        counts: dict[tuple[str, ...], int] = {}
        for idx in range(0, len(words) - width + 1):
            key = tuple(words[idx : idx + width])
            counts[key] = counts.get(key, 0) + 1
            if counts[key] >= 3:
                return True
    return False


def _normalize_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        normalized = re.sub(r"\s+", " ", str(item).strip().lower())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return tuple(result)


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


def _build_story_key(title: str) -> str:
    text = title.lower()
    normalized_models = re.sub(
        r"\b(gpt|claude|gemini|deepseek|llama|mistral)[-\s]?(\d+(?:\.\d+)?)\b",
        lambda match: f"{match.group(1)}-{match.group(2).replace('.', '-')}",
        text,
    )
    tokens = re.findall(r"[a-z0-9]+", normalized_models)
    stop_words = {
        "the",
        "a",
        "an",
        "to",
        "for",
        "and",
        "or",
        "of",
        "in",
        "on",
        "with",
        "from",
        "is",
        "are",
        "its",
        "new",
        "launch",
        "launches",
        "launched",
        "model",
        "models",
    }
    selected = [token for token in tokens if token not in stop_words][:8]
    return _normalize_story_key("-".join(selected) or "story")


def _normalize_story_key(value: str) -> str:
    text = value.lower()
    text = re.sub(
        r"\b(gpt|claude|gemini|deepseek|llama|mistral)[-\s]?(\d+(?:\.\d+)?)\b",
        lambda match: f"{match.group(1)}-{match.group(2).replace('.', '-')}",
        text,
    )
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-+", "-", text)
    return text[:90].strip("-") or "story"


def _extract_entities(text: str) -> tuple[str, ...]:
    known = (
        "openai",
        "anthropic",
        "google",
        "alphabet",
        "amazon",
        "microsoft",
        "meta",
        "nvidia",
        "apple",
        "deepmind",
        "tesla",
    )
    lower = text.lower()
    return tuple(entity for entity in known if re.search(rf"\b{re.escape(entity)}\b", lower))


def _extract_symbols(text: str) -> tuple[str, ...]:
    mapping = {
        "openai": ("MSFT", "NVDA"),
        "anthropic": ("GOOGL", "AMZN"),
        "google": ("GOOGL",),
        "alphabet": ("GOOGL",),
        "amazon": ("AMZN",),
        "microsoft": ("MSFT",),
        "meta": ("META",),
        "nvidia": ("NVDA",),
        "apple": ("AAPL",),
        "tesla": ("TSLA",),
        "bitcoin": ("BTC",),
        "ethereum": ("ETH",),
    }
    lower = text.lower()
    symbols: list[str] = []
    for keyword, values in mapping.items():
        if not re.search(rf"\b{re.escape(keyword)}\b", lower):
            continue
        for symbol in values:
            if symbol not in symbols:
                symbols.append(symbol)
    return tuple(symbols)
