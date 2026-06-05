"""Notification recovery — restore missed notifications from the event store.

When an operator disconnects and reconnects, this service queries the event store
to identify missed events and restore notification state.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from content_creation.events.store.models import EventRecord
from content_creation.events.store.repository import EventRepository
from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.repository import NotificationRepository

logger = logging.getLogger(__name__)

# Map event names to notification properties
_EVENT_TO_NOTIFICATION = {
    "brief_generated": ("Brief Generated", NotificationSeverity.INFO, NotificationCategory.WORKFLOW),
    "ci_generated": ("CI Generated", NotificationSeverity.INFO, NotificationCategory.WORKFLOW),
    "storyboard_generated": ("Storyboard Generated", NotificationSeverity.INFO, NotificationCategory.WORKFLOW),
    "asset_generated": ("Asset Generated", NotificationSeverity.INFO, NotificationCategory.WORKFLOW),
    "manifest_built": ("Manifest Built", NotificationSeverity.INFO, NotificationCategory.WORKFLOW),
    "brief_approved": ("Brief Approved", NotificationSeverity.SUCCESS, NotificationCategory.REVIEW),
    "brief_rejected": ("Brief Rejected", NotificationSeverity.WARNING, NotificationCategory.REVIEW),
    "storyboard_approved": ("Storyboard Approved", NotificationSeverity.SUCCESS, NotificationCategory.REVIEW),
    "storyboard_rejected": ("Storyboard Rejected", NotificationSeverity.WARNING, NotificationCategory.REVIEW),
    "asset_approved": ("Asset Approved", NotificationSeverity.SUCCESS, NotificationCategory.REVIEW),
    "asset_rejected": ("Asset Rejected", NotificationSeverity.WARNING, NotificationCategory.REVIEW),
    "job_created": ("Job Created", NotificationSeverity.INFO, NotificationCategory.JOB),
    "job_queued": ("Job Queued", NotificationSeverity.INFO, NotificationCategory.JOB),
    "job_started": ("Job Started", NotificationSeverity.INFO, NotificationCategory.JOB),
    "job_completed": ("Job Completed", NotificationSeverity.SUCCESS, NotificationCategory.JOB),
    "job_failed": ("Job Failed", NotificationSeverity.ERROR, NotificationCategory.JOB),
    "job_cancelled": ("Job Cancelled", NotificationSeverity.WARNING, NotificationCategory.JOB),
    "job_retried": ("Job Retried", NotificationSeverity.WARNING, NotificationCategory.JOB),
    "lock_expired": ("Lock Expired", NotificationSeverity.WARNING, NotificationCategory.SYSTEM),
    "stale_lock_expired": ("Stale Lock Expired", NotificationSeverity.WARNING, NotificationCategory.SYSTEM),
    "zombie_job_recovered": ("Zombie Job Recovered", NotificationSeverity.WARNING, NotificationCategory.SYSTEM),
    "pipeline_started": ("Pipeline Started", NotificationSeverity.INFO, NotificationCategory.WORKFLOW),
    "pipeline_completed": ("Pipeline Completed", NotificationSeverity.SUCCESS, NotificationCategory.WORKFLOW),
    "pipeline_failed": ("Pipeline Failed", NotificationSeverity.ERROR, NotificationCategory.WORKFLOW),
}


class NotificationRecoveryService:
    """Restores missed notifications from the event store.

    Scenario:
    1. Operator disconnects
    2. Events continue (workflow progresses, jobs run)
    3. Operator reconnects
    4. System queries EventStore for events since last known event
    5. System creates notifications for missed events

    Architecture:
    EventStore → NotificationRecoveryService → NotificationRepository

    Guarantees:
    - Never creates duplicate notifications (checks event_id)
    - Never mutates existing events
    - Fails independently
    """

    def __init__(
        self,
        event_store: EventRepository,
        notification_repo: NotificationRepository,
    ) -> None:
        self._event_store = event_store
        self._notification_repo = notification_repo

    def recover_missed_notifications(
        self,
        last_known_event_id: Optional[str] = None,
        last_known_timestamp: Optional[datetime] = None,
    ) -> List[Notification]:
        """Recover notifications for events missed during disconnection.

        Args:
            last_known_event_id: UUID of the last event the client received.
            last_known_timestamp: Fallback — use timestamp if event_id not available.

        Returns:
            List of notifications created for missed events.
        """
        from uuid import UUID

        # Determine which events to check
        if last_known_event_id:
            try:
                anchor_id = UUID(last_known_event_id)
                records = self._event_store.list_after_event(anchor_id, limit=500)
            except ValueError:
                logger.warning("Invalid last_known_event_id: %s", last_known_event_id)
                return []
        elif last_known_timestamp:
            now = datetime.now(timezone.utc)
            records = self._event_store.list_by_time_range(
                last_known_timestamp, now, limit=500
            )
        else:
            # No anchor — recover recent events (last hour)
            now = datetime.now(timezone.utc)
            from datetime import timedelta

            one_hour_ago = now - timedelta(hours=1)
            records = self._event_store.list_by_time_range(one_hour_ago, now, limit=500)

        # Filter to events that map to notifications
        notifications_created: List[Notification] = []
        for record in records:
            if record.event_name not in _EVENT_TO_NOTIFICATION:
                continue

            # Check if notification already exists for this event
            existing = self._find_notification_by_event_id(record.event_id)
            if existing is not None:
                continue

            # Create notification
            title, severity, category = _EVENT_TO_NOTIFICATION[record.event_name]
            payload = record.payload()
            message = payload.get("message", f"{title} for {record.entity_type}")

            notification = Notification(
                notification_id=record.event_id,
                title=title,
                message=message,
                severity=severity,
                category=category,
                status=NotificationStatus.UNREAD,
                timestamp=record.created_at,
                correlation_id=record.correlation_id,
                event_id=record.event_id,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
            )

            try:
                self._notification_repo.create_notification(notification)
                notifications_created.append(notification)
            except Exception:
                logger.exception(
                    "Failed to create recovery notification for event %s",
                    record.event_id,
                )

        if notifications_created:
            logger.info(
                "Recovered %d missed notifications",
                len(notifications_created),
            )

        return notifications_created

    def _find_notification_by_event_id(self, event_id) -> Optional[Notification]:
        """Check if a notification already exists for this event."""
        try:
            return self._notification_repo.get_notification(event_id)
        except Exception:
            return None
