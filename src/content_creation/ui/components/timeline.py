"""Reusable timeline component for displaying event history.

UI -> ServiceClient -> Application/EventStore
No direct repository or event store access from UI.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional

import streamlit as st


def render_event_timeline(
    client: Any = None,
    title: str = "Event Timeline",
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    max_events: int = 50,
    events: Optional[List[Any]] = None,
) -> None:
    """Render an event timeline with filtering and pagination.

    Args:
        client: ServiceClient or service providing get_event_timeline().
        title: Section title.
        category: Optional category filter.
        entity_type: Optional entity type filter.
        entity_id: Optional entity ID filter.
        max_events: Maximum events to display.
        events: Optional pre-fetched event list.
    """
    st.subheader(title)

    # Filters
    col1, col2, col3 = st.columns(3)
    categories = [None, "workflow", "review", "job", "lock", "recovery", "pipeline"]
    default_cat_idx = categories.index(category) if category in categories else 0
    with col1:
        filter_category = st.selectbox(
            "Category",
            categories,
            index=default_cat_idx,
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

    # Query events if not passed directly
    if events is None:
        if client is not None and hasattr(client, "get_event_timeline"):
            events = client.get_event_timeline(
                entity_type=filter_entity or None,
                entity_id=entity_id or None,
                category=filter_category or None,
                limit=max_events,
            )
        elif client is not None and hasattr(client, "entity_history"):
            if filter_entity and entity_id:
                events = client.entity_history(filter_entity, entity_id, limit=max_events)
            elif filter_category:
                events = client.recent_events(category=filter_category, page_size=max_events).events
            else:
                events = client.recent_events(page_size=max_events).events
        else:
            events = []

    # Apply search filter
    if filter_search and events:
        query_lower = filter_search.lower()
        events = [
            e
            for e in events
            if query_lower in getattr(e, "event_name", "").lower()
            or query_lower in getattr(e, "entity_type", "").lower()
            or query_lower in getattr(e, "source", "").lower()
        ]

    if not events:
        st.info("No events found.")
        return

    # Render timeline
    for event in events:
        _render_event_row(event)


def _render_event_row(event: Any) -> None:
    """Render a single event row in the timeline."""
    category_colors = {
        "workflow": "#2196F3",
        "review": "#9C27B0",
        "job": "#FF9800",
        "lock": "#607D8B",
        "recovery": "#F44336",
        "pipeline": "#4CAF50",
    }
    category = getattr(event, "category", "") or ""
    color = category_colors.get(category, "#757575")

    ts = getattr(event, "created_at", None)
    if ts is None:
        ts = datetime.now(timezone.utc)
    elif isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except ValueError:
            ts = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    time_str = ts.strftime("%Y-%m-%d %H:%M:%S")

    entity_type = getattr(event, "entity_type", "") or ""
    entity_id = getattr(event, "entity_id", "") or ""
    entity_info = f"{entity_type}" if entity_type else ""
    if entity_id:
        entity_info += f" ({entity_id[:8]}...)"

    event_name = getattr(event, "event_name", "") or ""
    source = getattr(event, "source", "") or ""
    correlation_id = getattr(event, "correlation_id", "") or ""

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
            <span style="color: {color}; font-weight: bold;">{event_name}</span>
            &nbsp;|&nbsp;
            <span>{source}</span>
            {f'&nbsp;|&nbsp;<span>{entity_info}</span>' if entity_info else ''}
            {f'&nbsp;|&nbsp;<code style="font-size:11px;">{correlation_id[:8]}...</code>' if correlation_id else ''}
        </div>""",
        unsafe_allow_html=True,
    )


def render_workflow_timeline(
    client: Any,
    topic_id: str,
) -> None:
    """Render timeline for a specific workflow topic."""
    render_event_timeline(
        client,
        title=f"Workflow Timeline — {topic_id[:16]}...",
        entity_type="brief",
        entity_id=topic_id,
    )


def render_job_timeline(
    client: Any,
    job_id: Optional[str] = None,
) -> None:
    """Render timeline for job events."""
    render_event_timeline(
        client,
        title="Job Timeline",
        category="job",
        entity_type="job" if job_id else None,
        entity_id=job_id,
    )


def render_pipeline_timeline(
    client: Any,
) -> None:
    """Render timeline for pipeline events."""
    render_event_timeline(
        client,
        title="Pipeline Timeline",
        category="pipeline",
    )

