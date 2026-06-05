"""SQLiteEventRepository — SQLite-backed event persistence."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from content_creation.events.store.models import EventRecord
from content_creation.events.store.repository import EventRepository
from content_creation.events.store.schema import create_event_store_schema

logger = logging.getLogger(__name__)


class SQLiteEventRepository(EventRepository):
    """SQLite implementation of EventRepository.

    Thread-safe. Uses WAL mode and busy_timeout for concurrency.
    Schema initialization is idempotent.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._all_conns = []
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
            with self._lock:
                self._all_conns.append(conn)
        return self._local.conn

    def _init_schema(self) -> None:
        """Initialize schema on the main thread connection."""
        conn = self._get_conn()
        create_event_store_schema(conn)

    def close(self) -> None:
        """Close all database connections created by this repository."""
        with self._lock:
            conns = list(self._all_conns)
            self._all_conns.clear()
        for conn in conns:
            try:
                conn.close()
            except Exception:
                logger.debug("Error closing event store connection")
        if hasattr(self._local, "conn"):
            self._local.conn = None

    def _row_to_record(self, row: sqlite3.Row) -> EventRecord:
        """Convert a SQLite row to an EventRecord."""
        return EventRecord(
            event_id=UUID(row["id"]),
            event_name=row["event_name"],
            category=row["category"],
            source=row["source"],
            correlation_id=row["correlation_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            payload_json=row["payload_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
            version=row["version"],
        )

    def save_event(self, record: EventRecord) -> None:
        """Persist an event record. Idempotent on duplicate event_id."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO events
                   (id, event_name, category, source, correlation_id,
                    entity_type, entity_id, payload_json, created_at, version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(record.event_id),
                    record.event_name,
                    record.category,
                    record.source,
                    record.correlation_id,
                    record.entity_type,
                    record.entity_id,
                    record.payload_json,
                    record.created_at.isoformat(),
                    record.version,
                ),
            )
            conn.commit()
            logger.debug("Saved event %s (%s)", record.event_id, record.event_name)
        except sqlite3.Error:
            logger.exception("Failed to save event %s", record.event_id)
            conn.rollback()
            raise

    def get_event(self, event_id: UUID) -> Optional[EventRecord]:
        """Retrieve a single event by ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE id = ?", (str(event_id),)
        )
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[EventRecord]:
        """List events with pagination, optionally filtered by category."""
        conn = self._get_conn()
        if category:
            cursor = conn.execute(
                "SELECT * FROM events WHERE category = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (category, limit, offset),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_correlation(
        self,
        correlation_id: str,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List all events sharing a correlation_id, ordered by timestamp."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE correlation_id = ? ORDER BY created_at ASC LIMIT ?",
            (correlation_id, limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List all events for a specific entity, ordered by timestamp."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at ASC LIMIT ?",
            (entity_type, entity_id, limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_category(
        self,
        category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EventRecord]:
        """List events by category with pagination."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE category = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (category, limit, offset),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List events within a time range, ordered by timestamp."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE created_at >= ? AND created_at <= ? ORDER BY created_at ASC LIMIT ?",
            (start.isoformat(), end.isoformat(), limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_after_event(
        self,
        event_id: UUID,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List events that occurred after a given event (for SSE replay)."""
        anchor = self.get_event(event_id)
        if anchor is None:
            return []
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE created_at > ? OR (created_at = ? AND id > ?) ORDER BY created_at ASC LIMIT ?",
            (anchor.created_at.isoformat(), anchor.created_at.isoformat(), str(event_id), limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def count_events(self, category: Optional[str] = None) -> int:
        """Count total events, optionally filtered by category."""
        conn = self._get_conn()
        if category:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM events WHERE category = ?", (category,)
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM events")
        return cursor.fetchone()[0]

    def delete_expired(self, before: datetime, category: Optional[str] = None) -> int:
        """Delete events older than the given timestamp. Returns count deleted."""
        conn = self._get_conn()
        if category:
            cursor = conn.execute(
                "DELETE FROM events WHERE created_at < ? AND category = ?",
                (before.isoformat(), category),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM events WHERE created_at < ?",
                (before.isoformat(),),
            )
        conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Deleted %d expired events before %s", deleted, before.isoformat())
        return deleted
