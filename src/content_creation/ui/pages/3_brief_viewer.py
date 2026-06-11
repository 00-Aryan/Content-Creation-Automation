"""Streamlit Page 4: Brief Synthesis and Viewer."""

import os
import sys
from pathlib import Path
import streamlit as st

src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from content_creation.ui.components.status import render_api_health
from content_creation.ui.services.client import ServiceClient
from content_creation.ui.state.session import init_session_state, set_selected_brief_id
from content_creation.shared.enums import ReviewStatus
from content_creation.application.brief_review_service import BriefDecision


def main() -> None:
    st.set_page_config(page_title="📝 3. Review Briefs", page_icon="📝", layout="wide")
    init_session_state()
    client = ServiceClient()
    render_api_health(client.is_generation_available())
    
    st.markdown("# 📝 Brief Synthesis & Viewer")
    st.markdown("---")
    
    scored_items = client.list_scored_topics()
    
    if not scored_items:
        st.info("No scored topics available. Ingest and score topics first.")
        return
        
    scored_items.sort(key=lambda x: x.priority_score, reverse=True)
    
    # 2. Filter & Search Controls
    st.markdown("### 🔍 Filter and Search Briefs")
    col_search, col_status = st.columns(2)
    with col_search:
        search_query = st.text_input("Search Title, Takeaway, or Analogy", value="")
    with col_status:
        review_filter = st.selectbox("Filter by Review Status", ["All", "Draft", "Needs Review", "Reviewed", "Approved", "Rejected"])

    filtered_items = []
    for item in scored_items:
        brief = client.get_brief(item.id)
        
        if brief:
            query_match = (
                not search_query
                or search_query.lower() in item.title.lower()
                or search_query.lower() in brief.student_takeaway.lower()
                or search_query.lower() in brief.why_it_matters.lower()
                or search_query.lower() in brief.analogy.lower()
            )
            
            status_val = brief.review_status.value if hasattr(brief.review_status, "value") else str(brief.review_status)
            status_match = (
                review_filter == "All"
                or review_filter.lower().replace(" ", "_") == status_val.lower()
            )
            
            if query_match and status_match:
                filtered_items.append(item)
        else:
            if review_filter == "All" and (not search_query or search_query.lower() in item.title.lower()):
                filtered_items.append(item)

    if not filtered_items:
        st.info("No briefs or topics match the search criteria.")
        return

    st.markdown("### Select Topic to View/Generate Brief")
    topic_options = {f"[{item.category.value.upper()}] {item.title} (Score: {item.priority_score:.1f})": item for item in filtered_items}
    selected_label = st.selectbox("Topic Selector", list(topic_options.keys()))
    
    if selected_label:
        selected_topic = topic_options[selected_label]
        
        brief = client.get_brief(selected_topic.id)
        
        if brief:
            set_selected_brief_id(brief.topic_id)
            
            st.success(f"✓ Brief found (Generated at: {brief.generated_at})")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("#### 📖 Plain English Summary")
                for item in brief.plain_english_summary:
                    st.markdown(f"- {item}")
                    
                st.markdown("#### 💡 Why It Matters")
                st.markdown(brief.why_it_matters)
                
                st.markdown("#### 🎓 Student Takeaway")
                st.markdown(brief.student_takeaway)
                
                st.markdown("#### 🪵 Analogy")
                st.markdown(brief.analogy)
                
                st.markdown("#### 🛑 Limitation")
                st.markdown(brief.limitation)
                
            with col2:
                st.markdown("#### 🔬 Metadata")
                st.markdown(f"**Review Status:** `{brief.review_status.value if hasattr(brief.review_status, 'value') else brief.review_status}`")
                if brief.review_notes:
                    st.markdown(f"**Review Notes:** {brief.review_notes}")
                st.markdown(f"**Target Audience Fit:** {brief.audience_fit}")
                st.markdown(f"**Source URL:** [Read Paper/Link]({brief.source_url})")
                
                st.markdown("#### 🛠️ Recommended Formats")
                for fmt in brief.recommended_formats:
                    st.markdown(f"- `{fmt}`")
            
            st.markdown("---")
            with st.expander("📄 View Raw Brief JSON"):
                st.json(brief.model_dump())

            # Show brief content before the review decision
            st.markdown("### 📄 Brief Summary")
            
            if hasattr(brief, 'why_it_matters') and brief.why_it_matters:
                st.info(f"**Why it matters:** {brief.why_it_matters}")
            
            if hasattr(brief, 'plain_english_summary') and brief.plain_english_summary:
                st.markdown("**Plain English Summary:**")
                for item in brief.plain_english_summary:
                    st.markdown(f"- {item}")
            
            if hasattr(brief, 'student_takeaway') and brief.student_takeaway:
                st.markdown(f"**Student Takeaway:** {brief.student_takeaway}")
            
            if hasattr(brief, 'source_url') and brief.source_url:
                st.markdown(f"**Source URL:** {brief.source_url}")

            # ------------------ REVIEW CONTROLS ------------------
            st.markdown("---")
            st.markdown("### ✅ Brief Review & Approval")

            current_status = brief.review_status.value if hasattr(brief.review_status, 'value') else str(brief.review_status)
            st.markdown(f"**Current Status:** `{current_status}`")

            col_review, col_history = st.columns([1, 1])

            with col_review:
                st.markdown("#### Review Action")
                review_action = st.selectbox(
                    "Set Review Status",
                    ["No Action", "Draft", "Needs Review", "Reviewed", "Approved", "Rejected"],
                    key="brief_review_action",
                )
                review_notes = st.text_area(
                    "Review Notes (optional)",
                    value=brief.review_notes or "",
                    key="brief_review_notes",
                    height=80,
                )

                if review_action != "No Action":
                    status_map = {
                        "Draft": ReviewStatus.DRAFT,
                        "Needs Review": ReviewStatus.NEEDS_REVIEW,
                        "Reviewed": ReviewStatus.REVIEWED,
                        "Approved": ReviewStatus.APPROVED,
                        "Rejected": ReviewStatus.REJECTED,
                    }
                    st.warning(f"⚠️ You are about to set this brief to **{review_action}**.")
                    if st.button("Apply Brief Review Decision", type="primary", use_container_width=True):
                        decision = BriefDecision(
                            status=status_map[review_action],
                            notes=review_notes if review_notes else None,
                        )
                        with st.status("Applying brief review decision...", expanded=True) as status:
                            try:
                                timed = client.apply_brief_decision(selected_topic.id, decision)
                                res = timed.result
                                st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                                st.write(f"Previous Status: `{res.previous_status.value}`")
                                st.write(f"New Status: `{res.new_status.value}`")
                                status.update(label="Brief review decision applied.", state="complete")
                                st.success("Brief review decision applied successfully.")
                                from content_creation.ui.components.notification_panel import render_inline_notification
                                render_inline_notification(
                                    f"Brief {review_action.lower()} for topic {selected_topic.id[:8]}",
                                    "success",
                                )
                                # Publish SSE event for real-time updates
                                try:
                                    latest_notifications = client.notification_service.list_recent(limit=1)
                                    if latest_notifications:
                                        client.publish_notification_event(latest_notifications[0])
                                except Exception as e:
                                    st.warning(f"A background operation failed and was skipped. ({type(e).__name__})")
                                st.rerun()
                            except Exception as e:
                                status.update(label="Brief review update failed.", state="error")
                                st.error(f"Failed to apply brief review decision: {e}")

            with col_history:
                st.markdown("#### Review History")
                brief_history = client.get_brief_review_history(selected_topic.id)
                if brief_history:
                    for entry in reversed(brief_history[-5:]):
                        ts = entry.timestamp[:19] if entry.timestamp else "N/A"
                        prev = entry.previous_status.value if entry.previous_status else "N/A"
                        st.markdown(
                            f"**{ts}** — `{prev}` → `{entry.new_status.value}`"
                        )
                        if entry.notes:
                            st.caption(f"Notes: {entry.notes}")
                else:
                    st.info("No review history recorded yet.")
                    
        else:
            st.warning("⚠️ No brief generated for this topic yet.")
            
            st.markdown("### Generate Brief")
            rate_limit_delay = st.slider("Rate Limit Delay (seconds)", 0.0, 10.0, 5.0, 0.5)
            
            btn_col, _ = st.columns([1, 2])
            with btn_col:
                gen_btn = st.button("📝 Generate Briefs", type="primary", use_container_width=True)
                
            if gen_btn:
                if not client.is_generation_available():
                    st.error("Cannot generate brief: Generation Service credentials are not configured on the backend.")
                else:
                    with st.status("Generating briefs...", expanded=True) as status:
                        try:
                            timed = client.generate_briefs(
                                top_n=20,
                                rate_limit_delay=rate_limit_delay,
                            )
                            res = timed.result
                            st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                            st.write(f"Generated: `{res.generated_count}`")
                            st.write(f"Skipped: `{res.skipped_count}`")
                            st.write(f"Failures: `{len(res.failures)}`")
                            for fail in res.failures:
                                st.error(f"{fail.topic_id[:8]}: {fail.error}")

                            brief = client.get_brief(selected_topic.id)
                            if brief:
                                status.update(
                                    label="Brief generation completed.",
                                    state="complete",
                                )
                                st.success("Generate Briefs completed.")
                                st.rerun()
                            elif res.failures:
                                status.update(
                                    label="Brief generation completed with failures.",
                                    state="error",
                                )
                            else:
                                status.update(
                                    label="Brief generation completed without this topic.",
                                    state="complete",
                                )
                                st.warning(
                                    "Brief generation ran, but this selected topic was not generated. "
                                    "Verify scored status and top-N priority."
                                )
                        except Exception as e:
                            status.update(label="Brief generation failed.", state="error")
                            st.error(f"Generate Briefs failed: {e}")


if __name__ == "__main__":
    main()
