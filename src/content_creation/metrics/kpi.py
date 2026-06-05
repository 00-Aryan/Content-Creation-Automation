"""KPICatalog — predefined operational KPI calculations from the metrics store."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from content_creation.metrics.repository import MetricRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KPIResult:
    """Result of a KPI calculation."""

    name: str
    value: float
    unit: str = ""
    description: str = ""
    metadata: Dict[str, float] = field(default_factory=dict)


class KPICatalog:
    """Predefined KPI calculations derived from the metrics store.

    Provides workflow, job, system, and notification KPIs.
    All calculations are read-only — no mutations.
    """

    def __init__(self, repository: MetricRepository) -> None:
        self._repository = repository

    def calculate_all(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, KPIResult]:
        """Calculate all available KPIs."""
        kpis: Dict[str, KPIResult] = {}

        # Workflow KPIs
        kpis["briefs_generated"] = self.briefs_generated(start, end)
        kpis["storyboards_generated"] = self.storyboards_generated(start, end)
        kpis["assets_generated"] = self.assets_generated(start, end)
        kpis["approval_rate"] = self.approval_rate(start, end)
        kpis["rejection_rate"] = self.rejection_rate(start, end)

        # Job KPIs
        kpis["jobs_started"] = self.jobs_started(start, end)
        kpis["jobs_completed"] = self.jobs_completed(start, end)
        kpis["jobs_failed"] = self.jobs_failed(start, end)
        kpis["job_success_rate"] = self.job_success_rate(start, end)
        kpis["job_retries"] = self.job_retries(start, end)
        kpis["average_job_runtime"] = self.average_job_runtime(start, end)

        # System KPIs
        kpis["lock_contentions"] = self.lock_contentions(start, end)
        kpis["zombie_recoveries"] = self.zombie_recoveries(start, end)
        kpis["stale_lock_expirations"] = self.stale_lock_expirations(start, end)

        # Notification KPIs
        kpis["pipelines_completed"] = self.pipelines_completed(start, end)
        kpis["pipelines_failed"] = self.pipelines_failed(start, end)
        kpis["pipeline_success_rate"] = self.pipeline_success_rate(start, end)

        return kpis

    # ── Workflow KPIs ──────────────────────────────────────────────

    def briefs_generated(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("briefs_generated_total", start, end)
        return KPIResult(name="briefs_generated", value=value, unit="count")

    def storyboards_generated(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("storyboards_generated_total", start, end)
        return KPIResult(name="storyboards_generated", value=value, unit="count")

    def assets_generated(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("assets_generated_total", start, end)
        return KPIResult(name="assets_generated", value=value, unit="count")

    def approval_rate(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        approved = (
            self._count("briefs_approved_total", start, end)
            + self._count("storyboards_approved_total", start, end)
            + self._count("assets_approved_total", start, end)
        )
        rejected = (
            self._count("briefs_rejected_total", start, end)
            + self._count("storyboards_rejected_total", start, end)
            + self._count("assets_rejected_total", start, end)
        )
        total = approved + rejected
        rate = (approved / total * 100.0) if total > 0 else 0.0
        return KPIResult(
            name="approval_rate",
            value=rate,
            unit="%",
            metadata={"approved": float(approved), "rejected": float(rejected)},
        )

    def rejection_rate(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        approval = self.approval_rate(start, end)
        return KPIResult(
            name="rejection_rate",
            value=100.0 - approval.value,
            unit="%",
        )

    # ── Job KPIs ───────────────────────────────────────────────────

    def jobs_started(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("jobs_started_total", start, end)
        return KPIResult(name="jobs_started", value=value, unit="count")

    def jobs_completed(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("jobs_completed_total", start, end)
        return KPIResult(name="jobs_completed", value=value, unit="count")

    def jobs_failed(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("jobs_failed_total", start, end)
        return KPIResult(name="jobs_failed", value=value, unit="count")

    def job_success_rate(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        completed = self._count("jobs_completed_total", start, end)
        failed = self._count("jobs_failed_total", start, end)
        total = completed + failed
        rate = (completed / total * 100.0) if total > 0 else 0.0
        return KPIResult(
            name="job_success_rate",
            value=rate,
            unit="%",
            metadata={"completed": float(completed), "failed": float(failed)},
        )

    def job_retries(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("jobs_retried_total", start, end)
        return KPIResult(name="job_retries", value=value, unit="count")

    def average_job_runtime(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._repository.aggregate_metrics(
            "job_duration_seconds", "avg", start=start, end=end,
        )
        return KPIResult(
            name="average_job_runtime",
            value=value or 0.0,
            unit="seconds",
        )

    # ── System KPIs ────────────────────────────────────────────────

    def lock_contentions(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("locks_expired_total", start, end)
        return KPIResult(name="lock_contentions", value=value, unit="count")

    def zombie_recoveries(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("zombie_jobs_recovered_total", start, end)
        return KPIResult(name="zombie_recoveries", value=value, unit="count")

    def stale_lock_expirations(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("stale_locks_expired_total", start, end)
        return KPIResult(name="stale_lock_expirations", value=value, unit="count")

    # ── Pipeline KPIs ──────────────────────────────────────────────

    def pipelines_completed(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("pipelines_completed_total", start, end)
        return KPIResult(name="pipelines_completed", value=value, unit="count")

    def pipelines_failed(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        value = self._count("pipelines_failed_total", start, end)
        return KPIResult(name="pipelines_failed", value=value, unit="count")

    def pipeline_success_rate(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None,
    ) -> KPIResult:
        completed = self._count("pipelines_completed_total", start, end)
        failed = self._count("pipelines_failed_total", start, end)
        total = completed + failed
        rate = (completed / total * 100.0) if total > 0 else 0.0
        return KPIResult(
            name="pipeline_success_rate",
            value=rate,
            unit="%",
            metadata={"completed": float(completed), "failed": float(failed)},
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _count(
        self,
        metric_name: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Count metrics by name in a time range."""
        result = self._repository.aggregate_metrics(
            metric_name, "count", start=start, end=end,
        )
        return int(result) if result is not None else 0
