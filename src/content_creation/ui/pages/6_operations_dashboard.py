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

from typing import Any

from content_creation.ui.services.client import ServiceClient
from content_creation.ui.state.session import init_session_state


def _status_color(status: object) -> str:
    """Map health status to display color."""
    val = getattr(status, "value", str(status)).lower()
    return {
        "healthy": "🟢",
        "degraded": "🟡",
        "unhealthy": "🔴",
        "unknown": "⚪",
    }.get(val, "⚪")


def _status_badge(status: object) -> str:
    """Format health status as a badge string."""
    icon = _status_color(status)
    val = getattr(status, "value", str(status)).upper()
    return f"{icon} {val}"


def _render_system_health(snapshot: Any) -> None:
    """Section 1: System Health."""
    st.subheader("System Health")

    if not snapshot:
        st.info("System health information unavailable.")
        return

    st.markdown(f"**Overall Status:** {_status_badge(snapshot.overall_status)}")

    components = getattr(snapshot, "components", None)
    if components:
        cols = st.columns(min(len(components), 4))
        for i, comp in enumerate(components):
            with cols[i % len(cols)]:
                comp_status = getattr(comp, "status", None)
                st.metric(
                    label=f"{_status_color(comp_status)} {comp.name}",
                    value=getattr(comp_status, "value", str(comp_status)).upper(),
                    help=comp.message,
                )


def _render_queue_monitoring(snapshot: Any) -> None:
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


def _render_worker_monitoring(snapshot: Any) -> None:
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

    # Explain worker status when not running
    if not is_running:
        q = snapshot.queue_metrics or {}
        queued = q.get("queued_count", 0)
        running = q.get("running_count", 0)
        has_jobs = queued > 0 or running > 0

        if not has_jobs:
            st.info("ℹ️ Worker Daemon: No active workers (no jobs queued — this is normal for manual operation)")
        else:
            st.error("⚠️ Worker Daemon: No active workers but jobs are queued — pipeline may be stalled")


def _render_lock_monitoring(snapshot: Any) -> None:
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


def _render_event_monitoring(snapshot: Any) -> None:
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


def _render_notification_monitoring(snapshot: Any) -> None:
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


def _render_metrics_monitoring(snapshot: Any) -> None:
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


def _render_audit_monitoring(snapshot: Any) -> None:
    """Section 8: Audit Monitoring."""
    st.subheader("Audit Monitoring")
    am = snapshot.audit_metrics
    if not am:
        st.info("Audit trail not available.")
        return

    cols = st.columns(2)
    cols[0].metric("Total Audit Records", am.get("audit_count", 0))


def _render_alerts(snapshot: Any) -> None:
    """Render active alerts."""
    if not snapshot or not getattr(snapshot, "alerts", None):
        return

    st.subheader("Operational Alerts")
    for alert in snapshot.alerts:
        sev = getattr(alert.severity, "value", str(alert.severity)).lower()
        icon = "🔴" if sev == "critical" else "🟡"
        comp_val = getattr(alert.component, "value", str(alert.component))
        with st.expander(f"{icon} [{sev.upper()}] {alert.title}", expanded=True):
            st.markdown(f"**Message:** {alert.message}")
            st.markdown(f"**Component:** {comp_val}")
            st.markdown(f"**Recommended Action:** {alert.recommended_action}")
            if alert.metrics:
                st.json(alert.metrics)


def main() -> None:
    st.set_page_config(
        page_title="🔧 System Health",
        page_icon="📊",
        layout="wide",
    )
    init_session_state()

    st.title("📊 Operations Dashboard")
    st.caption(f"Last refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    client = ServiceClient()
    snapshot = client.get_operations_snapshot()

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
