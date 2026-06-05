"""Tests for startup recovery and idempotency logic in RecoverySupervisor."""

from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType
from content_creation.jobs.models import Job, JobStatus, JobType
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


def test_startup_recovery_idempotency(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify startup recovery is idempotent: running twice yields identical database state."""
    repo = supervisor.repository
    lock_repo = supervisor.lock_repository
    now = datetime.now(timezone.utc)

    # 1. Insert a zombie job and a stale lock
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=now - timedelta(seconds=20),
        started_at=now - timedelta(seconds=15),
        last_heartbeat=now - timedelta(seconds=10),
        operator_id="test_user",
        target_type="calendar",
        target_id="week_23",
        payload={"action_id": "dry_run"},
        correlation_id="corr-1",
        retry_count=0,
        max_retries=3,
    )

    cursor = db_conn.cursor()
    cursor.execute(
        """
        INSERT INTO jobs (
            job_id, job_type, status, priority, action_id, operator_id,
            target_type, target_id, payload_json, result_json,
            retry_count, max_retries, created_at, queued_at,
            started_at, completed_at, run_after, last_heartbeat,
            correlation_id, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        repo._to_row(job),
    )

    # Insert a stale active lock
    lock_id = uuid4()
    lock_data = (
        str(lock_id),
        LockType.CALENDAR.value,
        "week_23",
        str(job_id),
        LockStatus.ACTIVE.value,
        (now - timedelta(seconds=15)).isoformat(),
        (now - timedelta(seconds=10)).isoformat(),
        None,
        "{}",
    )
    cursor.execute(
        """
        INSERT INTO locks (
            lock_id, lock_type, resource_id, owner_job_id, status,
            acquired_at, last_heartbeat, released_at, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        lock_data,
    )
    db_conn.commit()

    # 2. Run recovery once
    first_res = supervisor.recover_on_startup()

    assert len(first_res.recovered_jobs) == 1
    assert first_res.recovered_jobs[0] == str(job_id)
    assert len(first_res.released_locks) == 1
    assert first_res.released_locks[0] == str(lock_id)

    # Verify state after first run
    refreshed_job = repo.get_job(job_id)
    assert refreshed_job.status == JobStatus.QUEUED
    refreshed_lock = lock_repo.get_lock(lock_id)
    assert refreshed_lock.status == LockStatus.RELEASED

    # 3. Run recovery a second time
    second_res = supervisor.recover_on_startup()

    assert len(second_res.recovered_jobs) == 0
    assert len(second_res.failed_jobs) == 0
    assert len(second_res.expired_locks) == 0
    assert len(second_res.released_locks) == 0

    # Ensure state remains unchanged
    refreshed_job_2 = repo.get_job(job_id)
    assert refreshed_job_2.status == JobStatus.QUEUED
    refreshed_lock_2 = lock_repo.get_lock(lock_id)
    assert refreshed_lock_2.status == LockStatus.RELEASED
