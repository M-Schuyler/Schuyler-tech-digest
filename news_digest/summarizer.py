from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter

import requests

from .config import Settings
from .models import ArticleRaw, ArticleSummary

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "for",
    "to",
    "of",
    "in",
    "on",
    "at",
    "with",
    "by",
    "from",
    "this",
    "that",
    "these",
    "those",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "as",
    "about",
    "into",
    "over",
    "after",
    "before",
    "than",
    "their",
    "they",
    "them",
    "you",
    "your",
    "we",
    "our",
    "he",
    "she",
    "his",
    "her",
    "not",
    "can",
    "will",
    "just",
    "more",
    "most",
    "new",
}


class NewsSummarizer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        self._translation_target = os.getenv("FREE_TRANSLATION_TARGET", "zh-CN")
        self._translation_timeout = int(os.getenv("FREE_TRANSLATION_TIMEOUT", "15"))
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=api_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI client init failed, use local summary fallback: %s", exc)

    def summarize(self, article: ArticleRaw) -> ArticleSummary:
        if self._client:
            try:
                return self._summarize_with_openai(article)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI summary failed for %s: %s", article.url, exc)

        fallback = _fallback_summary(article.content)
        return self._fill_chinese_with_free_translation(fallback)

    def _summarize_with_openai(self, article: ArticleRaw) -> ArticleSummary:
        prompt = (
            "You are a bilingual tech news analyst. Return strict JSON with keys: "
            "summary_en (array of exactly 3 concise English sentences), "
            "summary_zh (array of exactly 3 concise Simplified Chinese translations aligned by index), and "
            "keywords (array of exactly 3 short English keywords)."
        )
        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        f"Title: {article.title}\n"
                        f"Content:\n{article.content[:8000]}"
                    ),
                },
            ],
        )

        raw_content = response.choices[0].message.content or "{}"
        data = json.loads(raw_content)

        en_sentences = _normalize_sentences(data.get("summary_en") or [])
        zh_sentences = _normalize_chinese_sentences(data.get("summary_zh") or [])
        keywords = _normalize_keywords(data.get("keywords") or [])

        if len(en_sentences) < 3 or len(zh_sentences) < 3 or len(keywords) < 3:
            fallback = self._fill_chinese_with_free_translation(_fallback_summary(article.content))
            if len(en_sentences) < 3:
                en_sentences = fallback.sentences_en
            if len(zh_sentences) < 3:
                zh_sentences = fallback.sentences_zh
            if len(keywords) < 3:
                keywords = fallback.keywords

        en_sentences, zh_sentences = _align_bilingual(en_sentences, zh_sentences)
        return ArticleSummary(
            sentences_en=en_sentences[:3],
            sentences_zh=zh_sentences[:3],
            keywords=keywords[:3],
        )

    def _fill_chinese_with_free_translation(self, summary: ArticleSummary) -> ArticleSummary:
        translated: list[str] = []
        for sentence in summary.sentences_en:
            translated_sentence = self._translate_free(sentence)
            translated.append(translated_sentence or _missing_translation_notice(sentence))

        return ArticleSummary(
            sentences_en=summary.sentences_en[:3],
            sentences_zh=translated[:3],
            keywords=summary.keywords[:3],
        )

    def _translate_free(self, text: str) -> str | None:
        clean_text = text.strip()
        if not clean_text:
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
                    "q": clean_text,
                },
                timeout=self._translation_timeout,
            )
            response.raise_for_status()
            data = response.json()
            chunks = data[0] if isinstance(data, list) and data else []
            merged = "".join(chunk[0] for chunk in chunks if isinstance(chunk, list) and chunk)
            return merged.strip() or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Free translation failed: %s", exc)
            return None


def _fallback_summary(content: str) -> ArticleSummary:
    sentences = _split_sentences(content)

    if not sentences:
        en = [
            "Unable to extract enough text for this article.",
            "Please open the original link for full details.",
            "This item was still recorded in the daily report.",
        ]
        zh = [
            "无法提取足够正文内容。",
            "请打开原文链接查看完整信息。",
            "该新闻仍已记录到每日日报。",
        ]
        return ArticleSummary(sentences_en=en, sentences_zh=zh, keywords=["technology", "news", "update"])

    scores = _sentence_scores(sentences)
    top = sorted(range(len(sentences)), key=lambda idx: scores[idx], reverse=True)[:3]
    en_selected = [_shorten_sentence(sentences[idx]) for idx in sorted(top)]

    while len(en_selected) < 3:
        en_selected.append(en_selected[-1])

    zh_selected = [_missing_translation_notice(en) for en in en_selected]
    keywords = _extract_keywords(content)
    return ArticleSummary(sentences_en=en_selected[:3], sentences_zh=zh_selected[:3], keywords=keywords[:3])


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = re.split(r"(?<=[.!?。！？])\s+", text)
    if len(chunks) < 3:
        chunks = re.split(r"(?<=[.!?;。！？；])\s*", text)
    return [chunk.strip() for chunk in chunks if len(chunk.strip()) > 30]


def _sentence_scores(sentences: list[str]) -> list[int]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", " ".join(sentences).lower())
    freq = Counter(word for word in words if word not in STOPWORDS)

    scores: list[int] = []
    for sentence in sentences:
        sentence_words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", sentence.lower())
        score = sum(freq[word] for word in sentence_words if word in freq)
        scores.append(score)

    return scores


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text.lower())
    freq = Counter(word for word in words if word not in STOPWORDS)
    keywords = [word for word, _ in freq.most_common(3)]

    while len(keywords) < 3:
        filler = ["technology", "innovation", "startup"]
        keywords.append(filler[len(keywords)])

    return keywords[:3]


def _normalize_sentences(items: list[str]) -> list[str]:
    clean = [_shorten_sentence(str(item).strip()) for item in items if str(item).strip()]
    return clean[:3]


def _normalize_chinese_sentences(items: list[str]) -> list[str]:
    clean = [str(item).strip() for item in items if str(item).strip()]
    return clean[:3]


def _normalize_keywords(items: list[str]) -> list[str]:
    clean = [str(item).strip() for item in items if str(item).strip()]
    unique: list[str] = []
    seen: set[str] = set()
    for item in clean:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:3]


def _shorten_sentence(sentence: str, max_words: int = 35) -> str:
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    return " ".join(words[:max_words]) + "..."


def _align_bilingual(en_sentences: list[str], zh_sentences: list[str]) -> tuple[list[str], list[str]]:
    en = en_sentences[:]
    zh = zh_sentences[:]

    while len(en) < 3:
        en.append(en[-1] if en else "No summary available.")
    while len(zh) < 3:
        base = en[len(zh)] if len(zh) < len(en) else "No summary available."
        zh.append(_missing_translation_notice(base))

    return en[:3], zh[:3]


def _missing_translation_notice(english_sentence: str) -> str:
    return f"（中文翻译暂不可用，保留英文原文）{english_sentence}"
