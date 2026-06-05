"""AuditSubscriber — persists every emitted event as an audit trail record."""

import logging
from typing import Optional

from content_creation.events.bus import EventBus, get_event_bus
from content_creation.events.models import WorkflowEvent
from content_creation.audit.models import AuditRecord
from content_creation.audit.repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditSubscriber:
    """Subscribes to all events on the EventBus and creates audit trail records.

    This is the bridge between the transient event system and the
    durable audit trail.

    Responsibilities:
    - Subscribe to all events via wildcard pattern
    - Convert WorkflowEvent to AuditRecord
    - Persist via AuditRepository

    Guarantees:
    - Never mutates the original event
    - Never blocks event execution (failure is isolated)
    - Fails independently — store failures don't affect other subscribers
    - All audit records originate from events (no direct writes)
    """

    SUBSCRIBER_ID = "audit_subscriber"

    def __init__(
        self,
        repository: AuditRepository,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._repository = repository
        self._bus = bus or get_event_bus()
        self._register()

    def _register(self) -> None:
        """Register for all events via wildcard pattern."""
        self._bus.subscribe_wildcard("*", self._handle_event)

    def _handle_event(self, event: WorkflowEvent) -> None:
        """Convert event to audit record and persist. Failure is isolated."""
        try:
            record = AuditRecord.from_workflow_event(event)
            self._repository.create_record(record)
            logger.debug(
                "Created audit record %s (%s)",
                record.audit_id,
                record.action_type,
            )
        except Exception:
            logger.exception(
                "Failed to create audit record for event %s — store failure isolated",
                event.event_id,
            )

    def shutdown(self) -> None:
        """Unregister from the event bus."""
        try:
            self._bus.unsubscribe_wildcard("*", self._handle_event)
        except Exception:
            logger.debug("Error during audit subscriber shutdown")
