"""Workflow domain notification subscriber: translates workflow and review events into operator notifications."""

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

_WORKFLOW_SEVERITY_MAP = {
    EventType.BRIEF_GENERATED: NotificationSeverity.INFO,
    EventType.CI_GENERATED: NotificationSeverity.INFO,
    EventType.STORYBOARD_GENERATED: NotificationSeverity.INFO,
    EventType.ASSET_GENERATED: NotificationSeverity.INFO,
    EventType.MANIFEST_BUILT: NotificationSeverity.SUCCESS,
    EventType.BRIEF_APPROVED: NotificationSeverity.SUCCESS,
    EventType.BRIEF_REJECTED: NotificationSeverity.WARNING,
    EventType.STORYBOARD_APPROVED: NotificationSeverity.SUCCESS,
    EventType.STORYBOARD_REJECTED: NotificationSeverity.WARNING,
    EventType.ASSET_APPROVED: NotificationSeverity.SUCCESS,
    EventType.ASSET_REJECTED: NotificationSeverity.WARNING,
    EventType.PIPELINE_STARTED: NotificationSeverity.INFO,
    EventType.PIPELINE_COMPLETED: NotificationSeverity.SUCCESS,
    EventType.PIPELINE_FAILED: NotificationSeverity.ERROR,
}

_WORKFLOW_TITLE_MAP = {
    EventType.BRIEF_GENERATED: "Brief Generated",
    EventType.CI_GENERATED: "Content Intelligence Generated",
    EventType.STORYBOARD_GENERATED: "Storyboard Generated",
    EventType.ASSET_GENERATED: "Asset Generated",
    EventType.MANIFEST_BUILT: "Manifest Built",
    EventType.BRIEF_APPROVED: "Brief Approved",
    EventType.BRIEF_REJECTED: "Brief Rejected",
    EventType.STORYBOARD_APPROVED: "Storyboard Approved",
    EventType.STORYBOARD_REJECTED: "Storyboard Rejected",
    EventType.ASSET_APPROVED: "Asset Approved",
    EventType.ASSET_REJECTED: "Asset Rejected",
    EventType.PIPELINE_STARTED: "Pipeline Started",
    EventType.PIPELINE_COMPLETED: "Pipeline Completed",
    EventType.PIPELINE_FAILED: "Pipeline Failed",
}

_WORKFLOW_CATEGORY_MAP = {
    EventType.BRIEF_GENERATED: NotificationCategory.WORKFLOW,
    EventType.CI_GENERATED: NotificationCategory.WORKFLOW,
    EventType.STORYBOARD_GENERATED: NotificationCategory.WORKFLOW,
    EventType.ASSET_GENERATED: NotificationCategory.WORKFLOW,
    EventType.MANIFEST_BUILT: NotificationCategory.WORKFLOW,
    EventType.BRIEF_APPROVED: NotificationCategory.REVIEW,
    EventType.BRIEF_REJECTED: NotificationCategory.REVIEW,
    EventType.STORYBOARD_APPROVED: NotificationCategory.REVIEW,
    EventType.STORYBOARD_REJECTED: NotificationCategory.REVIEW,
    EventType.ASSET_APPROVED: NotificationCategory.REVIEW,
    EventType.ASSET_REJECTED: NotificationCategory.REVIEW,
    EventType.PIPELINE_STARTED: NotificationCategory.WORKFLOW,
    EventType.PIPELINE_COMPLETED: NotificationCategory.WORKFLOW,
    EventType.PIPELINE_FAILED: NotificationCategory.WORKFLOW,
}


class WorkflowNotificationSubscriber:
    """Subscribes to workflow and review events and creates operator-facing notifications.

    Responsibilities:
    - Approvals, rejections, generation completions, dependency failures
    - Pipeline lifecycle events (started, completed, failed)

    This subscriber never mutates domain state. It only persists notifications.
    """

    SUBSCRIBER_ID = "workflow_notification_subscriber"

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository
        self._subscription = Subscription(
            subscriber_id=self.SUBSCRIBER_ID,
            event_filter=EventFilter(category="workflow"),
        )
        self._review_subscription = Subscription(
            subscriber_id=self.SUBSCRIBER_ID,
            event_filter=EventFilter(category="review"),
        )
        self._pipeline_subscription = Subscription(
            subscriber_id=self.SUBSCRIBER_ID,
            event_filter=EventFilter(category="pipeline"),
        )

    @property
    def subscription(self) -> Subscription:
        return self._subscription

    @property
    def review_subscription(self) -> Subscription:
        return self._review_subscription

    @property
    def pipeline_subscription(self) -> Subscription:
        return self._pipeline_subscription

    def handle_event(self, event: WorkflowEvent) -> Optional[Notification]:
        """Translate a workflow/review/pipeline event into a Notification and persist it."""
        notification = self._map_event_to_notification(event)
        if notification is None:
            return None

        try:
            self._repository.create_notification(notification)
            logger.info(
                "Workflow notification created: %s (id=%s)",
                notification.title,
                notification.notification_id,
            )
        except Exception as e:
            logger.exception(
                "Failed to persist workflow notification for event %s: %s",
                event.event_id,
                e,
            )
            raise

        return notification

    def _map_event_to_notification(
        self, event: WorkflowEvent
    ) -> Optional[Notification]:
        """Map event properties to a Notification domain object."""
        title = _WORKFLOW_TITLE_MAP.get(event.event_type)
        if title is None:
            logger.debug(
                "Skipping unmapped event type: %s", event.event_type.value
            )
            return None

        severity = _WORKFLOW_SEVERITY_MAP.get(
            event.event_type, NotificationSeverity.INFO
        )
        category = _WORKFLOW_CATEGORY_MAP.get(
            event.event_type, NotificationCategory.WORKFLOW
        )

        message = self._build_message(event)

        return Notification(
            notification_id=uuid4(),
            title=title,
            message=message,
            severity=severity,
            category=category,
            status=NotificationStatus.UNREAD,
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
            event_id=event.event_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
        )

    def _build_message(self, event: WorkflowEvent) -> str:
        """Build a human-readable notification message from event payload."""
        entity = event.entity_type
        entity_id = event.entity_id
        actor = event.actor_id

        error_msg = event.payload.get("error_message")
        if error_msg:
            return f"{entity.title()} {entity_id} failed: {error_msg} (actor: {actor})"

        return f"{entity.title()} {entity_id} {event.event_type.value.replace('_', ' ')} by {actor}"
