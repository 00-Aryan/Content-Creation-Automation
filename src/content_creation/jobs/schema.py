"""Database schema definition and initialization logic."""

import sqlite3


def create_schema(conn: sqlite3.Connection) -> None:
    """Initialize the SQLite schema, tables, and indexes for background jobs.

    Ensures WAL mode is enabled for parallel reading/writing.
    """
    # Enable Write-Ahead Logging (WAL) for concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    # 1. Create jobs table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            action_id TEXT NOT NULL,
            operator_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            result_json TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            created_at TEXT NOT NULL,
            queued_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            run_after TEXT,
            last_heartbeat TEXT,
            correlation_id TEXT NOT NULL,
            error_message TEXT
        );
        """
    )

    # 2. Create performance indexes
    # Optimize worker dequeueing and priority selection
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_polling
        ON jobs (status, priority, run_after, queued_at);
        """
    )

    # Optimize target lock checks
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_locks
        ON jobs (target_type, target_id, status);
        """
    )

    # Optimize correlation aggregates
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_correlation
        ON jobs (correlation_id);
        """
    )

    # Optimize zombie sweeps
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_zombie_sweep
        ON jobs (status, last_heartbeat);
        """
    )

    # 3. Create locks table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS locks (
            lock_id TEXT PRIMARY KEY,
            lock_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            owner_job_id TEXT NOT NULL,
            status TEXT NOT NULL,
            acquired_at TEXT NOT NULL,
            last_heartbeat TEXT NOT NULL,
            released_at TEXT,
            metadata_json TEXT
        );
        """
    )

    # 4. Create locks indexes
    # Optimize resource queries
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_locks_resource
        ON locks (lock_type, resource_id, status);
        """
    )

    # Optimize owner queries
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_locks_owner
        ON locks (owner_job_id);
        """
    )

    # Optimize status queries
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_locks_status
        ON locks (status);
        """
    )

    # Optimize heartbeat sweeps
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_locks_heartbeat
        ON locks (last_heartbeat);
        """
    )

    # Enforce database-level uniqueness constraint:
    # Only one ACTIVE lock may exist for (lock_type, resource_id) at any time.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_locks_active_unique
        ON locks (lock_type, resource_id)
        WHERE status = 'ACTIVE';
        """
    )

    conn.commit()
