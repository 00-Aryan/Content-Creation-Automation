"""EventTimelineService — query event history for timeline views."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from content_creation.events.store.models import EventRecord
from content_creation.events.store.repository import EventRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimelinePage:
    """Paginated timeline results."""

    events: List[EventRecord]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, -(-self.total // self.page_size))

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1


class EventTimelineService:
    """Application service for querying event timelines.

    Supports:
    - Recent events across all categories
    - Workflow history for a topic
    - Job history
    - Entity-specific history
    - Pipeline history

    UI → TimelineService → EventRepository
    No direct repository access from UI.
    """

    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    def recent_events(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
    ) -> TimelinePage:
        """Get recent events with pagination."""
        offset = (page - 1) * page_size
        events = self._repository.list_events(
            limit=page_size, offset=offset, category=category
        )
        total = self._repository.count_events(category=category)
        return TimelinePage(
            events=events, total=total, page=page, page_size=page_size
        )

    def workflow_history(
        self,
        topic_id: str,
        limit: int = 50,
    ) -> List[EventRecord]:
        """Get workflow event history for a specific topic."""
        return self._repository.list_by_entity("brief", topic_id, limit=limit)

    def job_history(
        self,
        job_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EventRecord]:
        """Get job event history, optionally for a specific job."""
        if job_id:
            return self._repository.list_by_entity("job", job_id, limit=limit)
        return self._repository.list_by_category("job", limit=limit)

    def entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> List[EventRecord]:
        """Get event history for any entity type."""
        return self._repository.list_by_entity(entity_type, entity_id, limit=limit)

    def pipeline_history(
        self,
        limit: int = 50,
    ) -> List[EventRecord]:
        """Get pipeline event history."""
        return self._repository.list_by_category("pipeline", limit=limit)

    def timeline_for_correlation(
        self,
        correlation_id: str,
    ) -> List[EventRecord]:
        """Get all events in a correlated operation."""
        return self._repository.list_by_correlation(correlation_id)

    def events_in_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> List[EventRecord]:
        """Get events within a time range."""
        return self._repository.list_by_time_range(start, end, limit=limit)

    def search_events(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[EventRecord]:
        """Search events by name or entity type (simple contains match)."""
        all_events = self._repository.list_events(limit=1000, category=category)
        query_lower = query.lower()
        return [
            e
            for e in all_events
            if query_lower in e.event_name.lower()
            or query_lower in e.entity_type.lower()
            or query_lower in e.source.lower()
        ][:limit]
