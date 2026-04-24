from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import SourceKind, SourceSpec, WatchEntity


@dataclass(frozen=True)
class MonitoringWatchlist:
    entities: tuple[WatchEntity, ...]
    sources: tuple[SourceSpec, ...]


def load_watchlist(path: Path) -> MonitoringWatchlist:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entities = tuple(_parse_entity(item) for item in payload.get("entities", []))
    sources = tuple(_parse_source(item) for item in payload.get("sources", []))
    _assert_unique("entity", (item.key for item in entities))
    _assert_unique("source", (item.key for item in sources))
    return MonitoringWatchlist(entities=entities, sources=sources)


def _parse_entity(item: dict) -> WatchEntity:
    return WatchEntity(
        key=_required_text(item, "key").lower(),
        label=_required_text(item, "label"),
        aliases=tuple(str(value).strip() for value in item.get("aliases", []) if str(value).strip()),
        symbols=tuple(str(value).strip().upper() for value in item.get("symbols", []) if str(value).strip()),
        tags=tuple(str(value).strip().lower() for value in item.get("tags", []) if str(value).strip()),
        priority=int(item.get("priority", 1)),
    )


def _parse_source(item: dict) -> SourceSpec:
    return SourceSpec(
        key=_required_text(item, "key").lower(),
        kind=SourceKind(_required_text(item, "kind").lower()),
        url=_required_text(item, "url"),
        trust_tier=int(item.get("trust_tier", 3)),
        tags=tuple(str(value).strip().lower() for value in item.get("tags", []) if str(value).strip()),
        enabled=bool(item.get("enabled", True)),
    )


def _required_text(item: dict, key: str) -> str:
    value = str(item.get(key, "")).strip()
    if not value:
        raise ValueError(f"Missing required field: {key}")
    return value


def _assert_unique(label: str, keys: Iterable[str]) -> None:
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            raise ValueError(f"Duplicate {label} key: {key}")
        seen.add(key)
