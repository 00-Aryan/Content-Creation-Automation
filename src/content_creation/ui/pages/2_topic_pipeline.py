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
    
    # Weight Adjustments UI
    st.markdown("### 🎛️ Weight Configuration Preview")
    st.caption("These sliders display the current scoring weights from `config/scoring.yaml`. Adjusting them does not affect scoring at runtime. See BACKLOG-001 for future implementation.")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        usefulness_w = st.slider("Usefulness", 0.0, 1.0, 0.30, 0.05)
    with col2:
        novelty_w = st.slider("Novelty", 0.0, 1.0, 0.25, 0.05)
    with col3:
        credibility_w = st.slider("Credibility", 0.0, 1.0, 0.20, 0.05)
    with col4:
        explainability_w = st.slider("Explainability", 0.0, 1.0, 0.15, 0.05)
    with col5:
        hook_w = st.slider("Hook Potential", 0.0, 1.0, 0.10, 0.05)
        
    total_w = usefulness_w + novelty_w + credibility_w + explainability_w + hook_w
    if abs(total_w - 1.0) > 0.001:
        st.warning(f"Preview weights sum to {total_w:.2f}. Actual scoring weights are read from `config/scoring.yaml`.")
    else:
        st.info(f"Preview weights sum to {total_w:.2f}. Actual scoring weights are read from `config/scoring.yaml`.")
        
    st.markdown("### Prioritization Actions")
    run_btn = st.button("⚖️ Score Topics", type="primary")
    
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
            data.append({
                "ID": item.id[:8],
                "Title": item.title,
                "Source": item.source,
                "Category": item.category.value if hasattr(item.category, 'value') else str(item.category),
                "Priority Score": round(item.priority_score, 2),
                "Validation Flags": ", ".join(item.validation_flags) if item.validation_flags else "None",
                "Status": item.status.value if hasattr(item.status, 'value') else str(item.status),
            })
        st.dataframe(data, use_container_width=True)
        
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


if __name__ == "__main__":
    main()
