"""Comprehensive tests for Phase 11.8.4 — Notification Service, Query Models, and Maintenance."""

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

import pytest

from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.query import (
    NotificationFilter,
    NotificationPage,
    NotificationQuery,
    NotificationSummary,
    SortOrder,
)
from content_creation.notifications.schema import create_notification_schema
from content_creation.notifications.service import NotificationService
from content_creation.notifications.maintenance import NotificationMaintenanceService
from content_creation.notifications.sqlite_repository import SQLiteNotificationRepository


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with notification schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    create_notification_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn: sqlite3.Connection) -> SQLiteNotificationRepository:
    return SQLiteNotificationRepository(db_conn)


@pytest.fixture
def service(repo: SQLiteNotificationRepository) -> NotificationService:
    return NotificationService(repo)


@pytest.fixture
def maintenance(repo: SQLiteNotificationRepository) -> NotificationMaintenanceService:
    return NotificationMaintenanceService(repo, retention_days=30, archive_after_days=7)


def _make_notification(
    title: str = "Test",
    message: str = "Test message",
    severity: NotificationSeverity = NotificationSeverity.INFO,
    category: NotificationCategory = NotificationCategory.WORKFLOW,
    status: NotificationStatus = NotificationStatus.UNREAD,
    timestamp: datetime = None,
    correlation_id: str = "corr-1",
    entity_type: str = None,
    entity_id: str = None,
) -> Notification:
    """Helper to create a Notification with defaults."""
    return Notification(
        notification_id=uuid4(),
        title=title,
        message=message,
        severity=severity,
        category=category,
        status=status,
        timestamp=timestamp or datetime.now(timezone.utc),
        correlation_id=correlation_id,
        event_id=uuid4(),
        entity_type=entity_type,
        entity_id=entity_id,
    )


# ======================================================================
# PART 3: NOTIFICATION QUERY MODELS TESTS
# ======================================================================


class TestNotificationFilter:
    def test_default_filter(self) -> None:
        f = NotificationFilter()
        assert f.status is None
        assert f.category is None
        assert f.severity is None
        assert f.date_from is None
        assert f.date_to is None

    def test_immutable(self) -> None:
        f = NotificationFilter(status=NotificationStatus.UNREAD)
        with pytest.raises(AttributeError):
            f.status = NotificationStatus.READ  # type: ignore

    def test_with_all_fields(self) -> None:
        now = datetime.now(timezone.utc)
        f = NotificationFilter(
            status=NotificationStatus.UNREAD,
            category=NotificationCategory.JOB,
            severity=NotificationSeverity.ERROR,
            date_from=now - timedelta(days=1),
            date_to=now,
        )
        assert f.status == NotificationStatus.UNREAD
        assert f.category == NotificationCategory.JOB
        assert f.severity == NotificationSeverity.ERROR


class TestNotificationQuery:
    def test_default_query(self) -> None:
        q = NotificationQuery()
        assert q.filter == NotificationFilter()
        assert q.sort_order == SortOrder.NEWEST_FIRST
        assert q.page == 1
        assert q.page_size == 20
        assert q.offset == 0

    def test_offset_calculation(self) -> None:
        q = NotificationQuery(page=3, page_size=10)
        assert q.offset == 20

    def test_page_1_offset(self) -> None:
        q = NotificationQuery(page=1, page_size=25)
        assert q.offset == 0

    def test_immutable(self) -> None:
        q = NotificationQuery(page=2)
        with pytest.raises(AttributeError):
            q.page = 3  # type: ignore


class TestNotificationPage:
    def test_total_pages(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=50, page=1, page_size=20
        )
        assert p.total_pages == 3

    def test_total_pages_exact(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=40, page=1, page_size=20
        )
        assert p.total_pages == 2

    def test_total_pages_zero(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=0, page=1, page_size=20
        )
        assert p.total_pages == 0

    def test_has_next(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=50, page=1, page_size=20
        )
        assert p.has_next is True

    def test_has_next_last_page(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=50, page=3, page_size=20
        )
        assert p.has_next is False

    def test_has_previous(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=50, page=2, page_size=20
        )
        assert p.has_previous is True

    def test_has_previous_first_page(self) -> None:
        p = NotificationPage(
            notifications=[], total_count=50, page=1, page_size=20
        )
        assert p.has_previous is False


class TestNotificationSummary:
    def test_creation(self) -> None:
        s = NotificationSummary(
            total_unread=5,
            unread_by_category={"WORKFLOW": 2, "JOB": 3},
            unread_by_severity={"INFO": 3, "ERROR": 2},
            recent_failures=[],
            recent_approvals=[],
            recent_completions=[],
        )
        assert s.total_unread == 5
        assert s.unread_by_category["WORKFLOW"] == 2
        assert s.unread_by_severity["ERROR"] == 2


# ======================================================================
# PART 2: NOTIFICATION SERVICE TESTS
# ======================================================================


class TestNotificationService:
    def test_unread_count_empty(self, service: NotificationService) -> None:
        assert service.unread_count() == 0

    def test_unread_count(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(_make_notification(title="Unread1", status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(title="Unread2", status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(title="Read1", status=NotificationStatus.READ))
        assert service.unread_count() == 2

    def test_get_notification(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        n = _make_notification(title="Fetch Me")
        repo.create_notification(n)
        fetched = service.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.title == "Fetch Me"

    def test_get_notification_nonexistent(self, service: NotificationService) -> None:
        assert service.get_notification(uuid4()) is None

    def test_query_all(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        for i in range(5):
            repo.create_notification(
                _make_notification(
                    title=f"Note {i}",
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                )
            )
        page = service.query(NotificationQuery())
        assert page.total_count == 5
        assert len(page.notifications) == 5

    def test_query_filter_status(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(_make_notification(status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(status=NotificationStatus.READ))
        page = service.query(
            NotificationQuery(filter=NotificationFilter(status=NotificationStatus.UNREAD))
        )
        assert page.total_count == 1

    def test_query_filter_category(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(_make_notification(category=NotificationCategory.WORKFLOW))
        repo.create_notification(_make_notification(category=NotificationCategory.JOB))
        page = service.query(
            NotificationQuery(filter=NotificationFilter(category=NotificationCategory.JOB))
        )
        assert page.total_count == 1

    def test_query_filter_severity(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(_make_notification(severity=NotificationSeverity.INFO))
        repo.create_notification(_make_notification(severity=NotificationSeverity.ERROR))
        page = service.query(
            NotificationQuery(filter=NotificationFilter(severity=NotificationSeverity.ERROR))
        )
        assert page.total_count == 1

    def test_query_filter_date_range(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        new = datetime(2026, 6, 1, tzinfo=timezone.utc)
        repo.create_notification(_make_notification(title="Old", timestamp=old))
        repo.create_notification(_make_notification(title="New", timestamp=new))
        page = service.query(
            NotificationQuery(
                filter=NotificationFilter(date_from=datetime(2026, 3, 1, tzinfo=timezone.utc))
            )
        )
        assert page.total_count == 1
        assert page.notifications[0].title == "New"

    def test_query_sorting_oldest_first(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
        repo.create_notification(_make_notification(title="Later", timestamp=t2))
        repo.create_notification(_make_notification(title="Earlier", timestamp=t1))
        page = service.query(NotificationQuery(sort_order=SortOrder.OLDEST_FIRST))
        assert page.notifications[0].title == "Earlier"
        assert page.notifications[1].title == "Later"

    def test_query_pagination(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        for i in range(10):
            repo.create_notification(
                _make_notification(
                    title=f"Note {i}",
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                )
            )
        page1 = service.query(NotificationQuery(page=1, page_size=3))
        page2 = service.query(NotificationQuery(page=2, page_size=3))
        assert len(page1.notifications) == 3
        assert len(page2.notifications) == 3
        assert page1.has_next is True
        assert page2.has_previous is True

    def test_mark_read(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        n = _make_notification(status=NotificationStatus.UNREAD)
        repo.create_notification(n)
        assert service.unread_count() == 1
        service.mark_read(n.notification_id)
        assert service.unread_count() == 0

    def test_mark_all_read(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        for i in range(5):
            repo.create_notification(_make_notification(title=f"Unread {i}", status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(title="Already Read", status=NotificationStatus.READ))
        count = service.mark_all_read()
        assert count == 5
        assert service.unread_count() == 0

    def test_archive(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        n = _make_notification(status=NotificationStatus.UNREAD)
        repo.create_notification(n)
        service.archive(n.notification_id)
        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.status == NotificationStatus.ARCHIVED

    def test_archive_all_read(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        for i in range(3):
            repo.create_notification(_make_notification(title=f"Read {i}", status=NotificationStatus.READ))
        repo.create_notification(_make_notification(title="Unread", status=NotificationStatus.UNREAD))
        count = service.archive_all_read()
        assert count == 3
        unread = service.unread_count()
        assert unread == 1

    def test_list_recent(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        for i in range(10):
            repo.create_notification(
                _make_notification(
                    title=f"Note {i}",
                    category=NotificationCategory.JOB if i % 2 == 0 else NotificationCategory.WORKFLOW,
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                )
            )
        recent = service.list_recent(limit=3)
        assert len(recent) == 3

    def test_list_recent_with_category(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(_make_notification(category=NotificationCategory.JOB))
        repo.create_notification(_make_notification(category=NotificationCategory.WORKFLOW))
        recent = service.list_recent(limit=10, category=NotificationCategory.JOB)
        assert len(recent) == 1

    def test_summary(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        repo.create_notification(
            _make_notification(
                severity=NotificationSeverity.ERROR,
                category=NotificationCategory.JOB,
                status=NotificationStatus.UNREAD,
            )
        )
        repo.create_notification(
            _make_notification(
                severity=NotificationSeverity.SUCCESS,
                category=NotificationCategory.REVIEW,
                status=NotificationStatus.UNREAD,
            )
        )
        repo.create_notification(
            _make_notification(
                severity=NotificationSeverity.SUCCESS,
                category=NotificationCategory.JOB,
                status=NotificationStatus.UNREAD,
            )
        )
        summary = service.summary()
        assert summary.total_unread == 3
        assert summary.unread_by_category["JOB"] == 2
        assert summary.unread_by_category["REVIEW"] == 1
        assert summary.unread_by_severity["ERROR"] == 1
        assert summary.unread_by_severity["SUCCESS"] == 2
        assert len(summary.recent_failures) == 1
        assert len(summary.recent_approvals) == 1
        assert len(summary.recent_completions) == 1

    def test_summary_empty(self, service: NotificationService) -> None:
        summary = service.summary()
        assert summary.total_unread == 0
        assert len(summary.recent_failures) == 0


# ======================================================================
# PART 8: NOTIFICATION MAINTENANCE SERVICE TESTS
# ======================================================================


class TestNotificationMaintenanceService:
    def test_cleanup_expired(self, maintenance: NotificationMaintenanceService, repo: SQLiteNotificationRepository) -> None:
        old_time = datetime.now(timezone.utc) - timedelta(days=60)
        repo.create_notification(
            _make_notification(title="Old Read", status=NotificationStatus.READ, timestamp=old_time)
        )
        repo.create_notification(
            _make_notification(title="Old Archived", status=NotificationStatus.ARCHIVED, timestamp=old_time)
        )
        repo.create_notification(
            _make_notification(title="Old Unread", status=NotificationStatus.UNREAD, timestamp=old_time)
        )
        repo.create_notification(
            _make_notification(title="New Read", status=NotificationStatus.READ)
        )
        result = maintenance.cleanup_expired()
        assert result["deleted"] == 2
        remaining = repo.list_notifications()
        assert len(remaining) == 2

    def test_archive_stale_read(self, maintenance: NotificationMaintenanceService, repo: SQLiteNotificationRepository) -> None:
        old_time = datetime.now(timezone.utc) - timedelta(days=14)
        repo.create_notification(
            _make_notification(title="Old Read", status=NotificationStatus.READ, timestamp=old_time)
        )
        repo.create_notification(
            _make_notification(title="New Read", status=NotificationStatus.READ)
        )
        result = maintenance.archive_stale_read()
        assert result["archived"] == 1
        old = repo.get_notification(
            next(n.notification_id for n in repo.list_notifications() if n.title == "Old Read")
        )
        assert old is not None
        assert old.status == NotificationStatus.ARCHIVED

    def test_enforce_retention(self, maintenance: NotificationMaintenanceService, repo: SQLiteNotificationRepository) -> None:
        very_old = datetime.now(timezone.utc) - timedelta(days=60)
        stale = datetime.now(timezone.utc) - timedelta(days=14)
        repo.create_notification(
            _make_notification(title="Very Old Read", status=NotificationStatus.READ, timestamp=very_old)
        )
        repo.create_notification(
            _make_notification(title="Stale Read", status=NotificationStatus.READ, timestamp=stale)
        )
        result = maintenance.enforce_retention()
        assert result["archived"] >= 1
        assert result["deleted"] >= 0

    def test_cleanup_nothing_to_clean(self, maintenance: NotificationMaintenanceService) -> None:
        result = maintenance.cleanup_expired()
        assert result["deleted"] == 0

    def test_archive_nothing_to_archive(self, maintenance: NotificationMaintenanceService) -> None:
        result = maintenance.archive_stale_read()
        assert result["archived"] == 0


# ======================================================================
# PART 9: INTEGRATION TESTS (End-to-End Service Flow)
# ======================================================================


class TestNotificationServiceIntegration:
    def test_full_lifecycle(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        """Test create → query → mark read → archive → cleanup lifecycle."""
        # Create notifications
        n1 = _make_notification(title="First", severity=NotificationSeverity.ERROR, category=NotificationCategory.JOB)
        n2 = _make_notification(title="Second", severity=NotificationSeverity.SUCCESS, category=NotificationCategory.REVIEW)
        n3 = _make_notification(title="Third", severity=NotificationSeverity.WARNING, category=NotificationCategory.SYSTEM)
        repo.create_notification(n1)
        repo.create_notification(n2)
        repo.create_notification(n3)

        # Verify unread count
        assert service.unread_count() == 3

        # Query all
        page = service.query(NotificationQuery())
        assert page.total_count == 3

        # Query by category
        page = service.query(NotificationQuery(filter=NotificationFilter(category=NotificationCategory.JOB)))
        assert page.total_count == 1
        assert page.notifications[0].title == "First"

        # Query by severity
        page = service.query(NotificationQuery(filter=NotificationFilter(severity=NotificationSeverity.ERROR)))
        assert page.total_count == 1

        # Mark one read
        service.mark_read(n1.notification_id)
        assert service.unread_count() == 2

        # Mark all read
        count = service.mark_all_read()
        assert count == 2
        assert service.unread_count() == 0

        # Archive all read
        count = service.archive_all_read()
        assert count == 3

        # Summary should be empty
        summary = service.summary()
        assert summary.total_unread == 0

    def test_concurrent_queries(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        """Verify service handles multiple sequential queries correctly."""
        for i in range(20):
            repo.create_notification(
                _make_notification(
                    title=f"Note {i}",
                    category=list(NotificationCategory)[i % 4],
                    severity=list(NotificationSeverity)[i % 4],
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                )
            )

        # Query with various filters
        for cat in NotificationCategory:
            page = service.query(
                NotificationQuery(filter=NotificationFilter(category=cat))
            )
            assert page.total_count == 5

        for sev in NotificationSeverity:
            page = service.query(
                NotificationQuery(filter=NotificationFilter(severity=sev))
            )
            assert page.total_count == 5

    def test_pagination_accuracy(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        """Verify pagination returns correct counts and pages."""
        for i in range(25):
            repo.create_notification(
                _make_notification(
                    title=f"Note {i}",
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                )
            )

        page1 = service.query(NotificationQuery(page=1, page_size=10))
        assert len(page1.notifications) == 10
        assert page1.total_count == 25
        assert page1.total_pages == 3
        assert page1.has_next is True
        assert page1.has_previous is False

        page3 = service.query(NotificationQuery(page=3, page_size=10))
        assert len(page3.notifications) == 5
        assert page3.has_next is False
        assert page3.has_previous is True

    def test_mark_read_does_not_affect_archived(
        self, service: NotificationService, repo: SQLiteNotificationRepository
    ) -> None:
        n = _make_notification(status=NotificationStatus.ARCHIVED)
        repo.create_notification(n)
        service.mark_read(n.notification_id)
        fetched = repo.get_notification(n.notification_id)
        assert fetched is not None
        assert fetched.status == NotificationStatus.ARCHIVED

    def test_summary_categories(self, service: NotificationService, repo: SQLiteNotificationRepository) -> None:
        """Verify summary counts by category correctly."""
        repo.create_notification(_make_notification(category=NotificationCategory.WORKFLOW, status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(category=NotificationCategory.WORKFLOW, status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(category=NotificationCategory.JOB, status=NotificationStatus.UNREAD))
        repo.create_notification(_make_notification(category=NotificationCategory.REVIEW, status=NotificationStatus.READ))

        summary = service.summary()
        assert summary.total_unread == 3
        assert summary.unread_by_category["WORKFLOW"] == 2
        assert summary.unread_by_category["JOB"] == 1
        assert summary.unread_by_category["REVIEW"] == 0
        assert summary.unread_by_category["SYSTEM"] == 0
