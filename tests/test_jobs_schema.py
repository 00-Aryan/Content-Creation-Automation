"""Tests for background jobs database schema creation and verification."""

import sqlite3
from content_creation.jobs.schema import (
    create_job_schema,
    create_lock_schema,
    create_schema,
)


def test_imports() -> None:
    """Verify that all three functions can be imported."""
    assert create_job_schema is not None
    assert create_lock_schema is not None
    assert create_schema is not None


def test_create_job_schema() -> None:
    """Verify that create_job_schema(conn) creates the jobs table and job indexes."""
    conn = sqlite3.connect(":memory:")
    try:
        create_job_schema(conn)

        # Verify jobs table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';")
        assert cursor.fetchone() is not None

        # Verify locks table does NOT exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='locks';")
        assert cursor.fetchone() is None

        # Verify job indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='jobs';")
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_jobs_polling",
            "idx_jobs_locks",
            "idx_jobs_correlation",
            "idx_jobs_zombie_sweep",
        }
        for idx in expected_indexes:
            assert idx in indexes

    finally:
        conn.close()


def test_create_lock_schema() -> None:
    """Verify that create_lock_schema(conn) creates the locks table and lock indexes."""
    conn = sqlite3.connect(":memory:")
    try:
        create_lock_schema(conn)

        # Verify locks table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='locks';")
        assert cursor.fetchone() is not None

        # Verify jobs table does NOT exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';")
        assert cursor.fetchone() is None

        # Verify lock indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='locks';")
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_locks_resource",
            "idx_locks_owner",
            "idx_locks_status",
            "idx_locks_heartbeat",
            "idx_locks_active_unique",
        }
        for idx in expected_indexes:
            assert idx in indexes

    finally:
        conn.close()


def test_create_schema() -> None:
    """Verify that create_schema(conn) creates both jobs and locks tables."""
    conn = sqlite3.connect(":memory:")
    try:
        create_schema(conn)

        cursor = conn.cursor()

        # Verify jobs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';")
        assert cursor.fetchone() is not None

        # Verify locks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='locks';")
        assert cursor.fetchone() is not None

    finally:
        conn.close()
