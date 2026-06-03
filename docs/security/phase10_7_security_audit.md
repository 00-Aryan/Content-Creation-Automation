# Phase 10.7 Security Architecture Audit

**Date:** 2026-06-03  
**Status:** COMPLETE  
**Authoritative Reference:** [v0.6_backend_signoff.md](../release/v0.6_backend_signoff.md)  
**UI Reference:** [page_inventory.md](../ui/page_inventory.md)  
**Deployment Reference:** [render_deployment_plan.md](../deployment/render_deployment_plan.md)  

---

## 1. Executive Summary

This report presents a security architecture audit of the `content-creation` factory pipeline and Streamlit dashboard MVP (v1.0). The audit assesses the security boundaries between the presentation, application, and infrastructure layers, verifies the handling of credentials, analyzes deployment security configurations, checks for information disclosure in artifacts, and details future readiness risks (authentication, multi-user concurrency, API exposure).

### Summary of Verdict
The system successfully isolates storage manipulation and execution logic from the presentation layer (no direct imports of `LocalStorage` or `WorkflowStateManager` in UI scripts). Secrets are excluded from version control and git indexes. However, the system contains architectural boundary smells—particularly around credential resolution residing in the presentation layer and configuration leakage—and lacks multi-user isolation mechanisms.

---

## 2. Findings

### Critical
*   **None.** No active credentials or private keys are checked into version control. No remote code execution (RCE) vectors exist in the current presentation/application adapter mappings.

### High
*   **SSRF (Server-Side Request Forgery) Vulnerability (Future Exposure Risk):** The collection ingestion service (`CollectTopicsService` / `IngestionEngine`) retrieves RSS feeds by parsing URLs via `feedparser`. Currently, feeds are parsed from a static config file [feeds.yaml](file:///home/aryan/May-2026/Content-Creation/config/feeds.yaml). However, if manual feed ingestion or URL inputs are exposed directly in the UI/API without strict host validation or allowlists, it presents a high risk of SSRF, allowing attackers to query internal metadata services (e.g., Render/AWS metadata endpoints at `http://169.254.169.254/`).
*   **Shared Global Context & Session Concurrency Risks:** The UI resolves its context via `@st.cache_resource def get_context()`. This caches the `ApplicationContext` globally across all sessions. Under Streamlit's architecture, this means all concurrent users share the exact same context instance, storage managers, and data directories (`data/`). In a multi-user environment, this leads to race conditions, concurrent file overwrite conflicts, and cross-session data leakage.
*   **Unbounded API Consumption & Denials of Cost (DoC):** The pipeline execution dashboard enables a visitor to trigger live end-to-end content generation runs via `run_full_pipeline`. Since the application has no authentication or rate limiting, any anonymous visitor can trigger multiple Gemini API calls, leading to potential denial of service through token quota exhaustion and financial costs.

### Medium
*   **UI Layer Credential Resolution Ownership (Design Smell):** The helper function `get_api_key()` resides in the presentation adapter layer [client.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/services/client.py). The UI pages then resolve this key and pass it manually as parameters down to Application Services (e.g., `client.generate_briefs(..., api_key=resolved_key)`). This violates clean architecture: configuration and credential resolution should be owned by the bootstrap or infrastructure config loader, not the UI presentation controllers.
*   **Hardcoded Model Configurations:** Model engine identifiers (such as `"gemini-2.5-flash"`) are hardcoded inside the provider classes (e.g., `GeminiProvider` inside [gemini.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/inference/providers/gemini.py)). This prevents configuration-driven runtime overrides and forces code changes to update target models.
*   **Lack of User Identity & Audit Logs:** State transitions logged by `WorkflowStateManager` and general pipeline log files record what action was taken and when, but they lack user identity context. This makes non-repudiation impossible to establish in multi-user settings.

### Low
*   **Pre-Release Package Resolution Dependency:** The `pyproject.toml` depends on open-ended packages (e.g., `"streamlit>=1.30.0"`). Although `uv.lock` locks versions locally, version drift could occur if dependency resolution is bypassed or rebuilt on unpinned containers.

---

## 3. Architectural Boundary Violations

The architecture enforces a clean hierarchy: `UI` $\rightarrow$ `ServiceClient` $\rightarrow$ `Application Services` $\rightarrow$ `Infrastructure`. However, we identified two boundary violations:

1.  **Credential Handling in UI:** Presentation scripts are aware of `GEMINI_API_KEY` and are responsible for resolving it via `os.environ` or `st.secrets` before passing it to services. The application services should independently extract credentials from their context or config layer instead of expecting the client to supply them.
2.  **Configuration Leakage:** UI widgets (like `st.sidebar.text_input` and `st.slider("Rate Limit Delay")`) define parameters that dictate backend API client behavior. Business variables (like model names or retry rate limits) should be loaded from YAML configs or env files in the Application/Infrastructure layer, keeping the UI strictly focused on layout rendering.

---

## 4. Secret Management Findings

*   **UI Credential Resolution:** Resolved via `get_api_key` in `client.py` using `os.environ.get("GEMINI_API_KEY")` with a fallback to `st.secrets.get("GEMINI_API_KEY")`. This resolves the Render environment variables successfully.
*   **Secret Leakage in State/Logs/Artifacts:**
    *   *UI State:* The credential input uses `type="password"`, hiding input characters.
    *   *Logs:* Checked `InferenceManager` log structures. Payloads and status outputs log model metadata and duration but **do not** write API keys to log files.
    *   *JSON Viewers:* Raw JSON viewer components render content files (briefs, storyboards, manifests) from the disk. None of these schemas hold credentials or keys.
    *   *Audit Classification:* **ACCEPTABLE** for single-operator console; **DESIGN SMELL** for credential lookup in the presentation layer.

---

## 5. Deployment Security Findings

*   **Secrets File Exposure:** Production configuration does not require `.env` or `secrets.toml` files to be committed. All variables are resolved dynamically from Render environment settings.
*   **Secrets Excluded from Git:** Verified that [gitignore](file:///home/aryan/May-2026/Content-Creation/.gitignore) correctly lists `.env`, and `git ls-files` confirms it is untracked.
*   **Persistent Disk Concern:** The persistent disk is mounted at `/workspace/data`. This isolates dynamic execution states from the application code directories, representing an acceptable separation of concerns.

---

## 6. Artifact Exposure Findings

*   **Raw JSON Viewers:** Display content structures (e.g. [Brief Schema](file:///home/aryan/May-2026/Content-Creation/docs/schema.md)). No metadata fields leak directory structure details or server paths (other than absolute file paths in manifests, which are local to the isolated Render container).
*   **Information Disclosure:** Only generated content assets (video scripts, slide titles, newsletter drafts) are exposed. No database handles, API endpoints, or provider routing tables are disclosed through UI viewers.

---

## 7. Future Security Risks

As the project scales from a single-operator local cockpit to a shared public application, the following architectural choices will present security vulnerabilities:

1.  **Shared Disk Workspace:** Because storage relies on standard JSON files in a single local directory (`data/`), any session user can read, overwrite, or delete artifacts created by another user.
2.  **Lack of Authentication Middleware:** The dashboard has no user lookup or login capabilities. Exposing the Streamlit dashboard on a public Render address makes it accessible to anyone.
3.  **No Authorization (RBAC):** There are no roles defined (e.g., Creator, Editor, Admin). Every authenticated session shares complete write/delete access over manifests and reviews.
4.  **SSRF in Feed Ingestion:** Lack of domain restrictions or query sanitization in URL ingestion parser will allow internal network access if the collection screen accepts arbitrary inputs.

---

## 8. Recommended Remediation Plan

### 8.1 Immediate (Fix Now)
*   **Telemetry Disable Verification:** Verify that the Render start command uses the configuration pointing to `.streamlit/config.toml` to ensure telemetry remains completely disabled on cloud starts.

### 8.2 Before Phase 11 (Prepare for Next Architectural Steps)
*   **Centralize Credential Resolution:** Move `get_api_key()` from `client.py` and page scripts into `ApplicationContext` or an infrastructure-specific configuration module.
*   **Externalize Model Configurations:** Remove hardcoded `"gemini-2.5-flash"` string literals. Define model configurations in `config/inference.yaml` and resolve them through the application context.

### 8.3 Before Multi-User Deployment
*   **Implement Session-Specific Workspaces:** Refactor `LocalStorage` to accept a `user_id` or session namespace, partitioning the `data/` folder into isolated directories per user (e.g., `data/{user_id}/briefs`).
*   **Introduce Authentication & Role-Based Access Control (RBAC):** Deploy a secure authentication wrapper (or FastAPI proxy) that validates JWTs and enforces page access restrictions based on user roles.
*   **Sanitize URL Ingestion (SSRF Protection):** Implement strict domain allowlists and resolution checks (verifying that URL targets do not resolve to local/private loopback addresses like `127.0.0.1` or link-local `169.254.169.254`).

---

## 9. Final Recommendation

> **REQUIRES SECURITY REMEDIATION**
> 
> The system requires design remediation (centralizing credentials, separating configuration layers, and preparing data scopes) before it is suitable for multi-user deployment or public exposure.
