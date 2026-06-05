"""Database schema definition for the notifications table."""

import sqlite3


def create_notification_schema(conn: sqlite3.Connection) -> None:
    """Initialize the SQLite schema, tables, and indexes for notifications.

    Ensures WAL mode is enabled for parallel reading/writing.
    """
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'UNREAD',
            timestamp TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            event_id TEXT,
            entity_type TEXT,
            entity_id TEXT
        );
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_status
        ON notifications (status);
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_timestamp
        ON notifications (timestamp DESC);
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_category
        ON notifications (category);
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_unread
        ON notifications (status, timestamp DESC)
        WHERE status = 'UNREAD';
        """
    )

    conn.commit()
