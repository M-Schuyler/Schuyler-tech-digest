from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


class GoogleTranslateFallback:
    """Lightweight translator via Google Translate web endpoint (no API key)."""

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.endpoint = "https://translate.googleapis.com/translate_a/single"

    def translate(self, text: str, target_lang: str = "zh-CN", source_lang: str = "auto") -> str | None:
        text = (text or "").strip()
        if not text:
            return ""

        try:
            response = requests.get(
                self.endpoint,
                params={
                    "client": "gtx",
                    "sl": source_lang,
                    "tl": target_lang,
                    "dt": "t",
                    "q": text,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            chunks = data[0] if isinstance(data, list) and data else []
            translated = "".join(part[0] for part in chunks if part and part[0])
            return translated.strip() or None
        except requests.RequestException as exc:
            logger.warning("Google translate request failed: %s", exc)
            return None
        except (ValueError, IndexError, TypeError) as exc:
            logger.warning("Google translate parse failed: %s", exc)
            return None

    def batch_translate(self, texts: list[str], target_lang: str = "zh-CN") -> list[str]:
        results: list[str] = []
        for text in texts:
            translated = self.translate(text, target_lang=target_lang)
            results.append(translated or "")
        return results
