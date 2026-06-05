"""Stream event models for real-time notification delivery."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class StreamEventType(str, Enum):
    """Types of events delivered through the SSE stream."""

    NOTIFICATION_CREATED = "notification_created"
    NOTIFICATION_READ = "notification_read"
    NOTIFICATION_ARCHIVED = "notification_archived"
    NOTIFICATION_DELETED = "notification_deleted"
    UNREAD_COUNT_UPDATED = "unread_count_updated"
    SUMMARY_UPDATED = "summary_updated"


@dataclass(frozen=True)
class NotificationStreamEvent:
    """Immutable event delivered through the SSE stream.

    Maps notification domain events to a stream-friendly format
    suitable for JSON serialization and SSE delivery.
    """

    event_id: UUID = field(default_factory=uuid4)
    event_type: StreamEventType = StreamEventType.NOTIFICATION_CREATED
    notification_id: Optional[UUID] = None
    category: str = ""
    severity: str = ""
    title: str = ""
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_sse_data(self) -> str:
        """Serialize to SSE-compatible data string."""
        import json

        data = {
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "notification_id": str(self.notification_id) if self.notification_id else None,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }
        return json.dumps(data)

    def to_sse_event(self) -> str:
        """Return the SSE event type field."""
        return self.event_type.value
