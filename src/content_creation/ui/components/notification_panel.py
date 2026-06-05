"""Reusable Notification Center component for Streamlit UI.

Service-driven rendering. No business logic in UI.
"""

import streamlit as st
from typing import List, Optional

from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.service import NotificationService


_SEVERITY_ICONS = {
    NotificationSeverity.INFO: "ℹ️",
    NotificationSeverity.SUCCESS: "✅",
    NotificationSeverity.WARNING: "⚠️",
    NotificationSeverity.ERROR: "🔴",
}

_CATEGORY_ICONS = {
    NotificationCategory.WORKFLOW: "⚙️",
    NotificationCategory.REVIEW: "📝",
    NotificationCategory.JOB: "🔧",
    NotificationCategory.SYSTEM: "🖥️",
}

_CATEGORY_LABELS = {
    NotificationCategory.WORKFLOW: "Workflow",
    NotificationCategory.REVIEW: "Review",
    NotificationCategory.JOB: "Job",
    NotificationCategory.SYSTEM: "System",
}


def render_notification_badge(unread_count: int) -> None:
    """Render the unread notification count badge in the sidebar."""
    if unread_count > 0:
        st.sidebar.markdown(
            f"### 🔔 Notifications\n"
            f"**{unread_count}** unread notification{'s' if unread_count != 1 else ''}"
        )
    else:
        st.sidebar.markdown("### 🔔 Notifications\nNo unread notifications")


def render_notification_summary_panel(
    service: NotificationService,
) -> None:
    """Render the notification summary panel on the dashboard."""
    summary = service.summary()

    st.markdown("### 🔔 Notification Summary")

    if summary.total_unread == 0:
        st.info("No unread notifications.")
        return

    # Unread by category
    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    for i, cat in enumerate(NotificationCategory):
        count = summary.unread_by_category.get(cat.value, 0)
        icon = _CATEGORY_ICONS.get(cat, "")
        label = _CATEGORY_LABELS.get(cat, cat.value)
        cols[i].metric(f"{icon} {label}", count)

    # Unread by severity
    severity_counts = summary.unread_by_severity
    if severity_counts:
        sev_parts = []
        for sev in NotificationSeverity:
            count = severity_counts.get(sev.value, 0)
            if count > 0:
                icon = _SEVERITY_ICONS.get(sev, "")
                sev_parts.append(f"{icon} {sev.value}: **{count}**")
        if sev_parts:
            st.markdown("Severity breakdown: " + " | ".join(sev_parts))

    # Recent failures
    if summary.recent_failures:
        st.markdown("#### 🔴 Recent Failures")
        for n in summary.recent_failures[:3]:
            _render_notification_row(n, show_actions=False)

    # Recent approvals
    if summary.recent_approvals:
        st.markdown("#### ✅ Recent Approvals")
        for n in summary.recent_approvals[:3]:
            _render_notification_row(n, show_actions=False)

    # Recent completions
    if summary.recent_completions:
        st.markdown("#### 🔧 Recent Completions")
        for n in summary.recent_completions[:3]:
            _render_notification_row(n, show_actions=False)


def render_notification_center(
    service: NotificationService,
    page_size: int = 20,
) -> None:
    """Render the full notification center with filtering, pagination, and actions."""
    st.markdown("### 🔔 Notification Center")

    # Filter controls
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        status_options = ["All", "Unread", "Read", "Archived"]
        selected_status = st.selectbox("Status", status_options, key="nc_status")

    with col_filter2:
        category_options = ["All"] + [_CATEGORY_LABELS[c] for c in NotificationCategory]
        selected_category = st.selectbox("Category", category_options, key="nc_category")

    with col_filter3:
        severity_options = ["All", "Info", "Success", "Warning", "Error"]
        selected_severity = st.selectbox("Severity", severity_options, key="nc_severity")

    # Map selections to enum values
    status_filter = None
    if selected_status == "Unread":
        status_filter = NotificationStatus.UNREAD
    elif selected_status == "Read":
        status_filter = NotificationStatus.READ
    elif selected_status == "Archived":
        status_filter = NotificationStatus.ARCHIVED

    category_filter = None
    for cat in NotificationCategory:
        if selected_category == _CATEGORY_LABELS[cat]:
            category_filter = cat
            break

    severity_filter = None
    for sev in NotificationSeverity:
        if selected_severity.lower() == sev.value.lower():
            severity_filter = sev
            break

    from content_creation.notifications.query import (
        NotificationFilter,
        NotificationQuery,
    )

    nfilter = NotificationFilter(
        status=status_filter,
        category=category_filter,
        severity=severity_filter,
    )

    # Pagination state
    if "nc_page" not in st.session_state:
        st.session_state.nc_page = 1

    query = NotificationQuery(
        filter=nfilter,
        page=st.session_state.nc_page,
        page_size=page_size,
    )

    page = service.query(query)

    # Action buttons
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("Mark All Read", key="nc_mark_all_read"):
            count = service.mark_all_read()
            if count > 0:
                st.success(f"Marked {count} notifications as read")
                st.rerun()
    with action_col2:
        if st.button("Archive All Read", key="nc_archive_all_read"):
            count = service.archive_all_read()
            if count > 0:
                st.success(f"Archived {count} read notifications")
                st.rerun()

    # Notification list
    if not page.notifications:
        st.info("No notifications match the current filters.")
    else:
        for notification in page.notifications:
            _render_notification_row(notification, service=service)

        # Pagination controls
        st.markdown("---")
        pag_col1, pag_col2, pag_info, pag_col3, pag_col4 = st.columns([1, 1, 2, 1, 1])

        with pag_info:
            st.caption(
                f"Page {page.page} of {page.total_pages} "
                f"({page.total_count} total)"
            )

        with pag_col1:
            if page.has_previous:
                if st.button("← Previous", key="nc_prev"):
                    st.session_state.nc_page -= 1
                    st.rerun()

        with pag_col4:
            if page.has_next:
                if st.button("Next →", key="nc_next"):
                    st.session_state.nc_page += 1
                    st.rerun()


def _render_notification_row(
    notification: Notification,
    service: Optional[NotificationService] = None,
    show_actions: bool = True,
) -> None:
    """Render a single notification row."""
    icon = _SEVERITY_ICONS.get(notification.severity, "")
    cat_icon = _CATEGORY_ICONS.get(notification.category, "")
    cat_label = _CATEGORY_LABELS.get(notification.category, notification.category.value)

    is_unread = notification.status == NotificationStatus.UNREAD
    title_style = "**" if is_unread else ""

    with st.container():
        cols = st.columns([4, 2, 1] if show_actions else [5, 2])

        with cols[0]:
            st.markdown(
                f"{icon} {cat_icon} {title_style}{notification.title}{title_style}"
            )
            st.caption(notification.message)

        with cols[1]:
            st.caption(f"{cat_label} • {notification.timestamp.strftime('%Y-%m-%d %H:%M')}")

        if show_actions and service is not None:
            with cols[2]:
                action_cols = st.columns(2)
                with action_cols[0]:
                    if notification.status != NotificationStatus.UNREAD:
                        pass
                    elif st.button("✓", key=f"read_{notification.notification_id}", help="Mark as read"):
                        service.mark_read(notification.notification_id)
                        st.rerun()
                with action_cols[1]:
                    if st.button("📦", key=f"archive_{notification.notification_id}", help="Archive"):
                        service.archive(notification.notification_id)
                        st.rerun()


def render_inline_notification(message: str, severity: str = "success") -> None:
    """Render an inline notification banner for action feedback.

    Used after review decisions, generation completions, etc.
    """
    if severity == "success":
        st.success(message)
    elif severity == "warning":
        st.warning(message)
    elif severity == "error":
        st.error(message)
    else:
        st.info(message)
