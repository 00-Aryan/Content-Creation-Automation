"""Streamlit Page 2: Topic Collection Ingestion."""

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
    st.set_page_config(page_title="Topic Collection", page_icon="📡", layout="wide")
    init_session_state()
    client = ServiceClient()
    render_api_health(client.is_generation_available())
    
    st.markdown("# 📡 Topic Ingestion & Collection")
    st.markdown("---")
    
    st.markdown("### Ingestion Actions")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        source_filter = st.text_input("Source ID Filter (Optional)", value="")
        run_btn = st.button("📡 Collect Topics", type="primary", use_container_width=True)
        
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
                except Exception as e:
                    status.update(label="Topic collection failed.", state="error")
                    st.error(f"Collect Topics failed: {e}")
        else:
            st.info("Run feed collection to download papers.")

    st.markdown("---")
    st.markdown("### 📥 Staged Topic Items")
    
    staged_items = client.list_staged_topics()
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
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No staged topics found in pipeline storage. Trigger feed collection above to ingest topics.")


if __name__ == "__main__":
    main()
