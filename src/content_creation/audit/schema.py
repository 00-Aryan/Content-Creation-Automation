"""SQLite schema for the audit trail store."""

import logging
import sqlite3

logger = logging.getLogger(__name__)

AUDIT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL DEFAULT '',
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    event_type TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    previous_state TEXT NOT NULL DEFAULT '',
    new_state TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'workflow',
    severity TEXT NOT NULL DEFAULT 'INFO'
);
"""

AUDIT_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit(actor_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit(correlation_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_event ON audit(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_audit_source ON audit(source)",
    "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit(action_type)",
]


def create_audit_schema(conn: sqlite3.Connection) -> None:
    """Initialize the audit table and indexes.

    Uses WAL mode for concurrent read/write performance.
    Idempotent — safe to call multiple times.
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute(AUDIT_SCHEMA_SQL)

    for index_sql in AUDIT_INDEXES_SQL:
        conn.execute(index_sql)

    conn.commit()
    logger.info("Audit store schema initialized")
