from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import RuntimeSettings
from ..models import AlertEvent, BriefRecord, CloseSummary, MarketBar, WatchSignal
from ..monitoring.models import MonitorEvent, MonitorSignal, SignalLevel


class StateStore:
    def __init__(
        self,
        *,
        url: str = "",
        auth_token: str = "",
        sqlite_path: Path | None = None,
        market_timezone: str = "America/New_York",
    ) -> None:
        self.url = url.strip()
        self.auth_token = auth_token.strip()
        self.sqlite_path = sqlite_path
        self.market_tz = ZoneInfo(market_timezone)
        self._ensure_parent_dir()
        self._ensure_schema()

    def record_alert(self, event: AlertEvent) -> AlertEvent:
        payload = (
            event.symbol,
            _to_utc_iso(event.window_start_ny),
            _to_utc_iso(event.window_end_ny),
            _to_utc_iso(event.triggered_at_ny),
            event.trading_date_ny.isoformat(),
            event.kind,
            event.direction,
            event.magnitude_pct,
            event.reason,
            event.source,
            json.dumps(list(event.related_symbols)),
            event.suppressed_reason,
            _to_utc_iso(event.dispatched_at_ny) if event.dispatched_at_ny else None,
            json.dumps(event.metadata),
        )
        self._execute(
            """
            INSERT INTO alert_events (
                symbol,
                window_start_utc,
                window_end_utc,
                triggered_at_utc,
                trading_date_ny,
                kind,
                direction,
                magnitude_pct,
                reason,
                source,
                related_symbols_json,
                suppressed_reason,
                dispatched_at_utc,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        latest = self._query_one("SELECT id FROM alert_events ORDER BY id DESC LIMIT 1")
        if latest and latest.get("id") is not None:
            event.id = int(latest["id"])
        return event

    def list_alerts(
        self,
        *,
        trade_date_ny: date | None = None,
        symbol: str | None = None,
        kind: str | None = None,
        since_ny: datetime | None = None,
        until_ny: datetime | None = None,
        include_suppressed: bool = True,
    ) -> list[AlertEvent]:
        clauses: list[str] = ["1=1"]
        params: list[Any] = []

        if trade_date_ny:
            clauses.append("trading_date_ny = ?")
            params.append(trade_date_ny.isoformat())
        if symbol:
            clauses.append("(symbol = ? OR related_symbols_json LIKE ?)")
            params.extend([symbol, f'%"{symbol}"%'])
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if since_ny:
            clauses.append("triggered_at_utc >= ?")
            params.append(_to_utc_iso(since_ny))
        if until_ny:
            clauses.append("triggered_at_utc <= ?")
            params.append(_to_utc_iso(until_ny))
        if not include_suppressed:
            clauses.append("suppressed_reason IS NULL")

        query = f"""
            SELECT
                id,
                symbol,
                window_start_utc,
                window_end_utc,
                triggered_at_utc,
                trading_date_ny,
                kind,
                direction,
                magnitude_pct,
                reason,
                source,
                related_symbols_json,
                suppressed_reason,
                dispatched_at_utc,
                metadata_json
            FROM alert_events
            WHERE {" AND ".join(clauses)}
            ORDER BY triggered_at_utc ASC, id ASC
        """
        rows = self._query_all(query, params)
        return [self._alert_from_row(row) for row in rows]

    def upsert_market_bars(self, symbol: str, interval: str, bars: Sequence[MarketBar]) -> None:
        if not bars:
            return
        self._executemany(
            """
            INSERT OR REPLACE INTO market_bars (
                symbol,
                interval,
                ts_utc,
                trading_date_ny,
                open,
                high,
                low,
                close,
                volume,
                source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    symbol,
                    interval,
                    _to_utc_iso(bar.ts_ny),
                    bar.trading_date_ny.isoformat(),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                    bar.source,
                )
                for bar in bars
            ],
        )

    def list_market_bars(
        self,
        *,
        symbol: str,
        interval: str,
        since_ny: datetime | None = None,
        limit: int | None = None,
    ) -> list[MarketBar]:
        clauses = ["symbol = ?", "interval = ?"]
        params: list[Any] = [symbol, interval]
        if since_ny:
            clauses.append("ts_utc >= ?")
            params.append(_to_utc_iso(since_ny))
        query = f"""
            SELECT symbol, ts_utc, open, high, low, close, volume, interval, source
            FROM market_bars
            WHERE {" AND ".join(clauses)}
            ORDER BY ts_utc ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"

        rows = self._query_all(query, params)
        return [
            MarketBar(
                symbol=row["symbol"],
                ts_ny=_from_utc_iso(row["ts_utc"], self.market_tz),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]) if row["volume"] is not None else None,
                interval=row["interval"],
                source=row["source"],
            )
            for row in rows
        ]

    def record_brief(self, brief: BriefRecord) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO brief_records (
                brief_date_sh,
                reference_trade_date_ny,
                top_three_json,
                ai_section,
                tech_section,
                market_section,
                cross_section,
                watchlist_json,
                chart_paths_json,
                generated_at_utc,
                published_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief.brief_date_sh.isoformat(),
                brief.reference_trade_date_ny.isoformat(),
                json.dumps(brief.top_three),
                brief.ai_section,
                brief.tech_section,
                brief.market_section,
                brief.cross_section,
                json.dumps([asdict(item) for item in brief.watchlist]),
                json.dumps(brief.chart_paths),
                _to_utc_iso(brief.generated_at),
                _to_utc_iso(brief.published_at) if brief.published_at else None,
            ),
        )

    def get_latest_brief(self) -> BriefRecord | None:
        row = self._query_one(
            """
            SELECT
                brief_date_sh,
                reference_trade_date_ny,
                top_three_json,
                ai_section,
                tech_section,
                market_section,
                cross_section,
                watchlist_json,
                chart_paths_json,
                generated_at_utc,
                published_at_utc
            FROM brief_records
            ORDER BY brief_date_sh DESC
            LIMIT 1
            """
        )
        if row is None:
            return None
        return self._brief_from_row(row)

    def record_close_summary(self, summary: CloseSummary) -> None:
        self._execute(
            """
            INSERT OR REPLACE INTO close_summaries (
                trade_date_ny,
                closing_verdict,
                strongest_assets_json,
                weakest_assets_json,
                ai_tech_thread,
                crypto_mood,
                tomorrow_watch_json,
                generated_at_utc,
                published_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.trade_date_ny.isoformat(),
                summary.closing_verdict,
                json.dumps(summary.strongest_assets),
                json.dumps(summary.weakest_assets),
                summary.ai_tech_thread,
                summary.crypto_mood,
                json.dumps([asdict(item) for item in summary.tomorrow_watch]),
                _to_utc_iso(summary.generated_at),
                _to_utc_iso(summary.published_at) if summary.published_at else None,
            ),
        )

    def get_close_summary(self, trade_date_ny: date) -> CloseSummary | None:
        row = self._query_one(
            """
            SELECT
                trade_date_ny,
                closing_verdict,
                strongest_assets_json,
                weakest_assets_json,
                ai_tech_thread,
                crypto_mood,
                tomorrow_watch_json,
                generated_at_utc,
                published_at_utc
            FROM close_summaries
            WHERE trade_date_ny = ?
            """,
            (trade_date_ny.isoformat(),),
        )
        if row is None:
            return None
        return CloseSummary(
            trade_date_ny=date.fromisoformat(row["trade_date_ny"]),
            closing_verdict=row["closing_verdict"],
            strongest_assets=json.loads(row["strongest_assets_json"]),
            weakest_assets=json.loads(row["weakest_assets_json"]),
            ai_tech_thread=row["ai_tech_thread"],
            crypto_mood=row["crypto_mood"],
            tomorrow_watch=[WatchSignal(**item) for item in json.loads(row["tomorrow_watch_json"])],
            generated_at=_from_utc_iso(row["generated_at_utc"], self.market_tz),
            published_at=_from_utc_iso(row["published_at_utc"], self.market_tz)
            if row["published_at_utc"]
            else None,
        )

    def record_monitor_event(self, event: MonitorEvent) -> MonitorEvent:
        self._execute(
            """
            INSERT OR IGNORE INTO monitor_events (
                source_key,
                source_kind,
                title,
                url,
                published_at_utc,
                first_seen_at_utc,
                content_hint,
                event_hash,
                entities_json,
                symbols_json,
                tags_json,
                trust_tier,
                raw_metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.source_key,
                event.source_kind,
                event.title,
                event.url,
                _to_utc_iso(event.published_at) if event.published_at else None,
                _to_utc_iso(event.first_seen_at),
                event.content_hint,
                event.event_hash,
                json.dumps(list(event.entities)),
                json.dumps(list(event.symbols)),
                json.dumps(list(event.tags)),
                event.trust_tier,
                json.dumps(event.raw_metadata),
            ),
        )
        persisted = self.get_monitor_event_by_hash(event.event_hash)
        if persisted is None:
            raise RuntimeError(f"Failed to persist monitor event: {event.event_hash}")
        return persisted

    def get_monitor_event_by_hash(self, event_hash: str) -> MonitorEvent | None:
        row = self._query_one(
            """
            SELECT
                id,
                source_key,
                source_kind,
                title,
                url,
                published_at_utc,
                first_seen_at_utc,
                content_hint,
                event_hash,
                entities_json,
                symbols_json,
                tags_json,
                trust_tier,
                raw_metadata_json
            FROM monitor_events
            WHERE event_hash = ?
            """,
            (event_hash,),
        )
        return self._monitor_event_from_row(row) if row else None

    def list_monitor_events(
        self,
        *,
        since_utc: datetime | None = None,
        limit: int | None = None,
    ) -> list[MonitorEvent]:
        clauses: list[str] = ["1=1"]
        params: list[Any] = []
        if since_utc:
            clauses.append("first_seen_at_utc >= ?")
            params.append(_to_utc_iso(since_utc))
        query = f"""
            SELECT
                id,
                source_key,
                source_kind,
                title,
                url,
                published_at_utc,
                first_seen_at_utc,
                content_hint,
                event_hash,
                entities_json,
                symbols_json,
                tags_json,
                trust_tier,
                raw_metadata_json
            FROM monitor_events
            WHERE {" AND ".join(clauses)}
            ORDER BY first_seen_at_utc ASC, id ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        return [self._monitor_event_from_row(row) for row in self._query_all(query, params)]

    def record_monitor_signal(self, signal: MonitorSignal) -> MonitorSignal:
        self._execute(
            """
            INSERT INTO monitor_signals (
                event_id,
                level,
                score,
                reason,
                entities_json,
                symbols_json,
                tags_json,
                created_at_utc,
                dispatched_at_utc,
                suppressed_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.event_id,
                _signal_level_value(signal.level),
                signal.score,
                signal.reason,
                json.dumps(list(signal.entities)),
                json.dumps(list(signal.symbols)),
                json.dumps(list(signal.tags)),
                _to_utc_iso(signal.created_at),
                _to_utc_iso(signal.dispatched_at) if signal.dispatched_at else None,
                signal.suppressed_reason,
            ),
        )
        latest = self._query_one("SELECT id FROM monitor_signals ORDER BY id DESC LIMIT 1")
        if latest and latest.get("id") is not None:
            signal.id = int(latest["id"])
        return signal

    def list_monitor_signals(
        self,
        *,
        level: SignalLevel | None = None,
        since_utc: datetime | None = None,
        limit: int | None = None,
    ) -> list[MonitorSignal]:
        clauses: list[str] = ["1=1"]
        params: list[Any] = []
        if level:
            clauses.append("level = ?")
            params.append(_signal_level_value(level))
        if since_utc:
            clauses.append("created_at_utc >= ?")
            params.append(_to_utc_iso(since_utc))
        query = f"""
            SELECT
                id,
                event_id,
                level,
                score,
                reason,
                entities_json,
                symbols_json,
                tags_json,
                created_at_utc,
                dispatched_at_utc,
                suppressed_reason
            FROM monitor_signals
            WHERE {" AND ".join(clauses)}
            ORDER BY created_at_utc ASC, id ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        return [self._monitor_signal_from_row(row) for row in self._query_all(query, params)]

    def mark_monitor_signal_dispatched(self, signal_id: int, dispatched_at: datetime) -> None:
        self._execute(
            "UPDATE monitor_signals SET dispatched_at_utc = ? WHERE id = ?",
            (_to_utc_iso(dispatched_at), signal_id),
        )

    def _ensure_parent_dir(self) -> None:
        if self.url:
            return
        if self.sqlite_path:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        if self.url:
            import libsql

            conn = libsql.connect(database=self.url, auth_token=self.auth_token or None)
            return conn

        if not self.sqlite_path:
            raise ValueError("sqlite_path is required when STATE_DB_URL is not configured")

        conn = sqlite3.connect(self.sqlite_path)
        return conn

    def _execute(self, statement: str, params: Sequence[Any] = ()) -> None:
        with self._connect() as conn:
            conn.execute(statement, tuple(params))
            conn.commit()

    def _executemany(self, statement: str, rows: Sequence[Sequence[Any]]) -> None:
        if not rows:
            return

        with self._connect() as conn:
            conn.executemany(statement, [tuple(row) for row in rows])
            conn.commit()

    def _query_all(self, statement: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(statement, tuple(params))
            rows = cursor.fetchall()
            return [_row_to_dict(cursor, row) for row in rows]

    def _query_one(self, statement: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        rows = self._query_all(statement, params)
        return rows[0] if rows else None

    def _ensure_schema(self) -> None:
        schema = [
            """
            CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                window_start_utc TEXT NOT NULL,
                window_end_utc TEXT NOT NULL,
                triggered_at_utc TEXT NOT NULL,
                trading_date_ny TEXT NOT NULL,
                kind TEXT NOT NULL,
                direction TEXT NOT NULL,
                magnitude_pct REAL NOT NULL,
                reason TEXT NOT NULL,
                source TEXT NOT NULL,
                related_symbols_json TEXT NOT NULL DEFAULT '[]',
                suppressed_reason TEXT,
                dispatched_at_utc TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_alert_events_trade_date ON alert_events (trading_date_ny)",
            "CREATE INDEX IF NOT EXISTS idx_alert_events_symbol ON alert_events (symbol, triggered_at_utc)",
            """
            CREATE TABLE IF NOT EXISTS market_bars (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                ts_utc TEXT NOT NULL,
                trading_date_ny TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                source TEXT NOT NULL,
                PRIMARY KEY (symbol, interval, ts_utc)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS brief_records (
                brief_date_sh TEXT PRIMARY KEY,
                reference_trade_date_ny TEXT NOT NULL,
                top_three_json TEXT NOT NULL,
                ai_section TEXT NOT NULL,
                tech_section TEXT NOT NULL,
                market_section TEXT NOT NULL,
                cross_section TEXT NOT NULL,
                watchlist_json TEXT NOT NULL,
                chart_paths_json TEXT NOT NULL,
                generated_at_utc TEXT NOT NULL,
                published_at_utc TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS close_summaries (
                trade_date_ny TEXT PRIMARY KEY,
                closing_verdict TEXT NOT NULL,
                strongest_assets_json TEXT NOT NULL,
                weakest_assets_json TEXT NOT NULL,
                ai_tech_thread TEXT NOT NULL,
                crypto_mood TEXT NOT NULL,
                tomorrow_watch_json TEXT NOT NULL,
                generated_at_utc TEXT NOT NULL,
                published_at_utc TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS monitor_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at_utc TEXT,
                first_seen_at_utc TEXT NOT NULL,
                content_hint TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                entities_json TEXT NOT NULL DEFAULT '[]',
                symbols_json TEXT NOT NULL DEFAULT '[]',
                tags_json TEXT NOT NULL DEFAULT '[]',
                trust_tier INTEGER NOT NULL,
                raw_metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_monitor_events_seen ON monitor_events (first_seen_at_utc)",
            "CREATE INDEX IF NOT EXISTS idx_monitor_events_source ON monitor_events (source_key, first_seen_at_utc)",
            """
            CREATE TABLE IF NOT EXISTS monitor_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                level TEXT NOT NULL,
                score INTEGER NOT NULL,
                reason TEXT NOT NULL,
                entities_json TEXT NOT NULL DEFAULT '[]',
                symbols_json TEXT NOT NULL DEFAULT '[]',
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at_utc TEXT NOT NULL,
                dispatched_at_utc TEXT,
                suppressed_reason TEXT,
                FOREIGN KEY(event_id) REFERENCES monitor_events(id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_monitor_signals_level_created ON monitor_signals (level, created_at_utc)",
        ]
        for statement in schema:
            self._execute(statement)

    def _alert_from_row(self, row: dict[str, Any]) -> AlertEvent:
        related = tuple(json.loads(row["related_symbols_json"] or "[]"))
        metadata = json.loads(row["metadata_json"] or "{}")
        return AlertEvent(
            id=int(row["id"]) if row["id"] is not None else None,
            symbol=row["symbol"],
            related_symbols=related,
            window_start_ny=_from_utc_iso(row["window_start_utc"], self.market_tz),
            window_end_ny=_from_utc_iso(row["window_end_utc"], self.market_tz),
            triggered_at_ny=_from_utc_iso(row["triggered_at_utc"], self.market_tz),
            trading_date_ny=date.fromisoformat(row["trading_date_ny"]),
            kind=row["kind"],
            direction=row["direction"],
            magnitude_pct=float(row["magnitude_pct"]),
            reason=row["reason"],
            source=row["source"],
            suppressed_reason=row["suppressed_reason"],
            dispatched_at_ny=_from_utc_iso(row["dispatched_at_utc"], self.market_tz)
            if row["dispatched_at_utc"]
            else None,
            metadata=metadata,
        )

    def _brief_from_row(self, row: dict[str, Any]) -> BriefRecord:
        return BriefRecord(
            brief_date_sh=date.fromisoformat(row["brief_date_sh"]),
            reference_trade_date_ny=date.fromisoformat(row["reference_trade_date_ny"]),
            top_three=json.loads(row["top_three_json"]),
            ai_section=row["ai_section"],
            tech_section=row["tech_section"],
            market_section=row["market_section"],
            cross_section=row["cross_section"],
            watchlist=[WatchSignal(**item) for item in json.loads(row["watchlist_json"])],
            chart_paths=json.loads(row["chart_paths_json"]),
            generated_at=_from_utc_iso(row["generated_at_utc"], self.market_tz),
            published_at=_from_utc_iso(row["published_at_utc"], self.market_tz)
            if row["published_at_utc"]
            else None,
        )

    def _monitor_event_from_row(self, row: dict[str, Any]) -> MonitorEvent:
        return MonitorEvent(
            id=int(row["id"]) if row["id"] is not None else None,
            source_key=row["source_key"],
            source_kind=row["source_kind"],
            title=row["title"],
            url=row["url"],
            published_at=_from_utc_iso(row["published_at_utc"], timezone.utc)
            if row["published_at_utc"]
            else None,
            first_seen_at=_from_utc_iso(row["first_seen_at_utc"], timezone.utc),
            content_hint=row["content_hint"],
            event_hash=row["event_hash"],
            entities=tuple(json.loads(row["entities_json"] or "[]")),
            symbols=tuple(json.loads(row["symbols_json"] or "[]")),
            tags=tuple(json.loads(row["tags_json"] or "[]")),
            trust_tier=int(row["trust_tier"]),
            raw_metadata=json.loads(row["raw_metadata_json"] or "{}"),
        )

    def _monitor_signal_from_row(self, row: dict[str, Any]) -> MonitorSignal:
        return MonitorSignal(
            id=int(row["id"]) if row["id"] is not None else None,
            event_id=int(row["event_id"]),
            level=SignalLevel(row["level"]),
            score=int(row["score"]),
            reason=row["reason"],
            entities=tuple(json.loads(row["entities_json"] or "[]")),
            symbols=tuple(json.loads(row["symbols_json"] or "[]")),
            tags=tuple(json.loads(row["tags_json"] or "[]")),
            created_at=_from_utc_iso(row["created_at_utc"], timezone.utc),
            dispatched_at=_from_utc_iso(row["dispatched_at_utc"], timezone.utc)
            if row["dispatched_at_utc"]
            else None,
            suppressed_reason=row["suppressed_reason"],
        )


def create_state_store(settings: RuntimeSettings) -> StateStore:
    return StateStore(
        url=settings.state_db_url,
        auth_token=settings.state_db_auth_token,
        sqlite_path=settings.state_db_local_path,
        market_timezone=settings.market_timezone,
    )


def _row_to_dict(cursor, row) -> dict[str, Any]:
    columns = [column[0] for column in cursor.description]
    return {column: row[idx] for idx, column in enumerate(columns)}


def _to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _from_utc_iso(value: str, timezone_name: ZoneInfo) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone_name)


def _signal_level_value(level: SignalLevel | str) -> str:
    if isinstance(level, SignalLevel):
        return level.value
    return str(level)
