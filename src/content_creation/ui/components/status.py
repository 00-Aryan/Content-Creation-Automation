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

