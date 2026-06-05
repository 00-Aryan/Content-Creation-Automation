"""MetricsSubscriber — persists every emitted event as operational metrics."""

import logging
from typing import Dict, List, Optional, Tuple

from content_creation.events.bus import EventBus, get_event_bus
from content_creation.events.models import EventType, WorkflowEvent
from content_creation.metrics.models import MetricRecord, MetricType
from content_creation.metrics.repository import MetricRepository

logger = logging.getLogger(__name__)

# Event-to-metric mapping: (event_type_value) -> (metric_name, metric_type, value_extractor)
# value_extractor receives the event payload and returns a float
_EVENT_TO_METRIC: Dict[str, Tuple[str, MetricType, Optional[str]]] = {
    # Workflow events -> counters
    "brief_generated": ("briefs_generated_total", MetricType.COUNTER, None),
    "ci_generated": ("ci_generated_total", MetricType.COUNTER, None),
    "storyboard_generated": ("storyboards_generated_total", MetricType.COUNTER, None),
    "asset_generated": ("assets_generated_total", MetricType.COUNTER, None),
    "manifest_built": ("manifests_built_total", MetricType.COUNTER, None),

    # Review events -> counters
    "brief_approved": ("briefs_approved_total", MetricType.COUNTER, None),
    "brief_rejected": ("briefs_rejected_total", MetricType.COUNTER, None),
    "storyboard_approved": ("storyboards_approved_total", MetricType.COUNTER, None),
    "storyboard_rejected": ("storyboards_rejected_total", MetricType.COUNTER, None),
    "asset_approved": ("assets_approved_total", MetricType.COUNTER, None),
    "asset_rejected": ("assets_rejected_total", MetricType.COUNTER, None),

    # Job events -> counters + timers
    "job_created": ("jobs_created_total", MetricType.COUNTER, None),
    "job_queued": ("jobs_queued_total", MetricType.COUNTER, None),
    "job_started": ("jobs_started_total", MetricType.COUNTER, None),
    "job_completed": ("jobs_completed_total", MetricType.COUNTER, None),
    "job_failed": ("jobs_failed_total", MetricType.COUNTER, None),
    "job_cancelled": ("jobs_cancelled_total", MetricType.COUNTER, None),
    "job_retried": ("jobs_retried_total", MetricType.COUNTER, None),

    # Lock events -> counters
    "lock_acquired": ("locks_acquired_total", MetricType.COUNTER, None),
    "lock_released": ("locks_released_total", MetricType.COUNTER, None),
    "lock_expired": ("locks_expired_total", MetricType.COUNTER, None),

    # Recovery events -> counters
    "zombie_job_recovered": ("zombie_jobs_recovered_total", MetricType.COUNTER, None),
    "stale_lock_expired": ("stale_locks_expired_total", MetricType.COUNTER, None),

    # Pipeline events -> counters + timers
    "pipeline_started": ("pipelines_started_total", MetricType.COUNTER, None),
    "pipeline_completed": ("pipelines_completed_total", MetricType.COUNTER, None),
    "pipeline_failed": ("pipelines_failed_total", MetricType.COUNTER, None),
}


class MetricsSubscriber:
    """Subscribes to all events on the EventBus and derives operational metrics.

    This is the bridge between the transient event system and the
    persistent metrics store.

    Responsibilities:
    - Subscribe to all events via wildcard pattern
    - Convert events into MetricRecords based on mapping rules
    - Persist via MetricRepository

    Guarantees:
    - Never mutates the original event
    - Never blocks event execution (failure is isolated)
    - Fails independently — store failures don't affect other subscribers
    - All metrics originate from events (no direct writes)
    """

    SUBSCRIBER_ID = "metrics_subscriber"

    def __init__(
        self,
        repository: MetricRepository,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._repository = repository
        self._bus = bus or get_event_bus()
        self._register()

    def _register(self) -> None:
        """Register for all events via wildcard pattern."""
        self._bus.subscribe_wildcard("*", self._handle_event)

    def _handle_event(self, event: WorkflowEvent) -> None:
        """Convert event to metric and persist. Failure is isolated."""
        try:
            metrics = self._extract_metrics(event)
            for metric in metrics:
                self._repository.save_metric(metric)
            if metrics:
                logger.debug(
                    "Derived %d metrics from event %s",
                    len(metrics),
                    event.event_id,
                )
        except Exception:
            logger.exception(
                "Failed to derive metrics from event %s — store failure isolated",
                event.event_id,
            )

    def _extract_metrics(self, event: WorkflowEvent) -> List[MetricRecord]:
        """Extract one or more metrics from a workflow event."""
        metrics: List[MetricRecord] = []
        event_name = event.event_type.value

        # Primary metric from mapping
        if event_name in _EVENT_TO_METRIC:
            metric_name, metric_type, _ = _EVENT_TO_METRIC[event_name]
            dimensions = {
                "source": event.source,
                "category": self._get_category(event.event_type),
            }
            if event.entity_type:
                dimensions["entity_type"] = event.entity_type

            if metric_type == MetricType.COUNTER:
                metrics.append(MetricRecord.counter(
                    name=metric_name,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    dimensions=dimensions,
                ))
            elif metric_type == MetricType.TIMER:
                duration = event.payload.get("duration_seconds")
                if duration is not None:
                    metrics.append(MetricRecord.timer(
                        name=metric_name,
                        duration_seconds=float(duration),
                        entity_type=event.entity_type,
                        entity_id=event.entity_id,
                        dimensions=dimensions,
                    ))

        # Job duration metric (extracted from payload)
        if event_name == "job_completed" and "duration_seconds" in event.payload:
            metrics.append(MetricRecord.timer(
                name="job_duration_seconds",
                duration_seconds=float(event.payload["duration_seconds"]),
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                dimensions={"job_type": event.payload.get("job_type", "unknown")},
            ))

        # Pipeline duration metric
        if event_name == "pipeline_completed" and "duration_seconds" in event.payload:
            metrics.append(MetricRecord.timer(
                name="pipeline_duration_seconds",
                duration_seconds=float(event.payload["duration_seconds"]),
                entity_type=event.entity_type,
                entity_id=event.entity_id,
            ))

        return metrics

    def _get_category(self, event_type: EventType) -> str:
        """Get the category for an event type."""
        from content_creation.events.bus import EVENT_TYPE_CATEGORIES
        return EVENT_TYPE_CATEGORIES.get(event_type, "unknown")

    def shutdown(self) -> None:
        """Unregister from the event bus."""
        try:
            self._bus.unsubscribe_wildcard("*", self._handle_event)
        except Exception:
            logger.debug("Error during metrics subscriber shutdown")
