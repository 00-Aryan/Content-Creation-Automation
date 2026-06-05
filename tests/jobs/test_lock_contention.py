"""Concurrency and lock contention tests for SQLiteLockRepository."""

import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import pytest
from uuid import UUID, uuid4

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite file path."""
    return tmp_path / "locks_test.db"


def test_scenario_a_lock_collision(temp_db_path: Path) -> None:
    """Worker A acquires topic_123, Worker B attempts to acquire topic_123 and fails."""
    conn = sqlite3.connect(str(temp_db_path))
    try:
        create_schema(conn)
        repo = SQLiteLockRepository(conn)

        owner_a = uuid4()
        owner_b = uuid4()
        now = datetime.now(timezone.utc)

        lock_a = ResourceLock(
            lock_id=uuid4(),
            lock_type=LockType.TOPIC,
            resource_id="topic_123",
            owner_job_id=owner_a,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
        repo.acquire_lock(lock_a)

        # Worker B tries to acquire lock on the same resource
        lock_b = ResourceLock(
            lock_id=uuid4(),
            lock_type=LockType.TOPIC,
            resource_id="topic_123",
            owner_job_id=owner_b,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )

        with pytest.raises(ValueError, match="Lock target collision"):
            repo.acquire_lock(lock_b)
    finally:
        conn.close()


def test_scenario_b_independent_resources(temp_db_path: Path) -> None:
    """Worker A acquires topic_123, Worker B acquires topic_456. Both succeed."""
    conn = sqlite3.connect(str(temp_db_path))
    try:
        create_schema(conn)
        repo = SQLiteLockRepository(conn)

        owner_a = uuid4()
        owner_b = uuid4()
        now = datetime.now(timezone.utc)

        lock_a = ResourceLock(
            lock_id=uuid4(),
            lock_type=LockType.TOPIC,
            resource_id="topic_123",
            owner_job_id=owner_a,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
        repo.acquire_lock(lock_a)

        lock_b = ResourceLock(
            lock_id=uuid4(),
            lock_type=LockType.TOPIC,
            resource_id="topic_456",
            owner_job_id=owner_b,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
        # Different resource, must succeed
        acquired_b = repo.acquire_lock(lock_b)
        assert acquired_b.status == LockStatus.ACTIVE
    finally:
        conn.close()


def test_scenario_c_release_and_handover(temp_db_path: Path) -> None:
    """Release lock, second worker acquires successfully."""
    conn = sqlite3.connect(str(temp_db_path))
    try:
        create_schema(conn)
        repo = SQLiteLockRepository(conn)

        owner_a = uuid4()
        owner_b = uuid4()
        now = datetime.now(timezone.utc)
        lock_id = uuid4()

        lock_a = ResourceLock(
            lock_id=lock_id,
            lock_type=LockType.TOPIC,
            resource_id="topic_123",
            owner_job_id=owner_a,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
        repo.acquire_lock(lock_a)

        # Release Worker A lock
        repo.release_lock(lock_id)

        # Worker B must now be able to acquire lock on 'topic_123'
        lock_b = ResourceLock(
            lock_id=uuid4(),
            lock_type=LockType.TOPIC,
            resource_id="topic_123",
            owner_job_id=owner_b,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
        acquired_b = repo.acquire_lock(lock_b)
        assert acquired_b.status == LockStatus.ACTIVE
    finally:
        conn.close()


def test_scenario_d_concurrent_thread_contention(temp_db_path: Path) -> None:
    """Simultaneous threads attempting acquisition on same resource; only one wins."""
    conn = sqlite3.connect(str(temp_db_path))
    try:
        create_schema(conn)
    finally:
        conn.close()

    def try_acquire(worker_uuid: str) -> tuple[str, bool]:
        thread_conn = sqlite3.connect(str(temp_db_path))
        # Wait up to 1 second for database locks
        thread_conn.execute("PRAGMA busy_timeout = 1000;")
        thread_repo = SQLiteLockRepository(thread_conn)
        now = datetime.now(timezone.utc)

        lock = ResourceLock(
            lock_id=uuid4(),
            lock_type=LockType.TOPIC,
            resource_id="topic_shared",
            owner_job_id=UUID(worker_uuid),
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
        try:
            thread_repo.acquire_lock(lock)
            return worker_uuid, True
        except (ValueError, sqlite3.OperationalError):
            return worker_uuid, False
        finally:
            thread_conn.close()

    workers = [str(uuid4()) for _ in range(5)]
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(try_acquire, w): w for w in workers}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    # Verify that exactly one worker won the race
    successes = [w for w, success in results if success is True]
    assert len(successes) == 1, f"Expected 1 claim, got: {results}"
