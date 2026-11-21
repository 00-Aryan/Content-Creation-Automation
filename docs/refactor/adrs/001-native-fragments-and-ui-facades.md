# ADR 001: Native Streamlit Fragments and Service Facade Layer Isolation

- **Status:** PROPOSED
- **Date:** 2026-11-21
- **Deciders:** `spec-architect`, `phase-orchestrator`
- **Target Phase:** Phase 2B (`refactor/phase2b-ui-and-fragments`)

---

## 1. Context & Problem Statement

During the Phase 2 architectural audit and live UI inspection (`docs/audit/ui-playwright-audit.md`), two major structural defects and design fragilities were identified in the Streamlit presentation tier:

1. **Massive Layer Boundary Violations (`UI-002`, `UI-003`):**
   - The operations dashboard (`src/content_creation/ui/pages/6_operations_dashboard.py`) and timeline component (`src/content_creation/ui/components/timeline.py`) bypass `ServiceClient` and `ApplicationContext`.
   - On every page render or UI interaction, `6_operations_dashboard.py` directly executes `sqlite3.connect()` on 6 distinct backend databases (`jobs.db`, `locks.db`, `events.db`, `notifications.db`, `metrics.db`, `audit.db`), triggers DDL schema creation routines (`create_*_schema`), and instantiates 11 internal infrastructure classes inline.
   - This architectural bypass violates `AGENTS.md` §6.1, creates high risk of `sqlite3.OperationalError: database is locked` under concurrent Streamlit page renders on Windows, and produces 18 AST layer boundary violations.

2. **Fragile Custom SSE Server and Broken JS Iframe (`UI-004`, `ERR-004`):**
   - The notification system embeds a custom HTTP Server-Sent Events daemon (`NotificationSSEServer` in `src/content_creation/notifications/streaming/server.py`) binding to TCP port 8502.
   - The Streamlit dashboard (`src/content_creation/ui/app.py`) embeds a raw JavaScript `<script>` via `st.components.v1.html()` creating an `EventSource('http://localhost:8502/events')`.
   - The script attempts to bridge events into Streamlit via `window.parent.postMessage`. However, the Streamlit Python runtime has no mechanism to receive or process raw `postMessage` events from embedded iframes without a custom compiled bi-directional React component.
   - On Windows, `localhost` resolves to IPv6 `::1` while the server binds to IPv4 `127.0.0.1`, triggering `PermissionError: [WinError 10013]` (WSAEACCES) socket errors. This produces 12 persistent test failures in `tests/test_notification_streaming.py` and continuous `net::ERR_CONNECTION_REFUSED` reconnect noise in the browser developer console.
   - Furthermore, `st.components.v1.html` is deprecated by Streamlit and scheduled for removal.

---

## 2. Decision Drivers

- **Deterministic Windows Execution:** Eliminate fragile TCP socket daemons and cross-platform IPv6 localhost resolution failures on Windows.
- **Architectural Layer Purity:** Enforce strict unidirectional dependencies (`UI -> ServiceClient/DTOs -> Application/Domain -> Persistence`). Presentation pages must never import SQLite repositories, execute DDL, or acquire raw database connection handles.
- **Modern Framework Idioms:** Leverage native Streamlit 1.58+ primitives (`@st.fragment`) designed specifically for partial page re-rendering and periodic polling without full script reruns.
- **Testability & Reliability:** Enable 100% headless automated testing via `streamlit.testing.v1.AppTest` without requiring background daemon threads or live TCP network ports.
- **Clean Pytest Suite:** Eliminate the 12 pre-existing socket test failures (`ERR-004`) so the test suite converges toward 100% pass rate.

---

## 3. Considered Options

### Option 1: Native Streamlit `@st.fragment` Polling via `ServiceClient` Facade (Chosen)
- Replace the SSE server, iframe, and `postMessage` bridge with Streamlit's official `@st.fragment(run_every="5s")` decorator.
- The notification badge and notification summary panel isolate their re-rendering scope to bounded UI fragments that poll `ServiceClient` methods (`get_notification_unread_count()`, `get_notification_summary()`).
- All operations dashboard queries are encapsulated behind `ServiceClient.get_operations_snapshot()`, which handles repository coordination and closes connection handles cleanly.
- Retire `NotificationSSEServer` and remove the 12 failing socket tests.

### Option 2: Retain SSE Server and Build Bi-Directional Custom Streamlit Component
- Write a compiled React/TypeScript custom component using `streamlit-component-lib` to handle `postMessage` and trigger `Streamlit.setComponentValue()`.
- Fix the IPv6 socket issue by hardcoding `127.0.0.1` and adjusting Windows socket permissions.
- *Rejected because:* Introduces Node.js/npm build toolchain dependencies (currently absent on host environment), adds unnecessary architectural complexity, and violates the local-first, lightweight mandate.

### Option 3: Full Page Polling via `st_autorefresh`
- Use third-party package `st_autorefresh` to trigger full-page script reruns every 5 seconds.
- *Rejected because:* Causes jarring whole-page UI flickers, resets interactive form inputs/selectors, adds an unmaintained external dependency, and is rendered obsolete by native `@st.fragment`.

---

## 4. Decision Outcome

**Chosen: Option 1.**

### Detailed Architectural Specifications:

1. **Service Facade Boundary:**
   - All presentation code in `src/content_creation/ui/pages/` must strictly interact with backend subsystems through `src/content_creation/ui/services/client.py`.
   - `ServiceClient` exposes:
     - `get_operations_snapshot() -> DashboardSnapshot`: Coordinates telemetry, queue, lock, event, and audit queries in a single encapsulated call.
     - `get_event_timeline(entity_type=None, entity_id=None, limit=50) -> List[Any]`: Returns formatted event records for UI consumption.
     - `get_notification_unread_count() -> int` and `get_notification_summary()`: Read-only notification metrics.
     - `storyboard_file_exists(topic_id: str) -> bool`: Explicit filesystem existence check to distinguish missing storyboards from corrupted 0-byte JSON files.
   - `6_operations_dashboard.py` and `timeline.py` are scrubbed of all `sqlite3`, DDL schema, and repository imports.

2. **Native Fragment Implementation:**
   - In `src/content_creation/ui/components/notification_panel.py`, define:
     ```python
     @st.fragment(run_every="5s")
     def render_notification_badge_fragment(client: ServiceClient) -> None:
         unread = client.get_notification_unread_count()
         render_notification_badge(unread)
     ```
   - In `src/content_creation/ui/app.py`, invoke `render_notification_badge_fragment(client)` and remove `render_sse_client()`.
   - The dashboard and sidebar update reactively every 5 seconds without triggering a rerun of the orchestration forms or expensive page elements.

3. **Retirement of Legacy SSE Subsystem:**
   - `src/content_creation/ui/components/sse_client.py`: Gutted / retired from all UI imports.
   - `src/content_creation/notifications/streaming/server.py`: Deprecated / retired.
   - `tests/test_notification_streaming.py`: Retire 12 socket integration tests asserting raw TCP HTTPConnection behaviors. Retain non-socket unit tests for notification repository, publisher, and maintenance logic.

---

## 5. Consequences

### Positive Consequences
- **0 AST Layer Violations:** The entire UI layer (`src/content_creation/ui/`) achieves 100% architectural boundary compliance.
- **Zero Windows Socket Contention (`ERR-004`):** Eliminates 12 socket test failures and removes port 8502/18503 conflicts.
- **Partial Reruns Without UI Jitter:** `@st.fragment` ensures only the badge and notification summary widgets rerun on timer ticks, preserving active user inputs and filter selections.
- **Headless Testability:** UI pages and components can be tested deterministically with `streamlit.testing.v1.AppTest` in headless CI/CD environments without network daemon dependencies.
- **Future-Proofing (`UI-006`):** Eliminates deprecated `st.components.v1.html` usage.

### Negative Consequences & Trade-Offs
- **5-Second Latency Window:** Notification updates occur on a 5-second polling interval rather than sub-second real-time push.
- *Mitigation:* In an editorial workflow platform where human authors create and review educational assets, 5-second polling latency is completely imperceptible and eliminates substantial architectural complexity.

---

## 6. Compliance & Verification

- **AST Verification Gate:**
  ```powershell
  # Verified by contract-verifier: must return 0 layer violations
  uv run python -c "import ast; ..."
  ```
- **Streamlit Headless Testing:**
  ```powershell
  uv run python -m pytest tests/test_ui_pages.py tests/test_ui_client.py -v
  ```
- **Socket Retirement Verification:**
  ```powershell
  uv run python -m pytest tests/test_notification_streaming.py -o addopts="" -p no:cov -v
  # Must pass 100% with 0 socket permission failures
  ```
