"""Authoritative factory helpers creating standardized event instances."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from content_creation.events.models import EventSeverity, EventType, WorkflowEvent


def create_event(
    event_type: EventType,
    source: str,
    correlation_id: str,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    severity: EventSeverity,
    payload: Optional[Dict[str, Any]] = None,
) -> WorkflowEvent:
    """Core builder establishing metadata and timestamp normalization across all events."""
    return WorkflowEvent(
        event_id=uuid4(),
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        source=source,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        payload=payload or {},
    )


def create_job_event(
    event_type: EventType,
    job_id: UUID,
    job_type: str,
    status: str,
    operator_id: str,
    correlation_id: str,
    target_type: str,
    target_id: str,
    retry_count: int = 0,
    max_retries: int = 3,
    error_message: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> WorkflowEvent:
    """Construct a standardized job system event with predefined payload schemas."""
    payload = {
        "job_id": str(job_id),
        "job_type": job_type,
        "status": status,
        "operator_id": operator_id,
        "target_type": target_type,
        "target_id": target_id,
        "retry_count": retry_count,
        "max_retries": max_retries,
    }
    if error_message:
        payload["error_message"] = error_message
    if extra_payload:
        payload.update(extra_payload)

    severity = EventSeverity.INFO
    if event_type == EventType.JOB_FAILED:
        severity = EventSeverity.CRITICAL
    elif event_type in (EventType.JOB_RETRIED, EventType.JOB_CANCELLED):
        severity = EventSeverity.WARNING

    return create_event(
        event_type=event_type,
        source="job_system",
        correlation_id=correlation_id,
        actor_id=operator_id,
        entity_type="job",
        entity_id=str(job_id),
        severity=severity,
        payload=payload,
    )


def create_lock_event(
    event_type: EventType,
    lock_id: UUID,
    lock_type: str,
    resource_id: str,
    owner_job_id: UUID,
    correlation_id: str,
) -> WorkflowEvent:
    """Construct a standardized lock event with metadata schema normalization."""
    payload = {
        "lock_id": str(lock_id),
        "lock_type": lock_type,
        "resource_id": resource_id,
        "owner_job_id": str(owner_job_id),
    }

    severity = EventSeverity.INFO
    if event_type == EventType.LOCK_EXPIRED:
        severity = EventSeverity.WARNING

    return create_event(
        event_type=event_type,
        source="lock_manager",
        correlation_id=correlation_id,
        actor_id=str(owner_job_id),
        entity_type="lock",
        entity_id=str(lock_id),
        severity=severity,
        payload=payload,
    )


def create_workflow_event(
    event_type: EventType,
    topic_id: str,
    operator_id: str,
    correlation_id: str,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> WorkflowEvent:
    """Construct a standardized workflow domain event (Brief, Script, Storyboard, Asset)."""
    payload = {
        "topic_id": topic_id,
        "operator_id": operator_id,
    }
    if extra_payload:
        payload.update(extra_payload)

    severity = EventSeverity.INFO
    if event_type in (EventType.BRIEF_REJECTED, EventType.STORYBOARD_REJECTED, EventType.ASSET_REJECTED):
        severity = EventSeverity.WARNING

    # Map target entity type
    entity_type = "topic"
    val = event_type.value
    if "brief" in val:
        entity_type = "brief"
    elif "storyboard" in val:
        entity_type = "storyboard"
    elif "asset" in val:
        entity_type = "asset"
    elif "manifest" in val:
        entity_type = "manifest"

    return create_event(
        event_type=event_type,
        source="workflow_engine",
        correlation_id=correlation_id,
        actor_id=operator_id,
        entity_type=entity_type,
        entity_id=topic_id,
        severity=severity,
        payload=payload,
    )


def create_pipeline_event(
    event_type: EventType,
    week_start: str,
    operator_id: str,
    correlation_id: str,
    error_message: Optional[str] = None,
) -> WorkflowEvent:
    """Construct a standardized posting pipeline execution lifecycle event."""
    payload = {
        "week_start": week_start,
        "operator_id": operator_id,
    }
    if error_message:
        payload["error_message"] = error_message

    severity = EventSeverity.INFO
    if event_type == EventType.PIPELINE_FAILED:
        severity = EventSeverity.CRITICAL

    return create_event(
        event_type=event_type,
        source="pipeline_service",
        correlation_id=correlation_id,
        actor_id=operator_id,
        entity_type="pipeline",
        entity_id=week_start,
        severity=severity,
        payload=payload,
    )


def create_recovery_event(
    event_type: EventType,
    entity_type: str,
    entity_id: str,
    correlation_id: str,
    details: Dict[str, Any],
) -> WorkflowEvent:
    """Construct a recovery supervisor audit event capturing system recovery mutations."""
    return create_event(
        event_type=event_type,
        source="recovery_supervisor",
        correlation_id=correlation_id,
        actor_id="recovery_supervisor",
        entity_type=entity_type,
        entity_id=entity_id,
        severity=EventSeverity.WARNING,
        payload=details,
    )
