"""Tests for WorkerDaemon graceful startup and shutdown functionality."""

import pytest
import sqlite3
import time

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.queue_engine import QueueEngine
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository
from content_creation.jobs.sqlite_repository import SQLiteJobRepository
from content_creation.jobs.worker_daemon import WorkerConfig, WorkerDaemon


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
        poll_interval_seconds=0.01,
        heartbeat_interval_seconds=0.1,
        zombie_timeout_seconds=5.0,
        max_concurrent_jobs=1,
        worker_id="test_shutdown_worker",
    )


def test_worker_daemon_start_stop_lifecycle(
    engine: QueueEngine,
    config: WorkerConfig,
) -> None:
    """Verify that start and stop APIs cleanly control thread execution lifecycle."""
    lock_mgr = engine._locks
    worker = WorkerDaemon(
        ctx=None,
        queue_engine=engine,
        lock_manager=lock_mgr,
        config=config,
    )

    assert worker._is_running is False
    assert worker._main_thread is None

    # Start worker
    worker.start()
    assert worker._is_running is True
    assert worker._main_thread is not None
    assert worker._main_thread.is_alive() is True

    # Give it a tiny bit of running loop cycles
    time.sleep(0.05)

    # Stop worker
    worker.stop()
    assert worker._is_running is False
    # Main thread should be stopped and joined
    assert worker._main_thread.is_alive() is False


def test_invalid_worker_config() -> None:
    """Verify validation checks on worker configurations."""
    # Negative poll interval
    with pytest.raises(ValueError, match="poll_interval_seconds must be positive"):
        WorkerConfig(
            poll_interval_seconds=-1.0,
            heartbeat_interval_seconds=10.0,
            zombie_timeout_seconds=30.0,
            max_concurrent_jobs=1,
            worker_id="worker-1",
        )

    # Invalid concurrent count
    with pytest.raises(ValueError, match="max_concurrent_jobs must be at least 1"):
        WorkerConfig(
            poll_interval_seconds=2.0,
            heartbeat_interval_seconds=10.0,
            zombie_timeout_seconds=30.0,
            max_concurrent_jobs=0,
            worker_id="worker-1",
        )
