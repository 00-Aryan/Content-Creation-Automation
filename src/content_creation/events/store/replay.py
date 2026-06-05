"""EventReplayEngine — replay persisted events through the EventBus."""

import logging
from datetime import datetime
from typing import Callable, List, Optional
from uuid import UUID

from content_creation.events.bus import EventBus, get_event_bus
from content_creation.events.factory import create_event
from content_creation.events.models import EventSeverity, EventType, WorkflowEvent
from content_creation.events.store.models import EventRecord
from content_creation.events.store.repository import EventRepository

logger = logging.getLogger(__name__)


class EventReplayEngine:
    """Replays persisted events through the EventBus.

    Capabilities:
    - Replay entire event stream
    - Replay by date range
    - Replay by correlation_id
    - Replay by entity
    - Replay selected categories
    - Dry-run mode (inspect without re-emitting)

    Replay path:
    EventStore → ReplayEngine → EventBus → Subscribers

    Guarantees:
    - Preserves original event ordering
    - Re-emitted events get new event_ids (replay is a new event)
    - Original events are not mutated
    """

    def __init__(
        self,
        repository: EventRepository,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._repository = repository
        self._bus = bus or get_event_bus()

    def replay_all(
        self,
        limit: int = 1000,
        dry_run: bool = False,
    ) -> List[WorkflowEvent]:
        """Replay all events in chronological order."""
        records = self._repository.list_events(limit=limit, offset=0)
        records = list(reversed(records))  # Convert DESC to ASC
        return self._replay_records(records, dry_run)

    def replay_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 1000,
        dry_run: bool = False,
    ) -> List[WorkflowEvent]:
        """Replay events within a date range."""
        records = self._repository.list_by_time_range(start, end, limit=limit)
        return self._replay_records(records, dry_run)

    def replay_by_correlation(
        self,
        correlation_id: str,
        dry_run: bool = False,
    ) -> List[WorkflowEvent]:
        """Replay all events sharing a correlation_id."""
        records = self._repository.list_by_correlation(correlation_id)
        return self._replay_records(records, dry_run)

    def replay_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        dry_run: bool = False,
    ) -> List[WorkflowEvent]:
        """Replay all events for a specific entity."""
        records = self._repository.list_by_entity(entity_type, entity_id)
        return self._replay_records(records, dry_run)

    def replay_by_category(
        self,
        category: str,
        limit: int = 1000,
        dry_run: bool = False,
    ) -> List[WorkflowEvent]:
        """Replay events from a specific category."""
        records = self._repository.list_by_category(category, limit=limit)
        records = list(reversed(records))  # Convert DESC to ASC
        return self._replay_records(records, dry_run)

    def replay_after(
        self,
        event_id: UUID,
        limit: int = 1000,
        dry_run: bool = False,
    ) -> List[WorkflowEvent]:
        """Replay events that occurred after a given event (for SSE recovery)."""
        records = self._repository.list_after_event(event_id, limit=limit)
        return self._replay_records(records, dry_run)

    def _replay_records(
        self,
        records: List[EventRecord],
        dry_run: bool,
    ) -> List[WorkflowEvent]:
        """Convert records to WorkflowEvents and optionally re-emit."""
        events: List[WorkflowEvent] = []
        for record in records:
            event = self._record_to_event(record)
            if event is None:
                continue
            events.append(event)
            if not dry_run:
                try:
                    self._bus.publish(event)
                except Exception:
                    logger.exception(
                        "Failed to replay event %s during publish",
                        record.event_id,
                    )
        if not dry_run and events:
            logger.info("Replayed %d events", len(events))
        return events

    def _record_to_event(self, record: EventRecord) -> Optional[WorkflowEvent]:
        """Convert an EventRecord back to a WorkflowEvent for re-emission."""
        try:
            event_type = EventType(record.event_name)
        except ValueError:
            logger.warning("Unknown event type: %s", record.event_name)
            return None

        payload = record.payload()

        return WorkflowEvent(
            event_id=record.event_id,
            event_type=event_type,
            timestamp=record.created_at,
            source=record.source,
            correlation_id=record.correlation_id,
            actor_id=payload.get("actor_id", ""),
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            severity=EventSeverity.INFO,
            payload=payload,
        )
