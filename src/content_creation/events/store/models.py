"""EventRecord — immutable, audit-safe domain model for persisted events."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EventRecord:
    """Immutable record of a persisted event.

    This is the authoritative historical representation of a platform event.
    It is serializable, audit-safe, and designed for long-term storage.

    Fields:
        event_id: Unique identifier (UUID).
        event_name: The EventType value (e.g. "brief_generated").
        category: Event category (workflow, review, job, lock, recovery, pipeline).
        source: Component that emitted the event.
        correlation_id: Links related events in a single operation.
        entity_type: Type of entity involved (brief, storyboard, asset, job, etc.).
        entity_id: ID of the entity involved.
        payload_json: JSON-serialized event payload.
        created_at: UTC timestamp of event creation.
        version: Schema version for forward compatibility.
    """

    event_id: UUID
    event_name: str
    category: str
    source: str
    correlation_id: str
    entity_type: str
    entity_id: str
    payload_json: str
    created_at: datetime
    version: int = 1

    @classmethod
    def from_workflow_event(cls, event: Any) -> "EventRecord":
        """Create an EventRecord from a WorkflowEvent domain object.

        This is the canonical bridge from the in-memory event system
        to the persistent store.
        """
        from content_creation.events.bus import EVENT_TYPE_CATEGORIES

        category = EVENT_TYPE_CATEGORIES.get(event.event_type, "unknown")
        payload = event.payload if isinstance(event.payload, dict) else {}
        payload_json = json.dumps(payload, default=str)

        return cls(
            event_id=event.event_id,
            event_name=event.event_type.value,
            category=category,
            source=event.source,
            correlation_id=event.correlation_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            payload_json=payload_json,
            created_at=event.timestamp,
            version=1,
        )

    def payload(self) -> Dict[str, Any]:
        """Deserialize the payload JSON into a dictionary."""
        try:
            return json.loads(self.payload_json) if self.payload_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary for API responses."""
        return {
            "event_id": str(self.event_id),
            "event_name": self.event_name,
            "category": self.category,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "payload": self.payload(),
            "created_at": self.created_at.isoformat(),
            "version": self.version,
        }
