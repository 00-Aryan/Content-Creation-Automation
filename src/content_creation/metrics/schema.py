"""SQLite schema for the metrics persistence store."""

import logging
import sqlite3

logger = logging.getLogger(__name__)

METRICS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    dimensions_json TEXT NOT NULL DEFAULT '{}'
);
"""

METRICS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_entity ON metrics(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, created_at)",
]


def create_metrics_schema(conn: sqlite3.Connection) -> None:
    """Initialize the metrics table and indexes.

    Uses WAL mode for concurrent read/write performance.
    Idempotent — safe to call multiple times.
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute(METRICS_SCHEMA_SQL)

    for index_sql in METRICS_INDEXES_SQL:
        conn.execute(index_sql)

    conn.commit()
    logger.info("Metrics store schema initialized")
