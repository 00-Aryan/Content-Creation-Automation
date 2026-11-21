# Error Taxonomy & Failure Catalog: Content Creation Automation

## 1. Catalog Metadata & Health Overview
- **Last Updated:** `2026-11-21T17:45:00+05:30`
- **Active Branch:** `refactor/phase2b-ui-and-fragments`
- **Audited Commit (SHA):** `1904b6d` (`1904b6d9f4fffa186b9ec80af3c4b5e65c3f7f50`)
- **Pytest Sweep Baseline:** `1366 passed, 6 failed, 0 skipped, 0 xfailed in 15.14s`
- **Total Observed Errors (`ERR-xxx`):** `23` (`5 OPEN`, `1 MITIGATED`, `17 RESOLVED`)
- **Total Anticipated Risks (`RISK-xxx`):** `5`
- **QA Coverage Ratio:** `19/23 (82.61%) Covered` (`1 Partial`, `3 Uncovered`)
- **Pending Operator Hygiene Action (`UI-005`):** 26 pre-existing 0-byte staged files (`data/staged/*.json`) and 5 pre-existing 0-byte storyboards (`data/storyboards/*.json`) safely guarded in code; pending operator execution of PowerShell cleanup: `Get-ChildItem -Path 'data/staged/*.json', 'data/storyboards/*.json' | Where-Object { $_.Length -eq 0 } | Remove-Item -Force`.
- **Runtime Friction Note:** Windows pytest cache file locking (`.pytest_cache\v\cache\nodeids`) observed under rapid consecutive pytest runs; mitigated via `-p no:cov` / `-o addopts=""`.

---

## 2. Stage x Error Class Heatmap

| Stage / Scope | TRANSPORT | SCHEMA | DATA_IO | QUALITY | STATE_CONCURRENCY | PLATFORM | STATIC_TYPING | BUDGET_CONFIG | Total |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Stage 1: Ingestion | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 3 |
| Stage 2: Scoring | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 3 |
| Stage 3: Briefs | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| Stage 4: Intelligence | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Stage 5: Storyboard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 6: Assets | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| Stage 7: Review | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 8: Manifest | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 9: Planning | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Stage 10: Dry Run | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Stage 11: Analytics | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 12: Event Store | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| Stage 13: Metrics | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 14: Audit | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 15: Jobs | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 16: Notifications | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| UI Presentation Tier | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 3 |
| CLI Entrypoint | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 |
| Infra / Tooling | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 4 |
| **Total** | **0** | **5** | **3** | **3** | **3** | **5** | **4** | **0** | **23** |

---

## 3. Master Summary Ledger

| ID | Title | Stage / Scope | Error Class | Severity | Status | QA Coverage | First Seen | Resolved In |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|
| `ERR-001` | CLI Main Scope Local sys and timedelta Variable Shadowing | CLI Entrypoint | `CODE_STATIC_TYPING` | High | `RESOLVED` | `COVERED` | `5bbee84` | `96ec8d7` |
| `ERR-002` | Event Store Replay Non-Deterministic UUID String Tie-Breaker | Stage 12: Event Store | `STATE_WORKFLOW_CONCURRENCY` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `74a0031` |
| `ERR-003` | Issue Runner Subprocess Spawns POSIX bash on Windows Hosts | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `91cd668` |
| `ERR-004` | Notification SSE Server IPv6 Localhost Socket Connect Denial and Legacy JS Iframe (UI-004) | Stage 16: Notifications | `ENVIRONMENT_PLATFORM` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `e1b0246` |
| `ERR-005` | Brief Generator Fallback Leaks ReviewStatus String into Recommended Formats | Stage 3: Briefs | `QUALITY_GROUNDING` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `775cea2` |
| `ERR-006` | 0-Byte Storyboard JSON Truncation Triggers JSONDecodeError in Asset Generation and Storyboard Loader (UI-001) | Stage 6: Assets | `DATA_ENCODING_IO` | High | `RESOLVED` | `COVERED` | `5bbee84` | `f2e8c78` |
| `ERR-007` | Scoring Component Float Rounding Drift Violates Score Consistency Invariant | Stage 2: Scoring | `QUALITY_GROUNDING` | Low | `RESOLVED` | `COVERED` | `5bbee84` | `b2ebad1` |
| `ERR-008` | Teaser RSS Feed Items Discarded Prematurely by Insufficient Text Filter | Stage 2: Scoring | `QUALITY_GROUNDING` | Medium | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-009` | CLI Subcommand Drift vs Documentation for Content Intelligence and Storyboards | CLI Entrypoint | `CODE_STATIC_TYPING` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `b69115d` |
| `ERR-010` | AppContainer Sandbox Permission Denial on Storage Directory Writeability Probe | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Medium | `OPEN` | `COVERED` | `5bbee84` | - |
| `ERR-011` | Non-UTF-8 CP1252 Smart Quotes in Staged Feed JSON Files Trigger Decoding Warnings | Stage 1: Ingestion | `DATA_ENCODING_IO` | Low | `RESOLVED` | `COVERED` | `5bbee84` | `16c90f3` |
| `ERR-012` | CLI Monolithic Main Function Variable Scope Collisions Under Strict Typing | CLI Entrypoint | `CODE_STATIC_TYPING` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `b69115d` |
| `ERR-013` | TopicItem Domain Model Typing.Any Metadata Leak | Stage 1: Ingestion | `SCHEMA_VALIDATION` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `3846d2d` |
| `ERR-014` | ScoredTopicItem Inherited Typing.Any Metadata Persistence Leak | Stage 2: Scoring | `SCHEMA_VALIDATION` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `3846d2d` |
| `ERR-015` | WeeklyCalendar Config Snapshot Raw Untyped Dict Leak | Stage 9: Planning | `SCHEMA_VALIDATION` | Low | `RESOLVED` | `COVERED` | `5bbee84` | `3846d2d` |
| `ERR-016` | ContentIntelligence Quality Status Unvalidated String Leak | Stage 4: Intelligence | `SCHEMA_VALIDATION` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `3846d2d` |
| `ERR-017` | AssetCheck Review Status Unvalidated String Leak in Dry Run | Stage 10: Dry Run | `SCHEMA_VALIDATION` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `3846d2d` |
| `ERR-018` | 0-Byte Staged JSON Truncation Triggers JSONDecodeError in Ingestion Staged Store | Stage 1: Ingestion | `DATA_ENCODING_IO` | Medium | `OPEN` | `COVERED` | `f6c3f43` | - |
| `ERR-019` | Windows File Lock Contention on .coverage Database During Pytest Invocations | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Low | `OPEN` | `UNCOVERED` | `f6c3f43` | - |
| `ERR-020` | Operations Dashboard Direct SQLite Connection and Inline DDL Schema Violations (UI-002) | UI Presentation Tier | `STATE_WORKFLOW_CONCURRENCY` | High | `RESOLVED` | `COVERED` | `5bbee84` | `c8acfb1` |
| `ERR-021` | Timeline Component Direct Backend SQLite Persistence Coupling (UI-003) | UI Presentation Tier | `STATE_WORKFLOW_CONCURRENCY` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `c8acfb1` |
| `ERR-022` | Streamlit Runtime Deprecated Parameters and Legacy Component Warnings (UI-006) | UI Presentation Tier | `CODE_STATIC_TYPING` | Low | `MITIGATED` | `PARTIAL` | `5bbee84` | - |
| `ERR-023` | Windows Pytest Cache Lock Contention on .pytest_cache During Rapid Invocations | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Low | `OPEN` | `UNCOVERED` | `1904b6d` | - |

---

## 4. Detailed Observed Error Cards

### `ERR-001`: CLI Main Scope Local sys and timedelta Variable Shadowing
- **Stage / Scope:** CLI Entrypoint
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** High
- **Status:** `RESOLVED` (`resolved_in_commit: 96ec8d7`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:11`, `docs/audit/handoffs/fix-phase1a-core-defects.md:11, 20-21`
- **Exception / Symptom:** cannot access local variable 'sys' where it is not associated with a value / cannot access local variable 'timedelta'
- **Root Cause Location:** `src/content_creation/cli.py:1350`, `src/content_creation/cli.py:1283`, `src/content_creation/cli.py:1338`, `src/content_creation/cli.py:1479`, `src/content_creation/cli.py:1726`
- **Affected Tests / Callsites:**
  - `tests/test_cli.py:test_status_command`
  - `tests/test_cli.py:test_collect_command_real`
  - `tests/test_cli.py:test_collect_command_all`
  - `tests/test_cli.py:test_plan_week_default_date_uses_unshadowed_timedelta`
- **Reproduction Command:** `uv run python -m pytest tests/test_cli.py -k test_status_command --no-cov`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_exception_handler_uses_unshadowed_sys verifying sys.stderr write on exception and test_plan_week_default_date_uses_unshadowed_timedelta.

---

### `ERR-002`: Event Store Replay Non-Deterministic UUID String Tie-Breaker
- **Stage / Scope:** Stage 12: Event Store
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 74a0031`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:12`, `docs/audit/handoffs/fix-phase1a-core-defects.md:22-25`
- **Exception / Symptom:** list_after_event returns empty list due to random UUID string comparison on identical timestamps
- **Root Cause Location:** `src/content_creation/events/store/sqlite_repository.py:205-206`
- **Affected Tests / Callsites:**
  - `tests/test_event_persistence.py:test_list_after_event`
  - `tests/test_event_persistence.py:test_replay_after_event`
  - `tests/test_event_persistence.py:test_replay_after_event_for_sse`
  - `tests/test_event_persistence.py:test_sse_recovery_no_duplicate_delivery`
- **Reproduction Command:** `uv run python -m pytest tests/test_event_persistence.py:test_list_after_event --no-cov`
- **Recommended Runtime Policy:** `DETERMINISTIC_STATE_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_list_after_event_identical_timestamps_deterministic enforcing rowid sorting on events with identical timestamps and inverted UUID strings.

---

### `ERR-003`: Issue Runner Subprocess Spawns POSIX bash on Windows Hosts
- **Stage / Scope:** Infra / Tooling
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 91cd668`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:13`, `tests/test_issue_runner.py:323`, `docs/audit/handoffs/refactor-phase2a-typer-cli.md:41-45`, `docs/audit/verification/refactor-phase2a-typer-cli-b09f85b.md:91`, `docs/audit/qa/refactor-phase2a-typer-cli.md:15-24, 92`
- **Exception / Symptom:** [WinError 1920] The file cannot be accessed by the system when invoking subprocess with bash on Windows (due to 0-byte WindowsApps UWP stub at AppData\Local\Microsoft\WindowsApps\bash.exe)
- **Root Cause Location:** `scripts/issue_runner.py:622-647`
- **Affected Tests / Callsites:**
  - `tests/test_issue_runner.py (83 tests in suite now pass on Windows)`
  - `tests/test_issue_runner.py:test_validation_sequential_failure_stops_block`
  - `tests/test_issue_runner.py:test_validation_successful_sequential_commands_pass`
  - `tests/test_issue_runner.py:test_validation_multiple_blocks_stop_at_first_failure`
  - `tests/test_issue_runner.py:test_validation_uses_bash_pipefail`
  - `tests/test_issue_runner.py:test_get_bash_executable_non_windows`
  - `tests/test_issue_runner.py:test_get_bash_executable_windows_valid_candidate_in_path`
  - `tests/test_issue_runner.py:test_get_bash_executable_windows_skips_windowsapps_stub_and_finds_git_bash`
  - `tests/test_issue_runner.py:test_get_bash_executable_windows_git_relative_paths`
  - `tests/test_issue_runner.py:test_get_bash_executable_windows_program_files_fallback`
  - `tests/test_issue_runner.py:test_get_bash_executable_windows_program_files_x86_fallback`
  - `tests/test_issue_runner.py:test_get_bash_executable_windows_fallback_to_bare_bash_when_not_found`
  - `tests/test_issue_runner.py:test_run_validation_blocks_invokes_resolved_bash_with_pipefail`
  - `tests/test_issue_runner.py:test_run_validation_blocks_short_circuit_and_error_propagation`
  - `tests/test_issue_runner.py:test_run_validation_blocks_empty_list`
- **Reproduction Command:** `uv run python -m pytest tests/test_issue_runner.py --no-cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Parametrize test_issue_runner.py to inspect sys.platform and verify get_bash_executable() discovers Git Bash or falls back gracefully without WinError 1920.

---

### `ERR-004`: Notification SSE Server IPv6 Localhost Socket Connect Denial and Legacy JS Iframe (UI-004)
- **Stage / Scope:** Stage 16: Notifications
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: e1b0246`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:14 (DEF-004)`, `docs/refactor/adrs/001-native-fragments-and-ui-facades.md (ADR-001)`, `docs/refactor/tasks/phase2b-ui-and-fragments.md:36-39, 53 (UI-004)`, `docs/audit/handoffs/refactor-phase2b-ui-and-fragments.md:22, 27-28`, `docs/audit/verification/refactor-phase2b-ui-and-fragments-a13ff82.md:101, 128-130`
- **Exception / Symptom:** [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions / broken JS postMessage bridge in embedded iframe; resolved by retiring background SSE server and iframe in favor of native Streamlit @st.fragment polling per ADR-001.
- **Root Cause Location:** `src/content_creation/notifications/streaming/server.py:254`, `src/content_creation/ui/components/sse_client.py:1-42`, `tests/test_notification_streaming.py:43`, `tests/test_notification_streaming.py:457`
- **Affected Tests / Callsites:**
  - `tests/test_notification_streaming.py (12 fragile socket integration tests retired per ADR-001; unit tests retained)`
  - `tests/test_ui_pages.py:test_all_pages_render_without_exceptions`
- **Reproduction Command:** `uv run python -m pytest tests/test_notification_streaming.py -o addopts="" -p no:cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Verify tests/test_notification_streaming.py runs cleanly with 0 failures and tests/test_ui_pages.py asserts @st.fragment notification polling badge renders cleanly without background SSE server.

---

### `ERR-005`: Brief Generator Fallback Leaks ReviewStatus String into Recommended Formats
- **Stage / Scope:** Stage 3: Briefs
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 775cea2`) (`mitigated_in_commit: aabeeeb`)
- **Source Evidence:** `docs/audit/handoffs/fix-phase1a-core-defects.md:26-30, 97-100`, `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:93-97, 127-130`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:18-19, 81-84`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:78-81`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:16-17`
- **Exception / Symptom:** Brief fallback sets recommended_formats=['needs_review'], causing downstream manifest builder to warn on unknown format and fallback to short_video
- **Root Cause Location:** `src/content_creation/generation/brief.py:71`, `src/content_creation/manifest.py:189-195`
- **Affected Tests / Callsites:**
  - `tests/test_manifest.py:test_upstream_brief_generator_fallback_does_not_leak_review_status`
  - `tests/test_manifest.py:test_recommended_formats_filters_review_status_leak`
  - `tests/test_manifest.py:test_recommended_formats_with_only_review_status_defaults_cleanly`
  - `tests/test_manifest.py:test_recommended_formats_genuine_unknown_format_logs_warning`
  - `tests/test_phase1b_qa.py:test_fallback_brief_generates_valid_short_video_without_leak`
  - `tests/test_phase1b_qa.py:test_fallback_brief_triggered_by_malformed_json_response`
  - `tests/test_phase1b_qa.py:test_manifest_builder_filters_all_review_status_leak_variants`
  - `tests/test_phase1b_qa.py:test_manifest_builder_preserves_valid_formats_in_mixed_list`
- **Reproduction Command:** `uv run python -m pytest tests/test_manifest.py -k test_upstream_brief_generator_fallback_does_not_leak_review_status --no-cov`
- **Recommended Runtime Policy:** `ENRICHMENT_OR_CRITIC_LOOP`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Verify test_upstream_brief_generator_fallback_does_not_leak_review_status asserts fallback brief recommended_formats produces valid format ('short_video') without 'needs_review'.

---

### `ERR-006`: 0-Byte Storyboard JSON Truncation Triggers JSONDecodeError in Asset Generation and Storyboard Loader (UI-001)
- **Stage / Scope:** Stage 6: Assets
- **Error Class:** `DATA_ENCODING_IO`
- **Severity:** High
- **Status:** `RESOLVED` (`resolved_in_commit: f2e8c78`)
- **Source Evidence:** `Live pipeline smoke test: generate-assets --top 2`, `docs/refactor/tasks/phase2b-ui-and-fragments.md:40-44, 50 (UI-001)`, `docs/audit/handoffs/refactor-phase2b-ui-and-fragments.md:18, 25, 43-47`, `docs/audit/verification/refactor-phase2b-ui-and-fragments-a13ff82.md:99, 120-125`, `Note: UI-005 tracks pending operator removal of 5 pre-existing 0-byte storyboards on disk`
- **Exception / Symptom:** Failed to load Storyboard <topic_id>.json: Expecting value: line 1 column 1 (char 0), crashing UI storyboard page and causing AssetGenerationService to skip asset generation. Resolved in JsonRepository with st_size == 0 guard, UTF-8/cp1252 fallback, atomic os.replace temp write, and client.storyboard_file_exists() UI diagnostics.
- **Root Cause Location:** `src/content_creation/platform/storage/json_repository.py:34-45`, `src/content_creation/platform/storage/json_repository.py:65-75`, `src/content_creation/ui/pages/4_storyboard.py:78-105`, `src/content_creation/ui/pages/5_asset_workshop.py:120-135`
- **Affected Tests / Callsites:**
  - `tests/test_json_repository.py:test_load_file_zero_byte_warning_returns_none`
  - `tests/test_json_repository.py:test_get_storyboard_corrupt_logs_error`
  - `tests/test_json_repository.py:test_atomic_write_creates_valid_json`
  - `tests/test_manifest.py:TestStoryboardFaultInjectionAndUpstreamProbes::test_load_storyboard_handles_empty_or_truncated_file`
  - `tests/test_ui_pages.py:test_all_pages_render_without_exceptions`
- **Reproduction Command:** `uv run python -m pytest tests/test_json_repository.py tests/test_manifest.py -k test_load_storyboard_handles_empty_or_truncated_file -o addopts="" -p no:cov`
- **Recommended Runtime Policy:** `DEFENSIVE_IO_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Verify tests/test_json_repository.py asserts 0-byte and corrupted storyboards log structured warnings and return None, while tests/test_ui_pages.py asserts corrupted files display clear UI diagnostic warnings rather than unhandled JSONDecodeError crashes.

---

### `ERR-007`: Scoring Component Float Rounding Drift Violates Score Consistency Invariant
- **Stage / Scope:** Stage 2: Scoring
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Low
- **Status:** `RESOLVED` (`resolved_in_commit: b2ebad1`)
- **Source Evidence:** `Live pipeline smoke test: score-topics validation log`, `src/content_creation/scoring/validation.py:49`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:24, 29`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:82`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:23`
- **Exception / Symptom:** Score inconsistency: priority_score (65.75) != sum of components (65.76) flagged across multiple scored topics due to floating-point representation drift
- **Root Cause Location:** `src/content_creation/scoring/base.py:108-115`, `src/content_creation/scoring/validation.py:48-50`
- **Affected Tests / Callsites:**
  - `tests/test_scoring.py:test_score_consistency_rule_tolerates_float_rounding_drift`
  - `tests/test_phase1b_qa.py:test_score_consistency_rule_drift_bva`
  - `tests/test_phase1b_qa.py:test_score_consistency_rule_disabled_when_config_false`
- **Reproduction Command:** `uv run python -m pytest tests/test_scoring.py:test_score_consistency_rule_tolerates_float_rounding_drift --no-cov`
- **Recommended Runtime Policy:** `ENRICHMENT_OR_CRITIC_LOOP`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_score_consistency_rule_tolerates_float_rounding_drift verifying 0.05 tolerance threshold ignores harmless floating-point delta while flagging genuine inconsistencies > 0.05.

---

### `ERR-008`: Teaser RSS Feed Items Discarded Prematurely by Insufficient Text Filter
- **Stage / Scope:** Stage 2: Scoring
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `Live pipeline smoke test: score-topics execution summary`, `src/content_creation/scoring/engine.py:252-254`
- **Exception / Symptom:** 290 out of 2048 topics rejected as insufficient_text when raw_text < 100 chars, discarding flagship posts (GPT-4o System Card, Introducing OpenAI o1)
- **Root Cause Location:** `src/content_creation/scoring/engine.py:252`
- **Affected Tests / Callsites:**
  - `None` (Discovered via runtime smoke test or verification audit)
- **Reproduction Command:** `uv run python -c "from content_creation.scoring.engine import ScoringEngine; from content_creation.scoring.config import ScoringConfig; from content_creation.models.topic import TopicItem; t = TopicItem(id='test', title='Introducing OpenAI o1', url='https://openai.com/index/o1', source='openai', category='release', raw_text='Short teaser'); e = ScoringEngine(ScoringConfig()); res = e.score_items([t]); print(res['rejected'][0].rejection_reason)"`
- **Recommended Runtime Policy:** `ENRICHMENT_OR_CRITIC_LOOP`
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add test_short_teaser_flagged_for_enrichment asserting that topics with short raw_text but high-credibility sources trigger an enrichment fetch rather than immediate rejection.

---

### `ERR-009`: CLI Subcommand Drift vs Documentation for Content Intelligence and Storyboards
- **Stage / Scope:** CLI Entrypoint
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: b69115d`)
- **Source Evidence:** `README.md:445, 448`, `docs/audit/handoffs/refactor-phase2a-typer-cli.md:23`, `docs/audit/verification/refactor-phase2a-typer-cli-b09f85b.md:89`, `docs/audit/qa/refactor-phase2a-typer-cli.md:25-34, 93`
- **Exception / Symptom:** cli.py: error: argument command: invalid choice: 'generate-ci' / 'generate-storyboards' when following README.md operational instructions; now implemented as Typer subcommands generate-ci and generate-storyboards with --top and --topic-id options
- **Root Cause Location:** `src/content_creation/cli/pipeline.py:84-148`
- **Affected Tests / Callsites:**
  - `tests/test_cli.py:TestCLI::test_generate_ci_and_storyboards_commands`
  - `tests/test_cli.py:test_generate_ci_custom_top_and_topic_id`
  - `tests/test_cli.py:test_generate_ci_default_targets_all_with_default_top`
  - `tests/test_cli.py:test_generate_ci_unrecognized_all_option_returns_usage_error`
  - `tests/test_cli.py:test_generate_ci_executor_failure_returns_exit_code_1`
  - `tests/test_cli.py:test_generate_ci_missing_gemini_api_key_passes_none`
  - `tests/test_cli.py:test_generate_storyboards_custom_top_and_topic_id`
  - `tests/test_cli.py:test_generate_storyboards_default_targets_all_with_default_top`
  - `tests/test_cli.py:test_generate_storyboards_unrecognized_all_option_returns_usage_error`
  - `tests/test_cli.py:test_generate_storyboards_executor_failure_returns_exit_code_1`
  - `tests/test_cli.py:test_generate_storyboards_missing_gemini_api_key_passes_none`
- **Reproduction Command:** `uv run python -m content_creation.cli generate-ci --top 5`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add comprehensive tests verifying generate-ci and generate-storyboards handle missing API keys, invalid topic IDs, and failure responses from WorkflowActionExecutor.

---

### `ERR-010`: AppContainer Sandbox Permission Denial on Storage Directory Writeability Probe
- **Stage / Scope:** Infra / Tooling
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:146`, `Live pytest sweep within AppContainer sandbox`
- **Exception / Symptom:** PermissionError: [WinError 13] Access is denied: '[USER_HOME]/.../.write_test_*' during LocalStorage initialization under AppContainer sandbox
- **Root Cause Location:** `src/content_creation/storage/local.py:64-70`
- **Affected Tests / Callsites:**
  - `tests/test_cli.py:TestCLI::test_status_command`
  - `tests/test_cli.py:TestCLI::test_collect_command_real`
  - `tests/test_cli.py:TestCLI::test_collect_command_all`
  - `tests/test_cli.py:TestCLI::test_plan_week_default_date_uses_unshadowed_timedelta`
- **Reproduction Command:** `uv run python -m pytest tests/test_cli.py --no-cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Update LocalStorage._verify_writeable to probe data/ subdirectory rather than workspace root, avoiding AppContainer ACL permission blocks on root.

---

### `ERR-011`: Non-UTF-8 CP1252 Smart Quotes in Staged Feed JSON Files Trigger Decoding Warnings
- **Stage / Scope:** Stage 1: Ingestion
- **Error Class:** `DATA_ENCODING_IO`
- **Severity:** Low
- **Status:** `RESOLVED` (`resolved_in_commit: 16c90f3`)
- **Source Evidence:** `docs/audit/handoffs/fix-phase1a-core-defects.md:101-103`, `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:131-135`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:25, 30`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:81`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:24`
- **Exception / Symptom:** 'utf-8' codec can't decode byte 0x97 in position 360: invalid start byte logged when inspecting staged JSON files
- **Root Cause Location:** `src/content_creation/storage/local.py:77-90`
- **Affected Tests / Callsites:**
  - `tests/test_storage.py:test_local_storage_cp1252_smart_quotes_decoding_fallback`
  - `tests/test_local_storage.py`
  - `tests/test_phase1b_qa.py:test_read_json_clean_utf8_does_not_log_fallback_warning`
  - `tests/test_phase1b_qa.py:test_read_json_cp1252_smart_punctuation_suite`
  - `tests/test_phase1b_qa.py:test_storage_write_methods_enforce_utf8`
- **Reproduction Command:** `uv run python -m pytest tests/test_storage.py:test_local_storage_cp1252_smart_quotes_decoding_fallback --no-cov`
- **Recommended Runtime Policy:** `DEFENSIVE_IO_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_local_storage_cp1252_smart_quotes_decoding_fallback asserting LocalStorage._read_json safely decodes non-UTF8 smart quotes using CP1252 fallback with a warning log.

---

### `ERR-012`: CLI Monolithic Main Function Variable Scope Collisions Under Strict Typing
- **Stage / Scope:** CLI Entrypoint
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: b69115d`)
- **Source Evidence:** `docs/audit/handoffs/fix-phase1a-core-defects.md:68-71`, `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:29, 136-139`, `docs/audit/handoffs/refactor-phase2a-typer-cli.md:18-25, 64-73`, `docs/audit/verification/refactor-phase2a-typer-cli-b09f85b.md:19, 64-73, 90`, `docs/audit/qa/refactor-phase2a-typer-cli.md:35-45, 94`
- **Exception / Symptom:** 127 errors in 1 file in monolithic cli.py due to repeated local variable scope collisions and unencoded CP1252 export; decomposed into 7 modular Typer submodules passing mypy --strict with 0 errors and explicit UTF-8 encoding
- **Root Cause Location:** `src/content_creation/cli/`
- **Affected Tests / Callsites:**
  - `tests/test_cli.py`
  - `tests/test_cli.py:test_main_programmatic_sequence_argument`
  - `tests/test_cli.py:test_main_programmatic_invalid_command_returns_code_2`
  - `tests/test_cli.py:test_main_programmatic_invalid_option_returns_code_2`
  - `tests/test_cli.py:test_main_unhandled_exception_returns_code_1`
  - `tests/test_cli.py:test_main_click_exception_with_exit_code_and_show_method`
  - `tests/test_cli.py:test_main_click_exception_without_callable_show`
  - `tests/test_cli.py:test_write_text_utf8_unicode_content`
  - `tests/test_cli.py:test_plan_week_markdown_export_utf8_with_unicode_characters`
  - `tests/test_cli.py:test_get_next_monday_bva_and_date_boundaries`
  - `tests/test_cli.py:test_get_next_monday_default_today`
  - `tests/test_cli.py:test_subcommand_dispatch_and_help_text_rendering`
- **Reproduction Command:** `uv run mypy src/content_creation/cli --strict`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add CI strict type checking on src/content_creation/cli and verify write_text_utf8 handles Unicode characters (em-dashes, smart quotes) during calendar export on Windows hosts.

---

### `ERR-013`: TopicItem Domain Model Typing.Any Metadata Leak
- **Stage / Scope:** Stage 1: Ingestion
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 3846d2d`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:47`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:20, 33`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:69`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:18`
- **Exception / Symptom:** TopicItem.metadata was declared as Dict[str, Any] = Field(default_factory=dict), allowing arbitrary unvalidated dictionary structures to bypass Pydantic type validation during ingestion normalization
- **Root Cause Location:** `src/content_creation/models/topic.py:34-60`
- **Affected Tests / Callsites:**
  - `tests/test_models.py:test_topic_metadata_schema_tightening`
  - `tests/test_phase1b_qa.py:test_topic_metadata_typed_and_dynamic_attributes`
  - `tests/test_phase1b_qa.py:test_topic_metadata_mutation_and_keyerror`
  - `tests/test_phase1b_qa.py:test_topic_item_roundtrip_preserves_extra_metadata_fields`
  - `tests/test_phase1b_qa.py:test_topic_storage_roundtrip_with_extra_metadata`
- **Reproduction Command:** `uv run python -m pytest tests/test_models.py:test_topic_metadata_schema_tightening --no-cov`
- **Recommended Runtime Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_topic_metadata_schema_tightening verifying TopicItem uses typed TopicMetadata with extra='allow' and dict access compatibility.

---

### `ERR-014`: ScoredTopicItem Inherited Typing.Any Metadata Persistence Leak
- **Stage / Scope:** Stage 2: Scoring
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 3846d2d`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:48`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:20, 33`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:69`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:18-19`
- **Exception / Symptom:** ScoredTopicItem inherited metadata: Dict[str, Any] from TopicItem, permitting arbitrary untyped payloads to propagate across the scoring stage and persist into data/scored/*.json
- **Root Cause Location:** `src/content_creation/models/topic.py:75`
- **Affected Tests / Callsites:**
  - `tests/test_models.py:test_topic_metadata_schema_tightening`
  - `tests/test_phase1b_qa.py:test_scored_topic_item_inherits_topic_metadata_cleanly`
  - `tests/test_phase1b_qa.py:test_scored_topic_item_priority_score_bva`
- **Reproduction Command:** `uv run python -m pytest tests/test_models.py:test_topic_metadata_schema_tightening --no-cov`
- **Recommended Runtime Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_topic_metadata_schema_tightening verifying ScoredTopicItem inherits typed TopicMetadata and validates schema persistence cleanly.

---

### `ERR-015`: WeeklyCalendar Config Snapshot Raw Untyped Dict Leak
- **Stage / Scope:** Stage 9: Planning
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Low
- **Status:** `RESOLVED` (`resolved_in_commit: 3846d2d`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:49`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:21, 34`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:70`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:20`
- **Exception / Symptom:** config_snapshot: Dict in WeeklyCalendar used raw unparameterized Dict with no key or value type constraints, allowing arbitrary unconstrained configuration objects to persist in calendar records
- **Root Cause Location:** `src/content_creation/models/calendar.py:23-68`
- **Affected Tests / Callsites:**
  - `tests/test_models.py:test_weekly_calendar_publishing_config_snapshot`
  - `tests/test_phase1b_qa.py:test_publishing_config_snapshot_typed_access_and_dict_compatibility`
  - `tests/test_phase1b_qa.py:test_publishing_config_snapshot_mutation_and_keyerror`
  - `tests/test_phase1b_qa.py:test_weekly_calendar_storage_roundtrip_with_config_snapshot_mutations`
- **Reproduction Command:** `uv run python -m pytest tests/test_models.py:test_weekly_calendar_publishing_config_snapshot --no-cov`
- **Recommended Runtime Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_weekly_calendar_publishing_config_snapshot asserting WeeklyCalendar uses typed PublishingConfigSnapshot preserving backward-compatible dict indexing and JSON serialization.

---

### `ERR-016`: ContentIntelligence Quality Status Unvalidated String Leak
- **Stage / Scope:** Stage 4: Intelligence
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 3846d2d`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:50`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:23, 35`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:72`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:21`
- **Exception / Symptom:** quality_status: Optional[str] = None used unconstrained str rather than QualityStatus enum, allowing invalid quality states to bypass Pydantic model validation
- **Root Cause Location:** `src/content_creation/domains/content_intelligence/model.py:53`
- **Affected Tests / Callsites:**
  - `tests/test_models.py:test_content_intelligence_quality_status_schema`
  - `tests/test_phase1b_qa.py:test_content_intelligence_quality_status_valid_variants`
  - `tests/test_phase1b_qa.py:test_content_intelligence_quality_status_invalid_variants_reject`
  - `tests/test_phase1b_qa.py:test_content_intelligence_storage_roundtrip`
- **Reproduction Command:** `uv run python -m pytest tests/test_models.py:test_content_intelligence_quality_status_schema --no-cov`
- **Recommended Runtime Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_content_intelligence_quality_status_schema enforcing QualityStatus enum validation and asserting ValidationError on illegal strings.

---

### `ERR-017`: AssetCheck Review Status Unvalidated String Leak in Dry Run
- **Stage / Scope:** Stage 10: Dry Run
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 3846d2d`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:51`, `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:22, 36`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:71`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:22`
- **Exception / Symptom:** AssetCheck.review_status was typed as unconstrained str instead of ReviewStatus enum or DryRunReviewStatus union, allowing invalid review states to pass dry run verification checks without schema error
- **Root Cause Location:** `src/content_creation/models/dryrun.py:7-17`
- **Affected Tests / Callsites:**
  - `tests/test_dryrun.py:test_asset_check_review_status_schema_constraint`
  - `tests/test_phase1b_qa.py:test_asset_check_review_status_valid_variants`
  - `tests/test_phase1b_qa.py:test_asset_check_review_status_invalid_variants_reject`
  - `tests/test_phase1b_qa.py:test_dryrun_report_storage_roundtrip`
- **Reproduction Command:** `uv run python -m pytest tests/test_dryrun.py:test_asset_check_review_status_schema_constraint --no-cov`
- **Recommended Runtime Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_asset_check_review_status_schema_constraint asserting AssetCheck rejects arbitrary string values outside ReviewStatus enum or allowed literal statuses.

---

### `ERR-018`: 0-Byte Staged JSON Truncation Triggers JSONDecodeError in Ingestion Staged Store
- **Stage / Scope:** Stage 1: Ingestion
- **Error Class:** `DATA_ENCODING_IO`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:114-117`, `Live LocalStorage.list_staged() scan`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:25-26`, `Note: UI-005 tracks pending operator removal of 26 pre-existing 0-byte staged JSON files in data/staged/`
- **Exception / Symptom:** Failed to load staged item data/staged/05738f6c55b7147880500b666d1a96e73b80de79c9a4453c521b0ffc55549d70.json: Expecting value: line 1 column 1 (char 0). Creation origin of 0-byte truncation in data/staged/ remains unconfirmed in storage backend; unhandled 0-byte read occurs in LocalStorage._read_json.
- **Root Cause Location:** `src/content_creation/storage/local.py:77-90`, `data/staged/05738f6c55b7147880500b666d1a96e73b80de79c9a4453c521b0ffc55549d70.json`
- **Affected Tests / Callsites:**
  - `tests/test_phase1b_qa.py:test_list_staged_handles_zero_byte_file_gracefully`
  - `tests/test_phase1b_qa.py:test_get_staged_handles_zero_byte_file`
  - `tests/test_phase1b_qa.py:test_list_and_get_scored_handles_zero_byte_file`
  - `tests/test_phase1b_qa.py:test_list_and_get_analytics_handles_zero_byte_file`
  - `tests/test_phase1b_qa.py:test_list_staged_handles_corrupt_non_dict_json`
  - `tests/test_phase1b_qa.py:test_save_staged_deduplication_atomic_mode_x`
- **Reproduction Command:** `uv run python -c "from content_creation.storage.local import LocalStorage; from pathlib import Path; s = LocalStorage(Path('.')); print(s.get_staged('05738f6c55b7147880500b666d1a96e73b80de79c9a4453c521b0ffc55549d70'))"`
- **Recommended Runtime Policy:** `DEFENSIVE_IO_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add test_read_json_handles_zero_byte_staged_file asserting LocalStorage._read_json or get_staged/list_staged detects 0-byte file and handles gracefully without raising unhandled JSONDecodeError.

---

### `ERR-019`: Windows File Lock Contention on .coverage Database During Pytest Invocations
- **Stage / Scope:** Infra / Tooling
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Low
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/handoffs/fix-phase1b-data-and-schemas.md:39-43`, `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:128`
- **Exception / Symptom:** PermissionError: [WinError 5] Access is denied: '[USER_HOME]/.../.coverage' when pytest-cov attempts to delete/recreate .coverage while a concurrent process or prior handle is locked on Windows hosts
- **Root Cause Location:** `pyproject.toml:68`
- **Affected Tests / Callsites:**
  - `None` (Discovered via runtime smoke test or verification audit)
- **Reproduction Command:** `uv run python -m pytest --tb=no -q`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Configure pytest invocations to pass -o addopts='' -p no:cacheprovider or specify distinct COVERAGE_FILE environment variable under Windows to prevent lock contention on workspace root.

---

### `ERR-020`: Operations Dashboard Direct SQLite Connection and Inline DDL Schema Violations (UI-002)
- **Stage / Scope:** UI Presentation Tier
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Severity:** High
- **Status:** `RESOLVED` (`resolved_in_commit: c8acfb1`)
- **Source Evidence:** `docs/audit/02-dependencies-and-boundaries.md:38`, `docs/refactor/adrs/001-native-fragments-and-ui-facades.md:14-18 (UI-002)`, `docs/refactor/tasks/phase2b-ui-and-fragments.md:31-35, 51`, `docs/audit/handoffs/refactor-phase2b-ui-and-fragments.md:20, 38-42`, `docs/audit/verification/refactor-phase2b-ui-and-fragments-a13ff82.md:83-85, 100`
- **Exception / Symptom:** Operations dashboard directly executed sqlite3.connect() on 6 backend databases (jobs.db, locks.db, events.db, notifications.db, metrics.db, audit.db), executed inline DDL migrations (create_*_schema), and instantiated 11 internal infrastructure classes on every page render, producing 18 AST layer boundary violations and high risk of Windows SQLite file lock contention
- **Root Cause Location:** `src/content_creation/ui/pages/6_operations_dashboard.py:24-286`
- **Affected Tests / Callsites:**
  - `tests/test_operations_dashboard.py`
  - `tests/test_ui_client.py:test_get_operations_snapshot`
  - `tests/test_ui_pages.py:test_all_pages_render_without_exceptions`
- **Reproduction Command:** `uv run python -m pytest tests/test_operations_dashboard.py tests/test_ui_client.py -o addopts="" -p no:cov`
- **Recommended Runtime Policy:** `DETERMINISTIC_STATE_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Assert AST scan confirms 0 direct sqlite3, repository, or DDL imports in 6_operations_dashboard.py and test_ui_client.py validates snapshot coordination without lock contention.

---

### `ERR-021`: Timeline Component Direct Backend SQLite Persistence Coupling (UI-003)
- **Stage / Scope:** UI Presentation Tier
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: c8acfb1`)
- **Source Evidence:** `docs/refactor/adrs/001-native-fragments-and-ui-facades.md:14-18 (UI-003)`, `docs/refactor/tasks/phase2b-ui-and-fragments.md:33, 52`, `docs/audit/handoffs/refactor-phase2b-ui-and-fragments.md:21`, `docs/audit/verification/refactor-phase2b-ui-and-fragments-a13ff82.md:83-85, 100`
- **Exception / Symptom:** Timeline presentation component directly instantiated EventTimelineService and imported backend EventRecord, bypassing ServiceClient and coupling UI rendering to SQLite event store internals
- **Root Cause Location:** `src/content_creation/ui/components/timeline.py:13-68`
- **Affected Tests / Callsites:**
  - `tests/test_ui_client.py:test_get_event_timeline`
  - `tests/test_ui_pages.py:test_all_pages_render_without_exceptions`
- **Reproduction Command:** `uv run python -m pytest tests/test_ui_client.py -k test_get_event_timeline -o addopts="" -p no:cov`
- **Recommended Runtime Policy:** `DETERMINISTIC_STATE_FIX`
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Assert timeline component accepts presentation-ready event DTOs without importing backend EventRecord or SQLite event repositories.

---

### `ERR-022`: Streamlit Runtime Deprecated Parameters and Legacy Component Warnings (UI-006)
- **Stage / Scope:** UI Presentation Tier
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** Low
- **Status:** `MITIGATED` (`mitigated_in_commit: 4dc3426`)
- **Source Evidence:** `docs/refactor/tasks/phase2b-ui-and-fragments.md:45-47, 54 (UI-006)`, `docs/audit/handoffs/refactor-phase2b-ui-and-fragments.md:23, 25-26, 89`, `docs/audit/verification/refactor-phase2b-ui-and-fragments-a13ff82.md:103, 151`
- **Exception / Symptom:** Streamlit runtime emits deprecation warnings for use_container_width=True (deprecated in Streamlit 1.58 in favor of width='stretch') and st.components.v1.html (scheduled for removal). Mitigated on app.py and pages 4, 5, 6; pages 1-3 cosmetic parameter cleanup deferred to Phase 2C.
- **Root Cause Location:** `src/content_creation/ui/pages/4_storyboard.py:145`, `src/content_creation/ui/pages/5_asset_workshop.py:79, 126, 140, 162, 178, 226, 276`, `src/content_creation/ui/app.py:84`, `src/content_creation/ui/pages/1_topic_collection.py`, `src/content_creation/ui/pages/2_topic_pipeline.py`, `src/content_creation/ui/pages/3_brief_viewer.py`
- **Affected Tests / Callsites:**
  - `tests/test_ui_pages.py:test_all_pages_render_without_exceptions`
- **Reproduction Command:** `uv run python -m pytest tests/test_ui_pages.py -o addopts="" -p no:cov`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX`
- **QA Coverage Status:** `PARTIAL`
- **QA Test Directive:** Headless AppTest verifies refactored pages 4, 5, 6 and app.py render without deprecation warnings; complete parameter migration on pages 1-3 during Phase 2C.

---

### `ERR-023`: Windows Pytest Cache Lock Contention on .pytest_cache During Rapid Invocations
- **Stage / Scope:** Infra / Tooling
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Low
- **Status:** `OPEN`
- **Source Evidence:** `Live pytest baseline sweep output on refactor/phase2b-ui-and-fragments`, `docs/audit/handoffs/refactor-phase2b-ui-and-fragments.md:49-52 (Error #3)`, `docs/audit/verification/refactor-phase2b-ui-and-fragments-a13ff82.md:164`
- **Exception / Symptom:** PytestCacheWarning: cache could not write path ... [Errno 13] Permission denied: '[USER_HOME]/.../.pytest_cache/v/cache/nodeids' and 'lastfailed' when pytest processes run consecutively or terminate rapidly under Windows NTFS file locking
- **Root Cause Location:** `.venv/Lib/site-packages/_pytest/cacheprovider.py:475`, `.venv/Lib/site-packages/_pytest/cacheprovider.py:429`
- **Affected Tests / Callsites:**
  - `None` (Discovered via runtime smoke test or verification audit)
- **Reproduction Command:** `uv run python -m pytest -o addopts="" -p no:cov -q`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Document standard Windows pytest invocation flags in developer docs and configure test scripts to use isolated cache roots or -p no:cacheprovider when rapid execution is required.

---

## 5. Anticipated Stage Risks

### `RISK-001`: Live LLM Provider Quota Exhaustion & Rate Limits
- **Stage / Scope:** Stage 3: Briefs
- **Error Class:** `TRANSPORT_TRANSIENT`
- **Likelihood / Severity:** High
- **Anchored Code Path:** `src/content_creation/inference/manager.py:70`, `src/content_creation/inference/providers/gemini.py:71`
- **Risk Description:** High-concurrency generation bursts without rate-limiting delays trigger HTTP 429 quota exhaustion on Gemini API endpoints.
- **Recommended Policy:** `RETRY_BACKOFF_FALLBACK`
- **QA Test Directive:** Mock 429 response from GeminiProvider and assert failover to OpenRouter without pipeline abort.

---

### `RISK-002`: Malformed Markdown Code Fences in LLM Synthesis Outputs
- **Stage / Scope:** Stage 4: Content Intelligence
- **Error Class:** `SCHEMA_VALIDATION`
- **Likelihood / Severity:** Medium
- **Anchored Code Path:** `src/content_creation/generation/brief.py:46`, `src/content_creation/domains/content_intelligence/generator.py:48`, `src/content_creation/domains/storyboard/generator.py:53`
- **Risk Description:** LLM outputting JSON wrapped in markdown fences (```json ... ```) or conversational commentary triggers json.JSONDecodeError in generator parsing.
- **Recommended Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Test Directive:** Test ContentIntelligenceGenerator and StoryboardGenerator against synthetic responses containing markdown fences, trailing commentary, and unescaped quotes.

---

### `RISK-003`: Unchecked API Token Budget Consumption During High-Volume Batches
- **Stage / Scope:** Stage 6: Asset Generation
- **Error Class:** `BUDGET_QUOTA_CONFIG`
- **Likelihood / Severity:** High
- **Anchored Code Path:** `src/content_creation/inference/manager.py:25`, `src/content_creation/application/asset_generation_service.py:86`
- **Risk Description:** Uncapped multi-format asset generation across large topic batches exhausts account token budgets mid-run, aborting downstream stages.
- **Recommended Policy:** `FAIL_FAST_NO_RETRY`
- **QA Test Directive:** Implement pre-flight token budget validator in AssetGenerationService that calculates estimated batch cost and aborts before LLM dispatch.

---

### `RISK-004`: In-Memory Event Bus Isolation Across Worker Daemon Subprocesses
- **Stage / Scope:** Stage 12: Event Store
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Likelihood / Severity:** Medium
- **Anchored Code Path:** `src/content_creation/events/bus.py:11`, `src/content_creation/jobs/worker_daemon.py:35`
- **Risk Description:** Process-bound singleton _EVENT_BUS in background worker processes drops event delivery to UI subscriber threads and SSE streaming server.
- **Recommended Policy:** `DETERMINISTIC_STATE_FIX`
- **QA Test Directive:** Add test verifying background job completion events are persisted to SQLiteEventRepository and picked up by main process SSE subscribers.

---

### `RISK-005`: POSIX Signal Handling Incompatibility in Windows Background Worker Daemon
- **Stage / Scope:** Stage 15: Jobs & Locks
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Likelihood / Severity:** Medium
- **Anchored Code Path:** `src/content_creation/jobs/worker_daemon.py:35`
- **Risk Description:** Signal handlers using SIGTERM or SIGQUIT fail on Windows OS process termination, leaving stale resource locks in data/jobs.db.
- **Recommended Policy:** `CROSS_PLATFORM_GUARD`
- **QA Test Directive:** Test WorkerDaemon graceful shutdown under Windows console termination events and verify LockManager releases all held locks on process exit.
