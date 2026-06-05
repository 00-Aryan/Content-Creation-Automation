"""Tests for the LockManager coordinator API."""

import pytest
import sqlite3
from uuid import uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository


@pytest.fixture
def manager() -> LockManager:
    """Fixture providing LockManager backed by in-memory SQLite repository."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    repo = SQLiteLockRepository(conn)
    yield LockManager(repo)
    conn.close()


def test_lock_manager_acquire_types(manager: LockManager) -> None:
    """Verify topic, manifest, and calendar locks can be acquired through the manager."""
    owner_id = uuid4()

    # Topic Lock
    topic_lock = manager.acquire_topic_lock(owner_id, "topic_123")
    assert topic_lock.lock_type == LockType.TOPIC
    assert topic_lock.resource_id == "topic_123"
    assert topic_lock.status == LockStatus.ACTIVE
    assert manager.is_locked(LockType.TOPIC, "topic_123") is True
    assert manager.get_lock_owner(LockType.TOPIC, "topic_123") == owner_id

    # Manifest Lock (distinct lock_type, so same resource_id is allowed to have an active manifest lock!)
    manifest_lock = manager.acquire_manifest_lock(owner_id, "topic_123")
    assert manifest_lock.lock_type == LockType.MANIFEST
    assert manifest_lock.resource_id == "topic_123"
    assert manager.is_locked(LockType.MANIFEST, "topic_123") is True

    # Calendar Lock
    calendar_lock = manager.acquire_calendar_lock(owner_id, "2026-06-01")
    assert calendar_lock.lock_type == LockType.CALENDAR
    assert calendar_lock.resource_id == "2026-06-01"
    assert manager.is_locked(LockType.CALENDAR, "2026-06-01") is True


def test_lock_manager_release_and_list(manager: LockManager) -> None:
    """Verify release and listing active locks through the coordinator."""
    owner_id = uuid4()
    lock = manager.acquire_topic_lock(owner_id, "topic_abc")

    assert len(manager.list_active_locks()) == 1

    manager.release_lock(lock.lock_id)
    assert len(manager.list_active_locks()) == 0
    assert manager.is_locked(LockType.TOPIC, "topic_abc") is False
