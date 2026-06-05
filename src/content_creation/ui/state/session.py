"""Session state helpers for the Streamlit UI application."""

import streamlit as st
from typing import Any, Dict, Optional


def init_session_state() -> None:
    """Initializes default values for UI session state keys."""
    defaults = {
        "selected_topic_id": None,
        "selected_brief_id": None,
        "filters": {"status": "all", "category": "all"},
        "nc_page": 1,
        "notification_unread_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_selected_topic_id() -> Optional[str]:
    """Retrieves the currently selected topic ID from session state."""
    init_session_state()
    return st.session_state.get("selected_topic_id")


def set_selected_topic_id(topic_id: Optional[str]) -> None:
    """Sets the currently selected topic ID in session state."""
    st.session_state["selected_topic_id"] = topic_id


def get_selected_brief_id() -> Optional[str]:
    """Retrieves the currently selected brief ID from session state."""
    init_session_state()
    return st.session_state.get("selected_brief_id")


def set_selected_brief_id(brief_id: Optional[str]) -> None:
    """Sets the currently selected brief ID in session state."""
    st.session_state["selected_brief_id"] = brief_id


def get_filters() -> Dict[str, Any]:
    """Retrieves the active UI filters dictionary."""
    init_session_state()
    return st.session_state.get("filters", {})


def set_filter(key: str, value: Any) -> None:
    """Updates a single filter key in the session state filters dictionary."""
    init_session_state()
    filters = st.session_state.get("filters", {})
    filters[key] = value
    st.session_state["filters"] = filters
