"""Credential Resolution layer for resolving sensitive keys and environment variables."""

import os
from typing import Optional


def resolve_credential(key: str) -> Optional[str]:
    """Resolves credentials from the environment, falling back to Streamlit secrets if available."""
    # 1. Environment Variable has precedence
    val = os.environ.get(key)
    if val:
        return val

    # 2. Fallback to Streamlit secrets (only check if Streamlit is imported / active)
    try:
        import streamlit as st
        # Check if st.secrets is available and has the key
        if hasattr(st, "secrets") and st.secrets:
            return st.secrets.get(key)
    except Exception:
        pass

    return None
