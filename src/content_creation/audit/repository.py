"""AuditRepository — abstract interface for audit trail persistence."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from content_creation.audit.models import AuditRecord, AuditActorType, AuditSource, AuditSeverity


class AuditRepository(ABC):
    """Abstract interface for audit trail persistence.

    Implementations must provide transaction-safe, indexed storage
    for AuditRecord objects. Records are immutable after creation.
    """

    @abstractmethod
    def create_record(self, record: AuditRecord) -> None:
        """Persist an audit record. Idempotent on duplicate audit_id."""

    @abstractmethod
    def get_record(self, audit_id: UUID) -> Optional[AuditRecord]:
        """Retrieve a single audit record by ID."""

    @abstractmethod
    def query_records(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor_type: Optional[AuditActorType] = None,
        actor_id: Optional[str] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source: Optional[AuditSource] = None,
        severity: Optional[AuditSeverity] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditRecord]:
        """Query audit records with flexible filtering."""

    @abstractmethod
    def query_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """List all audit records for a specific entity, ordered by timestamp."""

    @abstractmethod
    def query_by_actor(
        self,
        actor_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """List all audit records for a specific actor, ordered by timestamp."""

    @abstractmethod
    def query_by_correlation(
        self,
        correlation_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """List all audit records sharing a correlation_id, ordered by timestamp."""

    @abstractmethod
    def count_records(
        self,
        entity_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        source: Optional[AuditSource] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Count audit records matching filters."""

    @abstractmethod
    def delete_expired(self, before: datetime) -> int:
        """Delete audit records older than the given timestamp. Returns count deleted."""

    def close(self) -> None:
        """Release any resources held by the repository."""
