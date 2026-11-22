# Task Specification: Phase 2D — Creator Usability, Reliability Guards & UI Polish

- **Phase ID:** `2D-creator-usability-and-ui-polish`
- **Target Branch:** `feat/phase2d-creator-usability` branched from `main`
- **Prerequisites:** Phase 2A, Phase 2B, and Phase 2C merged into `main` (Head commit `5bbee84`)
- **Applicable Workspace Skills:**
  - `.agents/skills/windows-python-hygiene/SKILL.md`
  - `.agents/skills/security-and-cost-guard/SKILL.md`
  - `.agents/skills/performance-optimization/SKILL.md`
  - `.agents/skills/test-driven-development/SKILL.md`
  - `.agents/skills/verification-before-completion/SKILL.md`
- **Associated Architecture Decision Records:**
  - `docs/refactor/adrs/001-native-fragments-and-ui-facades.md`
  - `docs/refactor/adrs/003-single-wal-sqlite-database.md`
  - `docs/refactor/adrs/004-llm-cost-governance-and-eval-harness.md`

---

## 1. Governance & Explicit Scope Unfreezes (`AGENTS.md` §14)

- **Frozen Paths Evaluation:**
  - `src/content_creation/models/`: **NOT TOUCHED** (Strictly frozen; `TopicItem`, `ScoredTopicItem`, `Brief`, `Script`, `Carousel`, `Newsletter` schemas unchanged)
  - `src/content_creation/generation/`: **NOT TOUCHED** (Strictly frozen; prompt-fillers and generators untouched)
  - `prompts/`: **NOT TOUCHED** (Strictly frozen; markdown prompt templates untouched)
  - `docs/schema.md`: **NOT TOUCHED** (Strictly frozen; contract schemas untouched)
- **Secondary Channel Preservation Invariant:**
  - Explicit confirmation that `newsletter` (`src/content_creation/models/newsletter.py`, `src/content_creation/generation/newsletter.py`, `prompts/newsletter.md`) and `linkedin_post` (`prompts/linkedin_post.md`) are preserved **100% intact**.
  - All generators, prompts, models, and UI tabs for secondary channels must remain completely unaffected.
- **Architectural Boundary Invariant (0 AST Layer Violations):**
  - UI entrypoints (`src/content_creation/ui/app.py` and `src/content_creation/ui/pages/`) must NEVER directly import or access repository classes (`LocalStorage`, `SQLiteJobRepository`, `SQLiteEventRepository`), raw database connection handles, or inference providers.
  - All persistence, query operations, and formatting transformations MUST route exclusively through the `ServiceClient` facade (`src/content_creation/ui/services/client.py`).

---

## 2. Objective & Defect Resolution Scope

Phase 2D delivers a high-impact creator usability overhaul, runtime reliability guardrails, and visual polish across all 7 Streamlit console pages (`app.py` through `6_operations_dashboard.py`). It resolves recurring workflow friction points identified during Phase 2 testing while strictly capping modified `src/` modules to $\le 10$.

### Core Objectives:

1. **Manual Custom Topic Input (`1_topic_collection.py` & `ServiceClient`):**
   - Provide creators the ability to bypass automated RSS feed collection and manually ingest breaking AI research papers, repos, and concept ideas directly into the staging pipeline.
   - Implement `ServiceClient.create_manual_topic(title, notes, url="", source_id="manual")` returning a fully schema-compliant, UTF-8 encoded `TopicItem` saved into `data/staged/{topic_id}.json`.
   - Add a prominent, structured `"Add Custom Topic / Idea"` form on Page 1 above RSS collection.
   - Replace the static `"Run feed collection to download papers"` notice with a dynamic queue status indicator when staged items already exist.

2. **Production Cue Sheet & TTS Voiceover Copy Blocks (`4_storyboard.py`, `5_asset_workshop.py`, `ServiceClient`):**
   - Video creators currently receive fragmented text fields across scripts and storyboards, requiring manual copy-pasting to assemble production timelines.
   - Implement deterministic formatting utilities in `ServiceClient`:
     - `format_voiceover_script(topic_id)`: Extracts and formats clean, sequential spoken text optimized for direct paste into TTS engines (e.g., ElevenLabs).
     - `format_production_cue_sheet(topic_id)`: Merges storyboard visual metaphors, scene directions, time-ranges, spoken voiceover, and audio/sound cues into a unified video editing cue sheet.
   - Expose two one-click `st.code` blocks on Page 5 (`🎥 Video Script` tab): **🎙️ Voiceover Only (TTS Audio)** and **🎬 Full Production Cue Sheet (Video Editing)**.
   - Expose scene-cue copy on Page 4 (`4_storyboard.py`) for quick director review.
   - Replace raw Python list repr (`['script: missing']`) with clean UI badges for `manifest.blocking_reasons` on Page 5.

3. **Reliability Guards (`client.py`, `app.py`, `gemini.py`, `brief_generation_service.py`):**
   - **Direct Subpage Environment Loading (`client.py`):** Add `from dotenv import load_dotenv; load_dotenv()` at the top of `src/content_creation/ui/services/client.py`. When creators navigate directly or refresh subpages (e.g. `3_brief_viewer.py`), this ensures `.env` environment variables (`GEMINI_API_KEY`, etc.) are reliably loaded in process memory without falling back to `.streamlit/secrets.toml`.
   - **Startup DB Self-Heal:** Run `init_content_factory_db()` once per application bootstrap using `@st.cache_resource` in `app.py` / `ServiceClient` init. Automatically creates missing tables/indexes if `data/content_factory.db` is partial or newly created, while guaranteeing 0 DDL on page rerenders (`performance-optimization` Rule 4).
   - **Fail-Fast Auth Circuit Breaker:** In Google GenAI client, invalid credentials return HTTP 400 with message `API_KEY_INVALID`. Currently, `GeminiProvider._classify_client_error` misclassifies this as `ErrorCategory.INVALID_REQUEST`. Update classifier to correctly identify `400 API_KEY_INVALID` as `ErrorCategory.AUTH`.
   - Abort batch LLM loops in `BriefGenerationService.run()` immediately upon encountering an `ErrorCategory.AUTH` failure instead of sleeping 5 seconds and failing across all 20 queued topics sequentially.

4. **Streamlined Creator Flow & Visual Polish (Pages 0–6):**
   - `app.py`: Fix broken LaTeX escape `$\rightarrow$` which renders as `ightarrow` in Streamlit markdown; make metric cards clickable with forward navigation links (`st.page_link`).
   - `2_topic_pipeline.py`: Replace the 5 non-functional interactive weight sliders with a compact read-only expander (`"⚖️ Current Scoring Weights (config/scoring.yaml)"`) to bring `⚖️ Score Topics` and the scored table above the fold; add visual priority tier badges (`🟢 High`, `🟡 Medium`, `⚪ Low`).
   - `3_brief_viewer.py`: Remove duplicate stacked "Brief Summary" card; render raw `"needs_review"` field values as clean muted UI badges (`Pending review ⏳`).
   - `4_storyboard.py`: Remove duplicate empty-state warning box; display storyboard readiness indicators (`✅` / `⏳`) in Brief Selector labels.
   - `6_operations_dashboard.py` & `client.py`: Remove the retired `⚪ SSE Streaming: UNKNOWN` health check card from `get_operations_snapshot()`; downgrade `"Worker Daemon: Not running (manual mode)"` from a yellow warning alarm to a neutral info note when no background jobs are queued.
   - **Linear Flow & Layout Modernization:** Add forward `st.page_link` CTAs across pages (`1. Collect → 2. Score → 3. Briefs → 4. Storyboard → 5. Assets`) and modernize deprecated `use_container_width=True` to `width="stretch"` across Pages 1–3.

- **Defects & Drift IDs Resolved:**
  - `UI-003`: Broken `\rightarrow` escape sequence in `app.py:68` rendering as `ightarrow`
  - `UI-004`: Non-functional weight sliders on Page 2 pushing primary actions below the fold
  - `UI-005`: Duplicate stacked Brief Summary card on Page 3
  - `UI-006`: Raw Python list repr displayed for `manifest.blocking_reasons` on Page 5
  - `UI-007`: Retired SSE Streaming subsystem displayed as `⚪ SSE Streaming: UNKNOWN` on Page 6
  - `UI-008`: Worker offline status triggering false-positive yellow warning in manual operation mode
  - `REL-001`: Batch LLM loops failing slowly across all topics on non-retryable `400 API_KEY_INVALID`
  - `REL-002`: Missing SQLite tables in partial `content_factory.db` requiring manual CLI initialization

---

## 3. Atomic Commit Plan

Ordered, single-concern commits to be executed sequentially by `refactor-executor`:

### Commit 1: `feat(ui): add manual custom topic creation and dynamic queue prompt on page 1`
- **Files to Touch:**
  - `src/content_creation/ui/services/client.py` (Add `create_manual_topic` method)
  - `src/content_creation/ui/pages/1_topic_collection.py` (Lines 25-65: add custom topic form, dynamic staged prompt, modernize `width="stretch"`, add forward `st.page_link` to Page 2)
  - `tests/test_ui_client.py` (Unit tests for `create_manual_topic` validation and persistence)
  - `tests/test_ui_pages.py` (AppTest coverage for Page 1 manual topic submission)
- **Defect IDs Addressed:** Feature gap (manual research ingestion), `use_container_width` modernization
- **Acceptance Criteria:**
  - `ServiceClient.create_manual_topic(title, notes, url="", source_id="manual")` validates inputs, generates deterministic ID, constructs a valid `TopicItem` with `status=TopicStatus.STAGED`, and saves to `data/staged/{topic_id}.json` using UTF-8 encoding.
  - Page 1 provides a clean form allowing creators to input title, notes, and optional URL.
  - Submitting the form persists the topic, displays a success notification, and refreshes the staged list.
  - When staged topics exist, the notice dynamically displays `"{count} staged topics ready in queue"` instead of `"Run feed collection to download papers"`.
  - Deprecated `use_container_width=True` replaced with `width="stretch"` across Page 1.
  - Forward `st.page_link` points to `pages/2_topic_pipeline.py`.

### Commit 2: `feat(ui): add production cue sheet and tts voiceover copy blocks`
- **Files to Touch:**
  - `src/content_creation/ui/services/client.py` (Add `format_voiceover_script` and `format_production_cue_sheet`)
  - `src/content_creation/ui/pages/4_storyboard.py` (Add scene-cue copy block; add forward `st.page_link` to Page 5)
  - `src/content_creation/ui/pages/5_asset_workshop.py` (Lines 125-185: format blocking reasons as badges; add Voiceover Only and Full Production Cue Sheet `st.code` blocks)
  - `tests/test_ui_client.py` (Unit tests for cue sheet and voiceover formatting)
  - `tests/test_ui_pages.py` (AppTest coverage for cue sheet copy views and blocking reasons rendering)
- **Defect IDs Addressed:** `UI-006` (raw list repr), Feature gap (video editor export)
- **Acceptance Criteria:**
  - `format_voiceover_script(topic_id)` returns clean narration text formatted for TTS audio generation.
  - `format_production_cue_sheet(topic_id)` outputs a comprehensive cue sheet merging visual metaphors, scene numbers, timestamps, spoken voiceover, B-roll cues, and audio cues.
  - Page 5 `tab_script` renders two one-click `st.code` copy blocks for Voiceover Only and Full Production Cue Sheet.
  - Page 5 displays `manifest.blocking_reasons` as clean formatted badges/pills rather than raw `['script: missing']`.
  - Page 4 provides scene-cue copy in an expander.

### Commit 3: `fix(reliability): add startup db self-heal and fail-fast auth circuit breaker`
- **Files to Touch:**
  - `src/content_creation/ui/services/client.py` (Add top-of-file `from dotenv import load_dotenv; load_dotenv()`; add `@st.cache_resource` `ensure_database_initialized`)
  - `src/content_creation/ui/app.py` (Invoke `ensure_database_initialized` during bootstrap)
  - `src/content_creation/inference/providers/gemini.py` (Lines 14-40: classify `400 API_KEY_INVALID` as `ErrorCategory.AUTH`)
  - `src/content_creation/application/brief_generation_service.py` (Lines 103-106: fail fast on non-retryable auth error in batch loop)
  - `tests/test_inference_gemini_auth.py` (NEW domain test: verify `400 API_KEY_INVALID` classification and batch loop abort)
- **Defect IDs Addressed:** `REL-001` (slow loop failure on bad key), `REL-002` (partial DB self-heal)
- **Acceptance Criteria:**
  - `src/content_creation/ui/services/client.py` includes `from dotenv import load_dotenv; load_dotenv()` at module top-level so direct Streamlit subpage loads/reloads always load `.env` into process memory instead of falling back to `.streamlit/secrets.toml`.
  - `ensure_database_initialized()` runs idempotently on app startup via `@st.cache_resource`, ensuring all 6 tables exist in `content_factory.db` without executing DDL on page rerenders.
  - `GeminiProvider._classify_client_error` classifies `code == 400` with `"API_KEY_INVALID"` as `ErrorCategory.AUTH` with an actionable message.
  - `BriefGenerationService.run()` aborts immediately on the first topic when an auth error occurs, rather than iterating through all remaining topics with rate limit delays.

### Commit 4: `refactor(ui): streamline pages 0 through 6 layout, linear navigation, and dead artifact cleanup`
- **Files to Touch:**
  - `src/content_creation/ui/app.py` (Line 68: fix `\rightarrow` escape to `→`; lines 50-56: make metric cards navigable with `st.page_link`)
  - `src/content_creation/ui/pages/2_topic_pipeline.py` (Lines 25-46: replace 5 sliders with read-only scoring weights expander; add priority tier badges; modernize `width="stretch"`; add forward `st.page_link` to Page 3)
  - `src/content_creation/ui/pages/3_brief_viewer.py` (Lines 107, 121-144: remove duplicate stacked Brief Summary card; format `needs_review` as `Pending review ⏳`; modernize `width="stretch"`; add forward `st.page_link` to Page 4)
  - `src/content_creation/ui/pages/4_storyboard.py` (Lines 69-70: show `✅`/`⏳` readiness in Brief Selector; lines 320-323: remove duplicate empty-state notice)
  - `src/content_creation/ui/pages/6_operations_dashboard.py` (Lines 54-75, 227-244: filter out retired SSE component; ignore info-level worker alert in warning box)
  - `src/content_creation/ui/services/client.py` (Lines 616-665: exclude `ComponentType.SSE` from snapshot components; downgrade manual worker alert to `AlertSeverity.INFO`)
  - `tests/test_ui_pages.py` (Update AppTest assertions for cleaned UI structures)
- **Defect IDs Addressed:** `UI-003`, `UI-004`, `UI-005`, `UI-007`, `UI-008`
- **Acceptance Criteria:**
  - `app.py:68` renders clean `(Collect → Score → Briefs → CI → Storyboards → Assets → Manifests)` without KaTeX/raw escape artifacts.
  - App dashboard metric cards provide direct clickable navigation links to their respective stage pages.
  - Page 2 replaces non-functional sliders with a clean read-only summary, placing `⚖️ Score Topics` and scored table above the fold; priority scores display visual tier badges.
  - Page 3 removes redundant stacked Brief Summary card; `needs_review` statuses render with muted `Pending review ⏳` badge.
  - Page 4 Brief Selector shows `✅` for briefs with existing storyboards and `⏳` for pending storyboards; redundant empty-state notice removed.
  - Page 6 operations dashboard eliminates the retired `⚪ SSE Streaming: UNKNOWN` component; manual worker daemon status renders as a neutral informative note rather than a yellow alarm expander.

### Commit 5: `test(ui): add comprehensive unit and apptest coverage for phase 2d usability features`
- **Files to Touch:**
  - `tests/test_ui_client.py` (Full verification for manual topics, cue sheet generation, and DB self-heal)
  - `tests/test_ui_pages.py` (AppTest suite testing all 7 pages with new components, forms, and copy blocks)
  - `tests/test_inference_gemini_auth.py` (Auth circuit breaker tests with synthetic error payloads)
- **Acceptance Criteria:**
  - All unit and AppTest test suites pass 100% green (`pytest -o addopts="" -v`).
  - Total test count does not decrease from baseline.
  - Zero deprecation warnings in test output.

---

## 4. Strict File Allowlist

### 4.1 Existing Files to Modify (Strictly 10 `src/` modules + tests)
1. `src/content_creation/ui/app.py`
2. `src/content_creation/ui/services/client.py`
3. `src/content_creation/ui/pages/1_topic_collection.py`
4. `src/content_creation/ui/pages/2_topic_pipeline.py`
5. `src/content_creation/ui/pages/3_brief_viewer.py`
6. `src/content_creation/ui/pages/4_storyboard.py`
7. `src/content_creation/ui/pages/5_asset_workshop.py`
8. `src/content_creation/ui/pages/6_operations_dashboard.py`
9. `src/content_creation/inference/providers/gemini.py`
10. `src/content_creation/application/brief_generation_service.py`
11. `tests/test_ui_client.py`
12. `tests/test_ui_pages.py`

### 4.2 New Files to Create
1. `tests/test_inference_gemini_auth.py` (Domain-named test for Gemini auth error classification and batch loop abort)

### 4.3 Files to Delete / Retire
- None (All deprecated SSE files were already retired in Phase 2C).

### 4.4 Prohibited File Names (Anti-Drift Guardrail)
- **Prohibited:** Phase-named test files (e.g., `tests/test_phase2d_qa.py`, `tests/test_phase2d.py`, `tests/test_creator_usability.py`).
- Tests must strictly adhere to domain naming (`test_ui_client.py`, `test_ui_pages.py`, `test_inference_gemini_auth.py`).

---

## 5. Explicit Out-of-Scope / Deferred Items

To prevent scope creep and maintain bite-sized branches, the following items are strictly forbidden on this branch:
- [ ] **No Changes to Frozen Scopes:** Zero edits to `src/content_creation/models/`, `src/content_creation/generation/`, `prompts/`, or `docs/schema.md`.
- [ ] **No Secondary Channel Modifications:** `newsletter` and `linkedin_post` must remain 100% untouched.
- [ ] **No Phase 3 LangGraph Migration:** Do not introduce `langgraph`, `StateGraph`, `SqliteSaver`, or rewrite generation pipelines on this branch.
- [ ] **No PydanticAI / Ollama Local Tier:** Do not introduce PydanticAI agents or local Ollama endpoints (deferred to Phase 3A).
- [ ] **No External Service Plumbing:** Zero Docker, Redis, Celery, RabbitMQ, or cloud deployment infrastructure.

---

## 6. Required Verification Gates (Zero-Trust)

Downstream verification agents (`contract-verifier` and `qa-test-engineer`) will validate against these explicit gates before completion:

1. **Gate 1: Strict Scope & File Allowlist Compliance:**
   - Git diff must touch **only** the 10 `src/` files and 3 test files declared in §4.
   - Command: `git diff --name-only main`
   - Zero unauthorized file modifications.

2. **Gate 2: Static Typing Ratchet (`mypy --strict`):**
   - Command: `uv run mypy src/content_creation/ui src/content_creation/inference/providers/gemini.py src/content_creation/application/brief_generation_service.py --strict`
   - Expected: 0 errors in touched files. Baseline error count on untouched files must not increase.

3. **Gate 3: AST Layer-Violation Check:**
   - UI pages must have 0 direct imports of `LocalStorage`, database repositories, or inference classes.
   - All persistence and domain operations must route through `ServiceClient`.
   - File I/O encoding check: All `open()` calls in touched files must declare `encoding="utf-8"`.

4. **Gate 4: Targeted & Baseline Test Suites:**
   - Targeted UI client test: `uv run python -m pytest tests/test_ui_client.py -o addopts="" -v` (100% pass)
   - Targeted UI pages test: `uv run python -m pytest tests/test_ui_pages.py -o addopts="" -v` (100% pass)
   - Targeted Gemini auth test: `uv run python -m pytest tests/test_inference_gemini_auth.py -o addopts="" -v` (100% pass)
   - Baseline regression check: `uv run python -m pytest -o addopts="" --tb=no -q` (Passing count must be $\ge$ baseline).

5. **Gate 5: Real Runtime Headless AppTest Verification:**
   - AppTest execution of all 7 Streamlit pages (`app.py`, `1_topic_collection.py`, `2_topic_pipeline.py`, `3_brief_viewer.py`, `4_storyboard.py`, `5_asset_workshop.py`, `6_operations_dashboard.py`).
   - Every page must initialize, render components, and complete with `len(at.exception) == 0`.

---

## 7. Orchestrator Chain Directive

The `phase-orchestrator` must execute this specification using the standard sequential lifecycle:
1. `refactor-executor` on feature branch `feat/phase2d-creator-usability`
2. `contract-verifier` (audit against Gates 1–5; halt with BLOCK if any violation detected)
3. `error-taxonomy-chronicler` (harvest and document resolved defect IDs `UI-003` through `UI-008`, `REL-001`, `REL-002`)
4. `qa-test-engineer` (design domain tests; execute headless AppTest boundary checks and fault injection)
5. Final taxonomy and schema verification
6. Halt for human review — **DO NOT MERGE TO MAIN, DO NOT PUSH REMOTE**.
