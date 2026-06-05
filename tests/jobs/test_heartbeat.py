"""Tests for Job heartbeat, recovery, and retry scheduling logic."""

from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_repository import SQLiteJobRepository


@pytest.fixture
def repo() -> SQLiteJobRepository:
    """Fixture providing SQLiteJobRepository with in-memory database."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield SQLiteJobRepository(conn)
    conn.close()


def test_heartbeat_updates(repo: SQLiteJobRepository) -> None:
    """Verify heartbeat only updates RUNNING jobs."""
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.COLLECT.value,
        status=JobStatus.QUEUED,  # Not RUNNING
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="system",
        target_type="topic",
        target_id="123",
        payload={},
        correlation_id="corr-1",
    )
    repo.create_job(job)

    # Calling heartbeat on QUEUED job should do nothing
    repo.heartbeat(job_id)
    fetched = repo.get_job(job_id)
    assert fetched.last_heartbeat is None

    # Transition to RUNNING
    claimed = repo.claim_next_job("worker_1")
    assert claimed is not None
    assert claimed.last_heartbeat is not None
    orig_heartbeat = claimed.last_heartbeat

    # Update heartbeat
    repo.heartbeat(job_id)
    updated = repo.get_job(job_id)
    assert updated.last_heartbeat is not None
    # Heartbeat must be updated
    assert updated.last_heartbeat >= orig_heartbeat


def test_schedule_retry_and_exhaustion(repo: SQLiteJobRepository) -> None:
    """Verify retry scheduling and transitions on budget exhaustion."""
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.GENERATE_BRIEF.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="worker_1",
        target_type="brief",
        target_id="123",
        payload={},
        correlation_id="corr-1",
        retry_count=0,
        max_retries=2,
    )
    repo.create_job(job)

    # Retry 1: Status becomes RETRYING, retry_count becomes 1, run_after populated
    retried1 = repo.schedule_retry(job_id, backoff_seconds=10.0, error_message="LLM Timeout")
    assert retried1.status == JobStatus.RETRYING
    assert retried1.retry_count == 1
    assert retried1.run_after is not None
    assert retried1.error_message == "LLM Timeout"

    # Move to RUNNING again for next attempt
    repo.claim_next_job("worker_1")

    # Retry 2: Status becomes RETRYING, retry_count becomes 2
    retried2 = repo.schedule_retry(job_id, backoff_seconds=10.0, error_message="LLM Timeout")
    assert retried2.status == JobStatus.RETRYING
    assert retried2.retry_count == 2

    # Move to RUNNING again
    repo.claim_next_job("worker_1")

    # Retry 3: Exceeds max_retries (2). Status becomes FAILED, completed_at populated
    retried3 = repo.schedule_retry(job_id, backoff_seconds=10.0, error_message="Rate Limit")
    assert retried3.status == JobStatus.FAILED
    assert retried3.retry_count == 3
    assert retried3.completed_at is not None
    assert "Max retries exhausted" in retried3.error_message


def test_stale_job_recovery(repo: SQLiteJobRepository) -> None:
    """Verify zombie RUNNING jobs are recovered or failed based on retry budget."""
    # Job A: RUNNING, retry_count = 0, max_retries = 2, stale heartbeat (timeout=30s)
    job_id_a = uuid4()
    now = datetime.now(timezone.utc)
    stale_time = now - timedelta(seconds=40)

    job_a = Job(
        job_id=job_id_a,
        job_type=JobType.PLAN_WEEK.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=stale_time,
        operator_id="worker_1",
        target_type="calendar",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        started_at=stale_time,
        last_heartbeat=stale_time,
        retry_count=0,
        max_retries=2,
    )
    repo.create_job(job_a)

    # Job B: RUNNING, retry_count = 2, max_retries = 2, stale heartbeat (budget exhausted)
    job_id_b = uuid4()
    job_b = Job(
        job_id=job_id_b,
        job_type=JobType.PLAN_WEEK.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=stale_time,
        operator_id="worker_1",
        target_type="calendar",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        started_at=stale_time,
        last_heartbeat=stale_time,
        retry_count=2,
        max_retries=2,
    )
    repo.create_job(job_b)

    # Run sweep
    stats = repo.recover_stale_jobs(timeout_seconds=30)
    assert stats["rescheduled"] == 1
    assert stats["failed"] == 1

    # Check database statuses
    fetched_a = repo.get_job(job_id_a)
    assert fetched_a.status == JobStatus.QUEUED
    assert fetched_a.retry_count == 1
    assert fetched_a.started_at is None
    assert fetched_a.last_heartbeat is None

    fetched_b = repo.get_job(job_id_b)
    assert fetched_b.status == JobStatus.FAILED
    assert fetched_b.retry_count == 3
    assert fetched_b.completed_at is not None
    assert "heartbeat timeout" in fetched_b.error_message.lower()


def test_cleanup_old_jobs(repo: SQLiteJobRepository) -> None:
    """Verify cleanup prunes old completed/failed/cancelled records."""
    now = datetime.now(timezone.utc)
    completed_old = now - timedelta(days=10)
    completed_fresh = now - timedelta(days=2)
    failed_old = now - timedelta(days=40)
    failed_fresh = now - timedelta(days=10)

    # COMPLETED - Old (Pruned)
    job_comp_old = Job(
        job_id=uuid4(),
        job_type=JobType.SCORE.value,
        status=JobStatus.COMPLETED,
        priority=100,
        created_at=completed_old,
        completed_at=completed_old,
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        result=JobResult(duration_seconds=1.0),
    )
    repo.create_job(job_comp_old)

    # COMPLETED - Fresh (Kept)
    job_comp_fresh = Job(
        job_id=uuid4(),
        job_type=JobType.SCORE.value,
        status=JobStatus.COMPLETED,
        priority=100,
        created_at=completed_fresh,
        completed_at=completed_fresh,
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        result=JobResult(duration_seconds=1.0),
    )
    repo.create_job(job_comp_fresh)

    # FAILED - Old (Pruned)
    job_fail_old = Job(
        job_id=uuid4(),
        job_type=JobType.SCORE.value,
        status=JobStatus.FAILED,
        priority=100,
        created_at=failed_old,
        completed_at=failed_old,
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        error_message="Fail",
    )
    repo.create_job(job_fail_old)

    # FAILED - Fresh (Kept)
    job_fail_fresh = Job(
        job_id=uuid4(),
        job_type=JobType.SCORE.value,
        status=JobStatus.FAILED,
        priority=100,
        created_at=failed_fresh,
        completed_at=failed_fresh,
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        error_message="Fail",
    )
    repo.create_job(job_fail_fresh)

    # Run cleanup
    cleanup_stats = repo.cleanup_old_jobs()
    # Expect 2 deleted (job_comp_old, job_fail_old)
    assert cleanup_stats["deleted"] == 2

    # Check kept entries
    assert repo.get_job(job_comp_fresh.job_id) is not None
    assert repo.get_job(job_fail_fresh.job_id) is not None
    # Check deleted entries
    assert repo.get_job(job_comp_old.job_id) is None
    assert repo.get_job(job_fail_old.job_id) is None
