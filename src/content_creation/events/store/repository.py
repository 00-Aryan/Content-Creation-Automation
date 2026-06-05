"""EventRepository — abstract interface for event persistence."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from content_creation.events.store.models import EventRecord


class EventRepository(ABC):
    """Abstract interface for event persistence.

    Implementations must provide transaction-safe, indexed storage
    for EventRecord objects.
    """

    @abstractmethod
    def save_event(self, record: EventRecord) -> None:
        """Persist an event record. Idempotent on duplicate event_id."""

    @abstractmethod
    def get_event(self, event_id: UUID) -> Optional[EventRecord]:
        """Retrieve a single event by ID."""

    @abstractmethod
    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[EventRecord]:
        """List events with pagination, optionally filtered by category."""

    @abstractmethod
    def list_by_correlation(
        self,
        correlation_id: str,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List all events sharing a correlation_id, ordered by timestamp."""

    @abstractmethod
    def list_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List all events for a specific entity, ordered by timestamp."""

    @abstractmethod
    def list_by_category(
        self,
        category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EventRecord]:
        """List events by category with pagination."""

    @abstractmethod
    def list_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List events within a time range, ordered by timestamp."""

    @abstractmethod
    def list_after_event(
        self,
        event_id: UUID,
        limit: int = 100,
    ) -> List[EventRecord]:
        """List events that occurred after a given event (for SSE replay)."""

    @abstractmethod
    def count_events(self, category: Optional[str] = None) -> int:
        """Count total events, optionally filtered by category."""

    @abstractmethod
    def delete_expired(self, before: datetime, category: Optional[str] = None) -> int:
        """Delete events older than the given timestamp. Returns count deleted."""

    def close(self) -> None:
        """Release any resources held by the repository."""
