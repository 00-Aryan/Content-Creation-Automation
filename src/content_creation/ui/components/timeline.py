"""Reusable timeline component for displaying event history.

UI → TimelineService → EventRepository
No direct repository access from UI.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

import streamlit as st

from content_creation.events.store.models import EventRecord
from content_creation.events.store.timeline import EventTimelineService


def render_event_timeline(
    timeline_service: EventTimelineService,
    title: str = "Event Timeline",
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    max_events: int = 50,
) -> None:
    """Render an event timeline with filtering and pagination.

    Args:
        timeline_service: Service for querying event history.
        title: Section title.
        category: Optional category filter.
        entity_type: Optional entity type filter.
        entity_id: Optional entity ID filter.
        max_events: Maximum events to display.
    """
    st.subheader(title)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_category = st.selectbox(
            "Category",
            [None, "workflow", "review", "job", "lock", "recovery", "pipeline"],
            key=f"timeline_cat_{title}",
        )
    with col2:
        filter_entity = st.text_input(
            "Entity Type",
            value=entity_type or "",
            key=f"timeline_entity_{title}",
        )
    with col3:
        filter_search = st.text_input(
            "Search",
            value="",
            key=f"timeline_search_{title}",
        )

    # Query events
    if entity_type and entity_id:
        events = timeline_service.entity_history(entity_type, entity_id, limit=max_events)
    elif filter_category:
        events = timeline_service.recent_events(
            category=filter_category, page_size=max_events
        ).events
    else:
        events = timeline_service.recent_events(page_size=max_events).events

    # Apply search filter
    if filter_search:
        query_lower = filter_search.lower()
        events = [
            e
            for e in events
            if query_lower in e.event_name.lower()
            or query_lower in e.entity_type.lower()
            or query_lower in e.source.lower()
        ]

    if not events:
        st.info("No events found.")
        return

    # Render timeline
    for event in events:
        _render_event_row(event)


def _render_event_row(event: EventRecord) -> None:
    """Render a single event row in the timeline."""
    # Color coding by category
    category_colors = {
        "workflow": "#2196F3",
        "review": "#9C27B0",
        "job": "#FF9800",
        "lock": "#607D8B",
        "recovery": "#F44336",
        "pipeline": "#4CAF50",
    }
    color = category_colors.get(event.category, "#757575")

    # Format timestamp
    ts = event.created_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    time_str = ts.strftime("%Y-%m-%d %H:%M:%S")

    # Entity info
    entity_info = f"{event.entity_type}" if event.entity_type else ""
    if event.entity_id:
        entity_info += f" ({event.entity_id[:8]}...)"

    st.markdown(
        f"""<div style="
            padding: 8px 12px;
            margin: 4px 0;
            border-left: 3px solid {color};
            background: rgba(0,0,0,0.02);
            border-radius: 0 4px 4px 0;
            font-size: 13px;
        ">
            <span style="color: #888;">{time_str}</span>
            &nbsp;|&nbsp;
            <span style="color: {color}; font-weight: bold;">{event.event_name}</span>
            &nbsp;|&nbsp;
            <span>{event.source}</span>
            {f'&nbsp;|&nbsp;<span>{entity_info}</span>' if entity_info else ''}
            {f'&nbsp;|&nbsp;<code style="font-size:11px;">{event.correlation_id[:8]}...</code>' if event.correlation_id else ''}
        </div>""",
        unsafe_allow_html=True,
    )


def render_workflow_timeline(
    timeline_service: EventTimelineService,
    topic_id: str,
) -> None:
    """Render timeline for a specific workflow topic."""
    render_event_timeline(
        timeline_service,
        title=f"Workflow Timeline — {topic_id[:16]}...",
        entity_type="brief",
        entity_id=topic_id,
    )


def render_job_timeline(
    timeline_service: EventTimelineService,
    job_id: Optional[str] = None,
) -> None:
    """Render timeline for job events."""
    render_event_timeline(
        timeline_service,
        title="Job Timeline",
        category="job",
    )


def render_pipeline_timeline(
    timeline_service: EventTimelineService,
) -> None:
    """Render timeline for pipeline events."""
    render_event_timeline(
        timeline_service,
        title="Pipeline Timeline",
        category="pipeline",
    )
