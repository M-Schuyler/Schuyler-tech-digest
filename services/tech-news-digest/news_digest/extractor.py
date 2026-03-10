from __future__ import annotations

import logging
import re

import requests
import trafilatura
from bs4 import BeautifulSoup

from .config import Settings
from .models import ArticleRaw, ArticleSeed

logger = logging.getLogger(__name__)


class ArticleExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            }
        )

    def extract(self, seed: ArticleSeed) -> ArticleRaw | None:
        try:
            response = self.session.get(seed.url, timeout=self.settings.request_timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Failed to fetch article %s: %s", seed.url, exc)
            return None

        content = _extract_main_text(response.text)
        if not content:
            logger.warning("Could not extract readable content from %s", seed.url)
            return None

        return ArticleRaw(
            title=seed.title,
            source=seed.source,
            url=seed.url,
            published_at=seed.published_at,
            content=content,
        )


def _extract_main_text(html: str) -> str:
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        output_format="txt",
        favor_precision=True,
    )
    if text:
        return _cleanup_text(text)

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    fallback_text = "\n".join(p for p in paragraphs if len(p) > 40)
    return _cleanup_text(fallback_text)


def _cleanup_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text
