"""Notification query and filter models for the service layer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)


class SortOrder(str, Enum):
    """Sort order for notification listing."""

    NEWEST_FIRST = "NEWEST_FIRST"
    OLDEST_FIRST = "OLDEST_FIRST"


@dataclass(frozen=True)
class NotificationFilter:
    """Immutable filter criteria for querying notifications.

    All fields are optional. When None, the filter is not applied.
    """

    status: Optional[NotificationStatus] = None
    category: Optional[NotificationCategory] = None
    severity: Optional[NotificationSeverity] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@dataclass(frozen=True)
class NotificationQuery:
    """Immutable query specification for notification retrieval.

    Combines filters, sorting, and pagination into a single object.
    """

    filter: NotificationFilter = field(default_factory=NotificationFilter)
    sort_order: SortOrder = SortOrder.NEWEST_FIRST
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Compute the SQL OFFSET from 1-based page number."""
        return (self.page - 1) * self.page_size


@dataclass
class NotificationPage:
    """Result of a paginated notification query."""

    notifications: List[Notification]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Total number of pages based on total_count and page_size."""
        if self.page_size <= 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1


@dataclass(frozen=True)
class NotificationSummary:
    """Aggregated summary of notification counts by category and severity."""

    total_unread: int
    unread_by_category: dict
    unread_by_severity: dict
    recent_failures: List[Notification]
    recent_approvals: List[Notification]
    recent_completions: List[Notification]
