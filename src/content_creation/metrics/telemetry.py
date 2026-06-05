"""TelemetryService — high-level operational intelligence summaries."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from content_creation.metrics.kpi import KPICatalog, KPIResult
from content_creation.metrics.repository import MetricRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SystemSummary:
    """High-level system health summary."""

    total_events_stored: int = 0
    total_metrics_stored: int = 0
    uptime_indicator: str = "operational"
    event_categories: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowSummary:
    """Workflow pipeline summary."""

    briefs_generated: int = 0
    storyboards_generated: int = 0
    assets_generated: int = 0
    manifests_built: int = 0
    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    total_reviews: int = 0


@dataclass(frozen=True)
class JobSummary:
    """Job system summary."""

    jobs_started: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    jobs_retried: int = 0
    success_rate: float = 0.0
    average_runtime_seconds: float = 0.0
    total_jobs: int = 0


@dataclass(frozen=True)
class ReliabilitySummary:
    """System reliability summary."""

    lock_contentions: int = 0
    zombie_recoveries: int = 0
    stale_lock_expirations: int = 0
    pipeline_success_rate: float = 0.0
    pipelines_completed: int = 0
    pipelines_failed: int = 0


class TelemetryService:
    """Application service for high-level operational intelligence.

    Provides system, workflow, job, and reliability summaries
    for dashboard consumption. UI-independent — no Streamlit imports.

    All operations are read-only — no mutations.
    """

    def __init__(
        self,
        metrics_repository: MetricRepository,
        event_repository: Optional[object] = None,
    ) -> None:
        self._metrics_repo = metrics_repository
        self._event_repo = event_repository
        self._kpi_catalog = KPICatalog(metrics_repository)

    def system_summary(self) -> SystemSummary:
        """Get high-level system health summary."""
        event_count = 0
        event_categories: Dict[str, int] = {}

        if self._event_repo is not None:
            try:
                event_count = self._event_repo.count_events()
                for cat in ("workflow", "review", "job", "lock", "recovery", "pipeline"):
                    count = self._event_repo.count_events(category=cat)
                    if count > 0:
                        event_categories[cat] = count
            except Exception:
                logger.debug("Could not query event repository")

        metric_count = self._metrics_repo.count_metrics()

        return SystemSummary(
            total_events_stored=event_count,
            total_metrics_stored=metric_count,
            event_categories=event_categories,
        )

    def workflow_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> WorkflowSummary:
        """Get workflow pipeline summary."""
        kpis = self._kpi_catalog.calculate_all(start, end)

        return WorkflowSummary(
            briefs_generated=int(kpis["briefs_generated"].value),
            storyboards_generated=int(kpis["storyboards_generated"].value),
            assets_generated=int(kpis["assets_generated"].value),
            approval_rate=kpis["approval_rate"].value,
            rejection_rate=kpis["rejection_rate"].value,
            total_reviews=(
                int(kpis["approval_rate"].metadata.get("approved", 0))
                + int(kpis["approval_rate"].metadata.get("rejected", 0))
            ),
        )

    def job_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> JobSummary:
        """Get job system summary."""
        kpis = self._kpi_catalog.calculate_all(start, end)

        started = int(kpis["jobs_started"].value)
        completed = int(kpis["jobs_completed"].value)
        failed = int(kpis["jobs_failed"].value)
        retried = int(kpis["job_retries"].value)

        return JobSummary(
            jobs_started=started,
            jobs_completed=completed,
            jobs_failed=failed,
            jobs_retried=retried,
            success_rate=kpis["job_success_rate"].value,
            average_runtime_seconds=kpis["average_job_runtime"].value,
            total_jobs=started,
        )

    def reliability_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> ReliabilitySummary:
        """Get system reliability summary."""
        kpis = self._kpi_catalog.calculate_all(start, end)

        return ReliabilitySummary(
            lock_contentions=int(kpis["lock_contentions"].value),
            zombie_recoveries=int(kpis["zombie_recoveries"].value),
            stale_lock_expirations=int(kpis["stale_lock_expirations"].value),
            pipeline_success_rate=kpis["pipeline_success_rate"].value,
            pipelines_completed=int(kpis["pipelines_completed"].value),
            pipelines_failed=int(kpis["pipelines_failed"].value),
        )

    def full_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, object]:
        """Get all summaries combined."""
        return {
            "system": self.system_summary(),
            "workflow": self.workflow_summary(start, end),
            "jobs": self.job_summary(start, end),
            "reliability": self.reliability_summary(start, end),
        }
