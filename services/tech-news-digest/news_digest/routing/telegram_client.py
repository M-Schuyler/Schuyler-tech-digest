from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from ..config import BotConfig

logger = logging.getLogger(__name__)


class TelegramBotClient:
    def __init__(self, bot: BotConfig) -> None:
        self.bot = bot
        self.enabled = bot.enabled

    def send_message(self, text: str) -> bool:
        if not self.enabled:
            logger.info("Telegram client disabled; skipping text send")
            return False

        response = requests.post(
            self._endpoint("sendMessage"),
            data={
                "chat_id": self.bot.chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
            timeout=30,
        )
        response.raise_for_status()
        return True

    def send_photo(self, photo_path: Path, caption: str = "") -> bool:
        if not self.enabled:
            logger.info("Telegram client disabled; skipping photo send")
            return False

        with photo_path.open("rb") as photo_file:
            response = requests.post(
                self._endpoint("sendPhoto"),
                data={"chat_id": self.bot.chat_id, "caption": caption[:1024]},
                files={"photo": (photo_path.name, photo_file, "image/png")},
                timeout=60,
            )
        response.raise_for_status()
        return True

    def send_media_group(self, image_paths: list[Path]) -> bool:
        if not self.enabled:
            logger.info("Telegram client disabled; skipping media-group send")
            return False
        if not image_paths:
            return False

        media = []
        files = {}
        for idx, path in enumerate(image_paths):
            attach_name = f"file{idx}"
            media.append({"type": "photo", "media": f"attach://{attach_name}"})
            files[attach_name] = (path.name, path.open("rb"), "image/png")

        try:
            response = requests.post(
                self._endpoint("sendMediaGroup"),
                data={"chat_id": self.bot.chat_id, "media": json.dumps(media)},
                files=files,
                timeout=60,
            )
            response.raise_for_status()
        finally:
            for file_obj in files.values():
                file_obj[1].close()
        return True

    def _endpoint(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot.token}/{method}"


def split_text(text: str, max_len: int = 3500) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > max_len and current:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current:
        chunks.append(current.rstrip())
    return chunks
