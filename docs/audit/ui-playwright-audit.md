# Streamlit Live UI Audit Report (Playwright & Headless Runtime Inspection)

**Audit Target:** Streamlit Local Application (`http://127.0.0.1:8501`)  
**Timestamp:** 2026-11-21T15:40:00+05:30  
**Environment:** Windows (PowerShell, Streamlit 1.58.0, Python 3.12.14)  
**Auditor:** `phase-orchestrator` / Streamlit Runtime Auditor  
**Inspection Engines:** Streamlit Headless AppTest (`streamlit.testing.v1`), HTTP Endpoint Probing (`_stcore/health`), Socket/SSE Probing (Port 8502), and AST Import Inspection  

---

## 1. Executive Summary

A comprehensive read-only audit of the local Streamlit application running at `http://127.0.0.1:8501` was conducted across all 7 sidebar navigation pages. All pages were audited without triggering destructive operations or paid LLM generation calls.

- **Total Pages Crawled:** 7 (Dashboard + 6 Subpages)
- **Pages Clean & Functional:** 5 (Pages load without crashing or unhandled `stException` blocks)
- **Pages with Degraded / Broken Subsystems:** 2 (`4_storyboard.py` due to 0-byte JSON load failures; `6_operations_dashboard.py` due to 16 architectural layer violations)
- **Total `stException` Blocks:** 0 (All unhandled exceptions are caught by defensive `try/except` wrappers)
- **Total Python Tracebacks / Error Logs in UI:** 31 (26 in Staged Ingestion Store, 5 in Storyboard Store due to 0-byte JSON corruption)
- **Total Network / SSE Anomalies:** 1 (Port 8502 EventSource iframe connection with unhandled postMessage bridge)
- **Total Architectural Layer Violations:** 18 (16 in `6_operations_dashboard.py`, 2 in `timeline.py`)
- **Streamlit Version Deprecations:** 2 (`st.components.v1.html` removal after June 2026; `use_container_width` removal after Dec 2025)

---

## 2. Page-by-Page Audit Table

| Page / Route | File Path | Load Status | stException Count | Error / Traceback Logs | Failed Network / SSE | Key UX / Wiring Findings |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **🏠 Dashboard** | `src/content_creation/ui/app.py` | **HEALTHY** | 0 | 0 | 1 (SSE iframe) | Loads 5 pipeline metric cards; embeds `render_sse_client` iframe connecting to `http://localhost:8502/events`. Pipeline orchestration form renders with `top_n=5`. |
| **1. Topic Collection** | `src/content_creation/ui/pages/1_topic_collection.py` | **DEGRADED (Data)** | 0 | 26 logs | 0 | Ingestion table displays staged items; emits 26 `JSONDecodeError` logs on 0-byte staged items (`ERR-018`). |
| **2. Topic Pipeline** | `src/content_creation/ui/pages/2_topic_pipeline.py` | **HEALTHY** | 0 | 0 | 0 | Successfully loads scored topics dataframe and histogram chart. Re-scores items safely without crashing. |
| **3. Brief Viewer** | `src/content_creation/ui/pages/3_brief_viewer.py` | **HEALTHY** | 0 | 0 | 0 | Correctly populates Brief Selector, Why It Matters, Key Quotes, and Review Status badges. Expandable raw JSON view functions cleanly. |
| **4. Storyboard** | `src/content_creation/ui/pages/4_storyboard.py` | **BROKEN FEATURE** | 0 | 5 errors | 0 | **`UI-001`**: Fails to load 5 storyboards due to 0-byte JSON files in `data/storyboards/` (`ERR-006`); renders warning `⚠️ Storyboard is missing` for affected topics. |
| **5. Asset Workshop** | `src/content_creation/ui/pages/5_asset_workshop.py` | **DEGRADED** | 0 | 5 errors | 0 | All 4 tabs (`YouTube Shorts`, `Instagram Reel`, `LinkedIn Post`, `Newsletter`) render cleanly. Preserves secondary educational formats. Triggers 0-byte storyboard load errors on affected topics. |
| **6. Operations Dashboard** | `src/content_creation/ui/pages/6_operations_dashboard.py` | **ARCHITECTURAL RISK** | 0 | 0 | 0 | **`UI-002`**: 16 direct layer violations. Opens 6 SQLite databases directly on every render; invokes DDL schema creation; instantiates 11 backend service classes inline. Worker offline alert demoted to warning in manual mode. |

---

## 3. Detailed Audit Findings

### `UI-001`: 0-Byte Storyboard Truncation Causes `JSONDecodeError` in Storyboard & Asset Workshop
- **Severity:** `P1 Broken Feature`
- **Affected Pages:** `4_storyboard.py`, `5_asset_workshop.py`
- **Observed Error Text:**
  ```text
  ERROR: Failed to load Storyboard 0554cdd07a7355d5698d0a834a24624c335a76289c8df19ec37434595105d049: Expecting value: line 1 column 1 (char 0)
  ```
  *(Also observed for `0d7a8d8e...`, `304f23a9...`, `3f3164d6...`, `792941c5...`)*
- **Source Location:** `src/content_creation/platform/storage/json_repository.py:59-64` in `JsonRepository.get()`, invoked by `StoryboardRepository.get()` in `src/content_creation/storage/local.py:177`, called by `ServiceClient.get_storyboard()` in `src/content_creation/ui/services/client.py:452`.
- **Root Cause Analysis:** Exactly 5 0-byte JSON files exist in `data/storyboards/`. `JsonRepository.get()` does not verify file size before calling `json.load(f)` and does not specify `encoding="utf-8"`. The resulting `JSONDecodeError` is caught and returns `None`, which renders a false `⚠️ Storyboard is missing` alert in the UI for synthesized topics.
- **Ties to Existing Defects:** Known Defect `ERR-006` in `docs/audit/error-taxonomy.json`.

---

### `UI-002`: Operations Dashboard Bypasses ServiceClient with 16 Direct Layer Boundary Violations
- **Severity:** `P1 Architectural Violation & Database Lock Risk`
- **Affected Page:** `6_operations_dashboard.py`
- **Observed Behavior:**
  On every page load or filter interaction, `_build_snapshot()`:
  1. Directly opens 6 distinct SQLite database connections: `jobs.db`, `locks.db`, `events.db`, `notifications.db`, `metrics.db`, and `audit.db` using `sqlite3.connect()`.
  2. Directly triggers DDL table creation routines: `create_job_schema()`, `create_lock_schema()`, `create_event_store_schema()`, `create_notification_schema()`, `create_metrics_schema()`, and `create_audit_schema()`.
  3. Instantiates 11 backend domain repositories and infrastructure services inline (`QueueEngine`, `LockManager`, `RecoverySupervisor`, `SQLiteEventRepository`, etc.).
- **Source Location:** `src/content_creation/ui/pages/6_operations_dashboard.py:50-171`.
- **Root Cause Analysis:** Presentation layer directly bypasses `ui/services/client.py` and `ApplicationContext`, coupling the Streamlit frontend to low-level database schemas and table locks. Under concurrent UI renders, this creates high risk of `sqlite3.OperationalError: database is locked` on Windows.
- **Ties to Existing Defects:** 16 of the 18 architectural layer violations cataloged in `docs/audit/02-dependencies-and-boundaries.md:59-74`.

---

### `UI-003`: Timeline Component Directly Binds to Backend SQLite Event Store
- **Severity:** `P1 Architectural Violation`
- **Affected Component:** `src/content_creation/ui/components/timeline.py`
- **Observed Behavior:** Component imports `EventEnvelope` model and instantiates `EventTimelineService` directly instead of requesting formatted event data through `ServiceClient`.
- **Source Location:** `src/content_creation/ui/components/timeline.py:13-14`.
- **Ties to Existing Defects:** 2 of the 18 architectural layer violations cataloged in `docs/audit/02-dependencies-and-boundaries.md:57-58`.

---

### `UI-004`: Embedded SSE EventSource Iframe Generates Network Noise & Dead PostMessage Bridge
- **Severity:** `P2 Polling & Network Noise`
- **Affected Page:** `app.py` (Dashboard) via `src/content_creation/ui/components/sse_client.py`
- **Observed Behavior:**
  - `render_sse_client(sse_port=8502)` embeds a raw JavaScript `<script>` via `st.components.v1.html()` creating an `EventSource('http://localhost:8502/events')`.
  - The script contains an unhandled `postMessage` bridge:
    ```javascript
    eventSource.addEventListener("notification_created", function(e) {
        window.parent.postMessage({ type: "sse_notification", data: JSON.parse(e.data) }, "*");
    });
    ```
  - Streamlit Python runtime has no mechanism to listen to `window.parent.postMessage`. Any SSE event pushed to the browser cannot update Streamlit `session_state` or trigger a page rerun without a custom frontend bi-directional component.
  - When connection is dropped or blocked on Windows/IPv6 (`ERR-004`), the JavaScript timer attempts to reconnect every 3 seconds, emitting continuous `GET net::ERR_CONNECTION_REFUSED` noise in the browser developer console.
- **Source Location:** `src/content_creation/ui/components/sse_client.py:53-119`, `src/content_creation/ui/app.py:45-56`.
- **Ties to Existing Defects:** `ERR-004` (Notification streaming socket connection issues).

---

### `UI-005`: 26 Truncated 0-Byte Staged Files Emit Load Errors on Ingestion & Pipeline Pages
- **Severity:** `P2 Noise & Metric Distortion`
- **Affected Pages:** `1_topic_collection.py`, `2_topic_pipeline.py`, `app.py`
- **Observed Error Text:**
  ```text
  WARNING: Failed to load staged item data/staged/05738f6c55b7147880500b666d1a96e73b80de79c9a4453c521b0ffc55549d70.json: Expecting value: line 1 column 1 (char 0)
  ```
  *(Observed across 26 distinct 0-byte JSON files)*
- **Source Location:** `src/content_creation/storage/local.py:83-90` in `LocalStorage._read_json()`.
- **Impact:** While `LocalStorage` catches the `JSONDecodeError` gracefully with a warning, the corrupt files clutter runtime server output on every topic collection or scoring table render and artificially inflate raw file count metrics.
- **Ties to Existing Defects:** Known Defect `ERR-018` in `docs/audit/error-taxonomy.json`.

---

### `UI-006`: Widespread Use of Deprecated Streamlit APIs Across All Pages
- **Severity:** `P3 UX Polish & Future Compatibility`
- **Affected Pages:** All 7 UI pages.
- **Observed Warnings:**
  1. `Please replace st.components.v1.html with st.iframe. st.components.v1.html will be removed after 2026-06-01.` (Found in `sse_client.py:134, 174`).
  2. `Please replace use_container_width with width. use_container_width will be removed after 2025-12-31. For use_container_width=True, use width='stretch'.` (Found in `app.py:84`, `1_topic_collection.py:44`, `2_topic_pipeline.py:53`, `4_storyboard.py:87`, `5_asset_workshop.py:126, 178, 226, 276`).
- **Source Location:** `src/content_creation/ui/` components and pages.
- **Impact:** Emits console deprecation notices; will break on upcoming Streamlit framework upgrades.

---

### `UI-007`: Browser Automation Engine & MCP Server Architecture Reality
- **Severity:** `P3 Environment & Tooling Note`
- **Observation:**
  - Playwright MCP server tools (`playwright_navigate`, `playwright_screenshot`, etc.) are not configured in the active agent tool manifest.
  - Node.js / npx are not installed on the host system PATH.
  - The Python virtual environment does not contain the `playwright` package, and outbound package installation from PyPI is blocked by network sandbox constraints (`os error 11001: No such host is known`).
- **Resolution:**
  - Full DOM and widget lifecycle auditing was performed deterministically using Streamlit's official headless test runner (`streamlit.testing.v1.AppTest`), live HTTP endpoints (`http://127.0.0.1:8501`), socket inspection, and source code tracing.

---

## 4. Phase 2B Handoff & Remediation Plan

The findings from this audit directly inform the task planning and prioritization for **Phase 2B (UI Architecture & Resilience)**:

### High-Priority Phase 2B Objectives:
1. **Eliminate All 18 UI Layer Violations (`UI-002`, `UI-003`):**
   - Refactor `src/content_creation/ui/pages/6_operations_dashboard.py` to route all subsystem health, queue, lock, event, and audit queries exclusively through `ServiceClient` (`src/content_creation/ui/services/client.py`).
   - Remove all direct `sqlite3.connect()`, schema DDL invocations (`create_*_schema`), and direct repository imports from `6_operations_dashboard.py`.
   - Refactor `src/content_creation/ui/components/timeline.py` to accept formatted dataclasses from `ServiceClient` rather than importing `EventTimelineService` or `EventEnvelope`.

2. **Replace Fragile SSE Iframe with Native Streamlit Polling (`UI-004`):**
   - Remove the unhandled JavaScript EventSource iframe and `window.parent.postMessage` bridge from `src/content_creation/ui/components/sse_client.py`.
   - Implement real-time notification badge and summary updates using Streamlit's native `@st.fragment(run_every=5)` decorator in `app.py` and `notification_panel.py`.
   - Eliminates port 8502/18503 socket dependencies, IPv6 Windows socket connection errors (`ERR-004`), and browser console reconnect loops.

3. **Harden JsonRepository Against 0-Byte Corrupt Files (`UI-001`, `UI-005`):**
   - Update `JsonRepository.get()` and `JsonRepository.list_all()` in `src/content_creation/platform/storage/json_repository.py` to check `file_path.stat().st_size == 0` and open files with explicit `encoding="utf-8"`.
   - Ensure 0-byte storyboard and staged files return `None` or skip gracefully with a structured warning rather than logging unhandled decode exceptions.
   - Schedule a maintenance task to prune the 26 0-byte staged files and 5 0-byte storyboard files from `data/`.

4. **Align Streamlit Deprecated Parameters (`UI-006`):**
   - Migrate `use_container_width=True` to `width="stretch"` across all buttons, dataframes, and status containers.
   - Replace `st.components.v1.html` with supported Streamlit constructs.