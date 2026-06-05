"""Notification Repository Abstraction defining data access APIs for notifications."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationStatus,
)


class NotificationRepository(ABC):
    """Abstract base class establishing the contract for persisting and querying notifications."""

    @abstractmethod
    def create_notification(self, notification: Notification) -> None:
        """Persist a new notification in the database."""
        pass

    @abstractmethod
    def get_notification(self, notification_id: UUID) -> Optional[Notification]:
        """Retrieve a specific notification by its unique ID."""
        pass

    @abstractmethod
    def list_notifications(
        self,
        status: Optional[NotificationStatus] = None,
        category: Optional[NotificationCategory] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Notification]:
        """List notifications filtering by status and/or category, ordered by timestamp descending."""
        pass

    @abstractmethod
    def unread_count(self) -> int:
        """Return the count of all unread notifications."""
        pass

    @abstractmethod
    def mark_read(self, notification_id: UUID) -> None:
        """Mark a notification's status as READ."""
        pass

    @abstractmethod
    def archive(self, notification_id: UUID) -> None:
        """Mark a notification's status as ARCHIVED."""
        pass

    @abstractmethod
    def cleanup_expired_notifications(self, max_age_seconds: int) -> int:
        """Remove notifications older than the specified age threshold. Returns count deleted."""
        pass
