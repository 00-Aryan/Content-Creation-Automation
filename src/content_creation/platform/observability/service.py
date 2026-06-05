"""Observability service — read-only aggregation across all platform subsystems.

This service is strictly observational. It does not mutate any state.
All data is read from existing repositories and services.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from content_creation.platform.observability.health import (
    AlertSeverity,
    ComponentType,
    DashboardSnapshot,
    HealthStatus,
    OperationalAlert,
    SystemComponentHealth,
)
from content_creation.platform.observability.alerts import evaluate_alerts

logger = logging.getLogger(__name__)


class ObservabilityService:
    """Read-only aggregation service for platform observability.

    Collects health signals from all subsystems and produces a unified
    DashboardSnapshot for the operations dashboard.

    This service MUST NOT modify any repository, event bus, or subsystem state.
    """

    def __init__(
        self,
        queue_engine=None,
        worker_daemon=None,
        lock_manager=None,
        lock_repository=None,
        event_repository=None,
        notification_service=None,
        connection_manager=None,
        metrics_repository=None,
        kpi_catalog=None,
        telemetry_service=None,
        audit_repository=None,
        compliance_service=None,
        recovery_supervisor=None,
    ):
        """Initialize with optional references to platform subsystems.

        All parameters are optional. Missing subsystems will report UNKNOWN health.
        """
        self._queue_engine = queue_engine
        self._worker_daemon = worker_daemon
        self._lock_manager = lock_manager
        self._lock_repository = lock_repository
        self._event_repository = event_repository
        self._notification_service = notification_service
        self._connection_manager = connection_manager
        self._metrics_repository = metrics_repository
        self._kpi_catalog = kpi_catalog
        self._telemetry_service = telemetry_service
        self._audit_repository = audit_repository
        self._compliance_service = compliance_service
        self._recovery_supervisor = recovery_supervisor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def snapshot(self) -> DashboardSnapshot:
        """Generate a complete dashboard snapshot.

        Returns:
            DashboardSnapshot with all subsystem health, metrics, and alerts.
        """
        components = [
            self._check_queue(),
            self._check_worker(),
            self._check_lock(),
            self._check_event(),
            self._check_notification(),
            self._check_metrics(),
            self._check_audit(),
            self._check_sse(),
        ]

        overall = self._derive_overall_status(components)

        all_metrics = self._collect_all_metrics()
        alerts = evaluate_alerts(all_metrics)

        return DashboardSnapshot(
            overall_status=overall,
            components=components,
            alerts=alerts,
            timestamp=datetime.now(timezone.utc),
            kpi_summary=self._get_kpi_summary(),
            queue_metrics=self._get_queue_metrics(),
            worker_metrics=self._get_worker_metrics(),
            lock_metrics=self._get_lock_metrics(),
            event_metrics=self._get_event_metrics(),
            notification_metrics=self._get_notification_metrics(),
            audit_metrics=self._get_audit_metrics(),
            sse_metrics=self._get_sse_metrics(),
        )

    # ------------------------------------------------------------------
    # Component health checks
    # ------------------------------------------------------------------

    def _check_queue(self) -> SystemComponentHealth:
        if self._queue_engine is None:
            return SystemComponentHealth(
                component=ComponentType.QUEUE,
                name="Queue Engine",
                status=HealthStatus.UNKNOWN,
                message="Queue engine not configured.",
            )
        try:
            metrics = self._queue_engine.get_queue_metrics()
            queued = metrics.queued_count
            running = metrics.running_count
            failed = metrics.failed_count
            retrying = metrics.retrying_count

            if failed > 10:
                status = HealthStatus.UNHEALTHY
                msg = f"{failed} jobs failed."
            elif queued > 20 or retrying > 5:
                status = HealthStatus.DEGRADED
                msg = f"Backlog: {queued} queued, {retrying} retrying."
            else:
                status = HealthStatus.HEALTHY
                msg = f"Queue healthy: {queued} queued, {running} running."

            return SystemComponentHealth(
                component=ComponentType.QUEUE,
                name="Queue Engine",
                status=status,
                message=msg,
                metrics={
                    "queued_count": queued,
                    "running_count": running,
                    "retrying_count": retrying,
                    "completed_count": metrics.completed_count,
                    "failed_count": failed,
                    "cancelled_count": metrics.cancelled_count,
                    "oldest_queued_age_seconds": metrics.oldest_queued_age_seconds,
                },
            )
        except Exception as e:
            logger.warning("Queue health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.QUEUE,
                name="Queue Engine",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_worker(self) -> SystemComponentHealth:
        if self._worker_daemon is None:
            return SystemComponentHealth(
                component=ComponentType.WORKER,
                name="Worker Daemon",
                status=HealthStatus.UNKNOWN,
                message="Worker daemon not configured.",
            )
        try:
            is_running = getattr(self._worker_daemon, "_running", False)
            worker_id = getattr(
                self._worker_daemon,
                "_worker_id",
                getattr(self._worker_daemon, "worker_id", "unknown"),
            )

            if is_running:
                status = HealthStatus.HEALTHY
                msg = f"Worker '{worker_id}' is running."
            else:
                status = HealthStatus.DEGRADED
                msg = f"Worker '{worker_id}' is not running."

            return SystemComponentHealth(
                component=ComponentType.WORKER,
                name="Worker Daemon",
                status=status,
                message=msg,
                metrics={
                    "is_running": is_running,
                    "worker_id": worker_id,
                },
            )
        except Exception as e:
            logger.warning("Worker health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.WORKER,
                name="Worker Daemon",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_lock(self) -> SystemComponentHealth:
        if self._lock_manager is None and self._lock_repository is None:
            return SystemComponentHealth(
                component=ComponentType.LOCK,
                name="Lock Manager",
                status=HealthStatus.UNKNOWN,
                message="Lock manager not configured.",
            )
        try:
            repo = self._lock_repository
            if repo is None and self._lock_manager is not None:
                repo = getattr(self._lock_manager, "_repository", None)

            active_locks = []
            if repo is not None and hasattr(repo, "list_active_locks"):
                active_locks = repo.list_active_locks()

            active_count = len(active_locks)
            if active_count > 10:
                status = HealthStatus.DEGRADED
                msg = f"{active_count} active locks — possible contention."
            else:
                status = HealthStatus.HEALTHY
                msg = f"{active_count} active locks."

            return SystemComponentHealth(
                component=ComponentType.LOCK,
                name="Lock Manager",
                status=status,
                message=msg,
                metrics={
                    "active_locks": active_count,
                },
            )
        except Exception as e:
            logger.warning("Lock health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.LOCK,
                name="Lock Manager",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_event(self) -> SystemComponentHealth:
        if self._event_repository is None:
            return SystemComponentHealth(
                component=ComponentType.EVENT,
                name="Event Store",
                status=HealthStatus.UNKNOWN,
                message="Event repository not configured.",
            )
        try:
            total = self._event_repository.count_events()
            workflow = self._event_repository.count_events(category="workflow")
            job = self._event_repository.count_events(category="job")

            if total > 10000:
                status = HealthStatus.DEGRADED
                msg = f"Event store has {total} events — consider cleanup."
            else:
                status = HealthStatus.HEALTHY
                msg = f"Event store: {total} events."

            return SystemComponentHealth(
                component=ComponentType.EVENT,
                name="Event Store",
                status=status,
                message=msg,
                metrics={
                    "event_count": total,
                    "workflow_events": workflow,
                    "job_events": job,
                },
            )
        except Exception as e:
            logger.warning("Event health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.EVENT,
                name="Event Store",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_notification(self) -> SystemComponentHealth:
        if self._notification_service is None:
            return SystemComponentHealth(
                component=ComponentType.NOTIFICATION,
                name="Notifications",
                status=HealthStatus.UNKNOWN,
                message="Notification service not configured.",
            )
        try:
            summary = self._notification_service.summary()
            unread = summary.total_unread

            if unread > 50:
                status = HealthStatus.DEGRADED
                msg = f"{unread} unread notifications — backlog."
            else:
                status = HealthStatus.HEALTHY
                msg = f"{unread} unread notifications."

            return SystemComponentHealth(
                component=ComponentType.NOTIFICATION,
                name="Notifications",
                status=status,
                message=msg,
                metrics={
                    "unread_count": unread,
                    "unread_by_category": dict(summary.unread_by_category),
                    "unread_by_severity": dict(summary.unread_by_severity),
                },
            )
        except Exception as e:
            logger.warning("Notification health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.NOTIFICATION,
                name="Notifications",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_metrics(self) -> SystemComponentHealth:
        if self._metrics_repository is None:
            return SystemComponentHealth(
                component=ComponentType.METRICS,
                name="Metrics Store",
                status=HealthStatus.UNKNOWN,
                message="Metrics repository not configured.",
            )
        try:
            total = self._metrics_repository.count_metrics()

            status = HealthStatus.HEALTHY
            msg = f"Metrics store: {total} records."

            return SystemComponentHealth(
                component=ComponentType.METRICS,
                name="Metrics Store",
                status=status,
                message=msg,
                metrics={
                    "total_metrics": total,
                },
            )
        except Exception as e:
            logger.warning("Metrics health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.METRICS,
                name="Metrics Store",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_audit(self) -> SystemComponentHealth:
        if self._audit_repository is None:
            return SystemComponentHealth(
                component=ComponentType.AUDIT,
                name="Audit Trail",
                status=HealthStatus.UNKNOWN,
                message="Audit repository not configured.",
            )
        try:
            total = self._audit_repository.count_records()

            status = HealthStatus.HEALTHY
            msg = f"Audit trail: {total} records."

            return SystemComponentHealth(
                component=ComponentType.AUDIT,
                name="Audit Trail",
                status=status,
                message=msg,
                metrics={
                    "audit_count": total,
                },
            )
        except Exception as e:
            logger.warning("Audit health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.AUDIT,
                name="Audit Trail",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    def _check_sse(self) -> SystemComponentHealth:
        if self._connection_manager is None:
            return SystemComponentHealth(
                component=ComponentType.SSE,
                name="SSE Streaming",
                status=HealthStatus.UNKNOWN,
                message="SSE connection manager not configured.",
            )
        try:
            active_clients = self._connection_manager.active_client_count
            event_count = self._connection_manager.event_counter

            status = HealthStatus.HEALTHY
            msg = f"SSE: {active_clients} clients connected."

            return SystemComponentHealth(
                component=ComponentType.SSE,
                name="SSE Streaming",
                status=status,
                message=msg,
                metrics={
                    "active_clients": active_clients,
                    "events_delivered": event_count,
                },
            )
        except Exception as e:
            logger.warning("SSE health check failed: %s", e)
            return SystemComponentHealth(
                component=ComponentType.SSE,
                name="SSE Streaming",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {e}",
            )

    # ------------------------------------------------------------------
    # Metric collectors for alerts
    # ------------------------------------------------------------------

    def _collect_all_metrics(self) -> Dict[str, float]:
        """Collect all metrics needed for alert evaluation."""
        metrics: Dict[str, float] = {}

        queue = self._get_queue_metrics()
        metrics["queued_count"] = queue.get("queued_count", 0)
        metrics["failed_count"] = queue.get("failed_count", 0)
        metrics["retry_count"] = queue.get("retrying_count", 0)

        worker = self._get_worker_metrics()
        metrics["active_workers"] = 1.0 if worker.get("is_running", False) else 0.0

        lock = self._get_lock_metrics()
        metrics["expired_locks"] = lock.get("expired_locks", 0)

        event = self._get_event_metrics()
        metrics["event_count"] = event.get("event_count", 0)

        notif = self._get_notification_metrics()
        metrics["unread_count"] = notif.get("unread_count", 0)

        audit = self._get_audit_metrics()
        metrics["audit_count"] = audit.get("audit_count", 0)

        return metrics

    # ------------------------------------------------------------------
    # Detailed metric getters
    # ------------------------------------------------------------------

    def _get_queue_metrics(self) -> Dict[str, Any]:
        if self._queue_engine is None:
            return {}
        try:
            m = self._queue_engine.get_queue_metrics()
            return {
                "queued_count": m.queued_count,
                "running_count": m.running_count,
                "retrying_count": m.retrying_count,
                "completed_count": m.completed_count,
                "failed_count": m.failed_count,
                "cancelled_count": m.cancelled_count,
                "oldest_queued_age_seconds": m.oldest_queued_age_seconds,
            }
        except Exception:
            return {}

    def _get_worker_metrics(self) -> Dict[str, Any]:
        if self._worker_daemon is None:
            return {}
        try:
            return {
                "is_running": getattr(self._worker_daemon, "_running", False),
                "worker_id": getattr(
                    self._worker_daemon,
                    "_worker_id",
                    getattr(self._worker_daemon, "worker_id", "unknown"),
                ),
            }
        except Exception:
            return {}

    def _get_lock_metrics(self) -> Dict[str, Any]:
        if self._lock_manager is None and self._lock_repository is None:
            return {}
        try:
            repo = self._lock_repository
            if repo is None and self._lock_manager is not None:
                repo = getattr(self._lock_manager, "_repository", None)

            active_locks = []
            if repo is not None and hasattr(repo, "list_active_locks"):
                active_locks = repo.list_active_locks()

            return {
                "active_locks": len(active_locks),
                "lock_types": [lk.lock_type.value for lk in active_locks],
            }
        except Exception:
            return {}

    def _get_event_metrics(self) -> Dict[str, Any]:
        if self._event_repository is None:
            return {}
        try:
            return {
                "event_count": self._event_repository.count_events(),
                "workflow_events": self._event_repository.count_events(category="workflow"),
                "job_events": self._event_repository.count_events(category="job"),
                "review_events": self._event_repository.count_events(category="review"),
                "lock_events": self._event_repository.count_events(category="lock"),
                "pipeline_events": self._event_repository.count_events(category="pipeline"),
            }
        except Exception:
            return {}

    def _get_notification_metrics(self) -> Dict[str, Any]:
        if self._notification_service is None:
            return {}
        try:
            summary = self._notification_service.summary()
            return {
                "unread_count": summary.total_unread,
                "unread_by_category": dict(summary.unread_by_category),
                "unread_by_severity": dict(summary.unread_by_severity),
                "recent_failures": len(summary.recent_failures),
            }
        except Exception:
            return {}

    def _get_audit_metrics(self) -> Dict[str, Any]:
        if self._audit_repository is None:
            return {}
        try:
            return {
                "audit_count": self._audit_repository.count_records(),
            }
        except Exception:
            return {}

    def _get_sse_metrics(self) -> Dict[str, Any]:
        if self._connection_manager is None:
            return {}
        try:
            return {
                "active_clients": self._connection_manager.active_client_count,
                "events_delivered": self._connection_manager.event_counter,
            }
        except Exception:
            return {}

    def _get_kpi_summary(self) -> Dict[str, Any]:
        if self._kpi_catalog is None:
            return {}
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=30)
            kpis = self._kpi_catalog.calculate_all(start=start, end=end)
            return {name: {"value": kpi.value, "unit": kpi.unit} for name, kpi in kpis.items()}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Overall status derivation
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_overall_status(
        components: List[SystemComponentHealth],
    ) -> HealthStatus:
        """Derive overall platform health from component statuses."""
        if not components:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in components]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.UNKNOWN for s in statuses):
            return HealthStatus.UNKNOWN
        return HealthStatus.HEALTHY
