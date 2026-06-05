"""Tests for RecoverySupervisor core sweep and zombie job recovery logic."""

import dataclasses
from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType
from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
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
        max_recovery_batch_size=2,
    )
    return RecoverySupervisor(repo, lock_repo, queue, config)


def test_recovery_sweep_no_zombies(supervisor: RecoverySupervisor) -> None:
    """Verify that a sweep with no zombie jobs returns empty result lists."""
    res = supervisor.run_sweep()
    assert len(res.recovered_jobs) == 0
    assert len(res.failed_jobs) == 0
    assert len(res.expired_locks) == 0
    assert len(res.released_locks) == 0
    assert len(res.skipped_jobs) == 0
    assert res.execution_time_ms >= 0.0


def test_recovery_zombie_rescheduled(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify a zombie job with remaining retry budget is transitioned RUNNING -> RETRYING -> QUEUED."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)

    # Insert a RUNNING job whose heartbeat is stale (exceeds 5s timeout)
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

    # Insert directly via cursor to bypass normal validations
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
    db_conn.commit()

    # Also acquire a lock for this job to verify it gets released
    lock_mgr = supervisor.lock_repository
    lock_mgr.acquire_lock(
        supervisor.lock_repository._to_model(
            (
                str(uuid4()),
                LockType.CALENDAR.value,
                "week_23",
                str(job_id),
                LockStatus.ACTIVE.value,
                (now - timedelta(seconds=15)).isoformat(),
                (now - timedelta(seconds=10)).isoformat(),
                None,
                "{}",
            )
        )
    )

    # Run sweep
    sweep_res = supervisor.run_sweep()

    assert str(job_id) in sweep_res.recovered_jobs
    assert len(sweep_res.failed_jobs) == 0
    assert len(sweep_res.released_locks) == 1

    # Verify job status in DB
    refreshed = repo.get_job(job_id)
    assert refreshed.status == JobStatus.QUEUED
    assert refreshed.retry_count == 1
    assert refreshed.run_after is not None
    assert refreshed.started_at is None
    assert refreshed.last_heartbeat is None
    assert "Heartbeat timeout" in refreshed.error_message

    # Verify locks released
    active_locks = supervisor.lock_repository.list_active_locks()
    assert len(active_locks) == 0


def test_recovery_zombie_failed(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify a zombie job with NO remaining retry budget is transitioned RUNNING -> FAILED."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)

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
        retry_count=3,
        max_retries=3,  # Already hit max retry count
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
    db_conn.commit()

    sweep_res = supervisor.run_sweep()

    assert str(job_id) in sweep_res.failed_jobs
    assert len(sweep_res.recovered_jobs) == 0

    refreshed = repo.get_job(job_id)
    assert refreshed.status == JobStatus.FAILED
    assert refreshed.completed_at is not None
    assert "exhausted" in refreshed.error_message


def test_recovery_batch_limit(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify sweep honors max_recovery_batch_size and tracks excess zombies in skipped_jobs."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)

    # Create 3 zombie jobs (batch size is configured to 2)
    job_ids = [uuid4() for _ in range(3)]
    for jid in job_ids:
        job = Job(
            job_id=jid,
            job_type=JobType.DRY_RUN.value,
            status=JobStatus.RUNNING,
            priority=100,
            created_at=now - timedelta(seconds=20),
            started_at=now - timedelta(seconds=15),
            last_heartbeat=now - timedelta(seconds=10),
            operator_id="test_user",
            target_type="calendar",
            target_id=str(jid),
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
    db_conn.commit()

    sweep_res = supervisor.run_sweep()

    # Exactly 2 should be recovered, and 1 skipped
    assert len(sweep_res.recovered_jobs) == 2
    assert len(sweep_res.skipped_jobs) == 1
    assert UUID(sweep_res.skipped_jobs[0]) in job_ids


def test_terminal_jobs_protected(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify terminal jobs are ignored even if their heartbeat/completed timestamp is old."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)

    # Create a COMPLETED job
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.COMPLETED,
        priority=100,
        created_at=now - timedelta(seconds=20),
        started_at=now - timedelta(seconds=15),
        completed_at=now - timedelta(seconds=10),
        last_heartbeat=now - timedelta(seconds=10),
        operator_id="test_user",
        target_type="calendar",
        target_id="week_23",
        payload={"action_id": "dry_run"},
        correlation_id="corr-1",
        retry_count=0,
        max_retries=3,
        result=JobResult(duration_seconds=5.0),
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
    db_conn.commit()

    sweep_res = supervisor.run_sweep()

    assert len(sweep_res.recovered_jobs) == 0
    assert len(sweep_res.failed_jobs) == 0

    refreshed = repo.get_job(job_id)
    assert refreshed.status == JobStatus.COMPLETED


def test_invalid_recovery_config() -> None:
    """Verify invalid RecoveryConfig options raise ValueErrors."""
    with pytest.raises(ValueError, match="heartbeat_timeout_seconds"):
        RecoveryConfig(
            heartbeat_timeout_seconds=0,
            sweep_interval_seconds=10,
            max_recovery_batch_size=10,
        )
    with pytest.raises(ValueError, match="sweep_interval_seconds"):
        RecoveryConfig(
            heartbeat_timeout_seconds=10,
            sweep_interval_seconds=0,
            max_recovery_batch_size=10,
        )
    with pytest.raises(ValueError, match="max_recovery_batch_size"):
        RecoveryConfig(
            heartbeat_timeout_seconds=10,
            sweep_interval_seconds=10,
            max_recovery_batch_size=0,
        )


def test_lock_release_failure_handling(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify exceptions raised during lock release do not crash the sweep."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)
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
    db_conn.commit()

    mock_lock = MagicMock()
    mock_lock.owner_job_id = job_id
    mock_lock.lock_id = uuid4()
    mock_lock.last_heartbeat = datetime.now(timezone.utc)
    supervisor.lock_repository.list_active_locks = MagicMock(return_value=[mock_lock])
    supervisor.lock_repository.release_lock = MagicMock(side_effect=RuntimeError("Lock error"))

    sweep_res = supervisor.run_sweep()
    assert str(job_id) in sweep_res.recovered_jobs


def test_schedule_retry_failure_fails_job(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify if schedule_retry raises an exception, the supervisor attempts to fail the job."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)
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
    db_conn.commit()

    supervisor.queue_engine.schedule_retry = MagicMock(side_effect=RuntimeError("Retry error"))

    sweep_res = supervisor.run_sweep()

    assert str(job_id) in sweep_res.failed_jobs
    refreshed = repo.get_job(job_id)
    assert refreshed.status == JobStatus.FAILED
    assert "Failed recovery transition: Retry error" in refreshed.error_message


def test_fail_job_failure_is_suppressed(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify if fail_job fails, the exception is caught and bypassed."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)
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
        retry_count=3,
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
    db_conn.commit()

    supervisor.repository.fail_job = MagicMock(side_effect=RuntimeError("Fail error"))

    sweep_res = supervisor.run_sweep()
    assert len(sweep_res.failed_jobs) == 0

