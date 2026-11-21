"""Deprecated SSE client component.

Replaced by native Streamlit fragment polling (@st.fragment(run_every='5s'))
in src/content_creation/ui/components/notification_panel.py per ADR-001.
"""

import warnings
import streamlit as st


def render_sse_client(sse_port: int = 8502) -> None:
    """Deprecated: no-op shim for backwards compatibility.

    Native fragment polling in notification_panel.py renders SSE client obsolete.
    """
    warnings.warn(
        "render_sse_client is deprecated and replaced by native Streamlit @st.fragment polling.",
        DeprecationWarning,
        stacklevel=2,
    )


def render_notification_badge_live(
    unread_count: int,
    sse_port: int = 8502,
) -> None:
    """Deprecated: redirects to native notification badge rendering."""
    warnings.warn(
        "render_notification_badge_live is deprecated. Use render_notification_badge_fragment.",
        DeprecationWarning,
        stacklevel=2,
    )
    from content_creation.ui.components.notification_panel import render_notification_badge

    render_notification_badge(unread_count)
