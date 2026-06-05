"""Tests for queue and lock consistency checks in RecoverySupervisor."""

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


def test_queue_consistency_all_valid(supervisor: RecoverySupervisor) -> None:
    """Verify a clean database produces an empty consistency report."""
    report = supervisor.validate_queue_consistency()
    assert len(report.warnings) == 0
    assert len(report.errors) == 0
    assert len(report.recoverable_issues) == 0


def test_queue_consistency_anomalies(
    supervisor: RecoverySupervisor, db_conn: sqlite3.Connection
) -> None:
    """Verify that all five consistency anomaly conditions are detected and reported."""
    repo = supervisor.repository
    now = datetime.now(timezone.utc)

    # 1. RUNNING job with no worker heartbeat (last_heartbeat is NULL)
    job_no_hb_id = uuid4()
    job_no_hb = Job(
        job_id=job_no_hb_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=now - timedelta(seconds=10),
        started_at=now - timedelta(seconds=10),
        last_heartbeat=None,  # Invalid: RUNNING but no heartbeat
        operator_id="user_1",
        target_type="calendar",
        target_id="week_1",
        payload={"action_id": "dry_run"},
        correlation_id="corr-1",
    )

    # 2. QUEUED job past run_after
    job_queued_expired_id = uuid4()
    job_queued_expired = Job(
        job_id=job_queued_expired_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.QUEUED,
        priority=100,
        created_at=now - timedelta(seconds=20),
        queued_at=now - timedelta(seconds=20),
        run_after=now - timedelta(seconds=10),  # Expired
        operator_id="user_1",
        target_type="calendar",
        target_id="week_2",
        payload={"action_id": "dry_run"},
        correlation_id="corr-2",
    )

    # 3. RETRYING job with expired retry window
    job_retrying_expired_id = uuid4()
    job_retrying_expired = Job(
        job_id=job_retrying_expired_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.RETRYING,
        priority=100,
        created_at=now - timedelta(seconds=20),
        run_after=now - timedelta(seconds=10),  # Expired retry window
        operator_id="user_1",
        target_type="calendar",
        target_id="week_3",
        payload={"action_id": "dry_run"},
        correlation_id="corr-3",
    )

    # Insert jobs
    cursor = db_conn.cursor()
    for job in [job_no_hb, job_queued_expired, job_retrying_expired]:
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

    # 4. Lock referencing missing job
    lock_missing_job_id = uuid4()
    missing_job_id = uuid4()
    lock_missing_data = (
        str(lock_missing_job_id),
        LockType.TOPIC.value,
        "missing_topic",
        str(missing_job_id),  # Not in DB
        LockStatus.ACTIVE.value,
        now.isoformat(),
        now.isoformat(),
        None,
        "{}",
    )

    # 5. Lock owned by terminal job
    terminal_job_id = uuid4()
    terminal_job = Job(
        job_id=terminal_job_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.COMPLETED,
        priority=100,
        created_at=now - timedelta(seconds=20),
        started_at=now - timedelta(seconds=15),
        completed_at=now - timedelta(seconds=10),
        operator_id="user_1",
        target_type="calendar",
        target_id="week_4",
        payload={"action_id": "dry_run"},
        correlation_id="corr-4",
    )
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
        repo._to_row(terminal_job),
    )

    lock_terminal_owner_id = uuid4()
    lock_terminal_data = (
        str(lock_terminal_owner_id),
        LockType.TOPIC.value,
        "terminal_topic",
        str(terminal_job_id),  # Belongs to a COMPLETED job
        LockStatus.ACTIVE.value,
        now.isoformat(),
        now.isoformat(),
        None,
        "{}",
    )

    for row in [lock_missing_data, lock_terminal_data]:
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

    # Run validation
    report = supervisor.validate_queue_consistency()

    # Check warnings (running no heartbeat, queued past run_after, retrying expired window)
    assert len(report.warnings) == 3
    warn_types = [issue["type"] for issue in report.recoverable_issues]
    assert "running_no_heartbeat" in warn_types
    assert "queued_past_run_after" in warn_types
    assert "retrying_expired_window" in warn_types

    # Check errors (lock referencing missing job, lock owned by terminal job)
    assert len(report.errors) == 2
    err_types = [issue["type"] for issue in report.recoverable_issues if issue["type"] in ("lock_missing_job", "lock_owned_by_terminal_job")]
    assert "lock_missing_job" in err_types
    assert "lock_owned_by_terminal_job" in err_types
