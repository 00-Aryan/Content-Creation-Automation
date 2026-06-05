"""MetricRepository — abstract interface for metric persistence."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from content_creation.metrics.models import MetricRecord, MetricType


class MetricRepository(ABC):
    """Abstract interface for metric persistence.

    Implementations must provide transaction-safe, indexed storage
    for MetricRecord objects with aggregation support.
    """

    @abstractmethod
    def save_metric(self, record: MetricRecord) -> None:
        """Persist a metric record. Idempotent on duplicate metric_id."""

    @abstractmethod
    def get_metric(self, metric_id: UUID) -> Optional[MetricRecord]:
        """Retrieve a single metric by ID."""

    @abstractmethod
    def query_metrics(
        self,
        metric_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[MetricRecord]:
        """Query metrics with flexible filtering."""

    @abstractmethod
    def aggregate_metrics(
        self,
        metric_name: str,
        aggregation: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        entity_type: Optional[str] = None,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Aggregate metrics by name and operation.

        Supported aggregations: sum, avg, min, max, count.
        """

    @abstractmethod
    def aggregate_by_dimensions(
        self,
        metric_name: str,
        aggregation: str,
        dimension_key: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Aggregate metrics grouped by a dimension key."""

    @abstractmethod
    def count_metrics(
        self,
        metric_name: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Count total metrics matching filters."""

    @abstractmethod
    def delete_expired(self, before: datetime) -> int:
        """Delete metrics older than the given timestamp. Returns count deleted."""

    def close(self) -> None:
        """Release any resources held by the repository."""
