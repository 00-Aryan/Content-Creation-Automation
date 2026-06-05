"""ComplianceReportService — generate compliance and governance reports from the audit trail."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from content_creation.audit.models import AuditRecord, AuditActorType, AuditSource, AuditSeverity
from content_creation.audit.repository import AuditRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActorActivityReport:
    """Report of a single actor's activity."""

    actor_id: str
    actor_type: str
    total_actions: int
    action_breakdown: Dict[str, int]
    entity_breakdown: Dict[str, int]
    first_action: Optional[str] = None
    last_action: Optional[str] = None


@dataclass(frozen=True)
class WorkflowDecisionReport:
    """Report of workflow approval/rejection decisions."""

    total_decisions: int
    approvals: int
    rejections: int
    approval_rate: float
    by_entity: Dict[str, Dict[str, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class JobExecutionReport:
    """Report of job execution history."""

    total_jobs: int
    completed: int
    failed: int
    cancelled: int
    retried: int
    success_rate: float


@dataclass(frozen=True)
class IncidentTimeline:
    """Timeline of critical/warning events."""

    events: List[AuditRecord]
    total_critical: int
    total_warning: int


@dataclass(frozen=True)
class ComplianceSummary:
    """High-level compliance summary."""

    total_audit_records: int
    date_range_start: str
    date_range_end: str
    actors_active: int
    unique_entities: int
    source_breakdown: Dict[str, int]
    severity_breakdown: Dict[str, int]


class ComplianceReportService:
    """Application service for generating compliance and governance reports.

    Provides structured reports suitable for:
    - Operator activity monitoring
    - Workflow decision auditing
    - Job execution tracking
    - Incident investigation
    - Compliance reviews

    All operations are read-only — no mutations.
    No UI, worker, or executor imports.
    """

    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def operator_activity_report(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[ActorActivityReport]:
        """Generate operator activity reports."""
        records = self._repository.query_records(
            actor_type=AuditActorType.OPERATOR,
            start=start, end=end, limit=10000,
        )

        actor_data: Dict[str, Dict] = {}
        for r in records:
            if r.actor_id not in actor_data:
                actor_data[r.actor_id] = {
                    "actor_type": r.actor_type.value,
                    "actions": {},
                    "entities": {},
                    "first": r.timestamp.isoformat(),
                    "last": r.timestamp.isoformat(),
                }
            data = actor_data[r.actor_id]
            data["actions"][r.action_type] = data["actions"].get(r.action_type, 0) + 1
            data["entities"][r.entity_type] = data["entities"].get(r.entity_type, 0) + 1
            if r.timestamp.isoformat() < data["first"]:
                data["first"] = r.timestamp.isoformat()
            if r.timestamp.isoformat() > data["last"]:
                data["last"] = r.timestamp.isoformat()

        reports = []
        for actor_id, data in sorted(actor_data.items(), key=lambda x: sum(x[1]["actions"].values()), reverse=True):
            reports.append(ActorActivityReport(
                actor_id=actor_id,
                actor_type=data["actor_type"],
                total_actions=sum(data["actions"].values()),
                action_breakdown=data["actions"],
                entity_breakdown=data["entities"],
                first_action=data["first"],
                last_action=data["last"],
            ))

        return reports[:limit]

    def workflow_decision_report(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> WorkflowDecisionReport:
        """Generate workflow approval/rejection decision report."""
        approval_events = {"brief_approved", "storyboard_approved", "asset_approved"}
        rejection_events = {"brief_rejected", "storyboard_rejected", "asset_rejected"}

        records = self._repository.query_records(
            source=AuditSource.REVIEW,
            start=start, end=end, limit=10000,
        )

        approvals = 0
        rejections = 0
        by_entity: Dict[str, Dict[str, int]] = {}

        for r in records:
            if r.event_type in approval_events:
                approvals += 1
                entity_key = r.entity_type
                if entity_key not in by_entity:
                    by_entity[entity_key] = {"approved": 0, "rejected": 0}
                by_entity[entity_key]["approved"] += 1
            elif r.event_type in rejection_events:
                rejections += 1
                entity_key = r.entity_type
                if entity_key not in by_entity:
                    by_entity[entity_key] = {"approved": 0, "rejected": 0}
                by_entity[entity_key]["rejected"] += 1

        total = approvals + rejections
        rate = (approvals / total * 100.0) if total > 0 else 0.0

        return WorkflowDecisionReport(
            total_decisions=total,
            approvals=approvals,
            rejections=rejections,
            approval_rate=rate,
            by_entity=by_entity,
        )

    def job_execution_report(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> JobExecutionReport:
        """Generate job execution history report."""
        records = self._repository.query_records(
            source=AuditSource.JOB,
            start=start, end=end, limit=10000,
        )

        completed = 0
        failed = 0
        cancelled = 0
        retried = 0

        for r in records:
            if r.event_type == "job_completed":
                completed += 1
            elif r.event_type == "job_failed":
                failed += 1
            elif r.event_type == "job_cancelled":
                cancelled += 1
            elif r.event_type == "job_retried":
                retried += 1

        total_terminal = completed + failed + cancelled
        rate = (completed / total_terminal * 100.0) if total_terminal > 0 else 0.0

        return JobExecutionReport(
            total_jobs=total_terminal,
            completed=completed,
            failed=failed,
            cancelled=cancelled,
            retried=retried,
            success_rate=rate,
        )

    def incident_timeline(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> IncidentTimeline:
        """Generate timeline of critical and warning events."""
        critical = self._repository.query_records(
            severity=AuditSeverity.CRITICAL,
            start=start, end=end, limit=limit,
        )
        warning = self._repository.query_records(
            severity=AuditSeverity.WARNING,
            start=start, end=end, limit=limit,
        )

        all_events = sorted(critical + warning, key=lambda r: r.timestamp)

        return IncidentTimeline(
            events=all_events[:limit],
            total_critical=len(critical),
            total_warning=len(warning),
        )

    def compliance_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> ComplianceSummary:
        """Generate high-level compliance summary."""
        records = self._repository.query_records(
            start=start, end=end, limit=100000,
        )

        actors = set()
        entities = set()
        source_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}

        for r in records:
            actors.add(r.actor_id)
            entities.add(f"{r.entity_type}:{r.entity_id}")
            source_counts[r.source.value] = source_counts.get(r.source.value, 0) + 1
            severity_counts[r.severity.value] = severity_counts.get(r.severity.value, 0) + 1

        now = datetime.now(timezone.utc)
        range_start = (start or (now - timedelta(days=30))).isoformat()
        range_end = (end or now).isoformat()

        return ComplianceSummary(
            total_audit_records=len(records),
            date_range_start=range_start,
            date_range_end=range_end,
            actors_active=len(actors),
            unique_entities=len(entities),
            source_breakdown=source_counts,
            severity_breakdown=severity_counts,
        )
