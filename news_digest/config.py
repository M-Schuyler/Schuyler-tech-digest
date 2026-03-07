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
    max_articles_per_source: int = 10
    request_timeout: int = 20
    openai_model: str = "gpt-4o-mini"


DEFAULT_SETTINGS = Settings(
    rss_sources={
        "TechCrunch": "https://techcrunch.com/feed/",
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "Wired": "https://www.wired.com/feed/rss",
    },
    max_articles_per_source=int(os.getenv("MAX_ARTICLES_PER_SOURCE", "10")),
    request_timeout=int(os.getenv("REQUEST_TIMEOUT", "20")),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
)
