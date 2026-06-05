"""Notification Domain Models representing operator-facing alert messages and statuses."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class NotificationSeverity(str, Enum):
    """Notification severity levels mapping from events or errors."""

    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class NotificationCategory(str, Enum):
    """Notification routing/grouping categories."""

    WORKFLOW = "WORKFLOW"
    REVIEW = "REVIEW"
    JOB = "JOB"
    SYSTEM = "SYSTEM"


class NotificationStatus(str, Enum):
    """Notification read/unread/archive status lifecycle states."""

    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"


@dataclass
class Notification:
    """Pure domain model representation of an operator-facing notification."""

    notification_id: UUID
    title: str
    message: str
    severity: NotificationSeverity
    category: NotificationCategory
    status: NotificationStatus
    timestamp: datetime
    correlation_id: str
    event_id: Optional[UUID] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
