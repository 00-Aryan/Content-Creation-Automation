"""Tests for SQLiteLockRepository operation logic."""

from datetime import datetime, timezone
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Fixture providing SQLite connection with schema initialized."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn: sqlite3.Connection) -> SQLiteLockRepository:
    """Fixture providing SQLiteLockRepository."""
    return SQLiteLockRepository(db_conn)


def test_acquire_and_get_lock(repo: SQLiteLockRepository) -> None:
    """Verify that locks can be acquired, retrieved, and checked."""
    lock_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(timezone.utc)

    lock = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.TOPIC,
        resource_id="topic_123",
        owner_job_id=owner_id,
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )

    repo.acquire_lock(lock)

    # Get lock by ID
    fetched = repo.get_lock(lock_id)
    assert fetched is not None
    assert fetched.lock_id == lock_id
    assert fetched.resource_id == "topic_123"
    assert fetched.status == LockStatus.ACTIVE

    # Check lock state and ownership
    assert repo.is_locked(LockType.TOPIC, "topic_123") is True
    assert repo.get_lock_owner(LockType.TOPIC, "topic_123") == owner_id

    # Verify duplicates on same target throw ValueError
    another_lock = ResourceLock(
        lock_id=uuid4(),
        lock_type=LockType.TOPIC,
        resource_id="topic_123",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    with pytest.raises(ValueError, match="already locked"):
        repo.acquire_lock(another_lock)


def test_release_lock(repo: SQLiteLockRepository) -> None:
    """Verify lock release sets status and released_at timestamp."""
    lock_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(timezone.utc)

    lock = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.MANIFEST,
        resource_id="manifest_123",
        owner_job_id=owner_id,
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    repo.acquire_lock(lock)

    released = repo.release_lock(lock_id)
    assert released.status == LockStatus.RELEASED
    assert released.released_at is not None

    # Should no longer report as locked
    assert repo.is_locked(LockType.MANIFEST, "manifest_123") is False

    # Attempt to release again raises error
    with pytest.raises(ValueError, match="not in ACTIVE state"):
        repo.release_lock(lock_id)


def test_heartbeat_and_active_list(repo: SQLiteLockRepository) -> None:
    """Verify heartbeat modifications and listing active locks."""
    lock_id_1 = uuid4()
    lock_id_2 = uuid4()
    now = datetime.now(timezone.utc)

    lock1 = ResourceLock(
        lock_id=lock_id_1,
        lock_type=LockType.TOPIC,
        resource_id="topic_1",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    repo.acquire_lock(lock1)

    lock2 = ResourceLock(
        lock_id=lock_id_2,
        lock_type=LockType.TOPIC,
        resource_id="topic_2",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    repo.acquire_lock(lock2)

    active_locks = repo.list_active_locks()
    assert len(active_locks) == 2

    # Check heartbeat update
    repo.heartbeat(lock_id_1)
    updated1 = repo.get_lock(lock_id_1)
    assert updated1.last_heartbeat >= now


def test_delete_lock(repo: SQLiteLockRepository) -> None:
    """Verify lock records can be hard-deleted."""
    lock_id = uuid4()
    lock = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.CALENDAR,
        resource_id="calendar_1",
        owner_job_id=uuid4(),
        status=LockStatus.ACTIVE,
        acquired_at=datetime.now(timezone.utc),
        last_heartbeat=datetime.now(timezone.utc),
    )
    repo.acquire_lock(lock)

    assert repo.delete_lock(lock_id) is True
    assert repo.get_lock(lock_id) is None
    assert repo.delete_lock(lock_id) is False
