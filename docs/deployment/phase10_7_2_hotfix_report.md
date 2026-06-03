# Phase 10.7.2 Deployment Credential Resolution Hotfix Report

**Date:** 2026-06-03  
**Status:** COMPLETE  
**Reference Failures:** Pipeline execution error on Render ("No secrets found")  
**Deployment Plan Reference:** [render_deployment_plan.md](file:///home/aryan/May-2026/Content-Creation/docs/deployment/render_deployment_plan.md)  
**Hotfix Target:** Expose unified credentials mapping for Streamlit UI  

---

## 1. Root Cause Analysis

When invoking the "Run Full Pipeline" service wrapper on Render, execution crashed with a `"No secrets found"` exception. 
- **Cause:** [app.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/app.py) was hardcoded to read from `st.secrets.get("GEMINI_API_KEY")`.
- **Mismatch:** Streamlit Community Cloud uses `secrets.toml` mappings exposed via `st.secrets`, but Render deployments expose credentials as standard Unix environment variables (`os.environ`).
- **Result:** Under Render, `st.secrets` returned `None`, bypassing the environment variables and causing the service layer to abort due to missing API keys.

---

## 2. Implementation & Resolution

We introduced a unified credential resolver inside the UI adapter layer to abstract configuration lookups.

### 2.1 Credential Resolver Addition
In [src/content_creation/ui/services/client.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/services/client.py), we added `get_api_key()`:
```python
def get_api_key(key_name: str) -> Optional[str]:
    """Resolves an API key, prioritizing environment variables over Streamlit secrets."""
    api_key = os.environ.get(key_name)
    if api_key:
        return api_key
    try:
        if hasattr(st, "secrets") and st.secrets:
            return st.secrets.get(key_name)
    except Exception:
        pass
    return None
```

### 2.2 Propagation Across UI presentation components
To ensure consistency across the entire UI cockpit, all instances of `os.environ.get()` and `st.secrets.get()` in UI page contexts were refactored to use the unified `get_api_key()` resolver:
1. **[app.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/app.py):** Main orchestration block checks for the key via `get_api_key("GEMINI_API_KEY")` when running the pipeline.
2. **[components/status.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/components/status.py):** API health checks resolve both `GEMINI_API_KEY` and `OPENROUTER_API_KEY` status using the helper.
3. **[pages/3_brief_viewer.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/pages/3_brief_viewer.py):** Key input placeholder initialization and brief generation hooks use the resolver.
4. **[pages/4_storyboard.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/pages/4_storyboard.py):** Sidebar placeholder and generation execution actions use the resolver.
5. **[pages/5_asset_workshop.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/pages/5_asset_workshop.py):** Generation actions for asset suites resolve keys through the resolver.

---

## 3. Local Verification Results

- **Unit tests:** Run `uv run pytest`. All **245 tests pass successfully** with zero regressions.
- **Mock Verification:** Sourcing credentials via environment variables correctly populates health indicators and execution services. Bypassing environment variables and fallback simulating Streamlit `secrets` (via mock `st.secrets`) correctly falls back to values without errors.

---

## 4. Updates to render_deployment_plan.md

No changes to deployment commands or start scripts are required. The fix is purely code-isolated to the presentation adapter layer:
- Render environment variables (`GEMINI_API_KEY` and optional `OPENROUTER_API_KEY`) will now be resolved directly by the dashboard presentation layer.
- Streamlit Community Cloud deployments will continue to use `secrets.toml` correctly as a fallback.
