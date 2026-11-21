# Task Specification: Phase 2B — UI Architecture, Native Fragments & Storage Resilience

- **Phase ID:** `2B-ui-and-fragments`
- **Target Branch:** `refactor/phase2b-ui-and-fragments` branched from `main`
- **Prerequisites:** `Phase 2A merged into main` (Commit `b09f85b`)
- **Applicable Workspace Skills:**
  - `.agents/skills/windows-python-hygiene/SKILL.md`
  - `.agents/skills/security-and-cost-guard/SKILL.md`
- **Associated Architecture Decision Record:**
  - `docs/refactor/adrs/001-native-fragments-and-ui-facades.md`

---

## 1. Governance & Explicit Scope Unfreezes (`AGENTS.md` §14)

- **Frozen Paths Evaluation:**
  - `src/content_creation/models/`: **NOT TOUCHED** (Strictly frozen; zero schema modifications)
  - `src/content_creation/generation/`: **NOT TOUCHED** (Strictly frozen; asset/brief generators untouched)
  - `prompts/`: **NOT TOUCHED** (Strictly frozen; all prompt templates untouched)
  - `docs/schema.md`: **NOT TOUCHED** (Strictly frozen; data contracts unchanged)
- **Secondary Channel Preservation Invariant:**
  - Explicit confirmation that `newsletter` (`src/content_creation/models/newsletter.py`, `src/content_creation/generation/newsletter.py`, `prompts/newsletter.md`) and `linkedin_post` (`prompts/linkedin_post.md`) are preserved **100% intact**.
  - All UI tabs, selectors, and review components for `Newsletter Copy` and `LinkedIn Post` in `src/content_creation/ui/pages/5_asset_workshop.py` must remain fully functional.

---

## 2. Objective & Defect Resolution Scope

Phase 2B executes a surgical refactoring of the Streamlit presentation tier, resolving architectural layer violations, eliminating fragile network socket streaming on Windows, hardening the storage repository against corrupted/0-byte artifacts, and aligning deprecated Streamlit parameters with the installed Streamlit 1.58 runtime:

1. **Eliminate All 18 UI Layer Violations (`UI-002`, `UI-003`):**
   - Decouple `src/content_creation/ui/pages/6_operations_dashboard.py` from direct SQLite connections (`sqlite3.connect()`), inline DDL schema creation routines (`create_*_schema`), and inline repository instantiations. Route all dashboard queries exclusively through `ServiceClient.get_operations_snapshot()`.
   - Decouple `src/content_creation/ui/components/timeline.py` from raw SQLite event store imports, routing timeline queries through `ServiceClient.get_event_timeline()`.
   - Achieve **0 UI layer violations** (0 architectural violations repository-wide).

2. **Retire Fragile SSE Server & Iframe in Favor of Native Streamlit `@st.fragment` (`UI-004`, `ERR-004`, `DEAD-004`):**
   - Replace the broken JavaScript `EventSource` iframe and unhandled `window.parent.postMessage` bridge with native Streamlit `@st.fragment(run_every="5s")` polling in `notification_panel.py` and `app.py`.
   - Retire the background `NotificationSSEServer` daemon and its 12 failing Windows IPv6 socket tests (`PermissionError: [WinError 10013]` WSAEACCES in `tests/test_notification_streaming.py`), moving the pytest suite toward 100% green.

3. **Harden `JsonRepository` Against 0-Byte and Non-UTF-8 Files (`UI-001`, `ERR-006`):**
   - Add explicit `encoding="utf-8"` with fallback to `cp1252` and defensive `st_size == 0` guards in `src/content_creation/platform/storage/json_repository.py`.
   - Update `JsonRepository.save()` to use Windows-safe atomic writes (`tmp_file` rename via `os.replace`), preventing future 0-byte truncation on interrupted writes.
   - Update `4_storyboard.py` and `5_asset_workshop.py` to differentiate cleanly between "not yet generated" and "corrupt artifact on disk" without leaking unhandled `JSONDecodeError` logs.

4. **Version-Verified Deprecation & Dead-Code Cleanup (`UI-006`, `DEAD-003`):**
   - Eliminate deprecated `use_container_width=True` in favor of `width="stretch"` across refactored pages, validated against Streamlit 1.58.
   - Remove dead, unreferenced wrapper methods `DEAD-003` from `src/content_creation/ui/services/client.py`.

- **Defects & Drift Resolved:**
  - `UI-001`: 0-byte storyboard JSON load failures (`ERR-006`)
  - `UI-002`: Operations dashboard direct SQLite and DDL layer violations
  - `UI-003`: Timeline component direct backend SQLite bindings
  - `UI-004`: Embedded SSE iframe and unhandled postMessage bridge (`ERR-004`)
  - `UI-006`: Streamlit deprecation warnings (`st.components.v1.html`, `use_container_width`)
  - `ERR-004`: 12 failing Windows socket permission tests in `tests/test_notification_streaming.py`
  - `ERR-006`: `JsonRepository` 0-byte truncation crash during storyboard loading
  - `DEAD-003`: 6 unreferenced legacy service client wrapper properties in `client.py`
  - `DEAD-004`: Unreferenced `active_client_count` in `connection_manager.py`

---

## 3. Atomic Commit Plan

Ordered, single-concern commits to be executed sequentially by `refactor-executor`:

### Commit 1: `fix(storage): harden JsonRepository against 0-byte and non-UTF-8 corrupt files`
- **Files to Touch:**
  - `src/content_creation/platform/storage/json_repository.py` (Lines 29-65: explicit `encoding="utf-8"`, `file_path.stat().st_size == 0` guard, `cp1252` fallback with warning, atomic `os.replace` save)
  - `tests/test_json_repository.py` (New domain test suite verifying 0-byte handling, UTF-8 unicode encoding, and atomic writes)
- **Defect IDs Addressed:** `UI-001`, `ERR-006` (and defensively mitigates `ERR-018`)
- **Acceptance Criteria:**
  - `JsonRepository.get()` returns `None` and logs a structured `WARNING` (not an unhandled `ERROR` or traceback) when encountering a 0-byte or corrupted JSON file.
  - `JsonRepository.list_all()` skips 0-byte files with a warning and loads all valid JSON files.
  - `JsonRepository.save()` writes atomically to `.<id>.tmp` in the same directory and renames via `os.replace()`, passing `encoding="utf-8"`.
  - Targeted test `uv run python -m pytest tests/test_json_repository.py -v` passes 100%.

### Commit 2: `refactor(ui): decouple operations dashboard and timeline via ServiceClient facade`
- **Files to Touch:**
  - `src/content_creation/ui/services/client.py` (Lines 115-180, 450-522: add `get_operations_snapshot()`, `get_event_timeline()`, `storyboard_file_exists()`; remove dead properties `DEAD-003`)
  - `src/content_creation/ui/pages/6_operations_dashboard.py` (Lines 24-286: remove all `sqlite3.connect()`, DDL schema initialization, and inline repository imports; delegate snapshot generation to `client.get_operations_snapshot()`)
  - `src/content_creation/ui/components/timeline.py` (Lines 13-68: remove backend `EventRecord` and `EventTimelineService` imports; accept formatted event DTOs from `ServiceClient`)
  - `tests/test_ui_client.py` (New domain test suite verifying `ServiceClient.get_operations_snapshot()` and `get_event_timeline()` without SQLite lock contention)
- **Defect IDs Addressed:** `UI-002`, `UI-003`, `DEAD-003`
- **Acceptance Criteria:**
  - `6_operations_dashboard.py` contains 0 direct imports of `sqlite3`, `jobs.*`, `events.*`, `audit.*`, `metrics.*`, or `platform.observability.*`.
  - `timeline.py` contains 0 direct imports of backend event stores or timeline services.
  - AST Layer Violation Gate confirms **0 UI layer violations** (down from 18).
  - Targeted test `uv run python -m pytest tests/test_ui_client.py -v` passes 100%.

### Commit 3: `refactor(ui): replace SSE server and iframe with native Streamlit fragment polling`
- **Files to Touch:**
  - `src/content_creation/ui/components/notification_panel.py` (Lines 40-100: wrap sidebar badge and notification summary panel in `@st.fragment(run_every="5s")`)
  - `src/content_creation/ui/app.py` (Lines 23, 44-57: remove `render_sse_client()` and `render_notification_badge_live()`; use fragment badge)
  - `src/content_creation/ui/components/sse_client.py` (Retire/gut dead JavaScript iframe component)
  - `src/content_creation/ui/services/client.py` (Lines 100-112, 122-124, 495-522: remove background `NotificationSSEServer.start()` and SSE methods; provide no-op shims for event publishing)
  - `src/content_creation/notifications/streaming/server.py` (Retire/deprecate `NotificationSSEServer`)
  - `src/content_creation/notifications/streaming/connection_manager.py` (Retire/deprecate; eliminates `DEAD-004`)
  - `tests/test_notification_streaming.py` (Retire the 12 failing socket integration tests that assert raw TCP `localhost` connections on Windows)
- **Defect IDs Addressed:** `UI-004`, `ERR-004`, `DEAD-004`
- **Acceptance Criteria:**
  - No TCP socket binds to port 8502 on Streamlit startup.
  - Zero `st.components.v1.html` deprecation warnings on dashboard render.
  - Notification badge updates reactively every 5 seconds via native `@st.fragment`.
  - All 12 pre-existing socket test failures (`WinError 10013`) in `tests/test_notification_streaming.py` are eliminated.
  - Suite passes: `uv run python -m pytest tests/test_notification_streaming.py -o addopts="" -p no:cov` with 0 failures.

### Commit 4: `refactor(ui): align Streamlit parameters and handle corrupt artifacts gracefully`
- **Files to Touch:**
  - `src/content_creation/ui/pages/4_storyboard.py` (Lines 78-167: use `client.storyboard_file_exists()` to distinguish missing vs. corrupt artifacts; migrate `use_container_width=True` to `width="stretch"`)
  - `src/content_creation/ui/pages/5_asset_workshop.py` (Lines 79, 126, 140, 162, 178, 226, 276: migrate `use_container_width=True` to `width="stretch"`; handle corrupted storyboard gracefully)
  - `src/content_creation/ui/app.py` (Line 84: migrate `use_container_width=True` to `width="stretch"`)
  - `tests/test_ui_pages.py` (New domain test suite using `streamlit.testing.v1.AppTest` verifying all 7 pages render cleanly, fragments poll safely, and corrupt artifacts do not crash the UI)
- **Defect IDs Addressed:** `UI-001`, `UI-006`
- **Acceptance Criteria:**
  - If a storyboard file is 0-byte or corrupted, `4_storyboard.py` renders a clear warning: `⚠️ Storyboard file is corrupted or empty (0-byte) on disk (ID: ...)` rather than masking it as ungenerated.
  - If a storyboard file does not exist, `4_storyboard.py` renders: `ℹ️ Storyboard not yet generated for this topic`.
  - All buttons and dataframes in touched pages use `width="stretch"` without deprecation warnings.
  - Secondary educational formats (`Newsletter` and `LinkedIn Post`) in `5_asset_workshop.py` render cleanly and pass headless tests.
  - Headless UI test suite `uv run python -m pytest tests/test_ui_pages.py -v` passes 100%.

---

## 4. Strict File Allowlist

### 4.1 Existing Files to Modify (11 `src/` modules + 1 test file)
- `src/content_creation/platform/storage/json_repository.py`
- `src/content_creation/ui/services/client.py`
- `src/content_creation/ui/pages/6_operations_dashboard.py`
- `src/content_creation/ui/components/timeline.py`
- `src/content_creation/ui/components/notification_panel.py`
- `src/content_creation/ui/components/sse_client.py`
- `src/content_creation/ui/app.py`
- `src/content_creation/ui/pages/4_storyboard.py`
- `src/content_creation/ui/pages/5_asset_workshop.py`
- `src/content_creation/notifications/streaming/server.py`
- `src/content_creation/notifications/streaming/connection_manager.py`
- `tests/test_notification_streaming.py`

### 4.2 New Files to Create (Domain-Named Only)
- `tests/test_json_repository.py` (Verifies `JsonRepository` 0-byte, UTF-8, and atomic write resilience)
- `tests/test_ui_client.py` (Verifies `ServiceClient` operations snapshot and timeline DTO formatting)
- `tests/test_ui_pages.py` (Headless Streamlit `AppTest` suite covering all 7 UI pages and fragments)

### 4.3 Files to Delete / Retire
- None deleted from disk; `sse_client.py` and `notifications/streaming/server.py` are deprecated/gutted in-place to preserve backwards compatibility for any external tooling.

### 4.4 Prohibited File Names (Anti-Drift Guardrail)
- **PROHIBITED:** `tests/test_phase2b_qa.py`, `tests/test_refactor_phase2.py`, or any phase-named test files. All tests must be domain-named strictly reflecting the module under test.

---

## 5. Explicit Out-of-Scope / Deferred Items

To enforce the Anti-Mega-Branch Decomposition Rule and maintain strict focus on Phase 2B objectives:

1. **`UI-005` (Operator Data Hygiene):**
   - Quarantining or deleting the 26 truncated 0-byte files in `data/staged/*.json` and 5 0-byte files in `data/storyboards/*.json` is strictly an **Operator Runtime Task**.
   - **Zero modifications to `data/` files in this branch.** No runtime JSON or database files may be committed to Git.
   - *Operator one-liner for local workspace cleanup:*
     ```powershell
     Get-ChildItem -Path "data/staged/*.json", "data/storyboards/*.json" | Where-Object { $_.Length -eq 0 } | Remove-Item -Force
     ```

2. **Deferred Dead Code Removals (Phase 2C):**
   - `DEAD-001` (`src/content_creation/workflow/workflow_action_executor.py:70`): Unreferenced `fail_blocked` method — deferred to Phase 2C (touches workflow engine).
   - `DEAD-002` (`src/content_creation/workflow/workflow_action_executor.py:749`): Mock `publish` branch — deferred to Phase 2C.
   - `DEAD-005` (`src/content_creation/application/context.py:53`): Unreferenced `content_intelligence_dir` property — deferred to Phase 2C.

3. **Deferred Phase 2A Advisories (Phase 2C):**
   - Phase 2A Advisory #1 (`src/content_creation/cli/common.py:9`): Unused `LocalStorage` import — deferred to Phase 2C.
   - Phase 2A Advisory #2 (`src/content_creation/planning/dryrun.py:177`): Unencoded file open in `DryRunValidator.export_markdown` — deferred to Phase 2C.

4. **Deferred Cosmetic Parameter Migrations:**
   - Minor `use_container_width=True` migrations in pages 1, 2, and 3 (`1_topic_collection.py`, `2_topic_pipeline.py`, `3_brief_viewer.py`) are deferred to Phase 2C to keep the modified `src/` file count strictly $\le 11$.

5. **No Model or Prompt Changes:**
   - Frozen scopes (`src/content_creation/models/`, `src/content_creation/generation/`, `prompts/`, `docs/schema.md`) remain untouched.

---

## 6. Required Verification Gates (Zero-Trust)

`contract-verifier` and `qa-test-engineer` will validate against these explicit gates before signaling completion:

### Gate 1: Scope Compliance & Preservation
- `git diff --name-only main..HEAD` must match §4 File Allowlist with 0 extra files.
- `src/content_creation/models/newsletter.py` and `prompts/linkedin_post.md` confirmed present and untouched.
- Secret scan confirms 0 exposed tokens, `.env`, or `.db` files committed.

### Gate 2: Static Typing Ratchet (`mypy --strict`)
- Run per-file strict mypy check on all touched `src/` modules:
  ```powershell
  uv run mypy src/content_creation/platform/storage/json_repository.py src/content_creation/ui/services/client.py src/content_creation/ui/components/timeline.py src/content_creation/ui/components/notification_panel.py --strict
  ```
- Expected: 0 typing errors on all touched files. Baseline error count on untouched files must not increase.

### Gate 3: AST Layer-Violation & Windows Hygiene Check
- AST Layer Violation Audit:
  ```powershell
  uv run python -c "
  import ast
  from pathlib import Path

  src_path = Path('src/content_creation').resolve()
  cwd = Path.cwd().resolve()
  violations = []
  targets = ['jobs.queue_engine', 'jobs.lock_manager', 'jobs.sqlite', 'jobs.schema', 'events.store.sqlite', 'events.store.schema', 'events.store.timeline', 'events.store.models', 'audit.sqlite', 'audit.compliance', 'audit.schema', 'metrics.sqlite', 'metrics.schema', 'platform.observability.health', 'platform.observability.service']

  for py_file in src_path.rglob('*.py'):
      if 'ui' in py_file.parts:
          tree = ast.parse(py_file.read_text(encoding='utf-8'), filename=str(py_file))
          for node in ast.walk(tree):
              if isinstance(node, ast.Import):
                  for name in node.names:
                      if any(t in name.name for t in targets):
                          violations.append((str(py_file.relative_to(cwd)), node.lineno, name.name))
              elif isinstance(node, ast.ImportFrom):
                  mod = node.module or ''
                  if any(t in mod for t in targets):
                      violations.append((str(py_file.relative_to(cwd)), node.lineno, mod))

  print(f'AST UI Layer Violations: {len(violations)}')
  assert len(violations) == 0, f'Expected 0 violations, found {violations}'
  "
  ```
- Windows UTF-8 Hygiene: Verify all `open()`, `read_text()`, and `write_text()` in touched modules specify `encoding="utf-8"`.

### Gate 4: Targeted & Baseline Test Suites
- **Targeted Domain Suites:**
  ```powershell
  uv run python -m pytest tests/test_json_repository.py tests/test_ui_client.py tests/test_ui_pages.py -o addopts="" -p no:cov -v
  ```
  - Expected: 100% passing.
- **Socket Retirement Verification:**
  ```powershell
  uv run python -m pytest tests/test_notification_streaming.py -o addopts="" -p no:cov -v
  ```
  - Expected: 0 failures (12 pre-existing `ERR-004` socket failures eliminated).
- **Baseline Regression Check:**
  ```powershell
  uv run python -m pytest -o addopts="" -p no:cov --tb=no -q
  ```
  - Final passing test count must exceed the baseline (~1,343 passed) with $\le 6$ remaining failures (down from 18).

### Gate 5: Real Headless Streamlit Runtime Verification Check
- Execute live headless `AppTest` across `app.py` and all 6 subpages using an isolated temporary directory for `CONTENT_FACTORY_ROOT`:
  ```powershell
  uv run python -c "
  import os, tempfile
  from pathlib import Path
  from streamlit.testing.v1 import AppTest

  td = tempfile.mkdtemp()
  os.environ['CONTENT_FACTORY_ROOT'] = td

  pages = [
      'src/content_creation/ui/app.py',
      'src/content_creation/ui/pages/1_topic_collection.py',
      'src/content_creation/ui/pages/2_topic_pipeline.py',
      'src/content_creation/ui/pages/3_brief_viewer.py',
      'src/content_creation/ui/pages/4_storyboard.py',
      'src/content_creation/ui/pages/5_asset_workshop.py',
      'src/content_creation/ui/pages/6_operations_dashboard.py',
  ]

  for p in pages:
      print(f'Testing {p}...')
      at = AppTest.from_file(p, default_timeout=15)
      at.run()
      assert len(at.exception) == 0, f'Page {p} crashed with: {at.exception}'
      print(f'  ✓ {p} passed cleanly')

  print('All 7 Streamlit pages verified cleanly via AppTest!')
  "
  ```
- Expected: All 7 pages execute with 0 exceptions and 0 unhandled deprecation warnings.

---

## 7. Orchestrator Chain Directive

The `phase-orchestrator` must execute this specification using the standard sequential lifecycle:
1. `refactor-executor` executes atomic Commits 1 through 4 on feature branch `refactor/phase2b-ui-and-fragments`.
2. `contract-verifier` audits Gates 1 through 5 (halts if any gate fails).
3. `error-taxonomy-chronicler` updates `docs/audit/error-taxonomy.json` (marks `ERR-004` and `ERR-006` as RESOLVED, updates `ERR-018` coverage, records eliminated socket errors).
4. `qa-test-engineer` runs edge-case fault injection (0-byte JSON files, corrupt utf-8 bytes, rapid fragment poll ticks).
5. Final taxonomy sync.
6. Halt for human review — **DO NOT MERGE TO MAIN, DO NOT PUSH REMOTE**.
