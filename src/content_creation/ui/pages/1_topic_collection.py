"""Streamlit Page 1: Topic Collection Ingestion."""

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
    st.set_page_config(page_title="📥 1. Collect", page_icon="📡", layout="wide")
    init_session_state()
    client = ServiceClient()
    render_api_health(client.is_generation_available())
    
    st.markdown("# 📡 Topic Ingestion & Collection")
    st.markdown("---")

    staged_items = client.list_staged_topics()
    staged_count = len(staged_items)

    # Manual Custom Topic Form
    st.markdown("### ✍️ Add Custom Topic / Idea")
    with st.form("manual_topic_form", clear_on_submit=True):
        col_form1, col_form2 = st.columns([2, 1])
        with col_form1:
            manual_title = st.text_input(
                "Topic Title *",
                placeholder="e.g. FlashAttention-3: Fast and Accurate Attention",
            )
            manual_notes = st.text_area(
                "Notes / Research Excerpt *",
                placeholder="Key findings, abstract, notes, or paper highlights...",
            )
        with col_form2:
            manual_url = st.text_input(
                "Source URL (Optional)",
                placeholder="https://arxiv.org/abs/...",
            )
            manual_source = st.text_input(
                "Source Identifier",
                value="manual",
                placeholder="e.g. manual, arxiv, twitter",
            )
        submit_manual = st.form_submit_button("➕ Add to Staging Queue", type="primary", width="stretch")

        if submit_manual:
            clean_title = manual_title.strip()
            clean_notes = manual_notes.strip()
            if not clean_title:
                st.error("Topic title is required.")
            elif not clean_notes:
                st.error("Notes or research excerpt is required.")
            else:
                try:
                    created_item = client.create_manual_topic(
                        title=clean_title,
                        notes=clean_notes,
                        url=manual_url.strip(),
                        source_id=manual_source.strip(),
                    )
                    st.success(f"Added '{created_item.title}' to staging queue ({created_item.id[:8]}).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add manual topic: {e}")

    st.markdown("---")
    st.markdown("### 📡 Automated Feed Collection")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        source_filter = st.text_input("Source ID Filter (Optional)", value="")
        run_btn = st.button("📡 Collect Topics", type="primary", width="stretch")
        
    with col2:
        if run_btn:
            with st.status("Collecting topics...", expanded=True) as status:
                try:
                    timed = client.collect_topics(source_filter=source_filter or None)
                    res = timed.result
                    st.write(f"Duration: `{timed.duration_seconds:.2f}s`")
                    st.write(f"Items collected: `{res.count}`")
                    status.update(label="Topic collection completed.", state="complete")
                    st.success(f"Collect Topics completed. Found {res.count} items.")
                    st.rerun()
                except Exception as e:
                    status.update(label="Topic collection failed.", state="error")
                    st.error(f"Collect Topics failed: {e}")
        else:
            if staged_count > 0:
                st.info(f"{staged_count} staged topics ready in queue.")
            else:
                st.info("Run feed collection to download papers.")

    st.markdown("---")
    st.markdown("### 📥 Staged Topic Items")
    
    if staged_items:
        data = []
        for item in staged_items:
            data.append({
                "ID": item.id[:8],
                "Title": item.title,
                "Source": item.source,
                "Category": item.category.value if hasattr(item.category, 'value') else str(item.category),
                "Published At": item.published_at,
                "Author": item.author,
            })
        st.dataframe(data, width="stretch")
    else:
        st.info("No staged topics found in pipeline storage. Trigger feed collection above to ingest topics.")

    st.markdown("---")
    try:
        st.page_link("pages/2_topic_pipeline.py", label="Next: Score Topics in Pipeline ➡️", icon="⚖️")
    except Exception:
        st.caption("Next: Score Topics in Pipeline ➡️ (pages/2_topic_pipeline.py)")


if __name__ == "__main__":
    main()
