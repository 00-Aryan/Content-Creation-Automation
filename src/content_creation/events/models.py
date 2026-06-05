"""Workflow Event Domain Models representing event payloads, categories, and severities."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict
from uuid import UUID


class EventSeverity(str, Enum):
    """Classification of event severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    """AUTHORITATIVE classification of all supported event types."""

    # Workflow events
    BRIEF_GENERATED = "brief_generated"
    CI_GENERATED = "ci_generated"
    STORYBOARD_GENERATED = "storyboard_generated"
    ASSET_GENERATED = "asset_generated"
    MANIFEST_BUILT = "manifest_built"

    # Review events
    BRIEF_APPROVED = "brief_approved"
    BRIEF_REJECTED = "brief_rejected"
    STORYBOARD_APPROVED = "storyboard_approved"
    STORYBOARD_REJECTED = "storyboard_rejected"
    ASSET_APPROVED = "asset_approved"
    ASSET_REJECTED = "asset_rejected"

    # Job events
    JOB_CREATED = "job_created"
    JOB_QUEUED = "job_queued"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_RETRIED = "job_retried"

    # Lock events
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    LOCK_EXPIRED = "lock_expired"

    # Recovery events
    ZOMBIE_JOB_RECOVERED = "zombie_job_recovered"
    STALE_LOCK_EXPIRED = "stale_lock_expired"

    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"


@dataclass(frozen=True)
class EventMetadata:
    """Standardized metadata headers for all published events."""

    source: str
    correlation_id: str
    actor_id: str
    entity_type: str
    entity_id: str


@dataclass(frozen=True)
class WorkflowEvent:
    """Immutable domain representation of an asynchronous workflow event."""

    event_id: UUID
    event_type: EventType
    timestamp: datetime
    source: str
    correlation_id: str
    actor_id: str
    entity_type: str
    entity_id: str
    severity: EventSeverity
    payload: Dict[str, Any] = field(default_factory=dict)
