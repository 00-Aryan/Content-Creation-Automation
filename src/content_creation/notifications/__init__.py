"""Notification domain models, repository abstraction, and SQLite persistence for operator-facing alerts."""

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
from content_creation.notifications.schema import create_notification_schema
from content_creation.notifications.service import NotificationService
from content_creation.notifications.maintenance import NotificationMaintenanceService
from content_creation.notifications.sqlite_repository import SQLiteNotificationRepository

__all__ = [
    "Notification",
    "NotificationCategory",
    "NotificationSeverity",
    "NotificationStatus",
    "NotificationFilter",
    "NotificationPage",
    "NotificationQuery",
    "NotificationSummary",
    "SortOrder",
    "NotificationRepository",
    "SQLiteNotificationRepository",
    "NotificationService",
    "NotificationMaintenanceService",
    "create_notification_schema",
]

# Streaming sub-package is imported separately to keep core lightweight:
# from content_creation.notifications.streaming import ...

