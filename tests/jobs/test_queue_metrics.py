"""Tests for QueueEngine snapshot queue metrics queries."""

from datetime import datetime, timedelta
import pytest
import sqlite3
import time
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
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


def test_snapshot_metrics_status_counts(engine: QueueEngine) -> None:
    """Verify metrics counts match current states in queue database."""
    # Insert:
    # 1. Job A: COMPLETED
    res_a = engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="system",
        target_type="topic",
        target_id="1",
        payload={},
        correlation_id="corr-1",
    )
    engine.claim_next_job("worker_1")
    repo = engine._repo
    repo.complete_job(res_a.job_id, JobResult(duration_seconds=1.5))

    # 2. Job B: RUNNING
    engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score",
        operator_id="system",
        target_type="topic",
        target_id="2",
        payload={},
        correlation_id="corr-1",
    )
    engine.claim_next_job("worker_2")

    # 3. Job C: QUEUED
    engine.submit_job(
        job_type=JobType.GENERATE_BRIEF.value,
        action_id="generate",
        operator_id="system",
        target_type="brief",
        target_id="3",
        payload={},
        correlation_id="corr-1",
    )

    metrics = engine.get_queue_metrics()
    assert metrics.completed_count == 1
    assert metrics.running_count == 1
    assert metrics.queued_count == 1
    assert metrics.failed_count == 0


def test_oldest_queued_age_calculation(engine: QueueEngine) -> None:
    """Verify that oldest queued job age calculation returns accurate duration in seconds."""
    # No queued jobs -> age is 0.0
    metrics_empty = engine.get_queue_metrics()
    assert metrics_empty.oldest_queued_age_seconds == 0.0

    # Submit job
    res = engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )

    # Let some time pass (simulated or time.sleep)
    time.sleep(0.1)

    metrics_active = engine.get_queue_metrics()
    assert metrics_active.oldest_queued_age_seconds >= 0.1
