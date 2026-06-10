"""Operations Dashboard — unified platform observability view.

Sections:
1. System Health — overall indicator + component cards
2. Queue Monitoring — pending, running, retries, failures
3. Worker Monitoring — active workers, heartbeat status
4. Lock Monitoring — active locks, expired locks, contention
5. Event Monitoring — events/hour, replay activity
6. Notification Monitoring — unread, delivery activity
7. Metrics Monitoring — KPI summaries
8. Audit Monitoring — recent incidents, compliance alerts
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st

src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from content_creation.ui.state.session import init_session_state
from content_creation.platform.observability.health import (
    HealthStatus,
    ComponentType,
    DashboardSnapshot,
)


def _status_color(status: HealthStatus) -> str:
    """Map health status to display color."""
    return {
        HealthStatus.HEALTHY: "🟢",
        HealthStatus.DEGRADED: "🟡",
        HealthStatus.UNHEALTHY: "🔴",
        HealthStatus.UNKNOWN: "⚪",
    }.get(status, "⚪")


def _status_badge(status: HealthStatus) -> str:
    """Format health status as a badge string."""
    icon = _status_color(status)
    return f"{icon} {status.value.upper()}"


def _build_snapshot() -> DashboardSnapshot:
    """Build a DashboardSnapshot using available subsystems."""
    try:
        from content_creation.platform.observability.service import ObservabilityService
        from content_creation.jobs.queue_engine import QueueEngine
        from content_creation.jobs.lock_manager import LockManager
        from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository
        from content_creation.jobs.recovery_supervisor import RecoverySupervisor
        from content_creation.events.store.sqlite_repository import SQLiteEventRepository
        from content_creation.notifications.service import NotificationService
        from content_creation.notifications.sqlite_repository import SQLiteNotificationRepository
        from content_creation.metrics.sqlite_repository import SQLiteMetricRepository
        from content_creation.metrics.kpi import KPICatalog
        from content_creation.metrics.telemetry import TelemetryService
        from content_creation.audit.sqlite_repository import SQLiteAuditRepository
        from content_creation.audit.compliance import ComplianceReportService

        import sqlite3
        from pathlib import Path

        base_dir = Path.cwd()
        data_dir = base_dir / "data"
        data_dir.mkdir(exist_ok=True)

        def _open_db(name: str) -> sqlite3.Connection:
            db_path = data_dir / name
            conn = sqlite3.connect(str(db_path), timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            return conn

        queue_engine = None
        lock_manager = None
        lock_repo = None
        event_repo = None
        notification_svc = None
        metrics_repo = None
        kpi_catalog = None
        telemetry_svc = None
        audit_repo = None
        compliance_svc = None
        connection_mgr = None

        job_conn = None
        lock_conn = None
        event_conn = None
        notif_conn = None
        metrics_conn = None
        audit_conn = None

        try:
            try:
                from content_creation.jobs.sqlite_repository import SQLiteJobRepository
                from content_creation.jobs.schema import create_job_schema

                job_conn = _open_db("jobs.db")
                create_job_schema(job_conn)
                job_repo = SQLiteJobRepository(job_conn)

                lock_conn = _open_db("locks.db")
                from content_creation.jobs.schema import create_lock_schema
                create_lock_schema(lock_conn)
                lock_repo = SQLiteLockRepository(lock_conn)
                lock_manager = LockManager(repository=lock_repo)

                queue_engine = QueueEngine(repository=job_repo, lock_manager=lock_manager)
            except Exception as e:
                st.warning(f"Failed to initialize Job Queue. ({type(e).__name__})")

            try:
                from content_creation.events.store.schema import create_event_store_schema
                event_conn = _open_db("events.db")
                create_event_store_schema(event_conn)
                event_repo = SQLiteEventRepository(str(data_dir / "events.db"))
            except Exception as e:
                st.warning(f"Failed to initialize Event Store. ({type(e).__name__})")

            try:
                from content_creation.notifications.schema import create_notification_schema
                notif_conn = _open_db("notifications.db")
                create_notification_schema(notif_conn)
                notif_repo = SQLiteNotificationRepository(notif_conn)
                notification_svc = NotificationService(repository=notif_repo)
            except Exception as e:
                st.warning(f"Failed to initialize Notification Service. ({type(e).__name__})")

            try:
                from content_creation.metrics.schema import create_metrics_schema
                metrics_conn = _open_db("metrics.db")
                create_metrics_schema(metrics_conn)
                metrics_repo = SQLiteMetricRepository(str(data_dir / "metrics.db"))
                kpi_catalog = KPICatalog(repository=metrics_repo)
                telemetry_svc = TelemetryService(metrics_repository=metrics_repo, event_repository=event_repo)
            except Exception as e:
                st.warning(f"Failed to initialize Metrics Repository. ({type(e).__name__})")

            try:
                from content_creation.audit.schema import create_audit_schema
                audit_conn = _open_db("audit.db")
                create_audit_schema(audit_conn)
                audit_repo = SQLiteAuditRepository(str(data_dir / "audit.db"))
                compliance_svc = ComplianceReportService(repository=audit_repo)
            except Exception as e:
                st.warning(f"Failed to initialize Audit Repository. ({type(e).__name__})")

            try:
                from content_creation.notifications.streaming.connection_manager import ConnectionManager
                connection_mgr = ConnectionManager()
            except Exception as e:
                st.warning(f"Failed to initialize Connection Manager. ({type(e).__name__})")

            service = ObservabilityService(
                queue_engine=queue_engine,
                lock_manager=lock_manager,
                lock_repository=lock_repo,
                event_repository=event_repo,
                notification_service=notification_svc,
                connection_manager=connection_mgr,
                metrics_repository=metrics_repo,
                kpi_catalog=kpi_catalog,
                telemetry_service=telemetry_svc,
                audit_repository=audit_repo,
                compliance_service=compliance_svc,
            )
            return service.snapshot()
        finally:
            for conn in [job_conn, lock_conn, event_conn, notif_conn, metrics_conn, audit_conn]:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception as e:
                        st.warning(f"Failed to close database connection. ({type(e).__name__})")
            for r in [event_repo, metrics_repo, audit_repo]:
                if r is not None:
                    try:
                        r.close()
                    except Exception as e:
                        st.warning(f"Failed to close repository. ({type(e).__name__})")

    except Exception as e:
        from content_creation.platform.observability.health import (
            SystemComponentHealth,
            ComponentType,
        )
        return DashboardSnapshot(
            overall_status=HealthStatus.UNKNOWN,
            components=[
                SystemComponentHealth(
                    component=ComponentType.QUEUE,
                    name="System",
                    status=HealthStatus.UNKNOWN,
                    message=f"Failed to build snapshot: {e}",
                )
            ],
        )


def _render_system_health(snapshot: DashboardSnapshot) -> None:
    """Section 1: System Health."""
    st.subheader("System Health")

    st.markdown(f"**Overall Status:** {_status_badge(snapshot.overall_status)}")

    if snapshot.components:
        cols = st.columns(min(len(snapshot.components), 4))
        for i, comp in enumerate(snapshot.components):
            with cols[i % len(cols)]:
                st.metric(
                    label=f"{_status_color(comp.status)} {comp.name}",
                    value=comp.status.value.upper(),
                    help=comp.message,
                )


def _render_queue_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 2: Queue Monitoring."""
    st.subheader("Queue Monitoring")
    q = snapshot.queue_metrics
    if not q:
        st.info("Queue engine not available.")
        return

    cols = st.columns(5)
    cols[0].metric("Pending", q.get("queued_count", 0))
    cols[1].metric("Running", q.get("running_count", 0))
    cols[2].metric("Retrying", q.get("retrying_count", 0))
    cols[3].metric("Completed", q.get("completed_count", 0))
    cols[4].metric("Failed", q.get("failed_count", 0))


def _render_worker_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 3: Worker Monitoring."""
    st.subheader("Worker Monitoring")
    w = snapshot.worker_metrics
    if not w:
        st.info("Worker daemon not available.")
        return

    cols = st.columns(3)
    is_running = w.get("is_running", False)
    cols[0].metric("Status", "Running" if is_running else "Stopped")
    cols[1].metric("Worker ID", w.get("worker_id", "unknown"))


def _render_lock_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 4: Lock Monitoring."""
    st.subheader("Lock Monitoring")
    lk = snapshot.lock_metrics
    if not lk:
        st.info("Lock manager not available.")
        return

    cols = st.columns(3)
    cols[0].metric("Active Locks", lk.get("active_locks", 0))

    lock_types = lk.get("lock_types", [])
    if lock_types:
        from collections import Counter
        type_counts = Counter(lock_types)
        cols[1].metric("Lock Types", ", ".join(f"{k}: {v}" for k, v in type_counts.items()))


def _render_event_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 5: Event Monitoring."""
    st.subheader("Event Monitoring")
    ev = snapshot.event_metrics
    if not ev:
        st.info("Event store not available.")
        return

    cols = st.columns(3)
    cols[0].metric("Total Events", ev.get("event_count", 0))
    cols[1].metric("Workflow", ev.get("workflow_events", 0))
    cols[2].metric("Job Events", ev.get("job_events", 0))

    cols2 = st.columns(3)
    cols2[0].metric("Review", ev.get("review_events", 0))
    cols2[1].metric("Lock", ev.get("lock_events", 0))
    cols2[2].metric("Pipeline", ev.get("pipeline_events", 0))


def _render_notification_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 6: Notification Monitoring."""
    st.subheader("Notification Monitoring")
    nm = snapshot.notification_metrics
    if not nm:
        st.info("Notification service not available.")
        return

    cols = st.columns(3)
    cols[0].metric("Unread", nm.get("unread_count", 0))
    cols[1].metric("Recent Failures", nm.get("recent_failures", 0))

    by_cat = nm.get("unread_by_category", {})
    if by_cat:
        st.caption("Unread by Category:")
        cat_cols = st.columns(len(by_cat))
        for i, (cat, count) in enumerate(by_cat.items()):
            cat_cols[i].metric(cat, count)


def _render_metrics_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 7: Metrics / KPI Monitoring."""
    st.subheader("Metrics / KPIs")
    kpis = snapshot.kpi_summary
    if not kpis:
        st.info("Metrics store not available.")
        return

    workflow_kpis = {k: v for k, v in kpis.items() if k in [
        "briefs_generated", "storyboards_generated", "assets_generated",
        "approval_rate", "rejection_rate",
    ]}
    job_kpis = {k: v for k, v in kpis.items() if k in [
        "jobs_started", "jobs_completed", "jobs_failed", "job_success_rate",
        "job_retries", "average_job_runtime",
    ]}
    system_kpis = {k: v for k, v in kpis.items() if k in [
        "lock_contentions", "zombie_recoveries", "stale_lock_expirations",
    ]}

    if workflow_kpis:
        st.markdown("**Workflow KPIs:**")
        cols = st.columns(min(len(workflow_kpis), 5))
        for i, (name, kpi) in enumerate(workflow_kpis.items()):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{kpi['value']:.1f} {kpi['unit']}")

    if job_kpis:
        st.markdown("**Job KPIs:**")
        cols = st.columns(min(len(job_kpis), 6))
        for i, (name, kpi) in enumerate(job_kpis.items()):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{kpi['value']:.1f} {kpi['unit']}")

    if system_kpis:
        st.markdown("**System KPIs:**")
        cols = st.columns(min(len(system_kpis), 3))
        for i, (name, kpi) in enumerate(system_kpis.items()):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{kpi['value']:.1f} {kpi['unit']}")


def _render_audit_monitoring(snapshot: DashboardSnapshot) -> None:
    """Section 8: Audit Monitoring."""
    st.subheader("Audit Monitoring")
    am = snapshot.audit_metrics
    if not am:
        st.info("Audit trail not available.")
        return

    cols = st.columns(2)
    cols[0].metric("Total Audit Records", am.get("audit_count", 0))


def _render_alerts(snapshot: DashboardSnapshot) -> None:
    """Render active alerts."""
    if not snapshot.alerts:
        return

    st.subheader("Operational Alerts")
    for alert in snapshot.alerts:
        icon = "🔴" if alert.severity.value == "critical" else "🟡"
        with st.expander(f"{icon} [{alert.severity.value.upper()}] {alert.title}", expanded=True):
            st.markdown(f"**Message:** {alert.message}")
            st.markdown(f"**Component:** {alert.component.value}")
            st.markdown(f"**Recommended Action:** {alert.recommended_action}")
            if alert.metrics:
                st.json(alert.metrics)


def main() -> None:
    st.set_page_config(
        page_title="Operations Dashboard",
        page_icon="📊",
        layout="wide",
    )
    init_session_state()

    st.title("📊 Operations Dashboard")
    st.caption(f"Last refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    snapshot = _build_snapshot()

    _render_system_health(snapshot)
    st.divider()

    _render_alerts(snapshot)

    col1, col2 = st.columns(2)
    with col1:
        _render_queue_monitoring(snapshot)
    with col2:
        _render_worker_monitoring(snapshot)

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        _render_lock_monitoring(snapshot)
    with col4:
        _render_event_monitoring(snapshot)

    st.divider()

    col5, col6 = st.columns(2)
    with col5:
        _render_notification_monitoring(snapshot)
    with col6:
        _render_audit_monitoring(snapshot)

    st.divider()

    _render_metrics_monitoring(snapshot)


if __name__ == "__main__":
    main()
