"""Tests for Job domain models and status helpers."""

from datetime import datetime, timezone
import pytest
from uuid import uuid4

from content_creation.jobs.models import Job, JobResult, JobStatus, JobType


def test_status_helpers() -> None:
    """Verify that is_terminal and is_active behave correctly."""
    assert JobStatus.COMPLETED.is_terminal()
    assert JobStatus.FAILED.is_terminal()
    assert JobStatus.CANCELLED.is_terminal()
    assert not JobStatus.RUNNING.is_terminal()

    assert JobStatus.QUEUED.is_active()
    assert JobStatus.RUNNING.is_active()
    assert JobStatus.RETRYING.is_active()
    assert not JobStatus.COMPLETED.is_active()


def test_job_validation() -> None:
    """Verify entity validation constraints for retries."""
    job_id = uuid4()
    now = datetime.now(timezone.utc)

    # Negative retry count
    with pytest.raises(ValueError, match="retry_count must be non-negative"):
        Job(
            job_id=job_id,
            job_type=JobType.COLLECT.value,
            status=JobStatus.PENDING,
            priority=100,
            created_at=now,
            operator_id="system",
            target_type="topic",
            target_id="topic_1",
            payload={},
            correlation_id="corr_1",
            retry_count=-1,
        )

    # Negative max retries
    with pytest.raises(ValueError, match="max_retries must be non-negative"):
        Job(
            job_id=job_id,
            job_type=JobType.COLLECT.value,
            status=JobStatus.PENDING,
            priority=100,
            created_at=now,
            operator_id="system",
            target_type="topic",
            target_id="topic_1",
            payload={},
            correlation_id="corr_1",
            max_retries=-5,
        )


def test_coerce_string_status() -> None:
    """Verify string is coerced to JobStatus enum in post_init."""
    job = Job(
        job_id=uuid4(),
        job_type=JobType.COLLECT.value,
        status="PENDING",  # Pass raw string
        priority=100,
        created_at=datetime.now(timezone.utc),
        operator_id="system",
        target_type="topic",
        target_id="topic_1",
        payload={},
        correlation_id="corr_1",
    )
    assert job.status == JobStatus.PENDING
