import streamlit as st


def render_header() -> None:
    """Renders the top header/status section of the application shell."""
    st.markdown("# 🚀 Editorial Content Pipeline Dashboard")
    st.markdown("---")


def render_api_health(is_available: bool) -> None:
    """Displays generic system environment and generation availability status."""
    st.sidebar.markdown("### 🔑 System Health")

    if is_available:
        st.sidebar.success("Generation Service: Available")
    else:
        st.sidebar.error("Generation Service: Unavailable")


def render_metric_cards(metric_counts: dict) -> None:
    """Renders the top pipeline stages metric summary cards.

    Expects counts resolved through the UI service adapter.
    """
    st.markdown("### 📊 Pipeline Queue Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Staged Topics", metric_counts.get("staged", 0))
    col2.metric("Scored Topics", metric_counts.get("scored", 0))
    col3.metric("Briefs", metric_counts.get("briefs", 0))
    col4.metric("Storyboards", metric_counts.get("storyboards", 0))
    col5.metric("Topic Manifests", metric_counts.get("manifests", 0))


def format_review_status(status) -> str:
    """Format review status into a human-readable operator-facing label.

    - ReviewStatus.APPROVED / "approved" / "ReviewStatus.APPROVED" -> "Approved"
    - ReviewStatus.REJECTED / "rejected" / "ReviewStatus.REJECTED" -> "Rejected"
    - ReviewStatus.NEEDS_REVIEW / "needs_review" / "ReviewStatus.NEEDS_REVIEW" -> "Needs review"
    - ReviewStatus.DRAFT / "draft" / "ReviewStatus.DRAFT" -> "Draft"
    - ReviewStatus.REVIEWED / "reviewed" / "ReviewStatus.REVIEWED" -> "Reviewed"
    """
    if status is None:
        return "Unknown"

    val = status.value if hasattr(status, "value") else str(status)

    if val.startswith("ReviewStatus."):
        val = val.split("ReviewStatus.")[1]

    val_clean = val.strip().lower()

    mapping = {
        "draft": "Draft",
        "needs_review": "Needs review",
        "reviewed": "Reviewed",
        "approved": "Approved",
        "rejected": "Rejected",
    }

    if val_clean in mapping:
        return mapping[val_clean]

    if "_" in val:
        return val.replace("_", " ").capitalize()
    return val.capitalize()


def format_timestamp(ts) -> str:
    """Format an ISO timestamp or datetime object into readable operator-facing text.

    Examples:
    - datetime(2026, 5, 19, 11, 11, 24, tzinfo=timezone.utc) -> "May 19, 2026, 11:11 AM UTC"
    - "2026-05-19T11:11:24.481514+00:00" -> "May 19, 2026, 11:11 AM UTC"
    - "2026-05-19" -> "May 19, 2026"
    - None / malformed -> "Not available"
    """
    if not ts:
        return "Not available"

    from datetime import datetime, date

    # Note: datetime is a subclass of date, so check datetime first
    if isinstance(ts, datetime):
        if ts.tzinfo:
            tz_name = ts.tzname() or ts.strftime("%z")
            if tz_name in ("UTC", "+0000", "GMT", "Coordinated Universal Time", "UTC+00:00"):
                tz_display = "UTC"
            elif tz_name.startswith("UTC+") or tz_name.startswith("UTC-"):
                tz_display = tz_name[3:]
            elif tz_name.startswith("+") or tz_name.startswith("-"):
                if len(tz_name) == 5:
                    tz_display = f"{tz_name[:3]}:{tz_name[3:]}"
                else:
                    tz_display = tz_name
            else:
                tz_display = tz_name
            return ts.strftime(f"%B %d, %Y, %I:%M %p {tz_display}")
        else:
            return ts.strftime("%B %d, %Y, %I:%M %p")

    if isinstance(ts, date):
        return ts.strftime("%B %d, %Y")

    if not isinstance(ts, str):
        ts = str(ts)

    ts_clean = ts.strip()
    if not ts_clean or ts_clean.lower() in ("none", "n/a", "null", "undefined"):
        return "Not available"

    try:
        val = ts_clean
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"

        # If it's a date only (e.g. YYYY-MM-DD)
        if len(val) == 10 and val.count("-") == 2:
            dt = datetime.strptime(val, "%Y-%m-%d").date()
            return dt.strftime("%B %d, %Y")

        dt = datetime.fromisoformat(val)
        return format_timestamp(dt)
    except Exception:
        return ts_clean


