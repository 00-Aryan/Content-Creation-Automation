"""Tests for WorkerDaemon execution lifecycle and executor interactions."""

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
def repo(db_conn: sqlite3.Connection) -> SQLiteJobRepository:
    return SQLiteJobRepository(db_conn)


@pytest.fixture
def lock_mgr(db_conn: sqlite3.Connection) -> LockManager:
    lock_repo = SQLiteLockRepository(db_conn)
    return LockManager(lock_repo)


@pytest.fixture
def queue_engine(repo: SQLiteJobRepository, lock_mgr: LockManager) -> QueueEngine:
    return QueueEngine(repo, lock_mgr)


@pytest.fixture
def config() -> WorkerConfig:
    return WorkerConfig(
        poll_interval_seconds=0.1,
        heartbeat_interval_seconds=0.1,
        zombie_timeout_seconds=5.0,
        max_concurrent_jobs=1,
        worker_id="test_worker_1",
    )


def test_successful_job_execution(
    db_conn: sqlite3.Connection,
    queue_engine: QueueEngine,
    lock_mgr: LockManager,
    repo: SQLiteJobRepository,
    config: WorkerConfig,
) -> None:
    """Verify that worker claims, executes successfully via executor, and transitions job to COMPLETED."""
    # 1. Submit a job
    res = queue_engine.submit_job(
        job_type=JobType.COLLECT.value,
        action_id="collect",
        operator_id="client",
        target_type="topic",
        target_id="123",
        payload={},
        correlation_id="corr-1",
    )

    # 2. Mock the WorkflowActionExecutor to report success
    mock_executor = MagicMock()
    mock_executor.execute.return_value = ActionExecutionResult(
        action_id="collect",
        success=True,
        execution_status=ActionExecutionStatus.SUCCESS,
        affected_artifacts={"staged_count": "5"},
        warnings=["warning test"],
        blocking_reasons=[],
        execution_time=0.5,
        emitted_events=["event_1"],
    )

    worker = WorkerDaemon(
        ctx=None,
        queue_engine=queue_engine,
        lock_manager=lock_mgr,
        executor=mock_executor,
        config=config,
    )

    # 3. Run a single iteration of the worker
    run_res = worker.run_once()
    assert run_res is not None
    assert run_res.success is True
    assert run_res.job_id == str(res.job_id)
    assert run_res.warnings == ["warning test"]
    assert run_res.events_emitted == ["event_1"]

    # 4. Verify state updates in database
    fetched = repo.get_job(res.job_id)
    assert fetched.status == JobStatus.COMPLETED
    assert fetched.completed_at is not None
    assert fetched.result is not None
    assert fetched.result.generated_files == {"staged_count": "5"}

    # 5. Verify executor was called with parameters
    mock_executor.execute.assert_called_once_with(
        ctx=None,
        action_id="collect",
        target_artifact_type="topic",
        target_artifact_id="123",
        payload={},
        operator_id="client",
    )


def test_executor_failure_path_retry(
    db_conn: sqlite3.Connection,
    queue_engine: QueueEngine,
    lock_mgr: LockManager,
    repo: SQLiteJobRepository,
    config: WorkerConfig,
) -> None:
    """Verify worker handles action failure, transitioning job to RETRYING and scheduling retry."""
    res = queue_engine.submit_job(
        job_type=JobType.SCORE.value,
        action_id="score",
        operator_id="client",
        target_type="topic",
        target_id="123",
        payload={},
        correlation_id="corr-1",
        max_retries=2,
    )

    # Mock the WorkflowActionExecutor to report failure
    mock_executor = MagicMock()
    mock_executor.execute.return_value = ActionExecutionResult(
        action_id="score",
        success=False,
        execution_status=ActionExecutionStatus.FAILED,
        affected_artifacts={},
        warnings=[],
        blocking_reasons=["LLM provider overloaded"],
        execution_time=0.1,
    )

    worker = WorkerDaemon(
        ctx=None,
        queue_engine=queue_engine,
        lock_manager=lock_mgr,
        executor=mock_executor,
        config=config,
    )

    # Run once
    run_res = worker.run_once()
    assert run_res is not None
    assert run_res.success is False
    assert "LLM provider overloaded" in run_res.error_message

    # Verify job status is RETRYING
    fetched = repo.get_job(res.job_id)
    assert fetched.status == JobStatus.RETRYING
    assert fetched.retry_count == 1


def test_empty_queue_polling(
    queue_engine: QueueEngine,
    lock_mgr: LockManager,
    config: WorkerConfig,
) -> None:
    """Verify polling empty queue returns None without crashing."""
    worker = WorkerDaemon(
        ctx=None,
        queue_engine=queue_engine,
        lock_manager=lock_mgr,
        config=config,
    )
    assert worker.run_once() is None
