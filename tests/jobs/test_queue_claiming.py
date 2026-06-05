"""Tests for queue claiming, lock checks, and priority selection in QueueEngine."""

from datetime import datetime, timezone
import pytest
import sqlite3
import time
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


def test_claim_priority_and_fifo_order(engine: QueueEngine) -> None:
    """Verify claim_next_job selects jobs sorted by priority ASC, queued_at ASC."""
    # 1. Job 1: Standard priority (100), submitted first
    job1 = engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
        priority=100,
    )

    # Small delay to ensure created_at/queued_at differs
    time.sleep(0.005)

    # 2. Job 2: Urgent priority (10), submitted second (should be claimed FIRST)
    job2 = engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-2",
        priority=10,
    )

    time.sleep(0.005)

    # 3. Job 3: Standard priority (100), submitted third (should be claimed THIRD)
    job3 = engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-3",
        priority=100,
    )

    # Claim 1: must return Job 2 (priority 10)
    claim1 = engine.claim_next_job("worker_1")
    assert claim1 is not None
    assert claim1.job_id == job2.job_id

    # Claim 2: must return Job 1 (priority 100, oldest)
    claim2 = engine.claim_next_job("worker_1")
    assert claim2 is not None
    assert claim2.job_id == job1.job_id

    # Claim 3: must return Job 3 (priority 100, newest)
    claim3 = engine.claim_next_job("worker_1")
    assert claim3 is not None
    assert claim3.job_id == job3.job_id


def test_skip_future_retry_jobs(engine: QueueEngine) -> None:
    """Verify that jobs in RETRYING state with run_after in the future are skipped during claim."""
    # 1. Job A: RETRYING, run_after = 1 hour in future
    res_a = engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    # Put it in retry with 1 hour backoff
    engine.claim_next_job("worker_1")
    engine.schedule_retry(res_a.job_id, error_message="LLM Offline", base_delay=3600.0)

    # 2. Job B: QUEUED, run_after is None
    res_b = engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-2",
    )

    # Claim next job: Job A must be skipped (future run_after), claiming Job B instead
    claimed = engine.claim_next_job("worker_2")
    assert claimed is not None
    assert claimed.job_id == res_b.job_id
