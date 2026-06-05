"""System-level notification subscriber: translates lock expiry, zombie recovery, and sweep events."""

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

_SYSTEM_SEVERITY_MAP = {
    EventType.LOCK_EXPIRED: NotificationSeverity.WARNING,
    EventType.STALE_LOCK_EXPIRED: NotificationSeverity.WARNING,
    EventType.ZOMBIE_JOB_RECOVERED: NotificationSeverity.WARNING,
}

_SYSTEM_TITLE_MAP = {
    EventType.LOCK_EXPIRED: "Lock Expired",
    EventType.STALE_LOCK_EXPIRED: "Stale Lock Expired",
    EventType.ZOMBIE_JOB_RECOVERED: "Zombie Job Recovered",
}


class SystemNotificationSubscriber:
    """Subscribes to system-level events (locks, recovery) and creates operator notifications.

    Responsibilities:
    - Stale lock expired
    - Zombie job recovered
    - Recovery sweep completed

    This subscriber never mutates domain state. It only persists notifications.
    """

    SUBSCRIBER_ID = "system_notification_subscriber"

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository
        self._lock_subscription = Subscription(
            subscriber_id=self.SUBSCRIBER_ID,
            event_filter=EventFilter(category="lock"),
        )
        self._recovery_subscription = Subscription(
            subscriber_id=self.SUBSCRIBER_ID,
            event_filter=EventFilter(category="recovery"),
        )

    @property
    def lock_subscription(self) -> Subscription:
        return self._lock_subscription

    @property
    def recovery_subscription(self) -> Subscription:
        return self._recovery_subscription

    def handle_event(self, event: WorkflowEvent) -> Optional[Notification]:
        """Translate a system event into a Notification and persist it."""
        notification = self._map_event_to_notification(event)
        if notification is None:
            return None

        try:
            self._repository.create_notification(notification)
            logger.info(
                "System notification created: %s (id=%s)",
                notification.title,
                notification.notification_id,
            )
        except Exception as e:
            logger.exception(
                "Failed to persist system notification for event %s: %s",
                event.event_id,
                e,
            )
            raise

        return notification

    def _map_event_to_notification(
        self, event: WorkflowEvent
    ) -> Optional[Notification]:
        """Map system event properties to a Notification domain object."""
        title = _SYSTEM_TITLE_MAP.get(event.event_type)
        if title is None:
            logger.debug(
                "Skipping unmapped system event type: %s", event.event_type.value
            )
            return None

        severity = _SYSTEM_SEVERITY_MAP.get(
            event.event_type, NotificationSeverity.WARNING
        )

        message = self._build_message(event)

        return Notification(
            notification_id=uuid4(),
            title=title,
            message=message,
            severity=severity,
            category=NotificationCategory.SYSTEM,
            status=NotificationStatus.UNREAD,
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
            event_id=event.event_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
        )

    def _build_message(self, event: WorkflowEvent) -> str:
        """Build a human-readable notification message from system event payload."""
        entity_type = event.entity_type
        entity_id = event.entity_id

        if event.event_type == EventType.ZOMBIE_JOB_RECOVERED:
            rescheduled = event.payload.get("rescheduled", False)
            if rescheduled:
                return (
                    f"Zombie {entity_type} {entity_id} recovered and rescheduled"
                )
            return (
                f"Zombie {entity_type} {entity_id} recovered but could not be "
                f"rescheduled (max retries exceeded)"
            )

        if event.event_type in (EventType.LOCK_EXPIRED, EventType.STALE_LOCK_EXPIRED):
            lock_type = event.payload.get("lock_type", "unknown")
            resource_id = event.payload.get("resource_id", "unknown")
            return (
                f"{lock_type} lock on {resource_id} expired "
                f"(resource may be available for re-acquisition)"
            )

        return f"System event {event.event_type.value} on {entity_type} {entity_id}"
