from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import DB_PATH, DATA_DIR


@dataclass
class StoredArticle:
    title: str
    source: str
    summary: str
    keywords: str
    url: str
    date: str


class NewsRepository:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    date TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert(self, item: StoredArticle) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO news (title, source, summary, keywords, url, date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item.title, item.source, item.summary, item.keywords, item.url, item.date),
            )
            conn.commit()
            return cur.rowcount > 0
