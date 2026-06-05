"""Application service layer for notification consumption and management.

No Streamlit imports. Pure application service using repository abstraction only.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

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
from content_creation.notifications.repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Pure application service for notification operations.

    Responsibilities:
    - Unread count retrieval
    - Paginated notification listing with filtering
    - Mark read / mark all read
    - Archive / archive all read
    - Notification summary for dashboard
    - Cleanup expired notifications

    No Streamlit, worker, queue, or event bus imports.
    """

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    def unread_count(self) -> int:
        """Return the count of all unread notifications."""
        return self._repository.unread_count()

    def get_notification(self, notification_id: UUID) -> Optional[Notification]:
        """Retrieve a single notification by ID."""
        return self._repository.get_notification(notification_id)

    def query(self, q: NotificationQuery) -> NotificationPage:
        """Execute a paginated, filtered notification query.

        Applies filter criteria, sorts results, and returns a page.
        """
        filter_spec = q.filter

        # Fetch a superset for in-memory filtering (severity, date range)
        # The repository handles status and category filtering at DB level
        raw_limit = q.page_size * q.page + 100  # Over-fetch for sorting/filtering
        raw_notifications = self._repository.list_notifications(
            status=filter_spec.status,
            category=filter_spec.category,
            limit=raw_limit,
            offset=0,
        )

        # Apply in-memory filters not supported at DB level
        filtered = self._apply_filters(raw_notifications, filter_spec)

        # Apply sorting
        filtered = self._apply_sorting(filtered, q.sort_order)

        # Compute total before pagination
        total_count = len(filtered)

        # Apply pagination
        paginated = filtered[q.offset : q.offset + q.page_size]

        return NotificationPage(
            notifications=paginated,
            total_count=total_count,
            page=q.page,
            page_size=q.page_size,
        )

    def list_recent(
        self,
        limit: int = 10,
        category: Optional[NotificationCategory] = None,
        status: Optional[NotificationStatus] = None,
    ) -> List[Notification]:
        """List recent notifications with optional filters."""
        return self._repository.list_notifications(
            status=status,
            category=category,
            limit=limit,
            offset=0,
        )

    def mark_read(self, notification_id: UUID) -> None:
        """Mark a single notification as read."""
        self._repository.mark_read(notification_id)
        logger.info("Notification %s marked as read", notification_id)

    def mark_all_read(self) -> int:
        """Mark all unread notifications as read.

        Returns the number of notifications marked.
        """
        unread = self._repository.list_notifications(
            status=NotificationStatus.UNREAD,
            limit=10000,
        )
        for n in unread:
            self._repository.mark_read(n.notification_id)
        count = len(unread)
        if count > 0:
            logger.info("Marked %d notifications as read", count)
        return count

    def archive(self, notification_id: UUID) -> None:
        """Archive a single notification."""
        self._repository.archive(notification_id)
        logger.info("Notification %s archived", notification_id)

    def archive_all_read(self) -> int:
        """Archive all read (non-archived) notifications.

        Returns the number of notifications archived.
        """
        read_notifications = self._repository.list_notifications(
            status=NotificationStatus.READ,
            limit=10000,
        )
        for n in read_notifications:
            self._repository.archive(n.notification_id)
        count = len(read_notifications)
        if count > 0:
            logger.info("Archived %d read notifications", count)
        return count

    def summary(self) -> NotificationSummary:
        """Build a dashboard-ready notification summary.

        Includes unread counts by category and severity, plus recent
        notable notifications (failures, approvals, completions).
        """
        total_unread = self._repository.unread_count()

        # Unread by category
        unread_by_category: Dict[str, int] = {}
        for cat in NotificationCategory:
            unread = self._repository.list_notifications(
                status=NotificationStatus.UNREAD,
                category=cat,
                limit=10000,
            )
            unread_by_category[cat.value] = len(unread)

        # Unread by severity
        unread_all = self._repository.list_notifications(
            status=NotificationStatus.UNREAD,
            limit=10000,
        )
        unread_by_severity: Dict[str, int] = {}
        for n in unread_all:
            key = n.severity.value
            unread_by_severity[key] = unread_by_severity.get(key, 0) + 1

        # Recent failures (ERROR severity, last 5)
        recent_failures = [
            n for n in unread_all
            if n.severity == NotificationSeverity.ERROR
        ][:5]

        # Recent approvals (SUCCESS + REVIEW category, last 5)
        recent_approvals = [
            n for n in unread_all
            if n.severity == NotificationSeverity.SUCCESS
            and n.category == NotificationCategory.REVIEW
        ][:5]

        # Recent completions (SUCCESS + JOB category, last 5)
        recent_completions = [
            n for n in unread_all
            if n.severity == NotificationSeverity.SUCCESS
            and n.category == NotificationCategory.JOB
        ][:5]

        return NotificationSummary(
            total_unread=total_unread,
            unread_by_category=unread_by_category,
            unread_by_severity=unread_by_severity,
            recent_failures=recent_failures,
            recent_approvals=recent_approvals,
            recent_completions=recent_completions,
        )

    def _apply_filters(
        self,
        notifications: List[Notification],
        filter_spec: NotificationFilter,
    ) -> List[Notification]:
        """Apply in-memory filters not supported at DB level."""
        result = notifications

        if filter_spec.severity is not None:
            result = [n for n in result if n.severity == filter_spec.severity]

        if filter_spec.date_from is not None:
            result = [n for n in result if n.timestamp >= filter_spec.date_from]

        if filter_spec.date_to is not None:
            result = [n for n in result if n.timestamp <= filter_spec.date_to]

        return result

    def _apply_sorting(
        self,
        notifications: List[Notification],
        sort_order: SortOrder,
    ) -> List[Notification]:
        """Apply sort order to notification list."""
        reverse = sort_order == SortOrder.NEWEST_FIRST
        return sorted(notifications, key=lambda n: n.timestamp, reverse=reverse)
