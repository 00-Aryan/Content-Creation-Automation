"""Tests for lock expiration recovery in RecoverySupervisor."""

from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType
from content_creation.jobs.queue_engine import QueueEngine
from content_creation.jobs.recovery_supervisor import (
    RecoveryConfig,
    RecoverySupervisor,
)
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository
from content_creation.jobs.sqlite_repository import SQLiteJobRepository


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Fixture providing in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def supervisor(db_conn: sqlite3.Connection) -> RecoverySupervisor:
    repo = SQLiteJobRepository(db_conn)
    lock_repo = SQLiteLockRepository(db_conn)
    lock_mgr = LockManager(lock_repo)
    queue = QueueEngine(repo, lock_mgr)
    config = RecoveryConfig(
        heartbeat_timeout_seconds=5,
        sweep_interval_seconds=10,
        max_recovery_batch_size=10,
    )
    return RecoverySupervisor(repo, lock_repo, queue, config)


def test_lock_expiration_transitions(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify ACTIVE locks with stale heartbeats transition to EXPIRED, and fresh locks remain ACTIVE."""
    lock_repo = supervisor.lock_repository
    now = datetime.now(timezone.utc)

    # 1. Insert a stale active lock
    stale_lock_id = uuid4()
    stale_lock_data = (
        str(stale_lock_id),
        LockType.TOPIC.value,
        "stale_topic",
        str(uuid4()),
        LockStatus.ACTIVE.value,
        (now - timedelta(seconds=15)).isoformat(),
        (now - timedelta(seconds=10)).isoformat(),  # Stale heartbeat (timeout is 5s)
        None,
        "{}",
    )

    # 2. Insert a fresh active lock
    fresh_lock_id = uuid4()
    fresh_lock_data = (
        str(fresh_lock_id),
        LockType.TOPIC.value,
        "fresh_topic",
        str(uuid4()),
        LockStatus.ACTIVE.value,
        (now - timedelta(seconds=2)).isoformat(),
        (now - timedelta(seconds=2)).isoformat(),  # Fresh heartbeat
        None,
        "{}",
    )

    cursor = db_conn.cursor()
    for row in [stale_lock_data, fresh_lock_data]:
        cursor.execute(
            """
            INSERT INTO locks (
                lock_id, lock_type, resource_id, owner_job_id, status,
                acquired_at, last_heartbeat, released_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
    db_conn.commit()

    # Run lock recovery
    expired_ids = supervisor.recover_expired_locks()

    # Verify stale lock expired
    assert str(stale_lock_id) in expired_ids
    assert str(fresh_lock_id) not in expired_ids

    stale_refreshed = lock_repo.get_lock(stale_lock_id)
    assert stale_refreshed.status == LockStatus.EXPIRED
    assert stale_refreshed.released_at is not None

    fresh_refreshed = lock_repo.get_lock(fresh_lock_id)
    assert fresh_refreshed.status == LockStatus.ACTIVE
    assert fresh_refreshed.released_at is None
