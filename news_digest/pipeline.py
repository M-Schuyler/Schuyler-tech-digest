from __future__ import annotations

import logging
from datetime import date

from .config import DEFAULT_SETTINGS, Settings
from .db import NewsRepository, StoredArticle
from .extractor import ArticleExtractor
from .fetchers import RSSFetcher
from .notifier import TelegramNotifier
from .report import MarkdownReportWriter
from .summarizer import NewsSummarizer

logger = logging.getLogger(__name__)


class NewsPipeline:
    def __init__(self, settings: Settings = DEFAULT_SETTINGS) -> None:
        self.settings = settings
        self.fetcher = RSSFetcher(settings)
        self.extractor = ArticleExtractor(settings)
        self.summarizer = NewsSummarizer(settings)
        self.repository = NewsRepository()
        self.report_writer = MarkdownReportWriter(max_highlights=settings.daily_highlight_count)
        self.notifier = TelegramNotifier()

    def run(self, report_date: date | None = None) -> tuple[str, int]:
        run_day = report_date or date.today()

        seeds = self.fetcher.fetch()
        report_items: list[StoredArticle] = []

        for seed in seeds:
            raw = self.extractor.extract(seed)
            if not raw:
                continue

            summary = self.summarizer.summarize(raw)
            article_day = raw.published_at.date().isoformat() if raw.published_at else run_day.isoformat()
            item = StoredArticle(
                title=raw.title,
                source=raw.source,
                summary=summary.summary_text,
                keywords=", ".join(summary.keywords),
                url=raw.url,
                date=article_day,
            )
            self.repository.upsert(item)
            report_items.append(item)

        report_path = self.report_writer.write(run_day, report_items)
        self.notifier.send_report(run_day, report_path, len(report_items))
        logger.info("Report generated: %s (items=%s)", report_path, len(report_items))

        return str(report_path), len(report_items)
