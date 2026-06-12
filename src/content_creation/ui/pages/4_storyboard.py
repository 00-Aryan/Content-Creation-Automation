"""Streamlit Page 5: Content Intelligence and Storyboard."""

import os
import sys
from pathlib import Path
import streamlit as st

src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from content_creation.ui.components.status import render_api_health, format_review_status, format_timestamp
from content_creation.ui.services.client import ServiceClient
from content_creation.ui.state.session import init_session_state
from content_creation.shared.enums import ReviewStatus
from content_creation.application.storyboard_review_service import StoryboardDecision


def main() -> None:
    st.set_page_config(page_title="🗂️ 4. Storyboard", page_icon="🎨", layout="wide")
    init_session_state()
    client = ServiceClient()
    render_api_health(client.is_generation_available())
    
    st.markdown("# 🎨 Content Intelligence & Coordinated Storyboard")
    st.markdown("---")
    
    briefs = client.list_briefs()
    if not briefs:
        st.info("No synthesized briefs found in storage. Please generate a brief first.")
        return
        
    # 2. Filter & Search Controls
    st.markdown("### 🔍 Filter and Search Storyboards/CI")
    col_search, col_style = st.columns(2)
    with col_search:
        search_query = st.text_input("Search Title or Metaphor", value="")
    with col_style:
        visual_style_filter = st.selectbox(
            "Filter by Visual Style",
            ["All", "clean_minimal", "bold_typographic", "diagram_overlay", "metaphor_illustration"]
        )

    filtered_briefs = []
    for brief in briefs:
        scored_item = client.get_scored_topic(brief.topic_id)
        title = scored_item.title if scored_item else f"Topic {brief.topic_id[:8]}"
        sb = client.get_storyboard(brief.topic_id)
        
        query_match = (
            not search_query
            or search_query.lower() in title.lower()
            or (sb and search_query.lower() in sb.visual_metaphor.lower())
        )
        
        style_match = (
            visual_style_filter == "All"
            or (sb and sb.visual_style == visual_style_filter)
        )
        
        if query_match and style_match:
            filtered_briefs.append((brief, title))
            
    if not filtered_briefs:
        st.info("No items match the filter criteria.")
        return
        
    st.markdown("### Select a Brief")
    brief_options = {f"{title} (ID: {brief.topic_id[:8]})": brief for brief, title in filtered_briefs}
    selected_label = st.selectbox("Brief Selector", list(brief_options.keys()))
    if not selected_label:
        return
        
    selected_brief = brief_options[selected_label]
    topic_id = selected_brief.topic_id
    
    # Resolve artifacts
    ci = client.get_content_intelligence(topic_id)
    storyboard = client.get_storyboard(topic_id)
    
    # ------------------ ACTIONS ------------------
    col_actions1, col_actions2 = st.columns(2)
    
    with col_actions1:
        if not ci:
            st.warning("⚠️ Content Intelligence is missing.")
            gen_ci_btn = st.button("🎨 Generate Content Intelligence", type="primary", use_container_width=True)
            if gen_ci_btn:
                if not client.is_generation_available():
                    st.error("Cannot generate content intelligence: Generation Service credentials are not configured on the backend.")
                else:
                    with st.status("Generating content intelligence...", expanded=True) as status:
                        try:
                            timed = client.generate_content_intelligence(
                                top_n=20,
                                rate_limit_delay=5.0,
                            )
                            res = timed.result
                            st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                            st.write(f"Generated: `{res.generated_count}`")
                            st.write(f"Skipped: `{res.skipped_count}`")
                            st.write(f"Failures: `{len(res.failures)}`")
                            for fail in res.failures:
                                st.error(f"{fail.topic_id[:8]}: {fail.error}")
                            if res.failures:
                                status.update(
                                    label="Content Intelligence completed with failures.",
                                    state="error",
                                )
                            else:
                                status.update(
                                    label="Content Intelligence completed.",
                                    state="complete",
                                )
                                st.success("Generate Content Intelligence completed.")
                                st.rerun()
                        except Exception as e:
                            status.update(
                                label="Content Intelligence generation failed.",
                                state="error",
                            )
                            st.error(f"Generate Content Intelligence failed: {e}")
        else:
            st.success("✓ Content Intelligence exists for this topic.")
            
    with col_actions2:
        if not storyboard:
            st.warning("⚠️ Storyboard is missing.")
            gen_sb_btn = st.button("📋 Generate Storyboards", type="primary", use_container_width=True)
            if gen_sb_btn:
                if not client.is_generation_available():
                    st.error("Cannot generate storyboards: Generation Service credentials are not configured on the backend.")
                else:
                    with st.status("Generating storyboards...", expanded=True) as status:
                        try:
                            timed = client.generate_storyboards(
                                top_n=20,
                                rate_limit_delay=5.0,
                            )
                            res = timed.result
                            st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                            st.write(f"Generated: `{res.generated_count}`")
                            st.write(f"Skipped: `{res.skipped_count}`")
                            st.write(f"Failures: `{len(res.failures)}`")
                            for fail in res.failures:
                                st.error(f"{fail.topic_id[:8]}: {fail.error}")
                            if res.failures:
                                status.update(
                                    label="Storyboard generation completed with failures.",
                                    state="error",
                                )
                            else:
                                status.update(
                                    label="Storyboard generation completed.",
                                    state="complete",
                                )
                                st.success("Generate Storyboards completed.")
                                st.rerun()
                        except Exception as e:
                            status.update(
                                label="Storyboard generation failed.",
                                state="error",
                            )
                            st.error(f"Generate Storyboards failed: {e}")
        else:
            st.success("✓ Coordinated Storyboard exists for this topic.")
            
    st.markdown("---")
    
    # ------------------ DISPLAY CO-ORDINATED GRID ------------------
    if ci or storyboard:
        col_ci, col_sb = st.columns(2)
        
        with col_ci:
            if ci:
                st.markdown("### 🧠 Content Intelligence Insights")
                st.markdown(f"**Topic Type:** `{ci.topic_type.value if hasattr(ci.topic_type, 'value') else ci.topic_type}`")
                st.markdown(f"**Emotional Register:** `{ci.emotional_register.value if hasattr(ci.emotional_register, 'value') else ci.emotional_register}`")
                
                with st.expander("🔍 Curiosity Gap & Story Angle", expanded=True):
                    st.markdown(f"**Curiosity Gap:**\n{ci.curiosity_gap}")
                    st.markdown(f"**Story Angle:**\n{ci.story_angle}")
                    
                with st.expander("⚖️ Contrast Pair (Before vs After)", expanded=True):
                    c1, c2 = st.columns(2)
                    c1.metric("Before / Old Way", ci.contrast_pair.before)
                    c2.metric("After / New Way", ci.contrast_pair.after)
                    
                with st.expander("🪝 Generated Psychological Hooks", expanded=True):
                    st.markdown(f"**Primary Hook ({ci.primary_hook.hook_type}):**")
                    st.info(ci.primary_hook.hook_text)
                    st.markdown(f"**Secondary Hook ({ci.secondary_hook.hook_type}):**")
                    st.info(ci.secondary_hook.hook_text)
                    
                if ci.timeliness_hook:
                    st.markdown(f"**Timeliness Hook:** {ci.timeliness_hook}")
                st.markdown("---")
                with st.expander("📄 View Raw Content Intelligence JSON"):
                    st.json(ci.model_dump())
            else:
                st.info("No Content Intelligence data display available.")
                
        with col_sb:
            if storyboard:
                st.markdown("### 📋 Coordinated Narrative Storyboard")
                st.markdown(f"**Visual Style Selection:** `{storyboard.visual_style}`")
                sb_status = format_review_status(storyboard.review_status)
                st.markdown(f"**Review Status:** `{sb_status}`")
                if storyboard.review_notes:
                    st.markdown(f"**Review Notes:** {storyboard.review_notes}")
                st.markdown(f"**Visual Metaphor Concept:**")
                st.info(storyboard.visual_metaphor)
                
                with st.expander("⛓️ Format-Specific Hooks & CTAs", expanded=True):
                    tab_hook, tab_cta = st.tabs(["Hooks", "CTAs"])
                    with tab_hook:
                        st.markdown(f"**Script Hook:** `{storyboard.script_hook}`")
                        st.markdown(f"**Carousel Hook:** `{storyboard.carousel_hook}`")
                        st.markdown(f"**Newsletter Hook:** `{storyboard.newsletter_hook}`")
                        st.markdown(f"**Thumbnail Hook:** `{storyboard.thumbnail_hook}`")
                    with tab_cta:
                        st.markdown(f"**Script CTA:** `{storyboard.script_cta}`")
                        st.markdown(f"**Carousel CTA:** `{storyboard.carousel_cta}`")
                        st.markdown(f"**Newsletter CTA:** `{storyboard.newsletter_cta}`")
                        
                with st.expander("🧩 Editorial Format Claims-Split", expanded=True):
                    st.markdown("**Script Claims:**")
                    for claim in storyboard.script_claims:
                        st.markdown(f"- {claim}")
                    st.markdown("**Carousel Claims:**")
                    for claim in storyboard.carousel_claims:
                        st.markdown(f"- {claim}")
                    st.markdown("**Newsletter Claims:**")
                    for claim in storyboard.newsletter_claims:
                        st.markdown(f"- {claim}")
                st.markdown("---")
                with st.expander("📄 View Raw Storyboard JSON"):
                    st.json(storyboard.model_dump())

                # ------------------ STORYBOARD REVIEW CONTROLS ------------------
                st.markdown("---")
                st.markdown("### ✅ Storyboard Review & Approval")

                col_review_sb, col_history_sb = st.columns([1, 1])

                with col_review_sb:
                    st.markdown("#### Review Action")
                    sb_review_action = st.selectbox(
                        "Set Review Status",
                        ["No Action", "Draft", "Needs Review", "Reviewed", "Approved", "Rejected"],
                        key="sb_review_action",
                    )
                    sb_review_notes = st.text_area(
                        "Review Notes (optional)",
                        value=storyboard.review_notes or "",
                        key="sb_review_notes",
                        height=80,
                    )

                    if sb_review_action != "No Action":
                        sb_status_map = {
                            "Draft": ReviewStatus.DRAFT,
                            "Needs Review": ReviewStatus.NEEDS_REVIEW,
                            "Reviewed": ReviewStatus.REVIEWED,
                            "Approved": ReviewStatus.APPROVED,
                            "Rejected": ReviewStatus.REJECTED,
                        }
                        st.warning(f"⚠️ You are about to set this storyboard to **{sb_review_action}**.")
                        if st.button("Apply Storyboard Review Decision", type="primary", use_container_width=True):
                            sb_decision = StoryboardDecision(
                                status=sb_status_map[sb_review_action],
                                notes=sb_review_notes if sb_review_notes else None,
                            )
                            with st.status("Applying storyboard review decision...", expanded=True) as status:
                                try:
                                    timed = client.apply_storyboard_decision(topic_id, sb_decision)
                                    res = timed.result
                                    st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                                    st.write(f"Previous Status: `{res.previous_status.value}`")
                                    st.write(f"New Status: `{res.new_status.value}`")
                                    status.update(label="Storyboard review decision applied.", state="complete")
                                    st.success("Storyboard review decision applied successfully.")
                                    from content_creation.ui.components.notification_panel import render_inline_notification
                                    render_inline_notification(
                                        f"Storyboard {sb_review_action.lower()} for topic {topic_id[:8]}",
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
                                    status.update(label="Storyboard review update failed.", state="error")
                                    st.error(f"Failed to apply storyboard review decision: {e}")

                with col_history_sb:
                    st.markdown("#### Review History")
                    storyboard_history = client.get_storyboard_review_history(topic_id)
                    if storyboard_history:
                        for entry in reversed(storyboard_history[-5:]):
                            ts = format_timestamp(entry.timestamp)
                            prev = format_review_status(entry.previous_status) if entry.previous_status else "N/A"
                            new_st = format_review_status(entry.new_status) if entry.new_status else "N/A"
                            st.markdown(
                                f"**{ts}** — `{prev}` → `{new_st}`"
                            )
                            if entry.notes:
                                st.caption(f"Notes: {entry.notes}")
                    else:
                        st.info("No review history recorded yet.")
            else:
                st.info("No Storyboard narrative data display available.")
    else:
        st.info("Select a topic and run the generators above to view the intelligence and storyboard dashboard.")


if __name__ == "__main__":
    main()
