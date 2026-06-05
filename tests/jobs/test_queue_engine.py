"""Tests for the QueueEngine submission and query interfaces."""

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


def test_job_submission_success(engine: QueueEngine) -> None:
    """Verify that a valid job submission writes database record and transitions to QUEUED."""
    res = engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="streamlit_ui",
        target_type="topic",
        target_id="all",
        payload={"source": "arxiv"},
        correlation_id="corr-abc",
    )

    assert res.job_id is not None
    assert res.status == JobStatus.QUEUED
    assert res.created_at is not None

    # Verify we can list it
    queued_jobs = engine.list_queued_jobs()
    assert len(queued_jobs) == 1
    assert queued_jobs[0].job_id == res.job_id
    assert queued_jobs[0].payload == {"source": "arxiv"}


def test_job_submission_invalid_payload(engine: QueueEngine) -> None:
    """Verify that submission fails if payload is not a dictionary."""
    with pytest.raises(ValueError, match="payload must be a dictionary"):
        engine.submit_job(
            job_type=JobType.COLLECT.value,
            action_id="collect",
            operator_id="streamlit_ui",
            target_type="topic",
            target_id="all",
            payload="not-a-dict",  # type: ignore
            correlation_id="corr-abc",
        )


def test_job_cancellation_rules(engine: QueueEngine) -> None:
    """Verify that cancellation only operates on non-active states."""
    # 1. Cancel QUEUED job -> Allowed
    res = engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score_topics",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    cancelled = engine.cancel_job(res.job_id)
    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.completed_at is not None

    # 2. Cancel RUNNING job -> Forbidden in QueueEngine (requires worker cooperative signal cancellation)
    res2 = engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score_topics",
        operator_id="system",
        target_type="topic",
        target_id="all",
        payload={},
        correlation_id="corr-2",
    )
    # Claim it to make it RUNNING
    running_job = engine.claim_next_job("worker_1")
    assert running_job is not None
    assert running_job.status == JobStatus.RUNNING

    with pytest.raises(ValueError, match="State transition forbidden"):
        engine.cancel_job(res2.job_id)
