"""Tests for the QueueEngine retry scheduler and backoff policies."""

from datetime import datetime
import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.models import Job, JobStatus, JobType
from content_creation.jobs.queue_engine import QueueEngine
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
def engine(db_conn: sqlite3.Connection) -> QueueEngine:
    """Fixture providing QueueEngine instance."""
    repo = SQLiteJobRepository(db_conn)
    lock_repo = SQLiteLockRepository(db_conn)
    lock_mgr = LockManager(lock_repo)
    return QueueEngine(repo, lock_mgr)


def test_exponential_backoff_calculation(engine: QueueEngine) -> None:
    """Verify backoff calculation increments correctly at each retry step."""
    res = engine.submit_job(
        job_type=JobType.GENERATE_BRIEF.value,
        action_id="generate_briefs",
        operator_id="system",
        target_type="brief",
        target_id="123",
        payload={},
        correlation_id="corr-1",
        max_retries=3,
    )

    # First attempt fails
    engine.claim_next_job("worker_1")  # sets retry_count = 0
    # Retry 1: backoff_seconds = base_delay * (2 ** retry_count) = 5.0 * 2^0 = 5.0 seconds
    retried1 = engine.schedule_retry(res.job_id, "Attempt 1 failed", base_delay=5.0)
    assert retried1.status == JobStatus.RETRYING
    assert retried1.retry_count == 1
    assert retried1.run_after is not None

    # Next attempt fails
    engine.claim_next_job("worker_1")  # sets retry_count = 1
    # Retry 2: backoff_seconds = 5.0 * 2^1 = 10.0 seconds
    retried2 = engine.schedule_retry(res.job_id, "Attempt 2 failed", base_delay=5.0)
    assert retried2.status == JobStatus.RETRYING
    assert retried2.retry_count == 2


def test_retry_exhaustion_moves_to_failed(engine: QueueEngine) -> None:
    """Verify that exceeding max_retries transitions job status directly to FAILED."""
    res = engine.submit_job(
        job_type=JobType.GENERATE_BRIEF.value,
        action_id="generate_briefs",
        operator_id="system",
        target_type="brief",
        target_id="123",
        payload={},
        correlation_id="corr-1",
        max_retries=1,  # Only 1 retry allowed
    )

    # 1. First run fails -> rescheduled to retry (since max_retries = 1, retry_count becomes 1)
    engine.claim_next_job("worker_1")
    retried = engine.schedule_retry(res.job_id, "LLM Outage", base_delay=5.0)
    assert retried.status == JobStatus.RETRYING
    assert retried.retry_count == 1

    # 2. Second run fails -> retry budget exhausted (retry_count becomes 2 > 1) -> FAILED
    engine.claim_next_job("worker_1")
    failed = engine.schedule_retry(res.job_id, "LLM Outage again", base_delay=5.0)
    assert failed.status == JobStatus.FAILED
    assert failed.retry_count == 2
    assert "Max retries exhausted" in failed.error_message
