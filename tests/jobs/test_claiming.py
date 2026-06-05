"""Concurrency tests for SQLiteJobRepository claim lock execution."""

import concurrent.futures
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import pytest
from uuid import uuid4

from content_creation.jobs.models import Job, JobStatus, JobType
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_repository import SQLiteJobRepository


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite file path."""
    db_file = tmp_path / "jobs_test.db"
    return db_file


def test_concurrent_job_claiming(temp_db_path: Path) -> None:
    """Verify that multiple concurrent threads attempting to claim a job do not double-claim."""
    # 1. Initialize schema in the shared file database
    conn = sqlite3.connect(str(temp_db_path))
    try:
        create_schema(conn)

        # 2. Insert one QUEUED job
        job_id = uuid4()
        job = Job(
            job_id=job_id,
            job_type=JobType.COLLECT.value,
            status=JobStatus.QUEUED,
            priority=10,
            created_at=datetime.now(timezone.utc),
            operator_id="client",
            target_type="topic",
            target_id="123",
            payload={},
            correlation_id="corr-1",
        )
        repo = SQLiteJobRepository(conn)
        repo.create_job(job)
    finally:
        conn.close()

    # 3. Define the claiming target worker thread function
    def claim_job(worker_id: str) -> tuple[str, bool]:
        # Each worker thread must open its own SQLite connection
        thread_conn = sqlite3.connect(str(temp_db_path))
        # Set short connection timeouts
        thread_conn.execute("PRAGMA busy_timeout = 1000;")
        thread_repo = SQLiteJobRepository(thread_conn)
        try:
            claimed = thread_repo.claim_next_job(worker_id)
            has_claimed = claimed is not None
            return worker_id, has_claimed
        finally:
            thread_conn.close()

    # 4. Spin up Worker A and Worker B concurrently
    workers = ["worker_A", "worker_B"]
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(claim_job, w): w for w in workers}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    # 5. Assert concurrency invariants
    claims = [res for worker, res in results if res is True]
    assert len(claims) == 1, f"Expected exactly 1 claim, got: {results}"

    # Verify state in database
    conn = sqlite3.connect(str(temp_db_path))
    try:
        final_repo = SQLiteJobRepository(conn)
        final_job = final_repo.get_job(job_id)
        assert final_job is not None
        assert final_job.status == JobStatus.RUNNING
        # operator_id should preserve the original operator 'client'
        assert final_job.operator_id == "client"
    finally:
        conn.close()


def test_target_resource_locking(temp_db_path: Path) -> None:
    """Verify that a candidate job is skipped if its target resource is already busy (RUNNING)."""
    conn = sqlite3.connect(str(temp_db_path))
    try:
        create_schema(conn)
        repo = SQLiteJobRepository(conn)

        # 1. Insert a job that is already RUNNING on target 'topic_123'
        running_job = Job(
            job_id=uuid4(),
            job_type=JobType.GENERATE_BRIEF.value,
            status=JobStatus.RUNNING,
            priority=10,
            created_at=datetime.now(timezone.utc),
            operator_id="worker_A",
            target_type="topic",
            target_id="topic_123",
            payload={},
            correlation_id="corr-1",
            started_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
        )
        repo.create_job(running_job)

        # 2. Insert a second job targeting 'topic_123' that is QUEUED
        queued_job_blocked = Job(
            job_id=uuid4(),
            job_type=JobType.GENERATE_STORYBOARD.value,
            status=JobStatus.QUEUED,
            priority=10,
            created_at=datetime.now(timezone.utc),
            operator_id="client",
            target_type="topic",
            target_id="topic_123",
            payload={},
            correlation_id="corr-1",
        )
        repo.create_job(queued_job_blocked)

        # 3. Insert a third job targeting 'topic_456' that is QUEUED (should be claimable)
        queued_job_free = Job(
            job_id=uuid4(),
            job_type=JobType.GENERATE_STORYBOARD.value,
            status=JobStatus.QUEUED,
            priority=10,
            created_at=datetime.now(timezone.utc),
            operator_id="client",
            target_type="topic",
            target_id="topic_456",
            payload={},
            correlation_id="corr-1",
        )
        repo.create_job(queued_job_free)

        # Attempt to claim next job as 'worker_B'
        claimed = repo.claim_next_job("worker_B")
        assert claimed is not None
        # Must skip 'topic_123' job and claim 'topic_456' job
        assert claimed.job_id == queued_job_free.job_id
        assert claimed.target_id == "topic_456"
    finally:
        conn.close()
