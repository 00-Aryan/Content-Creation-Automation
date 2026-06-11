"""Main Dashboard and entrypoint for the Content Creation Pipeline Streamlit App."""

from dotenv import load_dotenv

load_dotenv()  # Load .env file so GEMINI_API_KEY and others are available

import sys
from pathlib import Path

import streamlit as st

# Ensure the project src directory is in Python path when running streamlit directly
src_dir = str(Path(__file__).resolve().parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from content_creation.ui.components.status import render_header, render_api_health, render_metric_cards
from content_creation.ui.components.notification_panel import (
    render_notification_badge,
    render_notification_center,
    render_notification_summary_panel,
)
from content_creation.ui.components.sse_client import render_sse_client, render_notification_badge_live
from content_creation.ui.services.client import ServiceClient
from content_creation.ui.state.session import init_session_state


def main() -> None:
    # 1. Setup Streamlit Page layout
    st.set_page_config(
        page_title="Editorial Content Pipeline Dashboard",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 2. Init UI State and resolve client context
    init_session_state()
    client = ServiceClient()
    
    # 3. Sidebar status checking
    render_api_health(client.is_generation_available())

    # 4. SSE client connection (real-time updates)
    try:
        render_sse_client(sse_port=client.sse_port)
    except Exception:
        pass

    # 5. Sidebar notification badge (live via SSE)
    try:
        unread_count = client.get_notification_unread_count()
        st.session_state["notification_unread_count"] = unread_count
        render_notification_badge_live(unread_count, sse_port=client.sse_port)
    except Exception:
        render_notification_badge(0)
    
    # 6. Render main layout
    render_header()
    try:
        render_metric_cards(client.get_metric_counts())
    except Exception as e:
        st.error(f"Error querying pipeline metrics: {e}")
        render_metric_cards({})

    # 6. Notification Summary Panel
    try:
        render_notification_summary_panel(client.notification_service)
    except Exception as e:
        st.warning(f"Notification summary unavailable: {e}")
    
    st.markdown("---")
    st.markdown("### 🎛️ E2E Pipeline Orchestration")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(
            "Click below to trigger the entire pipeline execution end-to-end "
            "(Collect $\rightarrow$ Score $\rightarrow$ Briefs $\rightarrow$ CI $\rightarrow$ Storyboards $\rightarrow$ Assets $\rightarrow$ Manifests)."
        )
        top_n = st.number_input("Top items", min_value=1, max_value=20, value=5, step=1)
        source_filter = st.text_input("Source ID Filter (Optional)", value="")
        run_btn = st.button("▶ Run Full Pipeline", type="primary", use_container_width=True)
        
    with col2:
        if run_btn:
            with st.status("Running full pipeline...", expanded=True) as status:
                try:
                    timed = client.run_full_pipeline(
                        top_n=int(top_n),
                        source_filter=source_filter or None,
                    )
                    res = timed.result
                    st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                    st.write(f"Stages executed: `{', '.join(res.stages)}`")
                    st.json(res.stage_summaries)
                    st.caption(f"Log path: {res.log_path}")
                    if res.success:
                        status.update(
                            label="Pipeline completed successfully.",
                            state="complete",
                        )
                        st.success("Full pipeline completed successfully.")
                    else:
                        status.update(
                            label="Pipeline completed with failures.",
                            state="error",
                        )
                        st.error("Pipeline run failed. Review the stage summary above.")
                except Exception as e:
                    status.update(label="Pipeline execution failed.", state="error")
                    st.error(f"Failed to execute pipeline service: {e}")
        else:
            st.markdown(
                "Console output will appear here after triggering execution."
            )
            st.code("No pipeline run active.")

    st.markdown("---")
    st.markdown("### 📈 Workflow Status Summaries")
    
    workflow_states = client.list_workflow_states()
    
    if workflow_states:
        matrix_data = []
        for ws in workflow_states:
            scored_item = client.get_scored_topic(ws.topic_id)
            title = scored_item.title if scored_item else f"Topic {ws.topic_id[:8]}"
            
            row = {
                "Topic Title": title,
                "Brief": "⚪ Pending",
                "Content Intel": "⚪ Pending",
                "Storyboard": "⚪ Pending",
                "Thumbnail": "⚪ Pending",
                "Script": "⚪ Pending",
                "Carousel": "⚪ Pending",
                "Newsletter": "⚪ Pending",
            }
            
            status_emojis = {
                "completed": "🟢 Completed",
                "failed": "🔴 Failed",
                "pending": "⚪ Pending",
                "needs_review": "🟡 Review Needed"
            }
            
            for stage_name, art_state in ws.stages.items():
                col_name = {
                    "brief": "Brief",
                    "content_intelligence": "Content Intel",
                    "storyboard": "Storyboard",
                    "thumbnail": "Thumbnail",
                    "script": "Script",
                    "carousel": "Carousel",
                    "newsletter": "Newsletter"
                }.get(stage_name)
                if col_name and col_name in row:
                    row[col_name] = status_emojis.get(art_state.status, "⚪ Pending")
            matrix_data.append(row)
            
        st.dataframe(matrix_data, use_container_width=True)
    else:
        st.info("No workflow state records found.")

    st.markdown("---")
    st.markdown("### 🕒 Recent Pipeline Activity")
    
    activity_events = []
    if workflow_states:
        for state in workflow_states:
            for stage_name, art_state in state.stages.items():
                if art_state.status == "completed" and art_state.completed_at:
                    activity_events.append({
                        "Timestamp": art_state.completed_at,
                        "Topic ID": state.topic_id[:8],
                        "Stage": stage_name.replace("_", " ").title(),
                        "Status": "Success 🟢",
                    })
                elif art_state.status == "failed":
                    activity_events.append({
                        "Timestamp": "N/A",
                        "Topic ID": state.topic_id[:8],
                        "Stage": stage_name.replace("_", " ").title(),
                        "Status": "Failed 🔴",
                    })
        
        activity_events.sort(key=lambda x: x["Timestamp"] or "", reverse=True)
        if activity_events:
            st.table(activity_events[:10])
        else:
            st.info("No completed workflow stage activities logged yet.")
    else:
        st.info("No pipeline activity recorded.")

    # 7. Notification Center
    st.markdown("---")
    try:
        render_notification_center(client.notification_service)
    except Exception as e:
        st.warning(f"Notification center unavailable: {e}")


if __name__ == "__main__":
    main()
