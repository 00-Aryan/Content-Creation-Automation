"""Comprehensive tests for Phase 11.8.3 — Event Subscriber Architecture & Notification Integration."""

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from content_creation.events.bus import InMemoryEventBus
from content_creation.events.factory import (
    create_event,
    create_job_event,
    create_lock_event,
    create_recovery_event,
    create_workflow_event,
)
from content_creation.events.models import EventSeverity, EventType, WorkflowEvent
from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.repository import NotificationRepository
from content_creation.notifications.schema import create_notification_schema
from content_creation.notifications.sqlite_repository import SQLiteNotificationRepository
from content_creation.subscribers.dispatcher import EventDispatcher
from content_creation.subscribers.job_subscriber import JobNotificationSubscriber
from content_creation.subscribers.models import (
    EventFilter,
    SubscriberExecutionResult,
    Subscription,
)
from content_creation.subscribers.system_subscriber import SystemNotificationSubscriber
from content_creation.subscribers.workflow_subscriber import WorkflowNotificationSubscriber


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with notification schema."""
    conn = sqlite3.connect(":memory:")
    create_notification_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn: sqlite3.Connection) -> SQLiteNotificationRepository:
    return SQLiteNotificationRepository(db_conn)


@pytest.fixture
def bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def dispatcher(bus: InMemoryEventBus) -> EventDispatcher:
    return EventDispatcher(bus)


# ======================================================================
# PART 2: SUBSCRIBER MODEL TESTS
# ======================================================================


class TestEventFilter:
    def test_exact_event_type_match(self) -> None:
        f = EventFilter(event_type=EventType.JOB_CREATED)
        assert f.matches(EventType.JOB_CREATED, "job_system") is True
        assert f.matches(EventType.JOB_FAILED, "job_system") is False

    def test_category_match(self) -> None:
        f = EventFilter(category="job")
        assert f.matches(EventType.JOB_CREATED, "job_system") is True
        assert f.matches(EventType.JOB_COMPLETED, "worker_daemon") is True
        assert f.matches(EventType.BRIEF_GENERATED, "workflow_engine") is False

    def test_source_match(self) -> None:
        f = EventFilter(source="lock_manager")
        assert f.matches(EventType.LOCK_ACQUIRED, "lock_manager") is True
        assert f.matches(EventType.LOCK_ACQUIRED, "other") is False

    def test_combined_filters(self) -> None:
        f = EventFilter(category="job", source="worker_daemon")
        assert f.matches(EventType.JOB_STARTED, "worker_daemon") is True
        assert f.matches(EventType.JOB_STARTED, "queue_engine") is False
        assert f.matches(EventType.BRIEF_GENERATED, "worker_daemon") is False

    def test_empty_filter_matches_all(self) -> None:
        f = EventFilter()
        assert f.matches(EventType.JOB_CREATED, "any_source") is True
        assert f.matches(EventType.BRIEF_GENERATED, "other") is True


class TestSubscription:
    def test_creation(self) -> None:
        s = Subscription(
            subscriber_id="test_sub",
            event_filter=EventFilter(category="job"),
        )
        assert s.subscriber_id == "test_sub"
        assert s.event_filter.category == "job"
        assert s.priority == 100

    def test_custom_priority(self) -> None:
        s = Subscription(
            subscriber_id="high_pri",
            event_filter=EventFilter(),
            priority=10,
        )
        assert s.priority == 10

    def test_empty_subscriber_id_raises(self) -> None:
        with pytest.raises(ValueError, match="subscriber_id must be non-empty"):
            Subscription(subscriber_id="", event_filter=EventFilter())

    def test_immutable(self) -> None:
        s = Subscription(
            subscriber_id="test",
            event_filter=EventFilter(),
        )
        with pytest.raises(AttributeError):
            s.subscriber_id = "new"  # type: ignore


class TestSubscriberExecutionResult:
    def test_success_result(self) -> None:
        eid = uuid4()
        r = SubscriberExecutionResult(
            subscriber_id="sub1",
            event_id=eid,
            execution_duration_ms=12.5,
            success=True,
        )
        assert r.success is True
        assert r.subscriber_id == "sub1"
        assert r.event_id == eid
        assert r.execution_duration_ms == 12.5
        assert r.exception_type is None
        assert r.exception_message is None
        assert isinstance(r.timestamp, datetime)

    def test_failure_result(self) -> None:
        r = SubscriberExecutionResult(
            subscriber_id="sub2",
            event_id=uuid4(),
            execution_duration_ms=5.0,
            success=False,
            exception_type="RuntimeError",
            exception_message="something broke",
        )
        assert r.success is False
        assert r.exception_type == "RuntimeError"
        assert r.exception_message == "something broke"


# ======================================================================
# PART 4: NOTIFICATION DOMAIN MODEL TESTS
# ======================================================================


class TestNotificationModels:
    def test_notification_severity_values(self) -> None:
        assert NotificationSeverity.INFO.value == "INFO"
        assert NotificationSeverity.SUCCESS.value == "SUCCESS"
        assert NotificationSeverity.WARNING.value == "WARNING"
        assert NotificationSeverity.ERROR.value == "ERROR"

    def test_notification_category_values(self) -> None:
        assert NotificationCategory.WORKFLOW.value == "WORKFLOW"
        assert NotificationCategory.REVIEW.value == "REVIEW"
        assert NotificationCategory.JOB.value == "JOB"
        assert NotificationCategory.SYSTEM.value == "SYSTEM"

    def test_notification_status_values(self) -> None:
        assert NotificationStatus.UNREAD.value == "UNREAD"
        assert NotificationStatus.READ.value == "READ"
        assert NotificationStatus.ARCHIVED.value == "ARCHIVED"

    def test_notification_creation(self) -> None:
        n = Notification(
            notification_id=uuid4(),
            title="Test",
            message="Test message",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.WORKFLOW,
            status=NotificationStatus.UNREAD,
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-1",
        )
        assert n.title == "Test"
        assert n.event_id is None
        assert n.entity_type is None
        assert n.entity_id is None


# ======================================================================
# PART 5: NOTIFICATION REPOSITORY TESTS
# ======================================================================


class TestSQLiteNotificationRepository:
    def test_create_and_get(self, repo: SQLiteNotificationRepository) -> None:
        n = Notification(
            notification_id=uuid4(),
            title="Test",
            message="msg",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.WORKFLOW,
            status=NotificationStatus.UNREAD,
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-1",
            event_id=uuid4(),
            entity_type="brief",
            entity_id="topic-1",
        )
        repo.create_notification(n)
        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.title == "Test"
        assert fetched.severity == NotificationSeverity.INFO
        assert fetched.category == NotificationCategory.WORKFLOW
        assert fetched.event_id == n.event_id

    def test_get_nonexistent(self, repo: SQLiteNotificationRepository) -> None:
        assert repo.get_notification(uuid4()) is None

    def test_create_duplicate_raises(self, repo: SQLiteNotificationRepository) -> None:
        n = Notification(
            notification_id=uuid4(),
            title="Dup",
            message="msg",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.JOB,
            status=NotificationStatus.UNREAD,
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-1",
        )
        repo.create_notification(n)
        with pytest.raises(ValueError, match="already exists"):
            repo.create_notification(n)

    def test_list_all(self, repo: SQLiteNotificationRepository) -> None:
        for i in range(5):
            repo.create_notification(
                Notification(
                    notification_id=uuid4(),
                    title=f"Note {i}",
                    message="msg",
                    severity=NotificationSeverity.INFO,
                    category=NotificationCategory.WORKFLOW,
                    status=NotificationStatus.UNREAD,
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                    correlation_id="corr-1",
                )
            )
        notes = repo.list_notifications()
        assert len(notes) == 5

    def test_list_filter_by_status(self, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Unread",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Read",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.READ,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        unread = repo.list_notifications(status=NotificationStatus.UNREAD)
        assert len(unread) == 1
        assert unread[0].title == "Unread"

    def test_list_filter_by_category(self, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Workflow",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Job",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.JOB,
                status=NotificationStatus.UNREAD,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        workflow = repo.list_notifications(category=NotificationCategory.WORKFLOW)
        assert len(workflow) == 1
        assert workflow[0].title == "Workflow"

    def test_unread_count(self, repo: SQLiteNotificationRepository) -> None:
        assert repo.unread_count() == 0
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Unread1",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Unread2",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Read",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.READ,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )
        assert repo.unread_count() == 2

    def test_mark_read(self, repo: SQLiteNotificationRepository) -> None:
        n = Notification(
            notification_id=uuid4(),
            title="Read me",
            message="msg",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.WORKFLOW,
            status=NotificationStatus.UNREAD,
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-1",
        )
        repo.create_notification(n)
        assert repo.unread_count() == 1
        repo.mark_read(n.notification_id)
        assert repo.unread_count() == 0
        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.status == NotificationStatus.READ

    def test_mark_read_does_not_affect_archived(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        n = Notification(
            notification_id=uuid4(),
            title="Archived",
            message="msg",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.WORKFLOW,
            status=NotificationStatus.ARCHIVED,
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-1",
        )
        repo.create_notification(n)
        repo.mark_read(n.notification_id)
        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.status == NotificationStatus.ARCHIVED

    def test_archive(self, repo: SQLiteNotificationRepository) -> None:
        n = Notification(
            notification_id=uuid4(),
            title="Archive me",
            message="msg",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.WORKFLOW,
            status=NotificationStatus.UNREAD,
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-1",
        )
        repo.create_notification(n)
        repo.archive(n.notification_id)
        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.status == NotificationStatus.ARCHIVED

    def test_cleanup_expired(self, repo: SQLiteNotificationRepository) -> None:
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Old Read",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.READ,
                timestamp=old_time,
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Old Archived",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.ARCHIVED,
                timestamp=old_time,
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Old Unread",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=old_time,
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="New Read",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.READ,
                timestamp=datetime.now(timezone.utc),
                correlation_id="corr-1",
            )
        )

        deleted = repo.cleanup_expired_notifications(max_age_seconds=86400)
        assert deleted == 2
        remaining = repo.list_notifications()
        assert len(remaining) == 2

    def test_list_pagination(self, repo: SQLiteNotificationRepository) -> None:
        for i in range(10):
            repo.create_notification(
                Notification(
                    notification_id=uuid4(),
                    title=f"Note {i}",
                    message="msg",
                    severity=NotificationSeverity.INFO,
                    category=NotificationCategory.WORKFLOW,
                    status=NotificationStatus.UNREAD,
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                    correlation_id="corr-1",
                )
            )
        page1 = repo.list_notifications(limit=3, offset=0)
        page2 = repo.list_notifications(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].notification_id != page2[0].notification_id

    def test_timestamp_ordering(self, repo: SQLiteNotificationRepository) -> None:
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Earlier",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=t1,
                correlation_id="corr-1",
            )
        )
        repo.create_notification(
            Notification(
                notification_id=uuid4(),
                title="Later",
                message="msg",
                severity=NotificationSeverity.INFO,
                category=NotificationCategory.WORKFLOW,
                status=NotificationStatus.UNREAD,
                timestamp=t2,
                correlation_id="corr-1",
            )
        )
        notes = repo.list_notifications()
        assert notes[0].title == "Later"
        assert notes[1].title == "Earlier"


# ======================================================================
# PART 6: EVENT BUS INTEGRATION — REGISTRATION / DEREGISTRATION
# ======================================================================


class TestEventDispatcherRegistration:
    def test_register_exact(self, dispatcher: EventDispatcher) -> None:
        sub = Subscription(
            subscriber_id="test_exact",
            event_filter=EventFilter(event_type=EventType.JOB_CREATED),
        )
        calls: List[WorkflowEvent] = []
        dispatcher.register(sub, lambda e: calls.append(e))

        evt = create_job_event(
            event_type=EventType.JOB_CREATED,
            job_id=uuid4(),
            job_type="COLLECT",
            status="PENDING",
            operator_id="user",
            correlation_id="c1",
            target_type="topic",
            target_id="t1",
        )
        dispatcher._bus.publish(evt)
        assert len(calls) == 1
        assert calls[0].event_id == evt.event_id

    def test_register_wildcard_category(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        sub = Subscription(
            subscriber_id="test_wildcard",
            event_filter=EventFilter(category="job"),
        )
        calls: List[WorkflowEvent] = []
        dispatcher.register(sub, lambda e: calls.append(e))

        for evt_type in (EventType.JOB_CREATED, EventType.JOB_STARTED, EventType.JOB_COMPLETED):
            evt = create_job_event(
                event_type=evt_type,
                job_id=uuid4(),
                job_type="COLLECT",
                status="PENDING",
                operator_id="user",
                correlation_id="c1",
                target_type="topic",
                target_id="t1",
            )
            bus.publish(evt)
        assert len(calls) == 3

    def test_register_global_wildcard(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        sub = Subscription(
            subscriber_id="test_all",
            event_filter=EventFilter(),
        )
        calls: List[WorkflowEvent] = []
        dispatcher.register(sub, lambda e: calls.append(e))

        bus.publish(
            create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=uuid4(),
                job_type="X",
                status="P",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        bus.publish(
            create_workflow_event(
                event_type=EventType.BRIEF_GENERATED,
                topic_id="t1",
                operator_id="u",
                correlation_id="c",
            )
        )
        assert len(calls) == 2

    def test_deregister(self, dispatcher: EventDispatcher, bus: InMemoryEventBus) -> None:
        sub = Subscription(
            subscriber_id="to_remove",
            event_filter=EventFilter(category="job"),
        )
        calls: List[WorkflowEvent] = []
        dispatcher.register(sub, lambda e: calls.append(e))

        evt = create_job_event(
            event_type=EventType.JOB_CREATED,
            job_id=uuid4(),
            job_type="X",
            status="P",
            operator_id="u",
            correlation_id="c",
            target_type="t",
            target_id="t",
        )
        bus.publish(evt)
        assert len(calls) == 1

        result = dispatcher.deregister("to_remove")
        assert result == 1

        bus.publish(evt)
        assert len(calls) == 1

    def test_deregister_nonexistent(self, dispatcher: EventDispatcher) -> None:
        assert dispatcher.deregister("nope") == 0

    def test_replace_existing_registration(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        sub1 = Subscription(
            subscriber_id="replace_me",
            event_filter=EventFilter(category="job"),
        )
        calls1: List[WorkflowEvent] = []
        dispatcher.register(sub1, lambda e: calls1.append(e))

        sub2 = Subscription(
            subscriber_id="replace_me",
            event_filter=EventFilter(category="job"),
        )
        calls2: List[WorkflowEvent] = []
        dispatcher.register(sub2, lambda e: calls2.append(e))

        bus.publish(
            create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=uuid4(),
                job_type="X",
                status="P",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        assert len(calls1) == 0
        assert len(calls2) == 1


# ======================================================================
# PART 7: FAILURE ISOLATION TESTS
# ======================================================================


class TestFailureIsolation:
    def test_subscriber_failure_does_not_block_others(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        good_calls: List[WorkflowEvent] = []

        def good_cb(e: WorkflowEvent) -> None:
            good_calls.append(e)

        def broken_cb(e: WorkflowEvent) -> None:
            raise RuntimeError("subscriber crashed")

        sub_good = Subscription(
            subscriber_id="good",
            event_filter=EventFilter(category="job"),
        )
        sub_broken = Subscription(
            subscriber_id="broken",
            event_filter=EventFilter(category="job"),
        )
        dispatcher.register(sub_good, good_cb)
        dispatcher.register(sub_broken, broken_cb)

        evt = create_job_event(
            event_type=EventType.JOB_CREATED,
            job_id=uuid4(),
            job_type="X",
            status="P",
            operator_id="u",
            correlation_id="c",
            target_type="t",
            target_id="t",
        )
        bus.publish(evt)
        assert len(good_calls) == 1

    def test_execution_result_captures_failure(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        def broken_cb(e: WorkflowEvent) -> None:
            raise ValueError("test error")

        sub = Subscription(
            subscriber_id="fail_sub",
            event_filter=EventFilter(category="job"),
        )
        dispatcher.register(sub, broken_cb)

        evt = create_job_event(
            event_type=EventType.JOB_CREATED,
            job_id=uuid4(),
            job_type="X",
            status="P",
            operator_id="u",
            correlation_id="c",
            target_type="t",
            target_id="t",
        )
        bus.publish(evt)

        results = dispatcher.execution_results
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].subscriber_id == "fail_sub"
        assert results[0].exception_type == "ValueError"
        assert results[0].exception_message == "test error"
        assert results[0].execution_duration_ms >= 0

    def test_execution_result_captures_success(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        sub = Subscription(
            subscriber_id="ok_sub",
            event_filter=EventFilter(category="job"),
        )
        dispatcher.register(sub, lambda e: None)

        evt = create_job_event(
            event_type=EventType.JOB_CREATED,
            job_id=uuid4(),
            job_type="X",
            status="P",
            operator_id="u",
            correlation_id="c",
            target_type="t",
            target_id="t",
        )
        bus.publish(evt)

        results = dispatcher.execution_results
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].exception_type is None

    def test_clear_results(self, dispatcher: EventDispatcher, bus: InMemoryEventBus) -> None:
        sub = Subscription(
            subscriber_id="clr",
            event_filter=EventFilter(category="job"),
        )
        dispatcher.register(sub, lambda e: None)

        bus.publish(
            create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=uuid4(),
                job_type="X",
                status="P",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        assert len(dispatcher.execution_results) == 1
        dispatcher.clear_results()
        assert len(dispatcher.execution_results) == 0

    def test_isolated_failures_do_not_crash_bus(
        self, dispatcher: EventDispatcher, bus: InMemoryEventBus
    ) -> None:
        results: List[str] = []

        def cb_a(e: WorkflowEvent) -> None:
            results.append("a")

        def cb_b(e: WorkflowEvent) -> None:
            raise RuntimeError("boom")

        def cb_c(e: WorkflowEvent) -> None:
            results.append("c")

        for sid, cb in [("a", cb_a), ("b", cb_b), ("c", cb_c)]:
            dispatcher.register(
                Subscription(
                    subscriber_id=sid,
                    event_filter=EventFilter(category="job"),
                ),
                cb,
            )

        bus.publish(
            create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=uuid4(),
                job_type="X",
                status="P",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        assert results == ["a", "c"]


# ======================================================================
# PART 3: WORKFLOW NOTIFICATION SUBSCRIBER TESTS
# ======================================================================


class TestWorkflowNotificationSubscriber:
    def test_creates_notification_on_brief_generated(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        evt = create_workflow_event(
            event_type=EventType.BRIEF_GENERATED,
            topic_id="topic-1",
            operator_id="user-1",
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.title == "Brief Generated"
        assert notification.severity == NotificationSeverity.INFO
        assert notification.category == NotificationCategory.WORKFLOW
        assert notification.status == NotificationStatus.UNREAD
        assert notification.event_id == evt.event_id

    def test_creates_notification_on_brief_approved(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        evt = create_workflow_event(
            event_type=EventType.BRIEF_APPROVED,
            topic_id="topic-1",
            operator_id="user-1",
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.SUCCESS
        assert notification.category == NotificationCategory.REVIEW

    def test_creates_notification_on_brief_rejected(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        evt = create_workflow_event(
            event_type=EventType.BRIEF_REJECTED,
            topic_id="topic-1",
            operator_id="user-1",
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.WARNING
        assert notification.category == NotificationCategory.REVIEW

    def test_creates_notification_on_pipeline_failed(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        evt = create_workflow_event(
            event_type=EventType.PIPELINE_FAILED,
            topic_id="pipeline-1",
            operator_id="user-1",
            correlation_id="corr-1",
            extra_payload={"error_message": "step 3 failed"},
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.ERROR
        assert "step 3 failed" in notification.message

    def test_returns_none_for_unmapped_event(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        evt = create_event(
            event_type=EventType.LOCK_ACQUIRED,
            source="lock_manager",
            correlation_id="c",
            actor_id="a",
            entity_type="lock",
            entity_id="l",
            severity=EventSeverity.INFO,
        )
        notification = sub.handle_event(evt)
        assert notification is None

    def test_persists_to_repository(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        evt = create_workflow_event(
            event_type=EventType.STORYBOARD_GENERATED,
            topic_id="topic-2",
            operator_id="user-1",
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        fetched = repo.get_notification(notification.notification_id)
        assert fetched is not None
        assert fetched.title == "Storyboard Generated"

    def test_exception_propagation(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        mock_repo = MagicMock(spec=NotificationRepository)
        mock_repo.create_notification.side_effect = RuntimeError("db down")
        sub = WorkflowNotificationSubscriber(mock_repo)
        evt = create_workflow_event(
            event_type=EventType.BRIEF_GENERATED,
            topic_id="t1",
            operator_id="u1",
            correlation_id="c1",
        )
        with pytest.raises(RuntimeError, match="db down"):
            sub.handle_event(evt)

    def test_all_workflow_events_mapped(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = WorkflowNotificationSubscriber(repo)
        workflow_events = [
            EventType.BRIEF_GENERATED,
            EventType.CI_GENERATED,
            EventType.STORYBOARD_GENERATED,
            EventType.ASSET_GENERATED,
            EventType.MANIFEST_BUILT,
        ]
        review_events = [
            EventType.BRIEF_APPROVED,
            EventType.BRIEF_REJECTED,
            EventType.STORYBOARD_APPROVED,
            EventType.STORYBOARD_REJECTED,
            EventType.ASSET_APPROVED,
            EventType.ASSET_REJECTED,
        ]
        pipeline_events = [
            EventType.PIPELINE_STARTED,
            EventType.PIPELINE_COMPLETED,
            EventType.PIPELINE_FAILED,
        ]

        for evt_type in workflow_events + review_events + pipeline_events:
            evt = create_event(
                event_type=evt_type,
                source="test",
                correlation_id="c",
                actor_id="a",
                entity_type="topic",
                entity_id="t1",
                severity=EventSeverity.INFO,
            )
            notification = sub.handle_event(evt)
            assert notification is not None, f"Event type {evt_type} produced None"

        assert repo.unread_count() == len(workflow_events) + len(review_events) + len(pipeline_events)


# ======================================================================
# PART 3: JOB NOTIFICATION SUBSCRIBER TESTS
# ======================================================================


class TestJobNotificationSubscriber:
    def test_creates_notification_on_job_started(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        evt = create_job_event(
            event_type=EventType.JOB_STARTED,
            job_id=uuid4(),
            job_type="GENERATE_BRIEF",
            status="RUNNING",
            operator_id="worker-1",
            correlation_id="corr-1",
            target_type="topic",
            target_id="topic-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.title == "Job Started"
        assert notification.severity == NotificationSeverity.INFO
        assert notification.category == NotificationCategory.JOB
        assert "GENERATE_BRIEF" in notification.message

    def test_creates_notification_on_job_completed(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        evt = create_job_event(
            event_type=EventType.JOB_COMPLETED,
            job_id=uuid4(),
            job_type="COLLECT",
            status="COMPLETED",
            operator_id="worker-1",
            correlation_id="corr-1",
            target_type="topic",
            target_id="topic-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.SUCCESS
        assert "completed successfully" in notification.message

    def test_creates_notification_on_job_failed(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        evt = create_job_event(
            event_type=EventType.JOB_FAILED,
            job_id=uuid4(),
            job_type="GENERATE_ASSETS",
            status="FAILED",
            operator_id="worker-1",
            correlation_id="corr-1",
            target_type="topic",
            target_id="topic-1",
            error_message="OOM killed",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.ERROR
        assert "OOM killed" in notification.message

    def test_creates_notification_on_job_cancelled(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        evt = create_job_event(
            event_type=EventType.JOB_CANCELLED,
            job_id=uuid4(),
            job_type="DRY_RUN",
            status="CANCELLED",
            operator_id="admin",
            correlation_id="corr-1",
            target_type="calendar",
            target_id="week-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.WARNING
        assert "cancelled" in notification.message

    def test_creates_notification_on_job_retried(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        evt = create_job_event(
            event_type=EventType.JOB_RETRIED,
            job_id=uuid4(),
            job_type="COLLECT",
            status="RETRYING",
            operator_id="worker-1",
            correlation_id="corr-1",
            target_type="topic",
            target_id="topic-1",
            retry_count=2,
            max_retries=3,
            error_message="transient",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.severity == NotificationSeverity.WARNING
        assert "attempt 2/3" in notification.message

    def test_returns_none_for_unmapped_event(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        evt = create_event(
            event_type=EventType.BRIEF_GENERATED,
            source="test",
            correlation_id="c",
            actor_id="a",
            entity_type="brief",
            entity_id="b1",
            severity=EventSeverity.INFO,
        )
        notification = sub.handle_event(evt)
        assert notification is None

    def test_all_job_events_mapped(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = JobNotificationSubscriber(repo)
        job_events = [
            EventType.JOB_CREATED,
            EventType.JOB_QUEUED,
            EventType.JOB_STARTED,
            EventType.JOB_COMPLETED,
            EventType.JOB_FAILED,
            EventType.JOB_CANCELLED,
            EventType.JOB_RETRIED,
        ]
        for evt_type in job_events:
            evt = create_job_event(
                event_type=evt_type,
                job_id=uuid4(),
                job_type="TEST",
                status="TEST",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
            notification = sub.handle_event(evt)
            assert notification is not None, f"Event type {evt_type} produced None"

        assert repo.unread_count() == len(job_events)


# ======================================================================
# PART 3: SYSTEM NOTIFICATION SUBSCRIBER TESTS
# ======================================================================


class TestSystemNotificationSubscriber:
    def test_creates_notification_on_lock_expired(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = SystemNotificationSubscriber(repo)
        evt = create_lock_event(
            event_type=EventType.LOCK_EXPIRED,
            lock_id=uuid4(),
            lock_type="TOPIC",
            resource_id="topic-1",
            owner_job_id=uuid4(),
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.title == "Lock Expired"
        assert notification.severity == NotificationSeverity.WARNING
        assert notification.category == NotificationCategory.SYSTEM
        assert "TOPIC" in notification.message
        assert "topic-1" in notification.message

    def test_creates_notification_on_stale_lock_expired(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = SystemNotificationSubscriber(repo)
        evt = create_lock_event(
            event_type=EventType.LOCK_EXPIRED,
            lock_id=uuid4(),
            lock_type="CALENDAR",
            resource_id="week-5",
            owner_job_id=uuid4(),
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.title == "Lock Expired"
        assert notification.severity == NotificationSeverity.WARNING

    def test_creates_notification_on_zombie_recovered_rescheduled(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = SystemNotificationSubscriber(repo)
        evt = create_recovery_event(
            event_type=EventType.ZOMBIE_JOB_RECOVERED,
            entity_type="job",
            entity_id="job-123",
            correlation_id="corr-1",
            details={"rescheduled": True, "old_status": "RUNNING"},
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert notification.title == "Zombie Job Recovered"
        assert notification.severity == NotificationSeverity.WARNING
        assert notification.category == NotificationCategory.SYSTEM
        assert "rescheduled" in notification.message

    def test_creates_notification_on_zombie_recovered_not_rescheduled(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = SystemNotificationSubscriber(repo)
        evt = create_recovery_event(
            event_type=EventType.ZOMBIE_JOB_RECOVERED,
            entity_type="job",
            entity_id="job-456",
            correlation_id="corr-1",
            details={"rescheduled": False},
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        assert "could not be rescheduled" in notification.message

    def test_returns_none_for_unmapped_event(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = SystemNotificationSubscriber(repo)
        evt = create_event(
            event_type=EventType.JOB_CREATED,
            source="test",
            correlation_id="c",
            actor_id="a",
            entity_type="job",
            entity_id="j1",
            severity=EventSeverity.INFO,
        )
        notification = sub.handle_event(evt)
        assert notification is None

    def test_persists_to_repository(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        sub = SystemNotificationSubscriber(repo)
        evt = create_lock_event(
            event_type=EventType.LOCK_EXPIRED,
            lock_id=uuid4(),
            lock_type="TOPIC",
            resource_id="topic-1",
            owner_job_id=uuid4(),
            correlation_id="corr-1",
        )
        notification = sub.handle_event(evt)
        assert notification is not None
        fetched = repo.get_notification(notification.notification_id)
        assert fetched is not None
        assert fetched.title == "Lock Expired"


# ======================================================================
# PART 6+7: MULTI-SUBSCRIBER DISPATCH INTEGRATION TESTS
# ======================================================================


class TestMultiSubscriberDispatch:
    def test_all_subscribers_receive_events(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        bus = InMemoryEventBus()
        dispatcher = EventDispatcher(bus)

        wf_sub = WorkflowNotificationSubscriber(repo)
        job_sub = JobNotificationSubscriber(repo)
        sys_sub = SystemNotificationSubscriber(repo)

        dispatcher.register(wf_sub.subscription, wf_sub.handle_event)
        dispatcher.register(wf_sub.review_subscription, wf_sub.handle_event)
        dispatcher.register(wf_sub.pipeline_subscription, wf_sub.handle_event)
        dispatcher.register(job_sub.subscription, job_sub.handle_event)
        dispatcher.register(sys_sub.lock_subscription, sys_sub.handle_event)
        dispatcher.register(sys_sub.recovery_subscription, sys_sub.handle_event)

        bus.publish(
            create_workflow_event(
                event_type=EventType.BRIEF_APPROVED,
                topic_id="t1",
                operator_id="u",
                correlation_id="c",
            )
        )
        bus.publish(
            create_job_event(
                event_type=EventType.JOB_COMPLETED,
                job_id=uuid4(),
                job_type="X",
                status="COMPLETED",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        bus.publish(
            create_lock_event(
                event_type=EventType.LOCK_EXPIRED,
                lock_id=uuid4(),
                lock_type="TOPIC",
                resource_id="r1",
                owner_job_id=uuid4(),
                correlation_id="c",
            )
        )
        bus.publish(
            create_recovery_event(
                event_type=EventType.ZOMBIE_JOB_RECOVERED,
                entity_type="job",
                entity_id="j1",
                correlation_id="c",
                details={"rescheduled": True},
            )
        )

        assert repo.unread_count() == 4
        results = dispatcher.execution_results
        assert len(results) == 4
        assert all(r.success for r in results)

    def test_subscriber_failure_does_not_affect_others(
        self, repo: SQLiteNotificationRepository
    ) -> None:
        bus = InMemoryEventBus()
        dispatcher = EventDispatcher(bus)

        good_sub = WorkflowNotificationSubscriber(repo)

        def failing_handler(e: WorkflowEvent) -> None:
            raise RuntimeError("catastrophic failure")

        dispatcher.register(
            Subscription(
                subscriber_id="failing",
                event_filter=EventFilter(category="workflow"),
            ),
            failing_handler,
        )
        dispatcher.register(good_sub.subscription, good_sub.handle_event)
        dispatcher.register(good_sub.review_subscription, good_sub.handle_event)
        dispatcher.register(good_sub.pipeline_subscription, good_sub.handle_event)

        bus.publish(
            create_workflow_event(
                event_type=EventType.BRIEF_GENERATED,
                topic_id="t1",
                operator_id="u",
                correlation_id="c",
            )
        )

        assert repo.unread_count() == 1
        results = dispatcher.execution_results
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True


# ======================================================================
# PART 6: WILDCARD SUBSCRIPTION TESTS
# ======================================================================


class TestWildcardSubscriptions:
    def test_category_wildcard_matches_all_in_category(
        self, bus: InMemoryEventBus
    ) -> None:
        received: List[WorkflowEvent] = []
        bus.subscribe_wildcard("job.*", lambda e: received.append(e))

        for evt_type in (EventType.JOB_CREATED, EventType.JOB_QUEUED, EventType.JOB_STARTED,
                         EventType.JOB_COMPLETED, EventType.JOB_FAILED, EventType.JOB_CANCELLED,
                         EventType.JOB_RETRIED):
            bus.publish(
                create_job_event(
                    event_type=evt_type,
                    job_id=uuid4(),
                    job_type="X",
                    status="P",
                    operator_id="u",
                    correlation_id="c",
                    target_type="t",
                    target_id="t",
                )
            )
        assert len(received) == 7

    def test_global_wildcard_receives_all_events(self, bus: InMemoryEventBus) -> None:
        received: List[WorkflowEvent] = []
        bus.subscribe_wildcard("*", lambda e: received.append(e))

        bus.publish(
            create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=uuid4(),
                job_type="X",
                status="P",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        bus.publish(
            create_workflow_event(
                event_type=EventType.BRIEF_GENERATED,
                topic_id="t1",
                operator_id="u",
                correlation_id="c",
            )
        )
        bus.publish(
            create_lock_event(
                event_type=EventType.LOCK_ACQUIRED,
                lock_id=uuid4(),
                lock_type="TOPIC",
                resource_id="r1",
                owner_job_id=uuid4(),
                correlation_id="c",
            )
        )
        assert len(received) == 3

    def test_multiple_subscribers_per_event(self, bus: InMemoryEventBus) -> None:
        results_a: List[str] = []
        results_b: List[str] = []

        bus.subscribe(EventType.JOB_CREATED, lambda e: results_a.append("a"))
        bus.subscribe(EventType.JOB_CREATED, lambda e: results_b.append("b"))

        bus.publish(
            create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=uuid4(),
                job_type="X",
                status="P",
                operator_id="u",
                correlation_id="c",
                target_type="t",
                target_id="t",
            )
        )
        assert results_a == ["a"]
        assert results_b == ["b"]


# ======================================================================
# PART 8: THREADED DISPATCH TEST
# ======================================================================


class TestThreadSafety:
    def test_concurrent_publishes(self) -> None:
        import tempfile
        import os

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = None
        try:
            conn = sqlite3.connect(
                tmp.name, timeout=10, check_same_thread=False
            )
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            create_notification_schema(conn)
            repo = SQLiteNotificationRepository(conn)

            lock = threading.Lock()

            class ThreadSafeRepo(NotificationRepository):
                def __init__(self, inner: SQLiteNotificationRepository) -> None:
                    self._inner = inner

                def create_notification(self, notification: Notification) -> None:
                    with lock:
                        self._inner.create_notification(notification)

                def get_notification(self, notification_id: UUID):
                    with lock:
                        return self._inner.get_notification(notification_id)

                def list_notifications(self, status=None, category=None, limit=100, offset=0):
                    with lock:
                        return self._inner.list_notifications(status, category, limit, offset)

                def unread_count(self) -> int:
                    with lock:
                        return self._inner.unread_count()

                def mark_read(self, notification_id: UUID) -> None:
                    with lock:
                        self._inner.mark_read(notification_id)

                def archive(self, notification_id: UUID) -> None:
                    with lock:
                        self._inner.archive(notification_id)

                def cleanup_expired_notifications(self, max_age_seconds: int) -> int:
                    with lock:
                        return self._inner.cleanup_expired_notifications(max_age_seconds)

            safe_repo = ThreadSafeRepo(repo)

            bus = InMemoryEventBus()
            dispatcher = EventDispatcher(bus)
            sub = JobNotificationSubscriber(safe_repo)
            dispatcher.register(sub.subscription, sub.handle_event)

            def publish_events() -> None:
                for _ in range(10):
                    evt = create_job_event(
                        event_type=EventType.JOB_CREATED,
                        job_id=uuid4(),
                        job_type="X",
                        status="P",
                        operator_id="u",
                        correlation_id="c",
                        target_type="t",
                        target_id="t",
                    )
                    bus.publish(evt)

            threads = [threading.Thread(target=publish_events) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert repo.unread_count() == 50
            assert len(dispatcher.execution_results) == 50
            assert all(r.success for r in dispatcher.execution_results)
        finally:
            if conn is not None:
                conn.close()
            os.unlink(tmp.name)
