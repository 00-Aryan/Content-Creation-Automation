"""Streamlit Page 6: Asset Workshop (Generation and Review)."""

import os
import sys
from pathlib import Path
import streamlit as st

src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from content_creation.ui.components.status import render_api_health
from content_creation.ui.services.client import ServiceClient
from content_creation.ui.state.session import init_session_state
from content_creation.shared.enums import ReviewStatus
from content_creation.application.asset_review_service import AssetDecision


def main() -> None:
    st.set_page_config(page_title="Asset Workshop", page_icon="🛠️", layout="wide")
    init_session_state()
    client = ServiceClient()
    render_api_health(client.is_generation_available())
    
    st.markdown("# 🛠️ Asset Generation & Review Workshop")
    st.markdown("---")
    
    briefs = client.list_briefs()
    if not briefs:
        st.info("No synthesized briefs found in storage. Please generate a brief and storyboard first.")
        return
        
    # 2. Filter & Search Controls
    st.markdown("### 🔍 Filter and Search Manifests & Assets")
    col_search, col_status = st.columns(2)
    with col_search:
        search_query = st.text_input("Search Title or Content", value="")
    with col_status:
        manifest_status_filter = st.selectbox("Filter by Manifest Status", ["All", "Complete", "Partial", "Blocked"])

    filtered_briefs = []
    for brief in briefs:
        scored_item = client.get_scored_topic(brief.topic_id)
        title = scored_item.title if scored_item else f"Topic {brief.topic_id[:8]}"
        
        manifest = client.get_manifest(brief.topic_id)
        manifest_status = manifest.overall_status.title() if manifest else "None"
            
        query_match = not search_query or search_query.lower() in title.lower()
        
        status_match = (
            manifest_status_filter == "All"
            or (manifest_status_filter == "Complete" and manifest_status == "Complete")
            or (manifest_status_filter == "Partial" and manifest_status == "Partial")
            or (manifest_status_filter == "Blocked" and manifest_status == "Blocked")
        )
        
        if query_match and status_match:
            filtered_briefs.append((brief, title))
            
    if not filtered_briefs:
        st.info("No manifests or assets match the criteria.")
        return
        
    st.markdown("### Select Topic/Brief to Manage Assets")
    brief_options = {f"{title} (ID: {brief.topic_id[:8]})": brief for brief, title in filtered_briefs}
    
    selected_label = st.selectbox("Brief Selector", list(brief_options.keys()))
    if not selected_label:
        return
        
    selected_brief = brief_options[selected_label]
    topic_id = selected_brief.topic_id
    
    # ------------------ GENERATION ACTION ------------------
    st.markdown("### ⚡ Generation Action")
    col_gen, _ = st.columns([1, 2])
    with col_gen:
        gen_assets_btn = st.button("⚡ Generate Asset Suite", type="primary", use_container_width=True)
        
    if gen_assets_btn:
        if not client.is_generation_available():
            st.error("Cannot generate asset suite: Generation Service credentials are not configured on the backend.")
        else:
            with st.status("Generating asset suite...", expanded=True) as status:
                try:
                    timed = client.generate_asset_suite(
                        top_n=20,
                        rate_limit_delay=5.0,
                    )
                    res = timed.result
                    st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                    st.write(f"Counts: `{res.counts}`")
                    st.write(f"Skipped: `{res.skipped_count}`")
                    st.write(f"Failed: `{res.failed_count}`")
                    if res.failed_count:
                        status.update(
                            label="Asset generation completed with failures.",
                            state="error",
                        )
                        st.error("Generate Asset Suite completed with backend failures.")
                    else:
                        status.update(
                            label="Asset generation completed.",
                            state="complete",
                        )
                        st.success("Generate Asset Suite completed.")
                        st.rerun()
                except ValueError as ve:
                    status.update(label="Asset generation blocked.", state="error")
                    st.error(str(ve))
                except Exception as e:
                    status.update(label="Asset generation failed.", state="error")
                    st.error(f"Generate Asset Suite failed: {e}")
                
    st.markdown("---")
    
    # ------------------ MANIFEST HEADER ------------------
    st.markdown("### 📋 Compiled Topic Manifest")
    manifest = client.get_manifest(topic_id)
            
    if manifest:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Overall Status", manifest.overall_status.upper())
        with col_m2:
            st.metric("Ready for Planner?", "YES" if manifest.ready_for_planner else "NO")
        with col_m3:
            st.write(f"**Blocking Reasons:** {manifest.blocking_reasons or 'None'}")
            
        st.markdown("#### 📁 Manifest Artifact References")
        ref_data = []
        for asset_name, asset_entry in manifest.assets.items():
            ref_data.append({
                "Asset Type": asset_name.replace("_", " ").title(),
                "Status": asset_entry.status.upper(),
                "Generated At": asset_entry.generated_at or "N/A",
                "File Path": asset_entry.path,
            })
        st.dataframe(ref_data, use_container_width=True)
        
        with st.expander("📄 View Raw Manifest JSON"):
            st.json(manifest.model_dump())
            
        st.markdown("---")
        st.markdown("### 📂 Assets Tabbed Editor & Audit Toolbar")
        
        # Tabs for assets
        tab_script, tab_carousel, tab_newsletter, tab_thumbnail = st.tabs([
            "🎥 Video Script",
            "📊 Carousel Slides",
            "✉️ Newsletter Copy",
            "🖼️ Thumbnail Prompt"
        ])
        
        # Load asset files
        assets = client.get_topic_assets(topic_id)
        script = assets["script"]
        carousel = assets["carousel"]
        newsletter = assets["newsletter"]
        thumbnail = assets["thumbnail"]
        storyboard = client.get_storyboard(topic_id)
        
        decisions = []
        
        with tab_script:
            if script:
                st.markdown(f"**Review Status:** `{script.review_status}`")
                st.markdown(f"**Hook:** {script.hook}")
                st.markdown("**Sections:**")
                for idx, sect in enumerate(script.script_sections):
                    st.markdown(f"**Section {idx+1}:** {sect}")
                st.markdown(f"**CTA:** {script.cta}")
                
                if storyboard:
                    st.markdown("#### ⚖️ Storyboard vs. Output Script Comparison")
                    col_comp1, col_comp2 = st.columns(2)
                    with col_comp1:
                        st.markdown("**Storyboard Input:**")
                        st.info(f"**Planned Hook:**\n{storyboard.script_hook}\n\n**Planned CTA:**\n{storyboard.script_cta}\n\n**Planned Claims:**\n" + "\n".join(f"- {c}" for c in storyboard.script_claims))
                    with col_comp2:
                        st.markdown("**Generated Output:**")
                        st.info(f"**Hook Used:**\n{script.hook}\n\n**CTA Used:**\n{script.cta}\n\n**Claims Used:**\n" + "\n".join(f"- {c}" for c in script.claims_used))
                st.markdown("---")
                with st.expander("📄 View Raw Script JSON"):
                    st.json(script.model_dump())
                
                choice = st.radio("Script Decision", ["No Action", "Approve", "Reject"], key="script_dec")
                if choice == "Approve":
                    decisions.append(AssetDecision(asset_type="script", status=ReviewStatus.APPROVED))
                elif choice == "Reject":
                    decisions.append(AssetDecision(asset_type="script", status=ReviewStatus.REJECTED))
            else:
                st.info("No Video Script generated for this topic.")
                
        with tab_carousel:
            if carousel:
                st.markdown(f"**Review Status:** `{carousel.review_status}`")
                st.markdown("**Slides:**")
                for slide in carousel.slides:
                    st.markdown(f"**Slide {slide.slide_number}: {slide.title}**")
                    st.write(slide.body)
                    st.caption(f"Visual Note: {slide.visual_note}")
                st.markdown(f"**CTA Slide:** {carousel.cta_slide}")
                
                if storyboard:
                    st.markdown("#### ⚖️ Storyboard vs. Output Carousel Comparison")
                    col_comp1, col_comp2 = st.columns(2)
                    with col_comp1:
                        st.markdown("**Storyboard Input:**")
                        st.info(f"**Planned Hook:**\n{storyboard.carousel_hook}\n\n**Planned CTA:**\n{storyboard.carousel_cta}\n\n**Planned Claims:**\n" + "\n".join(f"- {c}" for c in storyboard.carousel_claims))
                    with col_comp2:
                        st.markdown("**Generated Output:**")
                        st.info(f"**CTA Used:**\n{carousel.cta_slide}\n\n**Claims Used:**\n" + "\n".join(f"- {c}" for c in carousel.claims_used))
                st.markdown("---")
                with st.expander("📄 View Raw Carousel JSON"):
                    st.json(carousel.model_dump())
                
                choice = st.radio("Carousel Decision", ["No Action", "Approve", "Reject"], key="carousel_dec")
                if choice == "Approve":
                    decisions.append(AssetDecision(asset_type="carousel", status=ReviewStatus.APPROVED))
                elif choice == "Reject":
                    decisions.append(AssetDecision(asset_type="carousel", status=ReviewStatus.REJECTED))
            else:
                st.info("No Carousel generated for this topic.")
                
        with tab_newsletter:
            if newsletter:
                st.markdown(f"**Review Status:** `{newsletter.review_status}`")
                st.markdown(f"**Subject Line:** {newsletter.subject_line}")
                st.markdown("**Sections:**")
                for sect in newsletter.sections:
                    st.markdown(f"**Section ({sect.section_name}):**")
                    st.write(sect.content)
                st.markdown(f"**CTA:** {newsletter.cta}")
                
                if storyboard:
                    st.markdown("#### ⚖️ Storyboard vs. Output Newsletter Comparison")
                    col_comp1, col_comp2 = st.columns(2)
                    with col_comp1:
                        st.markdown("**Storyboard Input:**")
                        st.info(f"**Planned Hook:**\n{storyboard.newsletter_hook}\n\n**Planned CTA:**\n{storyboard.newsletter_cta}\n\n**Planned Claims:**\n" + "\n".join(f"- {c}" for c in storyboard.newsletter_claims))
                    with col_comp2:
                        st.markdown("**Generated Output:**")
                        st.info(f"**CTA Used:**\n{newsletter.cta}\n\n**Claims Used:**\n" + "\n".join(f"- {c}" for c in newsletter.claims_used))
                st.markdown("---")
                with st.expander("📄 View Raw Newsletter JSON"):
                    st.json(newsletter.model_dump())
                
                choice = st.radio("Newsletter Decision", ["No Action", "Approve", "Reject"], key="newsletter_dec")
                if choice == "Approve":
                    decisions.append(AssetDecision(asset_type="newsletter", status=ReviewStatus.APPROVED))
                elif choice == "Reject":
                    decisions.append(AssetDecision(asset_type="newsletter", status=ReviewStatus.REJECTED))
            else:
                st.info("No Newsletter generated for this topic.")
                
        with tab_thumbnail:
            if thumbnail:
                st.markdown(f"**Review Status:** `{thumbnail.review_status}`")
                st.markdown(f"**Title Text:** {thumbnail.title_text}")
                st.markdown(f"**Supporting Text:** {thumbnail.supporting_text}")
                st.markdown(f"**Visual Metaphor Concept:** {thumbnail.visual_metaphor}")
                st.markdown(f"**Style:** `{thumbnail.style}`")
                st.markdown(f"**Readability Notes:** {thumbnail.readability_notes}")
                st.markdown(f"**Negative Prompts:** {thumbnail.negative_prompt}")
                
                if storyboard:
                    st.markdown("#### ⚖️ Storyboard vs. Output Thumbnail Comparison")
                    col_comp1, col_comp2 = st.columns(2)
                    with col_comp1:
                        st.markdown("**Storyboard Input:**")
                        st.info(f"**Planned Hook:**\n{storyboard.thumbnail_hook}\n\n**Planned Metaphor:**\n{storyboard.visual_metaphor}\n\n**Planned Style:**\n{storyboard.visual_style}")
                    with col_comp2:
                        st.markdown("**Generated Output:**")
                        st.info(f"**Title Text:**\n{thumbnail.title_text}\n\n**Supporting Text:**\n{thumbnail.supporting_text}\n\n**Visual Metaphor Used:**\n{thumbnail.visual_metaphor}\n\n**Style Used:**\n{thumbnail.style}")
                st.markdown("---")
                with st.expander("📄 View Raw Thumbnail JSON"):
                    st.json(thumbnail.model_dump())
                
                choice = st.radio("Thumbnail Decision", ["No Action", "Approve", "Reject"], key="thumbnail_dec")
                if choice == "Approve":
                    decisions.append(AssetDecision(asset_type="thumbnail", status=ReviewStatus.APPROVED))
                elif choice == "Reject":
                    decisions.append(AssetDecision(asset_type="thumbnail", status=ReviewStatus.REJECTED))
            else:
                st.info("No Thumbnail prompt generated for this topic.")
                
        # Apply decisions button
        if decisions:
            st.markdown("#### 🛠️ Apply Decisions")
            decision_summary = ", ".join(f"{d.asset_type}={d.status.value}" for d in decisions)
            st.warning(f"⚠️ You are about to apply: {decision_summary}")
            if st.button("Apply Review Decisions & Rebuild Manifest", type="primary"):
                with st.status("Applying review decisions...", expanded=True) as status:
                    try:
                        timed = client.apply_asset_decisions(topic_id, decisions)
                        res = timed.result
                        st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                        st.write(f"Approved: `{res.approved_count}`")
                        st.write(f"Rejected: `{res.rejected_count}`")
                        status.update(label="Review decisions applied.", state="complete")
                        st.success("Review decisions applied and manifest rebuilt.")
                        from content_creation.ui.components.notification_panel import render_inline_notification
                        render_inline_notification(
                            f"Asset review: {res.approved_count} approved, {res.rejected_count} rejected for topic {topic_id[:8]}",
                            "success",
                        )
                        # Publish SSE event for real-time updates
                        try:
                            latest_notifications = client.notification_service.list_recent(limit=1)
                            if latest_notifications:
                                client.publish_notification_event(latest_notifications[0])
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as e:
                        status.update(label="Review decision update failed.", state="error")
                        st.error(f"Failed to apply decisions: {e}")

        # ------------------ REVIEW HISTORY ------------------
        st.markdown("---")
        st.markdown("### 📜 Asset Review History")
        asset_history_filtered = client.get_asset_review_history(topic_id)
        if asset_history_filtered:
            for entry in reversed(asset_history_filtered[-10:]):
                ts = entry.timestamp[:19] if entry.timestamp else "N/A"
                prev = entry.previous_status.value if entry.previous_status else "N/A"
                st.markdown(
                    f"**{ts}** — `{entry.asset_type}` — `{prev}` → `{entry.new_status.value}`"
                )
                if entry.notes:
                    st.caption(f"Notes: {entry.notes}")
        else:
            st.info("No asset review history recorded yet.")
    else:
        st.info("No manifest compiled for this topic. Run asset generation first.")


if __name__ == "__main__":
    main()
