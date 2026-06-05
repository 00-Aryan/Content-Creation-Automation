"""EventPersistenceSubscriber — persists every emitted event to the store."""

import logging
from typing import Optional

from content_creation.events.bus import EventBus, get_event_bus
from content_creation.events.models import WorkflowEvent
from content_creation.events.store.models import EventRecord
from content_creation.events.store.repository import EventRepository

logger = logging.getLogger(__name__)


class EventPersistenceSubscriber:
    """Subscribes to all events on the EventBus and persists them.

    This is the bridge between the transient in-memory event system
    and the durable event store.

    Responsibilities:
    - Subscribe to all events via wildcard pattern
    - Convert WorkflowEvent to EventRecord
    - Persist via EventRepository

    Guarantees:
    - Never mutates the original event
    - Never blocks event execution (failure is isolated)
    - Fails independently — store failures don't affect other subscribers
    """

    SUBSCRIBER_ID = "event_persistence_subscriber"

    def __init__(
        self,
        repository: EventRepository,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._repository = repository
        self._bus = bus or get_event_bus()
        self._register()

    def _register(self) -> None:
        """Register for all events via wildcard pattern."""
        self._bus.subscribe_wildcard("*", self._handle_event)

    def _handle_event(self, event: WorkflowEvent) -> None:
        """Convert and persist the event. Failure is isolated."""
        try:
            record = EventRecord.from_workflow_event(event)
            self._repository.save_event(record)
            logger.debug(
                "Persisted event %s (%s)",
                record.event_id,
                record.event_name,
            )
        except Exception:
            logger.exception(
                "Failed to persist event %s — store failure isolated",
                event.event_id,
            )

    def shutdown(self) -> None:
        """Unregister from the event bus."""
        try:
            self._bus.unsubscribe_wildcard("*", self._handle_event)
        except Exception:
            logger.debug("Error during persistence subscriber shutdown")
