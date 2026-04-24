from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SourceKind(str, Enum):
    RSS = "rss"
    WEB = "web"
    API = "api"
    MARKET = "market"


class SignalLevel(str, Enum):
    ARCHIVE_ONLY = "archive_only"
    DIGEST_CANDIDATE = "digest_candidate"
    INTERRUPT = "interrupt"


@dataclass(frozen=True)
class WatchEntity:
    key: str
    label: str
    aliases: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    priority: int = 1


@dataclass(frozen=True)
class SourceSpec:
    key: str
    kind: SourceKind
    url: str
    trust_tier: int
    tags: tuple[str, ...] = ()
    enabled: bool = True


@dataclass(frozen=True)
class RawSourceItem:
    source_key: str
    source_kind: SourceKind
    title: str
    url: str
    published_at: datetime | None
    content_hint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitorEvent:
    source_key: str
    source_kind: str
    title: str
    url: str
    published_at: datetime | None
    first_seen_at: datetime
    content_hint: str
    event_hash: str
    entities: tuple[str, ...]
    symbols: tuple[str, ...]
    tags: tuple[str, ...]
    trust_tier: int
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass
class MonitorSignal:
    event_id: int
    level: SignalLevel
    score: int
    reason: str
    entities: tuple[str, ...]
    symbols: tuple[str, ...]
    tags: tuple[str, ...]
    created_at: datetime
    dispatched_at: datetime | None = None
    suppressed_reason: str | None = None
    id: int | None = None
