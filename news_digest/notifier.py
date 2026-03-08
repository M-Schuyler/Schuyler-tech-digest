from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.enabled = bool(self.bot_token and self.chat_id)

    def send_report(self, report_date: date, report_path: Path, article_count: int) -> bool:
        if not self.enabled:
            logger.info("Telegram notifier disabled (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
            return False

        try:
            report_text = report_path.read_text(encoding="utf-8")
            chunks = _split_text(report_text, max_len=3500)
            header = f"Daily Tech Briefing {report_date.isoformat()}\\nItems: {article_count}"
            self._send_message(header)
            for chunk in chunks:
                self._send_message(chunk)
            self._send_document(report_path, report_date, article_count)
            logger.info("Telegram report sent: %s", report_path)
            return True
        except requests.RequestException as exc:
            logger.warning("Failed to send Telegram message: %s", exc)
            return False

    def _send_message(self, text: str) -> None:
        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        response = requests.post(
            endpoint,
            data={
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
            timeout=30,
        )
        response.raise_for_status()

    def _send_document(self, report_path: Path, report_date: date, article_count: int) -> None:
        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        caption = f"Daily Tech Briefing {report_date.isoformat()} (Markdown)\\nItems: {article_count}"
        with report_path.open("rb") as report_file:
            response = requests.post(
                endpoint,
                data={"chat_id": self.chat_id, "caption": caption},
                files={"document": (report_path.name, report_file, "text/markdown")},
                timeout=30,
            )
            response.raise_for_status()


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > max_len and current:
            chunks.append(current)
            current = line
        else:
            current += line

    if current:
        chunks.append(current)
    return chunks
