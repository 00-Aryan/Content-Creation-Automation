"""Canonical subscriber abstractions: filters, subscriptions, and execution results."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from content_creation.events.models import EventType


@dataclass(frozen=True)
class EventFilter:
    """Immutable filter defining which events a subscription matches.

    Supports:
    - Exact event type matching via ``event_type``
    - Category-based wildcard matching via ``category`` (e.g. ``"job"`` matches all job events)
    - Source-based filtering via ``source``
    - Severity-based filtering via ``min_severity``
    """

    event_type: Optional[EventType] = None
    category: Optional[str] = None
    source: Optional[str] = None

    def matches(self, event_type: EventType, source: str) -> bool:
        """Evaluate whether an event matches this filter."""
        from content_creation.events.bus import EVENT_TYPE_CATEGORIES

        if self.event_type is not None and event_type != self.event_type:
            return False
        if self.source is not None and source != self.source:
            return False
        if self.category is not None:
            event_category = EVENT_TYPE_CATEGORIES.get(event_type)
            if event_category != self.category:
                return False
        return True


@dataclass(frozen=True)
class Subscription:
    """Immutable definition binding a subscriber identity to an event filter.

    Subscriptions are registered on the event bus and used to route events
    to the appropriate subscriber callback.
    """

    subscriber_id: str
    event_filter: EventFilter
    priority: int = 100

    def __post_init__(self) -> None:
        if not self.subscriber_id:
            raise ValueError("subscriber_id must be non-empty")


@dataclass
class SubscriberExecutionResult:
    """Outcome of a single subscriber callback execution.

    Captures timing, success status, and exception details for failure isolation.
    """

    subscriber_id: str
    event_id: UUID
    execution_duration_ms: float
    success: bool
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
