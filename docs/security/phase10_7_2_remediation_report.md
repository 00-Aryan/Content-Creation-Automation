# Phase 10.7.2 Security Boundary Hardening Remediation Report

**Date:** 2026-06-03  
**Status:** COMPLETE  
**Reference Report:** [phase10_7_security_audit.md](./phase10_7_security_audit.md)  
**Deployment Plan Reference:** [render_deployment_plan.md](../deployment/render_deployment_plan.md)  

---

## 1. Executive Summary

This report details the architectural boundary hardening remediation applied to the `content-creation` pipeline. The goal was to enforce a strict boundary: `UI -> ServiceClient -> Application Services -> Provider Layer -> Credential Resolution`, removing all credential resolution logic, environment checks, and provider details from user-facing screens and dashboards.

---

## 2. Root Cause Analysis

Prior to this hardening phase:
1. **UI Credential Resolution Leakage:** Streamlit UI services resolved secrets from environment variables or `st.secrets` during the context initialization phase.
2. **Application Layer Pollution:** Application services directly resolved backend credentials from environment variables (`os.environ.get("GEMINI_API_KEY")`) and threw exceptions if missing.
3. **Implementation Detail Exposure:** Dashboard components leaked provider details (e.g. displaying "Provider" columns showing "gemini" / "openrouter").

---

## 3. Boundary Hardening Implementation

We fully decoupled credential resolution from both the presentation layer and the application service layer, assigning it to a dedicated bottom layer.

### 3.1 Dedicated Credential Resolution Layer
We created a new module `src/content_creation/inference/credentials.py` containing `resolve_credential(key: str)`. This is now the *only* place in the codebase that references `st.secrets` or `os.environ`:
```python
def resolve_credential(key: str) -> Optional[str]:
    # 1. Environment Variable takes precedence
    val = os.environ.get(key)
    if val:
        return val

    # 2. Fallback to Streamlit secrets (safely)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            return st.secrets.get(key)
    except Exception:
        pass
    return None
```

### 3.2 Decoupled Provider Layer
The `InferenceManager` constructor and individual LLM provider implementations (`GeminiProvider`, `OpenRouterProvider`) were modified to make their `api_key` parameter optional. If no key is passed:
- They automatically query the bottom `resolve_credential` helper.
- Standard errors like `ValueError("API key not found...")` are raised at the provider layer instead of the application services layer.

### 3.3 Cleansed Application Service Layer
All environment/secrets resolution logic was removed from the following application services:
- `BriefGenerationService`
- `ContentIntelligenceService`
- `StoryboardService`
- `AssetGenerationService`

The services no longer validate or resolve credentials; they simply instantiate or invoke the provider/generation layer, letting the bottom layer resolve credentials.

### 3.4 Cleansed UI & ServiceClient Layers
- **No Secrets Resolving:** Removed the `st.secrets` populating block from `get_context()` inside `src/content_creation/ui/services/client.py`.
- **Decoupled API Availability Check:** Modified `ServiceClient.is_generation_available()` to check `InferenceManager.is_available()`, rather than calling `os.environ.get()`.
- **Sanitized presentation components:**
  - Removed "Provider" column from recent pipeline activity logs inside `src/content_creation/ui/app.py`.
  - Retained clean system health status dashboard output: "Generation Service: Available" / "Generation Service: Unavailable".

---

## 4. Updates to render_deployment_plan.md

No configuration script changes are required. The required environment variables for Render deployment remain unchanged:
- `GEMINI_API_KEY` (Required for content synthesis)
- `OPENROUTER_API_KEY` (Optional fallback)
- `CONTENT_FACTORY_ROOT` (Mutable data state root)

Credential resolution is now cleanly isolated to the bottom of the execution stack, meaning UI containers run securely.
