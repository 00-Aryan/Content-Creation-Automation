# Error Taxonomy & Failure Catalog: Content Creation Automation

## 1. Catalog Metadata & Health Overview
- **Last Updated:** `2026-11-21T14:40:00+05:30`
- **Active Branch:** `refactor/phase2a-typer-cli`
- **Audited Commit (SHA):** `c3cb9c7` (`c3cb9c7a0f63ad02472f24713df6bded95ee315a`)
- **Pytest Sweep Baseline:** `1343 passed, 18 failed, 0 skipped, 0 xfailed in 20.05s`
- **Total Observed Errors (`ERR-xxx`):** `19` (`6 OPEN`, `0 MITIGATED`, `13 RESOLVED`)
- **Total Anticipated Risks (`RISK-xxx`):** `5`
- **QA Coverage Ratio:** `15/19 (78.95%) Covered` (`1 Partial`, `3 Uncovered`)

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
| CLI Entrypoint | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 |
| Infra / Tooling | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 |
| **Total** | **0** | **5** | **3** | **3** | **1** | **4** | **3** | **0** | **19** |

---

## 3. Master Summary Ledger

| ID | Title | Stage / Scope | Error Class | Severity | Status | QA Coverage | First Seen | Resolved In |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| `ERR-001` | CLI Main Scope Local sys and timedelta Variable Shadowing | CLI Entrypoint | `CODE_STATIC_TYPING` | High | `RESOLVED` | `COVERED` | `5bbee84` | `96ec8d7` |
| `ERR-002` | Event Store Replay Non-Deterministic UUID String Tie-Breaker | Stage 12: Event Store | `STATE_WORKFLOW_CONCURRENCY` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `74a0031` |
| `ERR-003` | Issue Runner Subprocess Spawns POSIX bash on Windows Hosts | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `91cd668` |
| `ERR-004` | Notification SSE Server IPv6 Localhost Socket Connect Denial | Stage 16: Notifications | `ENVIRONMENT_PLATFORM` | Medium | `OPEN` | `PARTIAL` | `5bbee84` | - |
| `ERR-005` | Brief Generator Fallback Leaks ReviewStatus String into Recommended Formats | Stage 3: Briefs | `QUALITY_GROUNDING` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `775cea2` |
| `ERR-006` | 0-Byte Storyboard JSON Truncation Triggers JSONDecodeError in Asset Generation | Stage 6: Assets | `DATA_ENCODING_IO` | High | `OPEN` | `UNCOVERED` | `5bbee84` | - |
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

### `ERR-004`: Notification SSE Server IPv6 Localhost Socket Connect Denial
- **Stage / Scope:** Stage 16: Notifications
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:14`, `tests/test_notification_streaming.py:43`
- **Exception / Symptom:** [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
- **Root Cause Location:** `src/content_creation/notifications/streaming/server.py:254`, `tests/test_notification_streaming.py:43`, `tests/test_notification_streaming.py:457`
- **Affected Tests / Callsites:**
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_health_endpoint`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_404`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_sse_connection`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_broadcasts_to_connected_client`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_multiple_clients`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_heartbeat`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_client_disconnect`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_health_with_clients`
  - `tests/test_notification_streaming.py:TestNotificationSSEServer::test_server_sse_no_connection_manager`
  - `tests/test_SSEIntegration::test_full_lifecycle`
  - `tests/test_notification_streaming.py:TestSSEIntegration::test_multiple_notifications_stream`
  - `tests/test_notification_streaming.py:TestSSEIntegration::test_read_event_flow`
- **Reproduction Command:** `uv run python -m pytest tests/test_notification_streaming.py -k test_server_health_endpoint --no-cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `PARTIAL`
- **QA Test Directive:** Update _local_sockets_available in test_notification_streaming.py to verify socket connect() to 127.0.0.1 and replace localhost with 127.0.0.1 in HTTPConnection calls.

---

### `ERR-005`: Brief Generator Fallback Leaks ReviewStatus String into Recommended Formats
- **Stage / Scope:** Stage 3: Briefs
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 775cea2`, `mitigated_in_commit: aabeeeb`)
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

### `ERR-006`: 0-Byte Storyboard JSON Truncation Triggers JSONDecodeError in Asset Generation
- **Stage / Scope:** Stage 6: Assets
- **Error Class:** `DATA_ENCODING_IO`
- **Severity:** High
- **Status:** `OPEN`
- **Source Evidence:** `Live pipeline smoke test: generate-assets --top 2`, `src/content_creation/platform/storage/json_repository.py:63`
- **Exception / Symptom:** Failed to load Storyboard <topic_id>.json: Expecting value: line 1 column 1 (char 0), causing AssetGenerationService to skip asset generation due to Storyboard Presence Gate. Creation origin of 0-byte truncation remains unconfirmed in storage backend; unhandled 0-byte read occurs in json_repository.py:59-64.
- **Root Cause Location:** `src/content_creation/platform/storage/json_repository.py:34-36`, `src/content_creation/platform/storage/json_repository.py:59-64`, `src/content_creation/application/asset_generation_service.py:66-72`
- **Affected Tests / Callsites:**
  - None (discovered during test suite execution)
- **Reproduction Command:** `uv run python -c "from pathlib import Path; p = Path('data/storyboards/test.json'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(''); from content_creation.storage.local import LocalStorage; s = LocalStorage(Path('.')); print(s.get_storyboard('test'))"`
- **Recommended Runtime Policy:** `DEFENSIVE_IO_FIX`
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add test_load_storyboard_handles_empty_or_truncated_file verifying that 0-byte or corrupted JSON files trigger defensive handling or clean error logging without aborting asset generation.

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
  - None (discovered during test suite execution)
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
- **Source Evidence:** `docs/audit/verification/fix-phase1b-data-and-schemas-a0a799b.md:114-117`, `Live LocalStorage.list_staged() scan`, `docs/audit/qa/fix-phase1b-data-and-schemas.md:25-26`
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
  - None (discovered during test suite execution)
- **Reproduction Command:** `uv run python -m pytest --tb=no -q`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD`
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Configure pytest invocations to pass -o addopts='' -p no:cacheprovider or specify distinct COVERAGE_FILE environment variable under Windows to prevent lock contention on workspace root.

---

## 5. Anticipated Stage Risks

### `RISK-001`: Live LLM Provider Quota Exhaustion & Rate Limits
- **Stage / Scope:** Stage 3: Briefs
- **Error Class:** `TRANSPORT_TRANSIENT`
- **Severity:** High
- **Anchored Code Path:** `src/content_creation/inference/manager.py:70`, `src/content_creation/inference/providers/gemini.py:71`
- **Risk Description:** High-concurrency generation bursts without rate-limiting delays trigger HTTP 429 quota exhaustion on Gemini API endpoints.
- **Recommended Policy:** `RETRY_BACKOFF_FALLBACK`
- **QA Test Directive:** Mock 429 response from GeminiProvider and assert failover to OpenRouter without pipeline abort.

---

### `RISK-002`: Malformed Markdown Code Fences in LLM Synthesis Outputs
- **Stage / Scope:** Stage 4: Content Intelligence
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Medium
- **Anchored Code Path:** `src/content_creation/generation/brief.py:46`, `src/content_creation/domains/content_intelligence/generator.py:48`, `src/content_creation/domains/storyboard/generator.py:53`
- **Risk Description:** LLM outputting JSON wrapped in markdown fences (```json ... ```) or conversational commentary triggers json.JSONDecodeError in generator parsing.
- **Recommended Policy:** `GUIDED_SCHEMA_REPAIR`
- **QA Test Directive:** Test ContentIntelligenceGenerator and StoryboardGenerator against synthetic responses containing markdown fences, trailing commentary, and unescaped quotes.

---

### `RISK-003`: Unchecked API Token Budget Consumption During High-Volume Batches
- **Stage / Scope:** Stage 6: Asset Generation
- **Error Class:** `BUDGET_QUOTA_CONFIG`
- **Severity:** High
- **Anchored Code Path:** `src/content_creation/inference/manager.py:25`, `src/content_creation/application/asset_generation_service.py:86`
- **Risk Description:** Uncapped multi-format asset generation across large topic batches exhausts account token budgets mid-run, aborting downstream stages.
- **Recommended Policy:** `FAIL_FAST_NO_RETRY`
- **QA Test Directive:** Implement pre-flight token budget validator in AssetGenerationService that calculates estimated batch cost and aborts before LLM dispatch.

---

### `RISK-004`: In-Memory Event Bus Isolation Across Worker Daemon Subprocesses
- **Stage / Scope:** Stage 12: Event Store
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Severity:** Medium
- **Anchored Code Path:** `src/content_creation/events/bus.py:11`, `src/content_creation/jobs/worker_daemon.py:35`
- **Risk Description:** Process-bound singleton _EVENT_BUS in background worker processes drops event delivery to UI subscriber threads and SSE streaming server.
- **Recommended Policy:** `DETERMINISTIC_STATE_FIX`
- **QA Test Directive:** Add test verifying background job completion events are persisted to SQLiteEventRepository and picked up by main process SSE subscribers.

---

### `RISK-005`: POSIX Signal Handling Incompatibility in Windows Background Worker Daemon
- **Stage / Scope:** Stage 15: Jobs & Locks
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Anchored Code Path:** `src/content_creation/jobs/worker_daemon.py:35`
- **Risk Description:** Signal handlers using SIGTERM or SIGQUIT fail on Windows OS process termination, leaving stale resource locks in data/jobs.db.
- **Recommended Policy:** `CROSS_PLATFORM_GUARD`
- **QA Test Directive:** Test WorkerDaemon graceful shutdown under Windows console termination events and verify LockManager releases all held locks on process exit.
