"""Streamlit Page 3: Topic Pipeline Scoring and Triage."""

import sys
from pathlib import Path
import streamlit as st

src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from content_creation.ui.components.status import render_api_health
from content_creation.ui.services.client import ServiceClient
from content_creation.ui.state.session import init_session_state


def main() -> None:
    st.set_page_config(page_title="⚙️ 2. Score & Filter", page_icon="⚖️", layout="wide")
    init_session_state()
    client = ServiceClient()
    render_api_health(client.is_generation_available())
    
    st.markdown("# ⚖️ Topic Prioritization & Pipeline Triage")
    st.markdown("---")
    
    # Weight Configuration Display
    with st.expander("⚖️ Current Scoring Weights (config/scoring.yaml)", expanded=False):
        st.markdown(
            "- **Usefulness:** `0.30`\n"
            "- **Novelty:** `0.25`\n"
            "- **Credibility:** `0.20`\n"
            "- **Explainability:** `0.15`\n"
            "- **Hook Potential:** `0.10`\n\n"
            "*Weights are read from `config/scoring.yaml`.*"
        )
        
    st.markdown("### Prioritization Actions")
    run_btn = st.button("⚖️ Score Topics", type="primary", width="stretch")
    
    if run_btn:
        with st.status("Scoring topics...", expanded=True) as status:
            try:
                timed = client.score_topics()
                res = timed.result
                st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                st.write(f"Scored: `{res.scored_count}`")
                st.write(f"Rejected: `{res.rejected_count}`")
                status.update(label="Topic scoring completed.", state="complete")
                st.success(
                    f"Score Topics completed. Scored {res.scored_count} topics, "
                    f"rejected {res.rejected_count} topics."
                )
            except Exception as e:
                status.update(label="Topic scoring failed.", state="error")
                st.error(f"Score Topics failed: {e}")

    st.markdown("---")
    st.markdown("### 📊 Scored Topics")
    
    scored_items = client.list_scored_topics()
    if scored_items:
        # Sort by priority score
        scored_items.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Display list
        data = []
        for item in scored_items:
            if item.priority_score >= 70.0:
                tier = "🟢 High"
            elif item.priority_score >= 40.0:
                tier = "🟡 Medium"
            else:
                tier = "⚪ Low"
            data.append({
                "ID": item.id[:8],
                "Title": item.title,
                "Priority Tier": tier,
                "Priority Score": round(item.priority_score, 2),
                "Source": item.source,
                "Category": item.category.value if hasattr(item.category, 'value') else str(item.category),
                "Validation Flags": ", ".join(item.validation_flags) if item.validation_flags else "None",
                "Status": item.status.value if hasattr(item.status, 'value') else str(item.status),
            })
        st.dataframe(data, width="stretch")
        
        # Detail inspector
        st.markdown("#### 🔍 Scored Item Inspector")
        options = {f"{item.title} (Score: {item.priority_score:.1f})": item.id for item in scored_items}
        selected_label = st.selectbox("Select scored topic to inspect details", list(options.keys()))
        if selected_label:
            selected_id = options[selected_label]
            selected_item = next((x for x in scored_items if x.id == selected_id), None)
            if selected_item:
                col_left, col_right = st.columns(2)
                with col_left:
                    st.write(f"**Title:** {selected_item.title}")
                    st.write(f"**URL:** [{selected_item.url}]({selected_item.url})")
                    st.write(f"**Author:** {selected_item.author}")
                    st.write(f"**Category:** {selected_item.category}")
                    st.write(f"**Validation Flags:** {selected_item.validation_flags or 'None'}")
                with col_right:
                    st.write("**Topic Scores Breakdown:**")
                    st.write(f"- Student Usefulness: `{selected_item.student_usefulness_score}`")
                    st.write(f"- Novelty: `{selected_item.novelty_score}`")
                    st.write(f"- Credibility: `{selected_item.credibility_score}`")
                    st.write(f"- Explainability: `{selected_item.explainability_score}`")
                    st.write(f"- Hook Potential: `{selected_item.hook_potential_score}`")
                    st.write(f"- Fired Scoring Rules: `{selected_item.scoring_rules_fired}`")
    else:
        st.info("No scored topics found in pipeline storage. Click 'Run Prioritization Scorer' above.")

    st.markdown("---")
    try:
        st.page_link("pages/3_brief_viewer.py", label="Next: Generate & View Briefs ➡️", icon="📝")
    except Exception:
        st.caption("Next: Generate & View Briefs ➡️ (pages/3_brief_viewer.py)")


if __name__ == "__main__":
    main()
