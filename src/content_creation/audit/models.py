"""AuditRecord — immutable domain model for audit trail entries."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class AuditSeverity(str, Enum):
    """Classification of audit event severity."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AuditActorType(str, Enum):
    """Classification of who/what performed the action."""

    OPERATOR = "operator"
    SYSTEM = "system"
    WORKER = "worker"
    RECOVERY = "recovery"
    SCHEDULER = "scheduler"


class AuditSource(str, Enum):
    """Source subsystem that generated the audit record."""

    WORKFLOW = "workflow"
    REVIEW = "review"
    JOB = "job"
    LOCK = "lock"
    RECOVERY = "recovery"
    PIPELINE = "pipeline"
    NOTIFICATION = "notification"
    METRICS = "metrics"


# Map event categories to audit sources
_EVENT_CATEGORY_TO_SOURCE: Dict[str, AuditSource] = {
    "workflow": AuditSource.WORKFLOW,
    "review": AuditSource.REVIEW,
    "job": AuditSource.JOB,
    "lock": AuditSource.LOCK,
    "recovery": AuditSource.RECOVERY,
    "pipeline": AuditSource.PIPELINE,
}

# Map event names to human-readable action types
_EVENT_TO_ACTION: Dict[str, str] = {
    "brief_generated": "generate_brief",
    "ci_generated": "generate_ci",
    "storyboard_generated": "generate_storyboard",
    "asset_generated": "generate_asset",
    "manifest_built": "build_manifest",
    "brief_approved": "approve_brief",
    "brief_rejected": "reject_brief",
    "storyboard_approved": "approve_storyboard",
    "storyboard_rejected": "reject_storyboard",
    "asset_approved": "approve_asset",
    "asset_rejected": "reject_asset",
    "job_created": "create_job",
    "job_queued": "queue_job",
    "job_started": "start_job",
    "job_completed": "complete_job",
    "job_failed": "fail_job",
    "job_cancelled": "cancel_job",
    "job_retried": "retry_job",
    "lock_acquired": "acquire_lock",
    "lock_released": "release_lock",
    "lock_expired": "expire_lock",
    "zombie_job_recovered": "recover_zombie_job",
    "stale_lock_expired": "expire_stale_lock",
    "pipeline_started": "start_pipeline",
    "pipeline_completed": "complete_pipeline",
    "pipeline_failed": "fail_pipeline",
}

# Map event severities to audit severities
_EVENT_SEVERITY_MAP = {
    "INFO": AuditSeverity.INFO,
    "WARNING": AuditSeverity.WARNING,
    "CRITICAL": AuditSeverity.CRITICAL,
}


@dataclass(frozen=True)
class AuditRecord:
    """Immutable record of an auditable action.

    This is the authoritative historical representation of a platform action.
    It is serializable, audit-safe, and designed for long-term compliance storage.

    Fields:
        audit_id: Unique identifier (UUID).
        timestamp: UTC timestamp of audit record creation.
        actor_type: Who/what performed the action (operator, system, worker, etc.).
        actor_id: ID of the actor (user ID, job ID, "system", etc.).
        action_type: Human-readable action (e.g. "approve_brief", "complete_job").
        entity_type: Type of entity involved (brief, job, lock, etc.).
        entity_id: ID of the entity involved.
        event_type: Original event type value (e.g. "brief_approved").
        correlation_id: Links related events in a single operation.
        previous_state: State before the action (if applicable).
        new_state: State after the action (if applicable).
        metadata: Additional key-value pairs for context.
        source: Source subsystem (workflow, review, job, etc.).
        severity: Severity of the audit event.
    """

    audit_id: UUID
    timestamp: datetime
    actor_type: AuditActorType
    actor_id: str
    action_type: str
    entity_type: str
    entity_id: str
    event_type: str
    correlation_id: str
    previous_state: str = ""
    new_state: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: AuditSource = AuditSource.WORKFLOW
    severity: AuditSeverity = AuditSeverity.INFO

    def __post_init__(self) -> None:
        """Automatically redact secrets in audit metadata and states."""
        from content_creation.security.redaction import redact_mapping, redact_text
        object.__setattr__(self, "metadata", redact_mapping(self.metadata))
        object.__setattr__(self, "previous_state", redact_text(self.previous_state))
        object.__setattr__(self, "new_state", redact_text(self.new_state))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary for API responses."""
        return {
            "audit_id": str(self.audit_id),
            "timestamp": self.timestamp.isoformat(),
            "actor_type": self.actor_type.value,
            "actor_id": self.actor_id,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "metadata": self.metadata,
            "source": self.source.value,
            "severity": self.severity.value,
        }

    @classmethod
    def from_workflow_event(cls, event: Any) -> "AuditRecord":
        """Create an AuditRecord from a WorkflowEvent domain object.

        This is the canonical bridge from the in-memory event system
        to the durable audit trail.
        """
        from content_creation.events.bus import EVENT_TYPE_CATEGORIES

        event_name = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        category = EVENT_TYPE_CATEGORIES.get(event.event_type, "unknown") if hasattr(event.event_type, "value") else "unknown"

        actor_type = AuditActorType.SYSTEM
        actor_id = event.actor_id if hasattr(event, "actor_id") else ""
        if actor_id and actor_id != "recovery_supervisor" and actor_id != "system":
            actor_type = AuditActorType.OPERATOR

        if category == "recovery":
            actor_type = AuditActorType.RECOVERY
            actor_id = "recovery_supervisor"

        action_type = _EVENT_TO_ACTION.get(event_name, event_name)
        source = _EVENT_CATEGORY_TO_SOURCE.get(category, AuditSource.WORKFLOW)

        severity = AuditSeverity.INFO
        if hasattr(event, "severity"):
            sev_val = event.severity.value if hasattr(event.severity, "value") else str(event.severity)
            severity = _EVENT_SEVERITY_MAP.get(sev_val, AuditSeverity.INFO)

        payload = event.payload if isinstance(event.payload, dict) else {}

        previous_state = ""
        new_state = ""
        if "previous_status" in payload:
            previous_state = str(payload["previous_status"])
        if "new_status" in payload:
            new_state = str(payload["new_status"])
        elif "status" in payload:
            new_state = str(payload["status"])

        return cls(
            audit_id=uuid4(),
            timestamp=event.timestamp if hasattr(event, "timestamp") else datetime.now(timezone.utc),
            actor_type=actor_type,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=event.entity_type if hasattr(event, "entity_type") else "",
            entity_id=event.entity_id if hasattr(event, "entity_id") else "",
            event_type=event_name,
            correlation_id=event.correlation_id if hasattr(event, "correlation_id") else "",
            previous_state=previous_state,
            new_state=new_state,
            metadata=payload,
            source=source,
            severity=severity,
        )
