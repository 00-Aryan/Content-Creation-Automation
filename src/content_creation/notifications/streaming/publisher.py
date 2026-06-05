"""Notification publisher: bridges notification repository events to SSE stream.

Subscribes to notification creation events and publishes SSE stream events.
Publisher must only observe results — never mutate state.
"""

import logging
from typing import Optional
from uuid import UUID

from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.repository import NotificationRepository
from content_creation.notifications.service import NotificationService
from content_creation.notifications.streaming.connection_manager import ConnectionManager
from content_creation.notifications.streaming.models import (
    NotificationStreamEvent,
    StreamEventType,
)

logger = logging.getLogger(__name__)


class NotificationPublisher:
    """Observes notification repository changes and publishes SSE stream events.

    Responsibilities:
    - Subscribe to notification creation events
    - Publish SSE events for new notifications
    - Publish unread count updates
    - Publish summary updates

    Must only observe results. Must never mutate state.
    No Streamlit, worker, or UI imports.
    """

    def __init__(
        self,
        repository: NotificationRepository,
        connection_manager: ConnectionManager,
    ) -> None:
        self._repository = repository
        self._connection_manager = connection_manager

    def on_notification_created(self, notification: Notification) -> None:
        """Handle a newly created notification by publishing an SSE event.

        Called by subscribers after a notification is persisted.
        """
        event = self._create_stream_event(
            event_type=StreamEventType.NOTIFICATION_CREATED,
            notification=notification,
        )
        delivered = self._connection_manager.broadcast(event)
        logger.debug(
            "Published notification_created for %s (delivered to %d clients)",
            notification.notification_id,
            delivered,
        )

        # Also broadcast unread count update
        self._broadcast_unread_count()

    def on_notification_read(self, notification_id: UUID) -> None:
        """Handle a notification being marked as read."""
        notification = self._repository.get_notification(notification_id)
        if notification is None:
            return

        event = self._create_stream_event(
            event_type=StreamEventType.NOTIFICATION_READ,
            notification=notification,
        )
        self._connection_manager.broadcast(event)
        self._broadcast_unread_count()

    def on_notification_archived(self, notification_id: UUID) -> None:
        """Handle a notification being archived."""
        notification = self._repository.get_notification(notification_id)
        if notification is None:
            return

        event = self._create_stream_event(
            event_type=StreamEventType.NOTIFICATION_ARCHIVED,
            notification=notification,
        )
        self._connection_manager.broadcast(event)
        self._broadcast_unread_count()

    def broadcast_unread_count(self) -> None:
        """Public method to broadcast current unread count to all clients."""
        self._broadcast_unread_count()

    def broadcast_summary_update(self) -> None:
        """Broadcast a summary update event to all clients."""
        event = NotificationStreamEvent(
            event_type=StreamEventType.SUMMARY_UPDATED,
            payload={"trigger": "summary_refresh"},
        )
        self._connection_manager.broadcast(event)

    def _broadcast_unread_count(self) -> None:
        """Broadcast the current unread count to all clients."""
        count = self._repository.unread_count()
        event = NotificationStreamEvent(
            event_type=StreamEventType.UNREAD_COUNT_UPDATED,
            payload={"unread_count": count},
        )
        self._connection_manager.broadcast(event)

    def _create_stream_event(
        self,
        event_type: StreamEventType,
        notification: Notification,
    ) -> NotificationStreamEvent:
        """Create a NotificationStreamEvent from a Notification domain object."""
        return NotificationStreamEvent(
            event_type=event_type,
            notification_id=notification.notification_id,
            category=notification.category.value,
            severity=notification.severity.value,
            title=notification.title,
            message=notification.message,
            timestamp=notification.timestamp,
            payload={
                "status": notification.status.value,
                "correlation_id": notification.correlation_id,
                "entity_type": notification.entity_type,
                "entity_id": notification.entity_id,
            },
        )
