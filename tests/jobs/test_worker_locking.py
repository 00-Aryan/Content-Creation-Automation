"""Tests for WorkerDaemon resource lock management and rollback rules."""

from datetime import datetime
import pytest
import sqlite3
from unittest.mock import MagicMock
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType
from content_creation.jobs.models import Job, JobStatus, JobType
from content_creation.jobs.queue_engine import QueueEngine
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository
from content_creation.jobs.sqlite_repository import SQLiteJobRepository
from content_creation.jobs.worker_daemon import WorkerConfig, WorkerDaemon
from content_creation.workflow.workflow_action_executor import ActionExecutionResult, ActionExecutionStatus


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Fixture providing in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def engine(db_conn: sqlite3.Connection) -> QueueEngine:
    repo = SQLiteJobRepository(db_conn)
    lock_repo = SQLiteLockRepository(db_conn)
    lock_mgr = LockManager(lock_repo)
    return QueueEngine(repo, lock_mgr)


@pytest.fixture
def config() -> WorkerConfig:
    return WorkerConfig(
        poll_interval_seconds=0.1,
        heartbeat_interval_seconds=0.1,
        zombie_timeout_seconds=5.0,
        max_concurrent_jobs=1,
        worker_id="test_worker_locks",
    )


def test_lock_acquisition_and_release(
    engine: QueueEngine,
    config: WorkerConfig,
) -> None:
    """Verify locks are acquired during run_once and released after execution."""
    res = engine.submit_job(
        job_type=JobType.GENERATE_BRIEF.value,
        action_id="generate_briefs",
        operator_id="client",
        target_type="topic",
        target_id="topic_123",
        payload={},
        correlation_id="corr-1",
    )

    mock_executor = MagicMock()
    mock_executor.execute.return_value = ActionExecutionResult(
        action_id="generate_briefs",
        success=True,
        execution_status=ActionExecutionStatus.SUCCESS,
        affected_artifacts={},
        warnings=[],
        blocking_reasons=[],
        execution_time=0.1,
    )

    # Let's inspect is_locked before running
    assert engine._locks.is_locked(LockType.TOPIC, "topic_123") is False

    worker = WorkerDaemon(
        ctx=None,
        queue_engine=engine,
        lock_manager=engine._locks,
        executor=mock_executor,
        config=config,
    )

    # We mock _acquire_locks to verify it gets called
    original_acquire = worker._acquire_locks
    worker._acquire_locks = MagicMock(side_effect=lambda j: original_acquire(j))

    run_res = worker.run_once()
    assert run_res.success is True

    # Verify locks were acquired
    worker._acquire_locks.assert_called_once()
    # Verify locks were released (released locks are inactive)
    assert engine._locks.is_locked(LockType.TOPIC, "topic_123") is False
    assert len(engine._locks.list_active_locks()) == 0


def test_lock_busy_reschedules_job(
    engine: QueueEngine,
    config: WorkerConfig,
) -> None:
    """Verify that worker returns job to QUEUED if locks cannot be acquired."""
    lock_mgr = engine._locks
    # 1. Acquire topic lock on 'topic_123' manually by another owner
    other_owner = uuid4()
    lock_mgr.acquire_topic_lock(other_owner, "topic_123")
    assert lock_mgr.is_locked(LockType.TOPIC, "topic_123") is True

    # 2. Submit a brief generation job targeting 'topic_123'
    res = engine.submit_job(
        job_type=JobType.GENERATE_BRIEF.value,
        action_id="generate_briefs",
        operator_id="client",
        target_type="topic",
        target_id="topic_123",
        payload={},
        correlation_id="corr-1",
    )

    mock_executor = MagicMock()
    worker = WorkerDaemon(
        ctx=None,
        queue_engine=engine,
        lock_manager=lock_mgr,
        executor=mock_executor,
        config=config,
    )

    # 3. Try to execute: lock manager should raise ValueError because topic_123 is already locked
    run_res = worker.run_once()
    assert run_res is not None
    assert run_res.success is False
    assert run_res.error_message == "Lock unavailable"

    # Job must not fail; it must transition back to QUEUED with run_after delay
    fetched = engine._repo.get_job(res.job_id)
    assert fetched.status == JobStatus.QUEUED
    assert fetched.run_after is not None
    assert fetched.started_at is None
    # Executor should never have been run
    mock_executor.execute.assert_not_called()
