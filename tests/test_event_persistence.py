"""Comprehensive tests for Phase 11.8.6 — Event Persistence & Replay System."""

import json
import os
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from content_creation.events.bus import InMemoryEventBus, get_event_bus
from content_creation.events.factory import (
    create_event,
    create_job_event,
    create_workflow_event,
)
from content_creation.events.models import EventSeverity, EventType, WorkflowEvent
from content_creation.events.store.models import EventRecord
from content_creation.events.store.repository import EventRepository
from content_creation.events.store.sqlite_repository import SQLiteEventRepository
from content_creation.events.store.schema import create_event_store_schema
from content_creation.events.store.subscriber import EventPersistenceSubscriber
from content_creation.events.store.replay import EventReplayEngine
from content_creation.events.store.timeline import EventTimelineService, TimelinePage
from content_creation.events.store.maintenance import EventMaintenanceService


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def tmp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def repo(tmp_db_path):
    """Create a SQLiteEventRepository with a temp database."""
    r = SQLiteEventRepository(tmp_db_path)
    yield r
    r.close()


@pytest.fixture
def bus():
    """Create a fresh InMemoryEventBus."""
    return InMemoryEventBus()


@pytest.fixture
def sample_event():
    """Create a sample WorkflowEvent."""
    return create_workflow_event(
        event_type=EventType.BRIEF_GENERATED,
        topic_id="test-topic-123",
        operator_id="operator-1",
        correlation_id="corr-123",
    )


@pytest.fixture
def sample_job_event():
    """Create a sample job WorkflowEvent."""
    return create_job_event(
        event_type=EventType.JOB_COMPLETED,
        job_id=uuid4(),
        job_type="brief_generation",
        status="completed",
        operator_id="operator-1",
        correlation_id="corr-456",
        target_type="brief",
        target_id="brief-789",
    )


def _make_event(
    event_type: EventType = EventType.BRIEF_GENERATED,
    entity_type: str = "brief",
    entity_id: str = "test-entity",
    correlation_id: str = "",
    source: str = "workflow_engine",
    payload: dict = None,
) -> WorkflowEvent:
    """Helper to create a WorkflowEvent with custom fields."""
    return create_event(
        event_type=event_type,
        source=source,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id or str(uuid4()),
        actor_id="test-actor",
        severity=EventSeverity.INFO,
        payload=payload or {"test": True},
    )


# ======================================================================
# PART 1: EventRecord MODEL TESTS
# ======================================================================


class TestEventRecord:
    def test_creation(self, sample_event):
        record = EventRecord.from_workflow_event(sample_event)
        assert record.event_id == sample_event.event_id
        assert record.event_name == sample_event.event_type.value
        assert record.source == sample_event.source
        assert record.correlation_id == sample_event.correlation_id
        assert record.entity_type == sample_event.entity_type
        assert record.entity_id == sample_event.entity_id
        assert record.version == 1

    def test_immutable(self, sample_event):
        record = EventRecord.from_workflow_event(sample_event)
        with pytest.raises(AttributeError):
            record.event_name = "changed"

    def test_payload_deserialization(self, sample_event):
        record = EventRecord.from_workflow_event(sample_event)
        payload = record.payload()
        assert isinstance(payload, dict)

    def test_to_dict(self, sample_event):
        record = EventRecord.from_workflow_event(sample_event)
        d = record.to_dict()
        assert d["event_name"] == sample_event.event_type.value
        assert "event_id" in d
        assert "created_at" in d

    def test_empty_payload(self):
        record = EventRecord(
            event_id=uuid4(),
            event_name="test",
            category="workflow",
            source="test",
            correlation_id="",
            entity_type="",
            entity_id="",
            payload_json="{}",
            created_at=datetime.now(timezone.utc),
        )
        assert record.payload() == {}

    def test_invalid_payload_json(self):
        record = EventRecord(
            event_id=uuid4(),
            event_name="test",
            category="workflow",
            source="test",
            correlation_id="",
            entity_type="",
            entity_id="",
            payload_json="not json",
            created_at=datetime.now(timezone.utc),
        )
        assert record.payload() == {}

    def test_from_workflow_event_categories(self):
        for event_type, expected_cat in [
            (EventType.BRIEF_GENERATED, "workflow"),
            (EventType.JOB_COMPLETED, "job"),
            (EventType.LOCK_ACQUIRED, "lock"),
            (EventType.ZOMBIE_JOB_RECOVERED, "recovery"),
            (EventType.PIPELINE_STARTED, "pipeline"),
        ]:
            event = _make_event(event_type=event_type)
            record = EventRecord.from_workflow_event(event)
            assert record.category == expected_cat, f"{event_type} should be {expected_cat}"


# ======================================================================
# PART 2: SCHEMA TESTS
# ======================================================================


class TestEventStoreSchema:
    def test_schema_creation(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_event_store_schema(conn)
            # Verify table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_schema_idempotent(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_event_store_schema(conn)
            create_event_store_schema(conn)  # Should not raise
        finally:
            conn.close()

    def test_indexes_created(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_event_store_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_events%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            assert "idx_events_timestamp" in indexes
            assert "idx_events_category" in indexes
            assert "idx_events_entity" in indexes
            assert "idx_events_correlation" in indexes
        finally:
            conn.close()


# ======================================================================
# PART 3: REPOSITORY CRUD TESTS
# ======================================================================


class TestSQLiteEventRepository:
    def test_save_and_get(self, repo, sample_event):
        record = EventRecord.from_workflow_event(sample_event)
        repo.save_event(record)
        retrieved = repo.get_event(record.event_id)
        assert retrieved is not None
        assert retrieved.event_name == record.event_name

    def test_get_nonexistent(self, repo):
        assert repo.get_event(uuid4()) is None

    def test_save_idempotent(self, repo, sample_event):
        record = EventRecord.from_workflow_event(sample_event)
        repo.save_event(record)
        repo.save_event(record)  # Duplicate — should be ignored
        assert repo.count_events() == 1

    def test_list_events(self, repo):
        for i in range(5):
            event = _make_event(payload={"index": i})
            repo.save_event(EventRecord.from_workflow_event(event))
        events = repo.list_events(limit=3)
        assert len(events) == 3

    def test_list_events_by_category(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.BRIEF_GENERATED)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.JOB_COMPLETED)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.JOB_FAILED)))
        job_events = repo.list_events(category="job")
        assert len(job_events) == 2
        workflow_events = repo.list_events(category="workflow")
        assert len(workflow_events) == 1

    def test_list_by_correlation(self, repo):
        cid = "corr-123"
        repo.save_event(EventRecord.from_workflow_event(_make_event(correlation_id=cid)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(correlation_id=cid)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(correlation_id="other")))
        events = repo.list_by_correlation(cid)
        assert len(events) == 2

    def test_list_by_entity(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event(entity_type="brief", entity_id="b1")))
        repo.save_event(EventRecord.from_workflow_event(_make_event(entity_type="brief", entity_id="b1")))
        repo.save_event(EventRecord.from_workflow_event(_make_event(entity_type="brief", entity_id="b2")))
        events = repo.list_by_entity("brief", "b1")
        assert len(events) == 2

    def test_list_by_category(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.BRIEF_GENERATED)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.JOB_COMPLETED)))
        events = repo.list_by_category("workflow")
        assert len(events) == 1

    def test_list_by_time_range(self, repo):
        now = datetime.now(timezone.utc)
        e1 = _make_event()
        r1 = EventRecord.from_workflow_event(e1)
        repo.save_event(r1)
        events = repo.list_by_time_range(now - timedelta(hours=1), now + timedelta(hours=1))
        assert len(events) >= 1

    def test_list_after_event(self, repo):
        e1 = _make_event(payload={"order": 1})
        e2 = _make_event(payload={"order": 2})
        r1 = EventRecord.from_workflow_event(e1)
        r2 = EventRecord.from_workflow_event(e2)
        # Ensure different timestamps
        time.sleep(0.01)
        repo.save_event(r1)
        repo.save_event(r2)
        events = repo.list_after_event(r1.event_id)
        assert len(events) >= 1
        assert events[0].event_id == r2.event_id

    def test_list_after_nonexistent_event(self, repo):
        events = repo.list_after_event(uuid4())
        assert events == []

    def test_count_events(self, repo):
        assert repo.count_events() == 0
        repo.save_event(EventRecord.from_workflow_event(_make_event()))
        assert repo.count_events() == 1
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.JOB_COMPLETED)))
        assert repo.count_events() == 2
        assert repo.count_events(category="job") == 1

    def test_delete_expired(self, repo):
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        record = EventRecord(
            event_id=uuid4(),
            event_name="old_event",
            category="lock",
            source="test",
            correlation_id="",
            entity_type="",
            entity_id="",
            payload_json="{}",
            created_at=old_time,
        )
        repo.save_event(record)
        recent = EventRecord.from_workflow_event(_make_event())
        repo.save_event(recent)
        deleted = repo.delete_expired(datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert deleted == 1
        assert repo.count_events() == 1

    def test_delete_expired_by_category(self, repo):
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        lock_record = EventRecord(
            event_id=uuid4(), event_name="lock_event", category="lock",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=old_time,
        )
        job_record = EventRecord(
            event_id=uuid4(), event_name="job_event", category="job",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=old_time,
        )
        repo.save_event(lock_record)
        repo.save_event(job_record)
        deleted = repo.delete_expired(datetime(2025, 1, 1, tzinfo=timezone.utc), category="lock")
        assert deleted == 1
        assert repo.count_events() == 1

    def test_thread_safety(self, tmp_db_path):
        repo = SQLiteEventRepository(tmp_db_path)
        try:
            errors: List[Exception] = []

            def save_events():
                try:
                    for _ in range(10):
                        event = _make_event()
                        repo.save_event(EventRecord.from_workflow_event(event))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=save_events) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == []
            assert repo.count_events() == 50
        finally:
            repo.close()


# ======================================================================
# PART 4: PERSISTENCE SUBSCRIBER TESTS
# ======================================================================


class TestEventPersistenceSubscriber:
    def test_persists_events(self, repo, bus):
        subscriber = EventPersistenceSubscriber(repository=repo, bus=bus)
        event = _make_event()
        bus.publish(event)
        assert repo.count_events() == 1

    def test_persists_multiple_events(self, repo, bus):
        subscriber = EventPersistenceSubscriber(repository=repo, bus=bus)
        for i in range(5):
            event = _make_event(payload={"index": i})
            bus.publish(event)
        assert repo.count_events() == 5

    def test_does_not_mutate_event(self, repo, bus):
        subscriber = EventPersistenceSubscriber(repository=repo, bus=bus)
        event = _make_event(payload={"original": True})
        bus.publish(event)
        # Event should be unchanged
        assert event.payload.get("original") is True

    def test_failure_isolation(self, repo, bus):
        subscriber = EventPersistenceSubscriber(repository=repo, bus=bus)

        def failing_callback(event):
            raise RuntimeError("Intentional failure")

        bus.subscribe_wildcard("*", failing_callback)
        event = _make_event()
        bus.publish(event)  # Should not raise
        assert repo.count_events() == 1

    def test_shutdown(self, repo, bus):
        subscriber = EventPersistenceSubscriber(repository=repo, bus=bus)
        subscriber.shutdown()
        event = _make_event()
        bus.publish(event)
        assert repo.count_events() == 0


# ======================================================================
# PART 5: REPLAY ENGINE TESTS
# ======================================================================


class TestEventReplayEngine:
    def test_replay_all(self, repo, bus):
        # Persist some events directly
        for i in range(3):
            event = _make_event(payload={"index": i})
            repo.save_event(EventRecord.from_workflow_event(event))

        # Create a new bus to capture re-emitted events
        replay_bus = InMemoryEventBus()
        received: List[WorkflowEvent] = []
        replay_bus.subscribe_wildcard("*", lambda e: received.append(e))

        engine = EventReplayEngine(repository=repo, bus=replay_bus)
        replayed = engine.replay_all(limit=10)
        assert len(replayed) == 3
        assert len(received) == 3

    def test_replay_dry_run(self, repo, bus):
        for i in range(3):
            event = _make_event(payload={"index": i})
            repo.save_event(EventRecord.from_workflow_event(event))

        replay_bus = InMemoryEventBus()
        received: List[WorkflowEvent] = []
        replay_bus.subscribe_wildcard("*", lambda e: received.append(e))

        engine = EventReplayEngine(repository=repo, bus=replay_bus)
        replayed = engine.replay_all(dry_run=True)
        assert len(replayed) == 3
        assert len(received) == 0  # Dry run — nothing published

    def test_replay_by_date_range(self, repo):
        now = datetime.now(timezone.utc)
        event = _make_event()
        repo.save_event(EventRecord.from_workflow_event(event))

        engine = EventReplayEngine(repository=repo)
        replayed = engine.replay_by_date_range(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert len(replayed) >= 1

    def test_replay_by_correlation(self, repo):
        cid = "corr-replay"
        for _ in range(3):
            event = _make_event(correlation_id=cid)
            repo.save_event(EventRecord.from_workflow_event(event))

        engine = EventReplayEngine(repository=repo)
        replayed = engine.replay_by_correlation(cid)
        assert len(replayed) == 3

    def test_replay_by_entity(self, repo):
        for _ in range(2):
            event = _make_event(entity_type="brief", entity_id="b1")
            repo.save_event(EventRecord.from_workflow_event(event))

        engine = EventReplayEngine(repository=repo)
        replayed = engine.replay_by_entity("brief", "b1")
        assert len(replayed) == 2

    def test_replay_by_category(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.BRIEF_GENERATED)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.JOB_COMPLETED)))

        engine = EventReplayEngine(repository=repo)
        replayed = engine.replay_by_category("job")
        assert len(replayed) == 1

    def test_replay_after_event(self, repo):
        e1 = _make_event(payload={"order": 1})
        e2 = _make_event(payload={"order": 2})
        r1 = EventRecord.from_workflow_event(e1)
        r2 = EventRecord.from_workflow_event(e2)
        time.sleep(0.01)
        repo.save_event(r1)
        repo.save_event(r2)

        engine = EventReplayEngine(repository=repo)
        replayed = engine.replay_after(r1.event_id)
        assert len(replayed) >= 1

    def test_unknown_event_type_skipped(self, repo):
        record = EventRecord(
            event_id=uuid4(),
            event_name="nonexistent_event_type",
            category="unknown",
            source="test",
            correlation_id="",
            entity_type="",
            entity_id="",
            payload_json="{}",
            created_at=datetime.now(timezone.utc),
        )
        repo.save_event(record)

        engine = EventReplayEngine(repository=repo)
        replayed = engine.replay_all()
        assert len(replayed) == 0


# ======================================================================
# PART 6: TIMELINE SERVICE TESTS
# ======================================================================


class TestEventTimelineService:
    def test_recent_events(self, repo):
        for _ in range(5):
            repo.save_event(EventRecord.from_workflow_event(_make_event()))

        service = EventTimelineService(repository=repo)
        page = service.recent_events(page_size=3)
        assert isinstance(page, TimelinePage)
        assert len(page.events) == 3
        assert page.total == 5
        assert page.total_pages == 2
        assert page.has_next is True
        assert page.has_previous is False

    def test_workflow_history(self, repo):
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(entity_type="brief", entity_id="topic-1")
        ))
        service = EventTimelineService(repository=repo)
        events = service.workflow_history("topic-1")
        assert len(events) == 1

    def test_job_history(self, repo):
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(EventType.JOB_COMPLETED, entity_type="job", entity_id="job-1")
        ))
        service = EventTimelineService(repository=repo)
        events = service.job_history()
        assert len(events) == 1

    def test_job_history_by_id(self, repo):
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(EventType.JOB_COMPLETED, entity_type="job", entity_id="job-1")
        ))
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(EventType.JOB_COMPLETED, entity_type="job", entity_id="job-2")
        ))
        service = EventTimelineService(repository=repo)
        events = service.job_history(job_id="job-1")
        assert len(events) == 1

    def test_entity_history(self, repo):
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(entity_type="asset", entity_id="a1")
        ))
        service = EventTimelineService(repository=repo)
        events = service.entity_history("asset", "a1")
        assert len(events) == 1

    def test_pipeline_history(self, repo):
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(EventType.PIPELINE_STARTED)
        ))
        service = EventTimelineService(repository=repo)
        events = service.pipeline_history()
        assert len(events) == 1

    def test_timeline_for_correlation(self, repo):
        cid = "corr-timeline"
        repo.save_event(EventRecord.from_workflow_event(_make_event(correlation_id=cid)))
        repo.save_event(EventRecord.from_workflow_event(_make_event(correlation_id=cid)))
        service = EventTimelineService(repository=repo)
        events = service.timeline_for_correlation(cid)
        assert len(events) == 2

    def test_events_in_range(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event()))
        service = EventTimelineService(repository=repo)
        now = datetime.now(timezone.utc)
        events = service.events_in_range(now - timedelta(hours=1), now + timedelta(hours=1))
        assert len(events) >= 1

    def test_search_events(self, repo):
        repo.save_event(EventRecord.from_workflow_event(
            _make_event(EventType.BRIEF_GENERATED, source="workflow_engine")
        ))
        service = EventTimelineService(repository=repo)
        events = service.search_events("brief")
        assert len(events) == 1

    def test_search_events_no_match(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event()))
        service = EventTimelineService(repository=repo)
        events = service.search_events("nonexistent")
        assert len(events) == 0


# ======================================================================
# PART 7: MAINTENANCE SERVICE TESTS
# ======================================================================


class TestEventMaintenanceService:
    def test_cleanup_expired(self, repo):
        old = EventRecord(
            event_id=uuid4(), event_name="old", category="lock",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        repo.save_event(old)
        recent = EventRecord.from_workflow_event(_make_event())
        repo.save_event(recent)

        service = EventMaintenanceService(repository=repo)
        deleted = service.cleanup_expired(category="lock")
        assert deleted == 1
        assert repo.count_events() == 1

    def test_enforce_retention(self, repo):
        old_lock = EventRecord(
            event_id=uuid4(), event_name="old_lock", category="lock",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        old_job = EventRecord(
            event_id=uuid4(), event_name="old_job", category="job",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        repo.save_event(old_lock)
        repo.save_event(old_job)

        service = EventMaintenanceService(repository=repo)
        summary = service.enforce_retention()
        assert "lock" in summary
        assert "job" in summary

    def test_storage_stats(self, repo):
        repo.save_event(EventRecord.from_workflow_event(_make_event()))
        repo.save_event(EventRecord.from_workflow_event(_make_event(EventType.JOB_COMPLETED)))
        service = EventMaintenanceService(repository=repo)
        stats = service.storage_stats()
        assert stats["total"] == 2
        assert stats["workflow"] == 1
        assert stats["job"] == 1


# ======================================================================
# PART 8: NOTIFICATION RECOVERY TESTS
# ======================================================================


class TestNotificationRecovery:
    def test_recover_missed_by_event_id(self, tmp_db_path):
        from content_creation.notifications.sqlite_repository import (
            SQLiteNotificationRepository,
        )
        from content_creation.notifications.schema import create_notification_schema
        from content_creation.notifications.recovery import NotificationRecoveryService

        event_repo = SQLiteEventRepository(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_notification_schema(conn)
            notif_repo = SQLiteNotificationRepository(conn)

            # Create events
            e1 = _make_event(EventType.BRIEF_GENERATED, payload={"title": "Brief Generated"})
            e2 = _make_event(EventType.JOB_COMPLETED, payload={"title": "Job Completed"})
            r1 = EventRecord.from_workflow_event(e1)
            r2 = EventRecord.from_workflow_event(e2)
            time.sleep(0.01)
            event_repo.save_event(r1)
            event_repo.save_event(r2)

            # Recover after r1
            service = NotificationRecoveryService(event_repo, notif_repo)
            recovered = service.recover_missed_notifications(
                last_known_event_id=str(r1.event_id)
            )
            assert len(recovered) >= 1
        finally:
            conn.close()
            event_repo.close()

    def test_no_duplicate_notifications(self, tmp_db_path):
        from content_creation.notifications.sqlite_repository import (
            SQLiteNotificationRepository,
        )
        from content_creation.notifications.schema import create_notification_schema
        from content_creation.notifications.recovery import NotificationRecoveryService

        event_repo = SQLiteEventRepository(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_notification_schema(conn)
            notif_repo = SQLiteNotificationRepository(conn)

            e1 = _make_event(EventType.BRIEF_GENERATED, payload={"title": "Brief Generated"})
            r1 = EventRecord.from_workflow_event(e1)
            event_repo.save_event(r1)

            # Pre-create notification
            from content_creation.notifications.models import (
                Notification,
                NotificationCategory,
                NotificationSeverity,
                NotificationStatus,
            )
            notif = Notification(
                notification_id=r1.event_id,
                title="Already exists",
                message="test",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=r1.created_at,
                correlation_id=r1.correlation_id,
            )
            notif_repo.create_notification(notif)

            service = NotificationRecoveryService(event_repo, notif_repo)
            recovered = service.recover_missed_notifications(
                last_known_event_id=str(r1.event_id)
            )
            # Should not create duplicate
            assert len(recovered) == 0
        finally:
            conn.close()
            event_repo.close()

    def test_unknown_event_not_recovered(self, tmp_db_path):
        from content_creation.notifications.sqlite_repository import (
            SQLiteNotificationRepository,
        )
        from content_creation.notifications.schema import create_notification_schema
        from content_creation.notifications.recovery import NotificationRecoveryService

        event_repo = SQLiteEventRepository(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_notification_schema(conn)
            notif_repo = SQLiteNotificationRepository(conn)

            # Event type not in _EVENT_TO_NOTIFICATION mapping
            e1 = _make_event(EventType.LOCK_ACQUIRED, payload={})
            r1 = EventRecord.from_workflow_event(e1)
            event_repo.save_event(r1)

            service = NotificationRecoveryService(event_repo, notif_repo)
            recovered = service.recover_missed_notifications(
                last_known_event_id=str(r1.event_id)
            )
            assert len(recovered) == 0
        finally:
            conn.close()
            event_repo.close()

    def test_invalid_event_id(self, tmp_db_path):
        from content_creation.notifications.sqlite_repository import (
            SQLiteNotificationRepository,
        )
        from content_creation.notifications.schema import create_notification_schema
        from content_creation.notifications.recovery import NotificationRecoveryService

        event_repo = SQLiteEventRepository(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_notification_schema(conn)
            notif_repo = SQLiteNotificationRepository(conn)

            service = NotificationRecoveryService(event_repo, notif_repo)
            recovered = service.recover_missed_notifications(
                last_known_event_id="not-a-uuid"
            )
            assert recovered == []
        finally:
            conn.close()
            event_repo.close()


# ======================================================================
# PART 9: INTEGRATION TESTS
# ======================================================================


class TestEventPersistenceIntegration:
    def test_full_lifecycle(self, tmp_db_path):
        """Test complete lifecycle: emit → persist → query → replay."""
        bus = InMemoryEventBus()
        event_repo = SQLiteEventRepository(tmp_db_path)
        try:
            # Subscribe persistence
            subscriber = EventPersistenceSubscriber(repository=event_repo, bus=bus)

            # Emit events
            for i in range(5):
                event = _make_event(payload={"step": i})
                bus.publish(event)

            assert event_repo.count_events() == 5

            # Query timeline
            timeline = EventTimelineService(repository=event_repo)
            page = timeline.recent_events(page_size=10)
            assert page.total == 5

            # Replay
            replay_bus = InMemoryEventBus()
            replayed_events: List[WorkflowEvent] = []
            replay_bus.subscribe_wildcard("*", lambda e: replayed_events.append(e))

            engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
            replayed = engine.replay_all()
            assert len(replayed) == 5
            assert len(replayed_events) == 5

            subscriber.shutdown()
        finally:
            event_repo.close()

    def test_retention_enforcement(self, tmp_db_path):
        """Test that retention cleanup works end-to-end."""
        event_repo = SQLiteEventRepository(tmp_db_path)
        try:
            # Add old events
            old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
            for i in range(5):
                record = EventRecord(
                    event_id=uuid4(), event_name=f"old_{i}", category="lock",
                    source="test", correlation_id="", entity_type="", entity_id="",
                    payload_json="{}", created_at=old_time,
                )
                event_repo.save_event(record)

            # Add recent events
            for i in range(3):
                event_repo.save_event(EventRecord.from_workflow_event(_make_event()))

            service = EventMaintenanceService(repository=event_repo)
            deleted = service.cleanup_expired(category="lock")
            assert deleted == 5
            assert event_repo.count_events() == 3
        finally:
            event_repo.close()

    def test_correlation_tracking(self, tmp_db_path):
        """Test that correlated events can be tracked together."""
        bus = InMemoryEventBus()
        event_repo = SQLiteEventRepository(tmp_db_path)
        try:
            subscriber = EventPersistenceSubscriber(repository=event_repo, bus=bus)

            correlation_id = str(uuid4())

            # Emit correlated events
            bus.publish(_make_event(EventType.BRIEF_GENERATED, correlation_id=correlation_id))
            bus.publish(_make_event(EventType.STORYBOARD_GENERATED, correlation_id=correlation_id))
            bus.publish(_make_event(EventType.ASSET_GENERATED, correlation_id=correlation_id))

            # Query by correlation
            events = event_repo.list_by_correlation(correlation_id)
            assert len(events) == 3
            assert all(e.correlation_id == correlation_id for e in events)

            subscriber.shutdown()
        finally:
            event_repo.close()


# ======================================================================
# PART 10: SSE RECOVERY INTEGRATION TESTS
# ======================================================================


class TestSSERecoveryIntegration:
    """Tests for SSE Last-Event-ID recovery via event store replay."""

    def test_replay_after_event_for_sse(self, repo):
        """Test that list_after_event returns events in correct order for SSE recovery."""
        e1 = _make_event(payload={"step": 1})
        e2 = _make_event(payload={"step": 2})
        e3 = _make_event(payload={"step": 3})
        r1 = EventRecord.from_workflow_event(e1)
        r2 = EventRecord.from_workflow_event(e2)
        r3 = EventRecord.from_workflow_event(e3)
        time.sleep(0.01)
        repo.save_event(r1)
        repo.save_event(r2)
        repo.save_event(r3)

        # Simulate Last-Event-ID = r2.event_id
        missed = repo.list_after_event(r2.event_id)
        assert len(missed) == 1
        assert missed[0].event_id == r3.event_id

    def test_replay_after_last_event_returns_empty(self, repo):
        """Test that replay after the last event returns nothing."""
        e1 = _make_event()
        r1 = EventRecord.from_workflow_event(e1)
        repo.save_event(r1)

        missed = repo.list_after_event(r1.event_id)
        assert missed == []

    def test_replay_engine_after_for_sse(self, repo):
        """Test EventReplayEngine.replay_after for SSE recovery."""
        e1 = _make_event(payload={"step": 1})
        e2 = _make_event(payload={"step": 2})
        r1 = EventRecord.from_workflow_event(e1)
        r2 = EventRecord.from_workflow_event(e2)
        time.sleep(0.01)
        repo.save_event(r1)
        repo.save_event(r2)

        replay_bus = InMemoryEventBus()
        received: List[WorkflowEvent] = []
        replay_bus.subscribe_wildcard("*", lambda e: received.append(e))

        engine = EventReplayEngine(repository=repo, bus=replay_bus)
        replayed = engine.replay_after(r1.event_id)
        assert len(replayed) == 1
        assert len(received) == 1
        assert received[0].event_id == r2.event_id

    def test_sse_recovery_no_duplicate_delivery(self, repo):
        """Test that SSE replay does not duplicate events already delivered."""
        e1 = _make_event(payload={"delivered": True})
        e2 = _make_event(payload={"missed": True})
        r1 = EventRecord.from_workflow_event(e1)
        r2 = EventRecord.from_workflow_event(e2)
        time.sleep(0.01)
        repo.save_event(r1)
        repo.save_event(r2)

        # Client already received r1, reconnects with Last-Event-ID = r1.event_id
        missed = repo.list_after_event(r1.event_id)
        assert len(missed) == 1
        assert missed[0].event_id == r2.event_id

    def test_sse_recovery_preserves_ordering(self, repo):
        """Test that replayed events maintain chronological order."""
        events = []
        for i in range(5):
            e = _make_event(payload={"order": i})
            r = EventRecord.from_workflow_event(e)
            time.sleep(0.005)
            repo.save_event(r)
            events.append(r)

        # Replay after event 2 (index 1)
        missed = repo.list_after_event(events[1].event_id)
        assert len(missed) == 3
        assert [m.event_id for m in missed] == [events[2].event_id, events[3].event_id, events[4].event_id]


# ======================================================================
# PART 11: REPOSITORY CLOSE & RESOURCE MANAGEMENT TESTS
# ======================================================================


class TestRepositoryClose:
    def test_close_releases_connection(self, tmp_db_path):
        repo = SQLiteEventRepository(tmp_db_path)
        repo.save_event(EventRecord.from_workflow_event(_make_event()))
        repo.close()
        # Should be able to create a new repo on the same path
        repo2 = SQLiteEventRepository(tmp_db_path)
        assert repo2.count_events() == 1
        repo2.close()

    def test_close_idempotent(self, tmp_db_path):
        repo = SQLiteEventRepository(tmp_db_path)
        repo.close()
        repo.close()  # Should not raise

    def test_operations_after_close_create_new_connection(self, tmp_db_path):
        repo = SQLiteEventRepository(tmp_db_path)
        repo.close()
        # Next operation should auto-create a new connection
        repo.save_event(EventRecord.from_workflow_event(_make_event()))
        assert repo.count_events() == 1
        repo.close()


# ======================================================================
# PART 12: EDGE CASE TESTS
# ======================================================================


class TestEdgeCases:
    def test_empty_repository_queries(self, repo):
        assert repo.count_events() == 0
        assert repo.list_events() == []
        assert repo.list_by_correlation("nonexistent") == []
        assert repo.list_by_entity("brief", "nonexistent") == []
        assert repo.list_by_category("workflow") == []

    def test_concurrent_reads_and_writes(self, tmp_db_path):
        repo = SQLiteEventRepository(tmp_db_path)
        try:
            errors: List[Exception] = []

            def writer():
                try:
                    for i in range(20):
                        repo.save_event(EventRecord.from_workflow_event(_make_event()))
                except Exception as e:
                    errors.append(e)

            def reader():
                try:
                    for _ in range(10):
                        repo.list_events(limit=5)
                        repo.count_events()
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=writer) for _ in range(3)]
            threads += [threading.Thread(target=reader) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == []
            assert repo.count_events() == 60
        finally:
            repo.close()

    def test_large_payload_persistence(self, repo):
        large_payload = {"data": "x" * 10000, "nested": {"key": list(range(100))}}
        event = _make_event(payload=large_payload)
        record = EventRecord.from_workflow_event(event)
        repo.save_event(record)

        retrieved = repo.get_event(record.event_id)
        assert retrieved is not None
        assert retrieved.payload()["data"] == "x" * 10000

    def test_unicode_payload(self, repo):
        payload = {"title": "ML pour les \u00e9tudiants", "emoji": "\u2705 done"}
        event = _make_event(payload=payload)
        record = EventRecord.from_workflow_event(event)
        repo.save_event(record)

        retrieved = repo.get_event(record.event_id)
        assert retrieved is not None
        assert retrieved.payload()["title"] == "ML pour les \u00e9tudiants"

    def test_special_characters_in_correlation_id(self, repo):
        cid = "corr:with:special/chars&more"
        repo.save_event(EventRecord.from_workflow_event(_make_event(correlation_id=cid)))
        events = repo.list_by_correlation(cid)
        assert len(events) == 1

    def test_maintenance_service_with_custom_retention(self, repo):
        from content_creation.events.store.maintenance import EventMaintenanceService

        custom_retention = {"workflow": 7, "job": 14}
        service = EventMaintenanceService(repository=repo, retention_days=custom_retention)

        # Add old workflow event (8 days old)
        old_time = datetime.now(timezone.utc) - timedelta(days=8)
        old_record = EventRecord(
            event_id=uuid4(), event_name="old_workflow", category="workflow",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=old_time,
        )
        repo.save_event(old_record)

        # Add recent job event (10 days old, within 14-day retention)
        recent_time = datetime.now(timezone.utc) - timedelta(days=10)
        recent_record = EventRecord(
            event_id=uuid4(), event_name="recent_job", category="job",
            source="test", correlation_id="", entity_type="", entity_id="",
            payload_json="{}", created_at=recent_time,
        )
        repo.save_event(recent_record)

        summary = service.enforce_retention()
        assert summary.get("workflow", 0) == 1
        assert summary.get("job", 0) == 0  # Within 14-day retention
        assert repo.count_events() == 1

    def test_timeline_page_properties(self):
        from content_creation.events.store.timeline import TimelinePage

        page = TimelinePage(events=[], total=0, page=1, page_size=10)
        assert page.total_pages == 1
        assert page.has_next is False
        assert page.has_previous is False

        page2 = TimelinePage(events=[], total=50, page=2, page_size=10)
        assert page2.total_pages == 5
        assert page2.has_next is True
        assert page2.has_previous is True
