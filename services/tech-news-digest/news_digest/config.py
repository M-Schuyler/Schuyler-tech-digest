from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
DB_PATH = DATA_DIR / "tech_news.db"


@dataclass(frozen=True)
class Settings:
    rss_sources: dict[str, str]
    max_articles_per_source: int = 20
    request_timeout: int = 20
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-2.5-flash"
    max_briefing_items: int = 10


DEFAULT_SETTINGS = Settings(
    rss_sources={
        "TechCrunch": "https://techcrunch.com/feed/",
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "Wired": "https://www.wired.com/feed/rss",
        "MIT Technology Review": "https://www.technologyreview.com/feed/",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
    },
    max_articles_per_source=int(os.getenv("MAX_ARTICLES_PER_SOURCE", "20")),
    request_timeout=int(os.getenv("REQUEST_TIMEOUT", "20")),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    max_briefing_items=int(os.getenv("MAX_BRIEFING_ITEMS", "10")),
)
