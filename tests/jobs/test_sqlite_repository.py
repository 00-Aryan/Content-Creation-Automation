"""Tests for SQLiteJobRepository implementation."""

from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_repository import SQLiteJobRepository


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Fixture providing an in-memory SQLite connection with schema initialized."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn: sqlite3.Connection) -> SQLiteJobRepository:
    """Fixture providing SQLiteJobRepository instance."""
    return SQLiteJobRepository(db_conn)


def test_create_and_get_job(repo: SQLiteJobRepository) -> None:
    """Verify that a job can be created and retrieved from SQLite."""
    job_id = uuid4()
    now = datetime.now(timezone.utc)
    job = Job(
        job_id=job_id,
        job_type=JobType.COLLECT.value,
        status=JobStatus.PENDING,
        priority=10,
        created_at=now,
        operator_id="system",
        target_type="topic",
        target_id="123",
        payload={"url": "https://example.com"},
        correlation_id="corr-abc",
    )

    repo.create_job(job)

    # Fetch back
    fetched = repo.get_job(job_id)
    assert fetched is not None
    assert fetched.job_id == job_id
    assert fetched.job_type == JobType.COLLECT.value
    assert fetched.status == JobStatus.PENDING
    assert fetched.priority == 10
    assert fetched.payload == {"url": "https://example.com"}
    assert fetched.correlation_id == "corr-abc"

    # Integrity collision
    with pytest.raises(ValueError, match="already exists"):
        repo.create_job(job)


def test_update_job(repo: SQLiteJobRepository) -> None:
    """Verify updates and terminal state immutability checks."""
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.GENERATE_BRIEF.value,
        status=JobStatus.PENDING,
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="cli",
        target_type="brief",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )

    repo.create_job(job)

    # Standard update
    import dataclasses
    updated_job = dataclasses.replace(job, priority=50, status=JobStatus.RUNNING)
    repo.update_job(updated_job)

    fetched = repo.get_job(job_id)
    assert fetched.priority == 50
    assert fetched.status == JobStatus.RUNNING

    # Transition to terminal state (COMPLETED) is allowed
    terminal_job = dataclasses.replace(updated_job, status=JobStatus.COMPLETED)
    repo.update_job(terminal_job)

    # Further updates are blocked once terminal
    blocked_job = dataclasses.replace(terminal_job, priority=10)
    with pytest.raises(ValueError, match="State invariant violation"):
        repo.update_job(blocked_job)


def test_enqueue_job(repo: SQLiteJobRepository) -> None:
    """Verify enqueue moves job from PENDING/BLOCKED to QUEUED."""
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.PLAN_WEEK.value,
        status=JobStatus.PENDING,
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="system",
        target_type="calendar",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    repo.create_job(job)

    enqueued = repo.enqueue_job(job_id)
    assert enqueued.status == JobStatus.QUEUED
    assert enqueued.queued_at is not None

    # Verify enqueuing terminal job raises ValueError
    repo.complete_job(job_id, JobResult(duration_seconds=1.0))
    with pytest.raises(ValueError, match="Terminal jobs cannot be enqueued"):
        repo.enqueue_job(job_id)


def test_complete_and_fail_job(repo: SQLiteJobRepository) -> None:
    """Verify terminal updates complete_job and fail_job."""
    job_id_1 = uuid4()
    job_id_2 = uuid4()
    now = datetime.now(timezone.utc)

    job1 = Job(
        job_id=job_id_1,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=now,
        operator_id="system",
        target_type="dryrun",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    repo.create_job(job1)

    result = JobResult(duration_seconds=4.5, warnings=["warning 1"])
    completed = repo.complete_job(job_id_1, result)
    assert completed.status == JobStatus.COMPLETED
    assert completed.completed_at is not None
    assert completed.result.duration_seconds == 4.5
    assert completed.result.warnings == ["warning 1"]

    job2 = Job(
        job_id=job_id_2,
        job_type=JobType.SCORE.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=now,
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-2",
    )
    repo.create_job(job2)

    failed = repo.fail_job(job_id_2, "Out of memory error")
    assert failed.status == JobStatus.FAILED
    assert failed.completed_at is not None
    assert failed.error_message == "Out of memory error"


def test_cancel_job(repo: SQLiteJobRepository) -> None:
    """Verify job cancellation and validation."""
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.SCORE.value,
        status=JobStatus.QUEUED,
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    repo.create_job(job)

    cancelled = repo.cancel_job(job_id)
    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.completed_at is not None

    with pytest.raises(ValueError, match="Terminal jobs cannot be cancelled"):
        repo.cancel_job(job_id)


def test_delete_job(repo: SQLiteJobRepository) -> None:
    """Verify delete removes row from database."""
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.SCORE.value,
        status=JobStatus.PENDING,
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    repo.create_job(job)

    assert repo.get_job(job_id) is not None
    assert repo.delete_job(job_id) is True
    assert repo.get_job(job_id) is None
    assert repo.delete_job(job_id) is False
