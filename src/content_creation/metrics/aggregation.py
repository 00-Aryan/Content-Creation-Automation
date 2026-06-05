"""MetricsAggregationService — time-bucketed aggregation of metrics."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from content_creation.metrics.models import MetricType
from content_creation.metrics.repository import MetricRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AggregationBucket:
    """A single time bucket in an aggregation result."""

    start: datetime
    end: datetime
    value: float
    count: int = 0


@dataclass(frozen=True)
class AggregationResult:
    """Result of a time-bucketed aggregation."""

    metric_name: str
    aggregation: str
    bucket_size: str
    buckets: List[AggregationBucket]
    total: float = 0.0


class MetricsAggregationService:
    """Application service for time-bucketed metric aggregation.

    Supports hourly, daily, weekly, and monthly bucket sizes.
    Operations: sum, average, min, max, count.

    All operations are read-only — no mutations.
    """

    def __init__(self, repository: MetricRepository) -> None:
        self._repository = repository

    def aggregate_hourly(
        self,
        metric_name: str,
        aggregation: str,
        start: datetime,
        end: datetime,
        entity_type: Optional[str] = None,
    ) -> AggregationResult:
        """Aggregate metrics into hourly buckets."""
        return self._aggregate_by_bucket(
            metric_name, aggregation, start, end, timedelta(hours=1), entity_type,
        )

    def aggregate_daily(
        self,
        metric_name: str,
        aggregation: str,
        start: datetime,
        end: datetime,
        entity_type: Optional[str] = None,
    ) -> AggregationResult:
        """Aggregate metrics into daily buckets."""
        return self._aggregate_by_bucket(
            metric_name, aggregation, start, end, timedelta(days=1), entity_type,
        )

    def aggregate_weekly(
        self,
        metric_name: str,
        aggregation: str,
        start: datetime,
        end: datetime,
        entity_type: Optional[str] = None,
    ) -> AggregationResult:
        """Aggregate metrics into weekly buckets."""
        return self._aggregate_by_bucket(
            metric_name, aggregation, start, end, timedelta(weeks=1), entity_type,
        )

    def aggregate_monthly(
        self,
        metric_name: str,
        aggregation: str,
        start: datetime,
        end: datetime,
        entity_type: Optional[str] = None,
    ) -> AggregationResult:
        """Aggregate metrics into monthly buckets (30-day)."""
        return self._aggregate_by_bucket(
            metric_name, aggregation, start, end, timedelta(days=30), entity_type,
        )

    def _aggregate_by_bucket(
        self,
        metric_name: str,
        aggregation: str,
        start: datetime,
        end: datetime,
        bucket_size: timedelta,
        entity_type: Optional[str] = None,
    ) -> AggregationResult:
        """Generic bucket-based aggregation."""
        agg_func = aggregation.lower()
        if agg_func not in ("sum", "avg", "min", "max", "count"):
            raise ValueError(f"Unsupported aggregation: {aggregation}")

        records = self._repository.query_metrics(
            metric_name=metric_name,
            start=start,
            end=end,
            entity_type=entity_type,
            limit=100000,
        )

        buckets: List[AggregationBucket] = []
        current = start
        while current < end:
            bucket_end = min(current + bucket_size, end)
            bucket_values = [
                r.value for r in records
                if current <= r.timestamp < bucket_end
            ]

            if bucket_values:
                if agg_func == "sum":
                    val = sum(bucket_values)
                elif agg_func == "avg":
                    val = sum(bucket_values) / len(bucket_values)
                elif agg_func == "min":
                    val = min(bucket_values)
                elif agg_func == "max":
                    val = max(bucket_values)
                else:
                    val = float(len(bucket_values))

                buckets.append(AggregationBucket(
                    start=current, end=bucket_end,
                    value=val, count=len(bucket_values),
                ))
            else:
                buckets.append(AggregationBucket(
                    start=current, end=bucket_end,
                    value=0.0, count=0,
                ))

            current = bucket_end

        total = sum(b.value for b in buckets)

        bucket_label = self._bucket_label(bucket_size)
        return AggregationResult(
            metric_name=metric_name,
            aggregation=agg_func,
            bucket_size=bucket_label,
            buckets=buckets,
            total=total,
        )

    def _bucket_label(self, size: timedelta) -> str:
        """Convert timedelta to human-readable label."""
        if size == timedelta(hours=1):
            return "hourly"
        elif size == timedelta(days=1):
            return "daily"
        elif size == timedelta(weeks=1):
            return "weekly"
        elif size == timedelta(days=30):
            return "monthly"
        return f"{size.total_seconds():.0f}s"

    def rolling_average(
        self,
        metric_name: str,
        window_days: int,
        end: Optional[datetime] = None,
    ) -> float:
        """Calculate rolling average over a window."""
        if end is None:
            end = datetime.now(timezone.utc)
        start = end - timedelta(days=window_days)

        result = self._repository.aggregate_metrics(
            metric_name, "avg", start=start, end=end,
        )
        return result if result is not None else 0.0

    def growth_rate(
        self,
        metric_name: str,
        period_days: int,
        end: Optional[datetime] = None,
    ) -> float:
        """Calculate growth rate between two consecutive periods."""
        if end is None:
            end = datetime.now(timezone.utc)

        current_start = end - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)

        current = self._repository.aggregate_metrics(
            metric_name, "sum", start=current_start, end=end,
        ) or 0.0

        previous = self._repository.aggregate_metrics(
            metric_name, "sum", start=previous_start, end=current_start,
        ) or 0.0

        if previous == 0.0:
            return 0.0 if current == 0.0 else 100.0

        return ((current - previous) / previous) * 100.0
