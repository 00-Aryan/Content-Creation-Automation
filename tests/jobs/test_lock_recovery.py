"""Tests for lock stale recovery, heartbeat refreshes, and expirations."""

from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository


@pytest.fixture
def repo() -> SQLiteLockRepository:
    """Fixture providing SQLiteLockRepository with in-memory DB."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield SQLiteLockRepository(conn)
    conn.close()


def test_lock_heartbeat_and_protection(repo: SQLiteLockRepository) -> None:
    """Verify heartbeat keeps lock alive and prevents stale sweep expiration."""
    lock_id = uuid4()
    now = datetime.now(timezone.utc)

    lock = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.TOPIC,
        resource_id="topic_1",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    repo.acquire_lock(lock)

    # Trigger heartbeat update
    repo.heartbeat(lock_id)
    updated = repo.get_lock(lock_id)
    assert updated.last_heartbeat >= now

    # Sweep with timeout of 10s should NOT expire this lock (last_heartbeat is fresh)
    stats = repo.release_stale_locks(timeout_seconds=10)
    assert stats["expired_count"] == 0

    fetched = repo.get_lock(lock_id)
    assert fetched.status == LockStatus.ACTIVE


def test_stale_lock_expiration(repo: SQLiteLockRepository) -> None:
    """Verify that locks with stale heartbeats are marked EXPIRED and released."""
    now = datetime.now(timezone.utc)
    stale_time = now - timedelta(seconds=40)

    # Lock A: Stale (last_heartbeat is 40s old, timeout is 30s)
    lock_id_a = uuid4()
    lock_a = ResourceLock(
        lock_id=lock_id_a,
        lock_type=LockType.TOPIC,
        resource_id="topic_A",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=stale_time,
        last_heartbeat=stale_time,
    )
    repo.acquire_lock(lock_a)

    # Lock B: Fresh (last_heartbeat is fresh)
    lock_id_b = uuid4()
    lock_b = ResourceLock(
        lock_id=lock_id_b,
        lock_type=LockType.TOPIC,
        resource_id="topic_B",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    repo.acquire_lock(lock_b)

    # Sweep stale locks with timeout=30
    stats = repo.release_stale_locks(timeout_seconds=30)
    assert stats["expired_count"] == 1
    assert "TOPIC:topic_A" in stats["released_resources"]

    # Verify database state
    fetched_a = repo.get_lock(lock_id_a)
    assert fetched_a.status == LockStatus.EXPIRED
    assert fetched_a.released_at is not None

    fetched_b = repo.get_lock(lock_id_b)
    assert fetched_b.status == LockStatus.ACTIVE
    assert fetched_b.released_at is None

    # The expired resource should now be lockable again!
    new_lock_id = uuid4()
    new_lock = ResourceLock(
        lock_id=new_lock_id,
        lock_type=LockType.TOPIC,
        resource_id="topic_A",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    # This should succeed since the previous lock is now EXPIRED
    repo.acquire_lock(new_lock)
    assert repo.is_locked(LockType.TOPIC, "topic_A") is True
