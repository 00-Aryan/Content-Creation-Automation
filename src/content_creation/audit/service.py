"""AuditQueryService — application service for querying audit records."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from content_creation.audit.models import AuditRecord, AuditActorType, AuditSource, AuditSeverity
from content_creation.audit.repository import AuditRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditPage:
    """Paginated audit query results."""

    records: List[AuditRecord]
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


class AuditQueryService:
    """Application service for querying audit trail records.

    Provides search, filtering, and pagination for audit records.
    All operations are read-only — no mutations.

    UI → AuditQueryService → AuditRepository
    No direct repository access from UI.
    """

    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def recent_records(
        self,
        page: int = 1,
        page_size: int = 20,
        source: Optional[AuditSource] = None,
    ) -> AuditPage:
        """Get recent audit records with pagination."""
        offset = (page - 1) * page_size
        records = self._repository.query_records(
            source=source, limit=page_size, offset=offset,
        )
        total = self._repository.count_records(source=source)
        return AuditPage(records=records, total=total, page=page, page_size=page_size)

    def search_by_entity(
        self,
        entity_type: str,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditRecord]:
        """Search audit records by entity type and optionally entity ID."""
        if entity_id:
            return self._repository.query_by_entity(entity_type, entity_id, limit=limit)
        records = self._repository.query_records(entity_type=entity_type, limit=limit)
        return records

    def search_by_actor(
        self,
        actor_id: str,
        limit: int = 50,
    ) -> List[AuditRecord]:
        """Search audit records by actor ID."""
        return self._repository.query_by_actor(actor_id, limit=limit)

    def search_by_correlation(
        self,
        correlation_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """Search all audit records in a correlated operation."""
        return self._repository.query_by_correlation(correlation_id, limit=limit)

    def search_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> List[AuditRecord]:
        """Search audit records within a date range."""
        return self._repository.query_records(start=start, end=end, limit=limit)

    def search_by_event_type(
        self,
        event_type: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """Search audit records by event type."""
        return self._repository.query_records(event_type=event_type, limit=limit)

    def search_by_action(
        self,
        action_type: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """Search audit records by action type."""
        return self._repository.query_records(action_type=action_type, limit=limit)

    def search_by_severity(
        self,
        severity: AuditSeverity,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """Search audit records by severity."""
        return self._repository.query_records(severity=severity, limit=limit)

    def search_records(
        self,
        query: str,
        limit: int = 50,
    ) -> List[AuditRecord]:
        """Full-text search across action_type, entity_type, and event_type."""
        all_records = self._repository.query_records(limit=1000)
        query_lower = query.lower()
        return [
            r for r in all_records
            if query_lower in r.action_type.lower()
            or query_lower in r.entity_type.lower()
            or query_lower in r.event_type.lower()
            or query_lower in r.actor_id.lower()
            or query_lower in r.entity_id.lower()
        ][:limit]

    def get_record(self, audit_id: UUID) -> Optional[AuditRecord]:
        """Get a single audit record by ID."""
        return self._repository.get_record(audit_id)

    def record_count(
        self,
        entity_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        source: Optional[AuditSource] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Count audit records matching filters."""
        return self._repository.count_records(
            entity_type=entity_type, actor_id=actor_id,
            source=source, start=start, end=end,
        )
