from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ArticleSeed:
    title: str
    source: str
    url: str
    published_at: datetime | None


@dataclass
class ArticleRaw:
    title: str
    source: str
    url: str
    published_at: datetime | None
    content: str


@dataclass
class ArticleSummary:
    sentences_en: list[str]
    sentences_zh: list[str]
    keywords: list[str]

    @property
    def summary_text(self) -> str:
        pairs = self.bilingual_pairs
        return "\n".join(f"{en}\n{zh}" for en, zh in pairs)

    @property
    def bilingual_pairs(self) -> list[tuple[str, str]]:
        max_len = max(len(self.sentences_en), len(self.sentences_zh))
        pairs: list[tuple[str, str]] = []
        for idx in range(max_len):
            en = self.sentences_en[idx] if idx < len(self.sentences_en) else ""
            zh = self.sentences_zh[idx] if idx < len(self.sentences_zh) else ""
            pairs.append((en, zh))
        return pairs


@dataclass
class ArticleAssessment:
    keep: bool
    category: str
    importance_score: int
    title: str
    summary_en: list[str]
    summary_zh: list[str]
    rejection_reason: str = ""
