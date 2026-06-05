"""SQLite schema for the event persistence store."""

import logging
import sqlite3

logger = logging.getLogger(__name__)

EVENT_STORE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    correlation_id TEXT NOT NULL DEFAULT '',
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
"""

EVENT_STORE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)",
    "CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id)",
]


def create_event_store_schema(conn: sqlite3.Connection) -> None:
    """Initialize the events table and indexes.

    Uses WAL mode for concurrent read/write performance.
    Idempotent — safe to call multiple times.
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute(EVENT_STORE_SCHEMA_SQL)

    for index_sql in EVENT_STORE_INDEXES_SQL:
        conn.execute(index_sql)

    conn.commit()
    logger.info("Event store schema initialized")
