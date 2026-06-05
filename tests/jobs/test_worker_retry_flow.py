"""Tests for WorkerDaemon retry flows and failure recovery limits."""

from datetime import datetime
import pytest
import sqlite3
from unittest.mock import MagicMock
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
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
        worker_id="test_worker",
    )


def test_exception_during_execution_triggers_retry(
    engine: QueueEngine,
    config: WorkerConfig,
) -> None:
    """Verify that a raw exception raised by the executor triggers retry scheduling."""
    # 1. Submit a job with max_retries = 2
    res = engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="client",
        target_type="topic",
        target_id="123",
        payload={},
        correlation_id="corr-1",
        max_retries=2,
    )

    # 2. Mock executor to raise a RuntimeError
    mock_executor = MagicMock()
    mock_executor.execute.side_effect = RuntimeError("Temporary socket failure")

    worker = WorkerDaemon(
        ctx=None,
        queue_engine=engine,
        lock_manager=engine._locks,
        executor=mock_executor,
        config=config,
    )

    # 3. Execute
    run_res = worker.run_once()
    assert run_res is not None
    assert run_res.success is False
    assert "Temporary socket failure" in run_res.error_message

    # 4. Verify job transitioned to RETRYING
    fetched = engine._repo.get_job(res.job_id)
    assert fetched.status == JobStatus.RETRYING
    assert fetched.retry_count == 1
    assert fetched.error_message == "Temporary socket failure"


def test_exception_exhaustion_transitions_to_failed(
    engine: QueueEngine,
    config: WorkerConfig,
) -> None:
    """Verify that repeated exceptions eventually transition the job to FAILED."""
    # Submit job with max_retries = 1
    res = engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="client",
        target_type="topic",
        target_id="123",
        payload={},
        correlation_id="corr-1",
        max_retries=1,
    )

    mock_executor = MagicMock()
    mock_executor.execute.side_effect = RuntimeError("Fatal LLM error")

    worker = WorkerDaemon(
        ctx=None,
        queue_engine=engine,
        lock_manager=engine._locks,
        executor=mock_executor,
        config=config,
    )

    # Attempt 1: RUNNING -> RETRYING (retry_count = 1)
    run_res_1 = worker.run_once()
    assert run_res_1.success is False

    fetched_attempt_1 = engine._repo.get_job(res.job_id)
    assert fetched_attempt_1.status == JobStatus.RETRYING

    # Clear run_after and move back to QUEUED to make it claimable immediately
    import dataclasses
    engine._repo.update_job(
        dataclasses.replace(
            fetched_attempt_1,
            status=JobStatus.QUEUED,
            run_after=None,
            started_at=None,
            last_heartbeat=None
        )
    )

    # Attempt 2: RUNNING -> FAILED (retry_count = 2 > max_retries = 1)
    run_res_2 = worker.run_once()
    assert run_res_2.success is False

    fetched_attempt_2 = engine._repo.get_job(res.job_id)
    assert fetched_attempt_2.status == JobStatus.FAILED
    assert "Max retries exhausted" in fetched_attempt_2.error_message
