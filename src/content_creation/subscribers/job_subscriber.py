"""Job domain notification subscriber: translates job lifecycle events into operator notifications."""

import logging
from typing import Optional
from uuid import uuid4

from content_creation.events.models import EventType, WorkflowEvent
from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.repository import NotificationRepository
from content_creation.subscribers.models import EventFilter, Subscription

logger = logging.getLogger(__name__)

_JOB_SEVERITY_MAP = {
    EventType.JOB_CREATED: NotificationSeverity.INFO,
    EventType.JOB_QUEUED: NotificationSeverity.INFO,
    EventType.JOB_STARTED: NotificationSeverity.INFO,
    EventType.JOB_COMPLETED: NotificationSeverity.SUCCESS,
    EventType.JOB_FAILED: NotificationSeverity.ERROR,
    EventType.JOB_CANCELLED: NotificationSeverity.WARNING,
    EventType.JOB_RETRIED: NotificationSeverity.WARNING,
}

_JOB_TITLE_MAP = {
    EventType.JOB_CREATED: "Job Created",
    EventType.JOB_QUEUED: "Job Queued",
    EventType.JOB_STARTED: "Job Started",
    EventType.JOB_COMPLETED: "Job Completed",
    EventType.JOB_FAILED: "Job Failed",
    EventType.JOB_CANCELLED: "Job Cancelled",
    EventType.JOB_RETRIED: "Job Retried",
}


class JobNotificationSubscriber:
    """Subscribes to job lifecycle events and creates operator-facing notifications.

    Responsibilities:
    - Job started, completed, failed, retry scheduled, cancelled

    This subscriber never mutates domain state. It only persists notifications.
    """

    SUBSCRIBER_ID = "job_notification_subscriber"

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository
        self._subscription = Subscription(
            subscriber_id=self.SUBSCRIBER_ID,
            event_filter=EventFilter(category="job"),
        )

    @property
    def subscription(self) -> Subscription:
        return self._subscription

    def handle_event(self, event: WorkflowEvent) -> Optional[Notification]:
        """Translate a job event into a Notification and persist it."""
        notification = self._map_event_to_notification(event)
        if notification is None:
            return None

        try:
            self._repository.create_notification(notification)
            logger.info(
                "Job notification created: %s (id=%s)",
                notification.title,
                notification.notification_id,
            )
        except Exception as e:
            logger.exception(
                "Failed to persist job notification for event %s: %s",
                event.event_id,
                e,
            )
            raise

        return notification

    def _map_event_to_notification(
        self, event: WorkflowEvent
    ) -> Optional[Notification]:
        """Map job event properties to a Notification domain object."""
        title = _JOB_TITLE_MAP.get(event.event_type)
        if title is None:
            logger.debug(
                "Skipping unmapped job event type: %s", event.event_type.value
            )
            return None

        severity = _JOB_SEVERITY_MAP.get(
            event.event_type, NotificationSeverity.INFO
        )

        message = self._build_message(event)

        return Notification(
            notification_id=uuid4(),
            title=title,
            message=message,
            severity=severity,
            category=NotificationCategory.JOB,
            status=NotificationStatus.UNREAD,
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
            event_id=event.event_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
        )

    def _build_message(self, event: WorkflowEvent) -> str:
        """Build a human-readable notification message from job event payload."""
        job_type = event.payload.get("job_type", "unknown")
        job_id = event.payload.get("job_id", "unknown")
        actor = event.payload.get("operator_id", event.actor_id)
        error_msg = event.payload.get("error_message")
        retry_count = event.payload.get("retry_count", 0)
        max_retries = event.payload.get("max_retries", 3)

        if event.event_type == EventType.JOB_RETRIED:
            return (
                f"{job_type} job {job_id} retried "
                f"(attempt {retry_count}/{max_retries}, actor: {actor})"
            )

        if event.event_type == EventType.JOB_CANCELLED:
            return f"{job_type} job {job_id} cancelled by {actor}"

        if event.event_type == EventType.JOB_COMPLETED:
            return f"{job_type} job {job_id} completed successfully (actor: {actor})"

        if error_msg:
            return (
                f"{job_type} job {job_id} failed: {error_msg} "
                f"(actor: {actor})"
            )

        return (
            f"{job_type} job {job_id} {event.event_type.value.replace('_', ' ')} "
            f"(actor: {actor})"
        )
