"""Tests for lock-related domain models and validation."""

from datetime import datetime, timezone
import pytest
from uuid import uuid4

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock


def test_lock_status_helpers() -> None:
    """Verify that is_active, is_released, and is_expired function correctly."""
    now = datetime.now(timezone.utc)
    lock_id = uuid4()
    owner_id = uuid4()

    lock_active = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.TOPIC,
        resource_id="topic_123",
        owner_job_id=owner_id,
        status=LockStatus.ACTIVE,
        acquired_at=now,
        last_heartbeat=now,
    )
    assert lock_active.is_active()
    assert not lock_active.is_released()
    assert not lock_active.is_expired()

    lock_released = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.TOPIC,
        resource_id="topic_123",
        owner_job_id=owner_id,
        status=LockStatus.RELEASED,
        acquired_at=now,
        last_heartbeat=now,
        released_at=now,
    )
    assert not lock_released.is_active()
    assert lock_released.is_released()
    assert not lock_released.is_expired()

    lock_expired = ResourceLock(
        lock_id=lock_id,
        lock_type=LockType.TOPIC,
        resource_id="topic_123",
        owner_job_id=owner_id,
        status=LockStatus.EXPIRED,
        acquired_at=now,
        last_heartbeat=now,
    )
    assert not lock_expired.is_active()
    assert not lock_expired.is_released()
    assert lock_expired.is_expired()


def test_lock_validation_resource_id() -> None:
    """Verify lock creation fails if resource_id is empty or whitespace."""
    now = datetime.now(timezone.utc)
    lock_id = uuid4()
    owner_id = uuid4()

    with pytest.raises(ValueError, match="resource_id cannot be empty"):
        ResourceLock(
            lock_id=lock_id,
            lock_type=LockType.TOPIC,
            resource_id="",
            owner_job_id=owner_id,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )

    with pytest.raises(ValueError, match="resource_id cannot be empty"):
        ResourceLock(
            lock_id=lock_id,
            lock_type=LockType.TOPIC,
            resource_id="   ",
            owner_job_id=owner_id,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )


def test_lock_validation_owner() -> None:
    """Verify lock creation fails if owner_job_id is missing."""
    now = datetime.now(timezone.utc)
    lock_id = uuid4()

    with pytest.raises(ValueError, match="owner_job_id cannot be empty"):
        ResourceLock(
            lock_id=lock_id,
            lock_type=LockType.TOPIC,
            resource_id="topic_123",
            owner_job_id=None,  # type: ignore
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )
