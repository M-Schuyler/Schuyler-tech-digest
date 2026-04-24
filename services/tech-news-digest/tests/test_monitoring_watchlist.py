from __future__ import annotations

import json

from news_digest.monitoring.models import SourceKind
from news_digest.monitoring.watchlist import load_watchlist


def test_load_watchlist_normalizes_aliases_symbols_and_source_kind(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "key": "openai",
                        "label": "OpenAI",
                        "aliases": ["OpenAI", "ChatGPT"],
                        "symbols": ["msft", "nvda"],
                        "tags": ["AI", "Agent"],
                        "priority": 5,
                    }
                ],
                "sources": [
                    {
                        "key": "openai-news",
                        "kind": "rss",
                        "url": "https://openai.com/news/rss.xml",
                        "trust_tier": 1,
                        "tags": ["official", "AI"],
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    watchlist = load_watchlist(path)

    assert watchlist.entities[0].symbols == ("MSFT", "NVDA")
    assert watchlist.entities[0].tags == ("ai", "agent")
    assert watchlist.sources[0].kind is SourceKind.RSS
    assert watchlist.sources[0].tags == ("official", "ai")


def test_load_watchlist_rejects_duplicate_entity_keys(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text(
        json.dumps(
            {
                "entities": [
                    {"key": "openai", "label": "OpenAI"},
                    {"key": "openai", "label": "OpenAI duplicate"},
                ],
                "sources": [],
            }
        ),
        encoding="utf-8",
    )

    try:
        load_watchlist(path)
    except ValueError as exc:
        assert "Duplicate entity key: openai" in str(exc)
    else:
        raise AssertionError("Expected duplicate entity key to fail")
