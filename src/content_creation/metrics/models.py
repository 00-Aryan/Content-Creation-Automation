"""MetricRecord — immutable domain model for persisted metrics."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class MetricType(str, Enum):
    """Classification of metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass(frozen=True)
class MetricRecord:
    """Immutable record of a persisted metric.

    This is the authoritative representation of an operational metric
    derived from the event stream. It is serializable, audit-safe,
    and designed for long-term storage and aggregation.

    Fields:
        metric_id: Unique identifier (UUID).
        metric_name: The metric name (e.g. "jobs_completed_total").
        metric_type: Type of metric (counter, gauge, histogram, timer).
        value: Numeric value of the metric.
        timestamp: UTC timestamp of metric creation.
        entity_type: Type of entity this metric relates to (optional).
        entity_id: ID of the entity this metric relates to (optional).
        dimensions: Additional key-value dimensions for slicing/dicing.
    """

    metric_id: UUID
    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    entity_type: str = ""
    entity_id: str = ""
    dimensions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary for API responses."""
        return {
            "metric_id": str(self.metric_id),
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "dimensions": self.dimensions,
        }

    @classmethod
    def counter(
        cls,
        name: str,
        value: float = 1.0,
        entity_type: str = "",
        entity_id: str = "",
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "MetricRecord":
        """Create a counter metric."""
        return cls(
            metric_id=uuid4(),
            metric_name=name,
            metric_type=MetricType.COUNTER,
            value=value,
            timestamp=timestamp or datetime.now(timezone.utc),
            entity_type=entity_type,
            entity_id=entity_id,
            dimensions=dimensions or {},
        )

    @classmethod
    def gauge(
        cls,
        name: str,
        value: float,
        entity_type: str = "",
        entity_id: str = "",
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "MetricRecord":
        """Create a gauge metric."""
        return cls(
            metric_id=uuid4(),
            metric_name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            timestamp=timestamp or datetime.now(timezone.utc),
            entity_type=entity_type,
            entity_id=entity_id,
            dimensions=dimensions or {},
        )

    @classmethod
    def timer(
        cls,
        name: str,
        duration_seconds: float,
        entity_type: str = "",
        entity_id: str = "",
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "MetricRecord":
        """Create a timer metric."""
        return cls(
            metric_id=uuid4(),
            metric_name=name,
            metric_type=MetricType.TIMER,
            value=duration_seconds,
            timestamp=timestamp or datetime.now(timezone.utc),
            entity_type=entity_type,
            entity_id=entity_id,
            dimensions=dimensions or {},
        )
