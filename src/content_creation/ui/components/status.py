"""UI components for status, headers, and metric cards."""

import streamlit as st

from content_creation.ui.services.client import get_api_key


def render_header() -> None:
    """Renders the top header/status section of the application shell."""
    st.markdown("# 🚀 Editorial Content Pipeline Dashboard")
    st.markdown("---")


def render_api_health() -> None:
    """Validates and displays system environment and API credentials status."""
    st.sidebar.markdown("### 🔑 System Health")
    gemini_key = get_api_key("GEMINI_API_KEY")
    openrouter_key = get_api_key("OPENROUTER_API_KEY")

    if gemini_key:
        st.sidebar.success("Gemini API: Connected")
    else:
        st.sidebar.error("Gemini API: Key Missing")

    if openrouter_key:
        st.sidebar.success("OpenRouter Fallback: Configured")
    else:
        st.sidebar.info("OpenRouter Fallback: Optional")


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
