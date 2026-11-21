# Task Specification: Phase 2C — SQLite Consolidation, Windows Python Hygiene & SSE Deprecation Retiral

- **Phase ID:** `2C-sqlite-consolidation-and-hygiene`
- **Target Branch:** `refactor/phase2c-sqlite-consolidation` branched from `main`
- **Prerequisites:** Phase 2A and Phase 2B merged into `main` (Head commit `fc6ef5c`)
- **Applicable Workspace Skills:**
  - `.agents/skills/windows-python-hygiene/SKILL.md`
  - `.agents/skills/security-and-cost-guard/SKILL.md`
  - `.agents/skills/performance-optimization/SKILL.md`
  - `.agents/skills/test-driven-development/SKILL.md`
  - `.agents/skills/verification-before-completion/SKILL.md`
- **Associated Architecture Decision Record:**
  - `docs/refactor/adrs/003-single-wal-sqlite-database.md`

---

## 1. Governance & Explicit Scope Unfreezes (`AGENTS.md` §14)

- **Frozen Paths Evaluation:**
  - `src/content_creation/models/`: **NOT TOUCHED** (Strictly frozen; zero domain schema modifications)
  - `src/content_creation/generation/`: **NOT TOUCHED** (Strictly frozen; script/carousel/newsletter generators untouched)
  - `prompts/`: **NOT TOUCHED** (Strictly frozen; `prompts/short_video.md`, `newsletter.md`, `linkedin_post.md` untouched)
  - `docs/schema.md`: **NOT TOUCHED** (Strictly frozen; data contracts unchanged)
- **Secondary Channel Preservation Invariant:**
  - Explicit confirmation that `newsletter` (`src/content_creation/models/newsletter.py`, `src/content_creation/generation/newsletter.py`, `prompts/newsletter.md`) and `linkedin_post` (`prompts/linkedin_post.md`) are preserved **100% intact**.
  - All generators, prompts, models, and UI tabs for secondary channels must remain completely unaffected.
- **Git & Worktree Hygiene:**
  - Zero `.db`, `.sqlite`, `.sqlite3`, `.db-wal`, or `.db-shm` files may be committed to git. All SQLite files remain strictly gitignored (`.gitignore`).
  - All test persistence must execute inside `pytest`'s isolated `tmp_path` fixture.

---

## 2. Objective & Defect Resolution Scope

Phase 2C executes three coordinated architectural objectives across storage persistence, Windows test suite greening, and deprecated code retiral:

1. **Single WAL-Mode SQLite Database (`data/content_factory.db`) (`RISK-001`, `ARCH-001`, `UI-002`, `PERF-001`):**
   - Consolidate all 6 discrete SQLite database files (`jobs.db`, `locks.db`, `events.db`, `notifications.db`, `metrics.db`, `audit.db`) into a single, unified database: `data/content_factory.db`.
   - Verified schema orthogonality: All 6 tables (`jobs`, `locks`, `events`, `notifications`, `metrics`, `audit`) and their 24 indexes have 100% distinct, non-colliding names.
   - Introduce `src/content_creation/platform/storage/database.py` providing centralized connection management, idempotent schema initialization (`init_content_factory_db`), and uniform WAL-mode pragmas (`PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;`, `PRAGMA foreign_keys=ON;`, `PRAGMA synchronous=NORMAL;`).
   - Eliminate inline DDL schema checks (`create_*_schema`) from Streamlit render hot paths (`ServiceClient.get_operations_snapshot()` and `get_notification_connection()`), fulfilling `performance-optimization` Rule 4 ("Zero DDL in Hot Paths").
   - Update `ApplicationContext` to carry `db_path: Path = base_dir / "data" / "content_factory.db"` and provide `get_db_connection()`.
   - Update `cli/observability.py` to route to `content_factory.db` with transparent fallback to legacy discrete files for backward compatibility.

2. **100% Green Native Windows Test Suite — Fix Last 2 Windows Encoding Failures (`ERR-011`, `ERR-012`):**
   - **Failure 1 (`src/content_creation/planning/dryrun.py:177-178`):** `DryRunValidator.export_markdown()` writes report markdown containing Unicode symbols (`✓` `\u2713` and `✗` `\u2717`) using unencoded `with open(output_path, "w") as f:`. On native Windows environments with default CP1252 codepage, this triggers `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`. Add explicit `encoding="utf-8"` per `windows-python-hygiene` Rule 1.
   - **Failure 2 (`tests/test_youtube_shorts_generation.py:719`):** `test_prompt_content_requirements` reads `prompts/short_video.md` via `real_prompt_path.read_text()` without an explicit encoding parameter. On Windows CP1252, the UTF-8 en-dash in `50–58 seconds` (`\u2013`, bytes `0xE2 0x80 0x93`) decodes as mojibake `50â€“58 seconds`, causing assertion `assert "50–58 seconds" in prompt_content` to fail at line 727. Ground-truth inspection confirms the prompt wording is 100% correct; adding `encoding="utf-8"` to `read_text()` in the test resolves the failure cleanly without touching the frozen prompt file.

3. **Eliminate Remaining 35 Deprecation Warnings & Clean Up Deferred Dead Code (`ERR-004`, `DEAD-001`, `DEAD-002`, `DEAD-004`, `DEAD-005`):**
   - Cleanly remove the deprecated `ConnectionManager()` instantiation in `src/content_creation/ui/services/client.py:578` and remove unused streaming imports (lines 29-31). Set `connection_manager=None` when creating `ObservabilityService`.
   - Retire the deprecated SSE streaming stubs per ADR-001 (`src/content_creation/notifications/streaming/server.py`, `connection_manager.py`, and `publisher.py`), and clean up `src/content_creation/notifications/streaming/__init__.py`.
   - Retire the warning-only socket tests in `tests/test_notification_streaming.py`, eliminating all 35 deprecation warnings repository-wide.
   - Clean up deferred dead code:
     - `DEAD-001`: Remove unreferenced `fail_blocked` classmethod in `src/content_creation/workflow/workflow_action_executor.py:69-81`.
     - `DEAD-002`: Remove unreferenced mock stub branch `elif action_id == "publish":` in `src/content_creation/workflow/workflow_action_executor.py:749-750`.
     - `DEAD-005`: Remove unreferenced `content_intelligence_dir` property in `src/content_creation/application/context.py:53-55`.
     - Phase 2A Advisory #1: Remove unused `from content_creation.storage.local import LocalStorage` import in `src/content_creation/cli/common.py:9`.
   - **Decomposition Guardrail:** Cosmetic `use_container_width=True` -> `width="stretch"` on UI pages 1–3 is explicitly deferred to keep total modified `src/` modules strictly $\le 12$.

- **Defects & Taxonomy IDs Resolved:**
  - `ERR-004` / `DEAD-004`: Clean retiral of deprecated SSE streaming stubs, eliminating 35 deprecation warnings
  - `ERR-011` / `ERR-012`: Windows CP1252 file I/O: explicit `encoding="utf-8"` in `DryRunValidator.export_markdown` and `test_youtube_shorts_generation.py`
  - `UI-002` / `PERF-001`: Elimination of inline DDL in Streamlit render hot paths
  - `RISK-001` / `ARCH-001`: Consolidation of 6 fragmented SQLite databases into `data/content_factory.db` with WAL mode
  - `DEAD-001`: Dead classmethod `WorkflowActionExecutor.fail_blocked`
  - `DEAD-002`: Unimplemented mock stub `WorkflowActionExecutor.publish`
  - `DEAD-005`: Unreferenced property `ApplicationContext.content_intelligence_dir`
  - Phase 2A Advisory #1: Unused `LocalStorage` import in `cli/common.py:9`

---

## 3. Atomic Commit Plan

Ordered, single-concern commits to be executed sequentially by `refactor-executor`:

### Commit 1: `fix(windows): enforce utf-8 encoding across dryrun export and shorts generation test`
- **Files to Touch:**
  - `src/content_creation/planning/dryrun.py` (Line 177: change `with open(output_path, "w") as f:` to `with open(output_path, "w", encoding="utf-8") as f:`)
  - `tests/test_youtube_shorts_generation.py` (Line 719: change `real_prompt_path.read_text()` to `real_prompt_path.read_text(encoding="utf-8")`)
- **Defect IDs Addressed:** `ERR-011`, `ERR-012`
- **Acceptance Criteria:**
  - `DryRunValidator.export_markdown()` writes report files containing Unicode checkmarks (`✓`) and ballot Xs (`✗`) on Windows hosts without `UnicodeEncodeError`.
  - `tests/test_youtube_shorts_generation.py::test_prompt_content_requirements` passes cleanly on native Windows without mojibake.
  - `prompts/short_video.md` remains 100% untouched.
  - Targeted test: `uv run python -m pytest tests/test_dryrun.py tests/test_youtube_shorts_generation.py -o addopts="" -p no:cov -v` passes 100% green.

### Commit 2: `refactor(streaming): retire deprecated sse stubs and remove client connection manager`
- **Files to Touch:**
  - `src/content_creation/ui/services/client.py` (Lines 29-31: remove unused `ConnectionManager`, `NotificationPublisher`, `NotificationSSEServer` imports; lines 576-581: remove `ConnMgrMod.ConnectionManager()` instantiation and set `connection_manager=None` when creating `ObservabilityService`)
  - `src/content_creation/notifications/streaming/server.py` (RETIRE / DELETE file per ADR-001)
  - `src/content_creation/notifications/streaming/connection_manager.py` (RETIRE / DELETE file per ADR-001; resolves `DEAD-004`)
  - `src/content_creation/notifications/streaming/publisher.py` (RETIRE / DELETE file per ADR-001)
  - `src/content_creation/notifications/streaming/__init__.py` (Clean up re-exports, leaving deprecation docstring and retained models)
  - `tests/test_notification_streaming.py` (RETIRE / Replace with test verifying SSE stubs are cleanly retired per ADR-001)
- **Defect IDs Addressed:** `ERR-004`, `DEAD-004`
- **Acceptance Criteria:**
  - All 35 deprecation warnings related to `ConnectionManager` and `NotificationSSEServer` are permanently eliminated.
  - `ServiceClient.get_operations_snapshot()` executes with `connection_manager=None` and produces a healthy snapshot without warnings.
  - `tests/test_ui_client.py` and `tests/test_ui_pages.py` execute with 0 deprecation warnings.
  - Targeted test: `uv run python -m pytest tests/test_ui_client.py tests/test_ui_pages.py -o addopts="" -p no:cov -v` passes 100% green.

### Commit 3: `refactor(storage): consolidate sqlite databases into single wal-mode content_factory.db`
- **Files to Touch:**
  - `src/content_creation/platform/storage/database.py` (NEW: Consolidated SQLite connection factory, WAL mode pragma configuration, unified schema initializer `init_content_factory_db`, and db path resolution)
  - `src/content_creation/application/context.py` (Add `db_path: Path` to `ApplicationContext` pointing to `base_dir / "data" / "content_factory.db"`; provide `get_db_connection()`; remove `content_intelligence_dir` property `DEAD-005`)
  - `src/content_creation/ui/services/client.py` (Lines 77-83: point `get_notification_connection()` to `content_factory.db` and eliminate inline DDL `create_notification_schema(conn)`; lines 482-595: refactor `get_operations_snapshot()` to open single connection to `content_factory.db` without inline DDL; lines 705-707: point `get_event_timeline()` to `content_factory.db` with legacy fallback)
  - `src/content_creation/cli/observability.py` (Update default database path resolution to use `content_factory.db` with transparent fallback to legacy discrete files)
  - `tests/test_content_factory_db.py` (NEW: Comprehensive domain test suite verifying unified schema initialization, WAL mode pragmas, multi-subsystem concurrent CRUD, and fallback handling)
- **Defect IDs Addressed:** `RISK-001`, `ARCH-001`, `UI-002`, `PERF-001`, `DEAD-005`
- **Acceptance Criteria:**
  - Single database `data/content_factory.db` accommodates all 6 subsystem tables (`jobs`, `locks`, `events`, `notifications`, `metrics`, `audit`) with zero table-name or index-name collisions.
  - Every connection opened by `create_connection()` has `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;`, `PRAGMA foreign_keys=ON;`, and `PRAGMA synchronous=NORMAL;` active.
  - Zero DDL runs inside `get_operations_snapshot()` or `get_notification_connection()`.
  - `tests/test_content_factory_db.py` runs 100% green in an isolated `tmp_path` without mutating working tree `data/`.
  - Targeted test: `uv run python -m pytest tests/test_content_factory_db.py tests/test_ui_client.py -o addopts="" -p no:cov -v` passes 100% green.

### Commit 4: `chore(cleanup): remove dead code in workflow executor and unused cli imports`
- **Files to Touch:**
  - `src/content_creation/workflow/workflow_action_executor.py` (Lines 69-81: remove dead `fail_blocked` classmethod `DEAD-001`; lines 749-750: remove dead mock `publish` stub `DEAD-002`)
  - `src/content_creation/cli/common.py` (Line 9: remove unused `from content_creation.storage.local import LocalStorage` import; update `get_context()` to respect `CONTENT_FACTORY_ROOT` env var for CLI tests)
- **Defect IDs Addressed:** `DEAD-001`, `DEAD-002`, Phase 2A Advisory #1
- **Acceptance Criteria:**
  - `WorkflowActionExecutor` contains 0 unreferenced factory methods or mock stubs.
  - `src/content_creation/cli/common.py` imports only actively referenced symbols.
  - AST Layer Violation Gate confirms 0 unused imports and 0 layer violations.
  - Full CLI test suite runs cleanly with proper directory isolation.

---

## 4. Strict File Allowlist

### 4.1 Existing Files to Modify (7 `src/` modules + 2 `tests/` files)
- `src/content_creation/planning/dryrun.py`
- `src/content_creation/ui/services/client.py`
- `src/content_creation/notifications/streaming/__init__.py`
- `src/content_creation/application/context.py`
- `src/content_creation/cli/observability.py`
- `src/content_creation/workflow/workflow_action_executor.py`
- `src/content_creation/cli/common.py`
- `tests/test_youtube_shorts_generation.py`
- `tests/test_notification_streaming.py`

### 4.2 New Files to Create (1 `src/` module + 1 `tests/` file)
- `src/content_creation/platform/storage/database.py` (Consolidated SQLite connection factory and schema manager)
- `tests/test_content_factory_db.py` (Domain test suite verifying consolidated SQLite persistence)

### 4.3 Files to Delete / Retire (3 `src/` modules)
- `src/content_creation/notifications/streaming/server.py` (Deprecated SSE daemon retired per ADR-001)
- `src/content_creation/notifications/streaming/connection_manager.py` (Deprecated socket connection manager retired per ADR-001)
- `src/content_creation/notifications/streaming/publisher.py` (Deprecated SSE publisher retired per ADR-001)

### 4.4 Prohibited File Names (Anti-Drift Guardrail)
- **Strictly Prohibited:** Phase-named test files (e.g., `tests/test_phase2c.py`, `tests/test_phase2c_qa.py`, `tests/test_refactor_sqlite.py`).
- All tests must strictly be named after the domain module they verify (e.g., `tests/test_content_factory_db.py`).

### 4.5 Module Count Summary
- Total modified `src/` modules: 7
- Total new `src/` modules: 1
- Total retired/deleted `src/` modules: 3
- **Total `src/` modules touched:** **11 modules** ($\le 12$ threshold satisfied; Anti-Mega-Branch invariant fully enforced).

---

## 5. Explicit Out-of-Scope / Deferred Items

The following items are strictly forbidden on this branch to prevent scope creep:
- [ ] **No changes to UI presentation pages 1–3:** Cosmetic `use_container_width=True` -> `width="stretch"` on pages 1–3 is deferred to keep total modified `src/` modules $\le 12$.
- [ ] **No changes to LLM prompts:** `prompts/short_video.md`, `prompts/carousel.md`, `prompts/newsletter.md`, `prompts/linkedin_post.md` are strictly frozen.
- [ ] **No changes to Pydantic domain models:** `src/content_creation/models/` is strictly frozen.
- [ ] **No cloud deployment or containerization:** Do NOT add Docker, Docker Compose, Redis, Celery, or cloud database plumbing.
- [ ] **No Phase 3 LangGraph migration:** Phase 2C prepares the SQLite anchor (`content_factory.db`); full LangGraph state engine migration occurs in Phase 3.
- [ ] **Zero `data/` mutation committed to git:** No `.db`, `.sqlite`, or runtime JSON files committed.

---

## 6. Required Verification Gates (Zero-Trust)

`contract-verifier` and `qa-test-engineer` will validate against these explicit gates before any handoff:

1. **Gate 1: Scope Compliance & File Allowlist:**
   - Git diff must match §4 exactly: max 11 `src/` modules (1 new, 7 modified, 3 deleted) and 3 `tests/` files (1 new, 2 modified).
   - Zero out-of-scope files touched.
   - Preserved assets check: `newsletter.py`, `generation/newsletter.py`, `prompts/newsletter.md`, and `prompts/linkedin_post.md` verified 100% intact.
   - Secret hygiene check: 0 credentials, 0 `.env`, 0 `*.db` files committed.

2. **Gate 2: Static Typing Ratchet (`mypy --strict`):**
   - Command: `uv run mypy src/content_creation/platform/storage/database.py src/content_creation/ui/services/client.py src/content_creation/application/context.py src/content_creation/workflow/workflow_action_executor.py src/content_creation/cli/common.py src/content_creation/planning/dryrun.py --strict`
   - Expected: 0 errors on new module (`database.py`); 0 new errors on touched modules.

3. **Gate 3: AST Layer-Violation & Windows Hygiene Check:**
   - Direct SQLite or DDL imports in `src/content_creation/ui/`: Exactly 0.
   - Missing UTF-8 encodings in file I/O across touched files: Exactly 0.
   - Zero hardcoded `bash`/`sh` subprocess calls; uses `sys.executable` and `pathlib`.

4. **Gate 4: Targeted & Full Regression Test Suites:**
   - Targeted suite: `uv run python -m pytest tests/test_content_factory_db.py tests/test_dryrun.py tests/test_youtube_shorts_generation.py tests/test_ui_client.py tests/test_ui_pages.py -o addopts="" -p no:cov -v` (100% green).
   - Baseline regression sweep: `uv run python -m pytest -o addopts="" -p no:cov --tb=no -q`.
   - Passing test count must increase ($\ge 1,407$ passing).
   - Deprecation warnings: All 35 SSE/ConnectionManager deprecation warnings permanently eliminated.

5. **Gate 5: Real Runtime Verification Check:**
   - Beyond `--help`: Execute real runtime SQLite verification script against a temporary workspace:
     ```powershell
     uv run python -c "from content_creation.platform.storage.database import init_content_factory_db, create_connection; conn = create_connection('data/content_factory.db'); init_content_factory_db(conn); print('Tables:', [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]); conn.close()"
     ```
   - Streamlit headless AppTest: Run all 7 pages via `tests/test_ui_pages.py` to confirm operations dashboard snapshot and notification fragments render with 0 unhandled exceptions.

---

## 7. Orchestrator Chain Directive

The `phase-orchestrator` must execute this specification using the standard sequential lifecycle:
1. `refactor-executor` on feature branch `refactor/phase2c-sqlite-consolidation` (branched from `main`).
2. `contract-verifier` (audit against Gates 1–5; halt if any gate reports BLOCK).
3. `error-taxonomy-chronicler` (harvest any observed errors/exceptions into `error-taxonomy.json`).
4. `qa-test-engineer` (design domain tests; run fault injection and boundary checks on `content_factory.db`).
5. Final taxonomy sync.
6. Halt for human review — **DO NOT MERGE TO MAIN, DO NOT PUSH REMOTE**.
