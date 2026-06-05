"""SQLiteAuditRepository — SQLite-backed audit trail persistence."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from content_creation.audit.models import AuditRecord, AuditActorType, AuditSource, AuditSeverity
from content_creation.audit.repository import AuditRepository
from content_creation.audit.schema import create_audit_schema

logger = logging.getLogger(__name__)


class SQLiteAuditRepository(AuditRepository):
    """SQLite implementation of AuditRepository.

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
        create_audit_schema(conn)

    def close(self) -> None:
        """Close all database connections created by this repository."""
        with self._lock:
            conns = list(self._all_conns)
            self._all_conns.clear()
        for conn in conns:
            try:
                conn.close()
            except Exception:
                logger.debug("Error closing audit store connection")
        if hasattr(self._local, "conn"):
            self._local.conn = None

    def _row_to_record(self, row: sqlite3.Row) -> AuditRecord:
        """Convert a SQLite row to an AuditRecord."""
        metadata = {}
        try:
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return AuditRecord(
            audit_id=UUID(row["id"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            actor_type=AuditActorType(row["actor_type"]),
            actor_id=row["actor_id"],
            action_type=row["action_type"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            event_type=row["event_type"],
            correlation_id=row["correlation_id"],
            previous_state=row["previous_state"],
            new_state=row["new_state"],
            metadata=metadata,
            source=AuditSource(row["source"]),
            severity=AuditSeverity(row["severity"]),
        )

    def create_record(self, record: AuditRecord) -> None:
        """Persist an audit record. Idempotent on duplicate audit_id."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO audit
                   (id, timestamp, actor_type, actor_id, action_type,
                    entity_type, entity_id, event_type, correlation_id,
                    previous_state, new_state, metadata_json, source, severity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(record.audit_id),
                    record.timestamp.isoformat(),
                    record.actor_type.value,
                    record.actor_id,
                    record.action_type,
                    record.entity_type,
                    record.entity_id,
                    record.event_type,
                    record.correlation_id,
                    record.previous_state,
                    record.new_state,
                    json.dumps(record.metadata, default=str),
                    record.source.value,
                    record.severity.value,
                ),
            )
            conn.commit()
            logger.debug("Saved audit record %s (%s)", record.audit_id, record.action_type)
        except sqlite3.Error:
            logger.exception("Failed to save audit record %s", record.audit_id)
            conn.rollback()
            raise

    def get_record(self, audit_id: UUID) -> Optional[AuditRecord]:
        """Retrieve a single audit record by ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM audit WHERE id = ?", (str(audit_id),)
        )
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def query_records(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor_type: Optional[AuditActorType] = None,
        actor_id: Optional[str] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source: Optional[AuditSource] = None,
        severity: Optional[AuditSeverity] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditRecord]:
        """Query audit records with flexible filtering."""
        conn = self._get_conn()
        conditions: List[str] = []
        params: List = []

        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if actor_type:
            conditions.append("actor_type = ?")
            params.append(actor_type.value)
        if actor_id:
            conditions.append("actor_id = ?")
            params.append(actor_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if correlation_id:
            conditions.append("correlation_id = ?")
            params.append(correlation_id)
        if source:
            conditions.append("source = ?")
            params.append(source.value)
        if severity:
            conditions.append("severity = ?")
            params.append(severity.value)
        if start:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())
        if action_type:
            conditions.append("action_type = ?")
            params.append(action_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM audit WHERE {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def query_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """List all audit records for a specific entity, ordered by timestamp."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM audit WHERE entity_type = ? AND entity_id = ? ORDER BY timestamp ASC LIMIT ?",
            (entity_type, entity_id, limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def query_by_actor(
        self,
        actor_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """List all audit records for a specific actor, ordered by timestamp."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM audit WHERE actor_id = ? ORDER BY timestamp ASC LIMIT ?",
            (actor_id, limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def query_by_correlation(
        self,
        correlation_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """List all audit records sharing a correlation_id, ordered by timestamp."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM audit WHERE correlation_id = ? ORDER BY timestamp ASC LIMIT ?",
            (correlation_id, limit),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def count_records(
        self,
        entity_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        source: Optional[AuditSource] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Count audit records matching filters."""
        conn = self._get_conn()
        conditions: List[str] = []
        params: List = []

        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if actor_id:
            conditions.append("actor_id = ?")
            params.append(actor_id)
        if source:
            conditions.append("source = ?")
            params.append(source.value)
        if start:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT COUNT(*) FROM audit WHERE {where_clause}"

        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]

    def delete_expired(self, before: datetime) -> int:
        """Delete audit records older than the given timestamp. Returns count deleted."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM audit WHERE timestamp < ?",
            (before.isoformat(),),
        )
        conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Deleted %d expired audit records before %s", deleted, before.isoformat())
        return deleted
