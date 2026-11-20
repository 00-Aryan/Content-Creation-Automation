# Error Taxonomy & Failure Catalog: Content Creation Automation

## 1. Catalog Metadata & Health Overview
- **Last Updated:** `2026-11-21T00:05:00+05:30`
- **Active Branch:** `fix/phase1a-core-defects`
- **Audited Commit (SHA):** `9cf14d7` (`9cf14d75d2121d11b5bfca553db4423080d06e88`)
- **Total Observed Errors (`ERR-xxx`):** `12` (`9 OPEN`, `1 MITIGATED`, `2 RESOLVED`)
- **Total Anticipated Risks (`RISK-xxx`):** `5`
- **QA Coverage Ratio:** `4/12 (33.33%) Covered` (`2 Partial`, `6 Uncovered`)

---

## 2. Stage x Error Class Heatmap

| Stage / Scope | TRANSPORT | SCHEMA | DATA_IO | QUALITY | STATE_CONCURRENCY | PLATFORM | STATIC_TYPING | BUDGET_CONFIG | Total |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Stage 1: Ingestion | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| Stage 2: Scoring | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 |
| Stage 3: Briefs | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| Stage 4: Intelligence | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 5: Storyboard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 6: Assets | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| Stage 7: Review | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 8: Manifest | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 9: Planning | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 10: Dry Run | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 11: Analytics | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 12: Event Store | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| Stage 13: Metrics | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 14: Audit | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 15: Jobs | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Stage 16: Notifications | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| CLI Entrypoint | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 |
| Infra / Tooling | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| **Total** | **0** | **0** | **2** | **3** | **1** | **3** | **3** | **0** | **12** |

---

## 3. Master Summary Ledger

| ID | Title | Stage / Scope | Error Class | Severity | Status | QA Coverage | First Seen | Resolved In |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| `ERR-001` | CLI Main Scope Local `sys` and `timedelta` Variable Shadowing | CLI Entrypoint | `CODE_STATIC_TYPING` | High | `RESOLVED` | `COVERED` | `5bbee84` | `96ec8d7` |
| `ERR-002` | Event Store Replay Non-Deterministic UUID String Tie-Breaker | Stage 12: Event Store | `STATE_WORKFLOW_CONCURRENCY` | Medium | `RESOLVED` | `COVERED` | `5bbee84` | `74a0031` |
| `ERR-003` | Issue Runner Subprocess Spawns POSIX `bash` on Windows Hosts | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Medium | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-004` | Notification SSE Server IPv6 Localhost Socket Connect Denial | Stage 16: Notifications | `ENVIRONMENT_PLATFORM` | Medium | `OPEN` | `PARTIAL` | `5bbee84` | - |
| `ERR-005` | Brief Generator Fallback Leaks ReviewStatus String into Recommended Formats | Stage 3: Briefs | `QUALITY_GROUNDING` | Medium | `MITIGATED` | `COVERED` | `5bbee84` | - |
| `ERR-006` | Non-Atomic 0-Byte Storyboard JSON Write Triggers JSONDecodeError in Asset Generation | Stage 6: Assets | `DATA_ENCODING_IO` | High | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-007` | Scoring Component Float Rounding Drift Violates Score Consistency Invariant | Stage 2: Scoring | `QUALITY_GROUNDING` | Low | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-008` | Teaser RSS Feed Items Discarded Prematurely by Insufficient Text Filter | Stage 2: Scoring | `QUALITY_GROUNDING` | Medium | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-009` | CLI Subcommand Drift vs Documentation for Content Intelligence and Storyboards | CLI Entrypoint | `CODE_STATIC_TYPING` | Medium | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-010` | AppContainer Sandbox Permission Denial on Storage Directory Writeability Probe | Infra / Tooling | `ENVIRONMENT_PLATFORM` | Medium | `OPEN` | `COVERED` | `5bbee84` | - |
| `ERR-011` | Non-UTF-8 CP1252 Smart Quotes in Staged Feed JSON Files Trigger Decoding Warnings | Stage 1: Ingestion | `DATA_ENCODING_IO` | Low | `OPEN` | `UNCOVERED` | `5bbee84` | - |
| `ERR-012` | CLI Monolithic Main Function Variable Scope Collisions Under Strict Typing | CLI Entrypoint | `CODE_STATIC_TYPING` | Medium | `OPEN` | `PARTIAL` | `5bbee84` | - |

---

## 4. Detailed Observed Error Cards

### `ERR-001`: CLI Main Scope Local sys and timedelta Variable Shadowing
- **Stage / Scope:** CLI Entrypoint
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** High
- **Status:** `RESOLVED` (`resolved_in_commit: 96ec8d7`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:11` (`DEF-001`), `docs/audit/handoffs/fix-phase1a-core-defects.md:11, 20-21`
- **Exception / Symptom:** `UnboundLocalError: cannot access local variable 'sys' where it is not associated with a value` / `cannot access local variable 'timedelta'`
- **Root Cause Location:** `src/content_creation/cli.py:1350` (`sys = summary["system"]`), `src/content_creation/cli.py:1283, 1338, 1479, 1726` (`from datetime import timedelta`)
- **Affected Tests / Callsites:**
  - `tests/test_cli.py:test_status_command`
  - `tests/test_cli.py:test_collect_command_real`
  - `tests/test_cli.py:test_collect_command_all`
  - `tests/test_cli.py:test_plan_week_default_date_uses_unshadowed_timedelta`
- **Reproduction Command:** `uv run python -m pytest tests/test_cli.py -k test_status_command --no-cov`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX` (Rename local telemetry variable to `sys_summary` and remove redundant function-level `timedelta` re-imports)
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add `test_exception_handler_uses_unshadowed_sys` verifying `sys.stderr` write on exception and `test_plan_week_default_date_uses_unshadowed_timedelta`.

---

### `ERR-002`: Event Store Replay Non-Deterministic UUID String Tie-Breaker
- **Stage / Scope:** Stage 12: Event Store
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Severity:** Medium
- **Status:** `RESOLVED` (`resolved_in_commit: 74a0031`)
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:12` (`DEF-002`), `docs/audit/handoffs/fix-phase1a-core-defects.md:22-25`
- **Exception / Symptom:** `list_after_event` returns empty list due to random UUID string comparison on identical timestamps, breaking deterministic replay assertions.
- **Root Cause Location:** `src/content_creation/events/store/sqlite_repository.py:205-206` (`WHERE created_at > ? OR (created_at = ? AND id > ?)` comparing stringified UUID4s)
- **Affected Tests / Callsites:**
  - `tests/test_event_persistence.py:test_list_after_event`
  - `tests/test_event_persistence.py:test_replay_after_event`
  - `tests/test_event_persistence.py:test_replay_after_event_for_sse`
  - `tests/test_event_persistence.py:test_sse_recovery_no_duplicate_delivery`
- **Reproduction Command:** `uv run python -m pytest tests/test_event_persistence.py:test_list_after_event --no-cov`
- **Recommended Runtime Policy:** `DETERMINISTIC_STATE_FIX` (Query anchor event's SQLite `rowid` and apply secondary tie-breaker `(created_at = ? AND rowid > ?) ORDER BY created_at ASC, rowid ASC`)
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add `test_list_after_event_identical_timestamps_deterministic` enforcing rowid sorting on events with identical timestamps and inverted UUID strings.

---

### `ERR-003`: Issue Runner Subprocess Spawns POSIX bash on Windows Hosts
- **Stage / Scope:** Infra / Tooling
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:13` (`DEF-003`), `tests/test_issue_runner.py:323`
- **Exception / Symptom:** `OSError: [WinError 1920] The file cannot be accessed by the system` when Windows `CreateProcess` fails to locate `bash`.
- **Root Cause Location:** `scripts/issue_runner.py:629` (`res = subprocess.run(["bash", "-c", block], ...)` assuming POSIX bash on Windows)
- **Affected Tests / Callsites:**
  - `tests/test_issue_runner.py:test_validation_sequential_failure_stops_block`
  - `tests/test_issue_runner.py:test_validation_successful_sequential_commands_pass`
  - `tests/test_issue_runner.py:test_validation_multiple_blocks_stop_at_first_failure`
- **Reproduction Command:** `uv run python -m pytest tests/test_issue_runner.py --no-cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD` (Inspect `sys.platform` and dispatch to PowerShell or check `shutil.which("bash")` fallback with skip/mock guard on Windows)
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Parametrize `test_issue_runner.py` across platform shells or mock `subprocess.run` to verify non-POSIX execution path.

---

### `ERR-004`: Notification SSE Server IPv6 Localhost Socket Connect Denial
- **Stage / Scope:** Stage 16: Notifications
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/03-drift-and-defects-register.md:14` (`DEF-004`), `tests/test_notification_streaming.py:43`
- **Exception / Symptom:** `PermissionError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`
- **Root Cause Location:** `src/content_creation/notifications/streaming/server.py:254`, `tests/test_notification_streaming.py:43, 457` (Server binds to IPv4 `0.0.0.0` / `127.0.0.1` while tests connect to `"localhost"`, which resolves to IPv6 `::1` on Windows; test helper `_local_sockets_available` checks only `bind` without `connect`)
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
  - `tests/test_notification_streaming.py:TestSSEIntegration::test_full_lifecycle`
  - `tests/test_notification_streaming.py:TestSSEIntegration::test_multiple_notifications_stream`
  - `tests/test_notification_streaming.py:TestSSEIntegration::test_read_event_flow`
- **Reproduction Command:** `uv run python -m pytest tests/test_notification_streaming.py -k test_server_health_endpoint --no-cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD` (Update client connection to use explicit IPv4 loopback `"127.0.0.1"` instead of `"localhost"`, and enhance `_local_sockets_available` to test `connect()`)
- **QA Coverage Status:** `PARTIAL`
- **QA Test Directive:** Update `_local_sockets_available` in `tests/test_notification_streaming.py:28` to perform ephemeral socket bind AND connect before running SSE tests.

---

### `ERR-005`: Brief Generator Fallback Leaks ReviewStatus String into Recommended Formats
- **Stage / Scope:** Stage 3: Briefs
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Medium
- **Status:** `MITIGATED` (`mitigated_in_commit: aabeeeb`)
- **Source Evidence:** `docs/audit/handoffs/fix-phase1a-core-defects.md:26-30, 97-100`, `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:93-97, 127-130` (Advisory #1)
- **Exception / Symptom:** `BriefGenerator` fallback populates all string fields with `"needs_review"`, including `recommended_formats=["needs_review"]`. Downstream `ManifestBuilder` previously flagged `"needs_review"` as an unknown format and forced fallback to `short_video`.
- **Root Cause Location:** `src/content_creation/generation/brief.py:71` (upstream generator fallback defect); defensively filtered downstream at `src/content_creation/manifest.py:189-195`.
- **Affected Tests / Callsites:**
  - `tests/test_manifest.py:test_recommended_formats_filters_review_status_leak`
  - `tests/test_manifest.py:test_recommended_formats_with_only_review_status_defaults_cleanly`
  - `tests/test_manifest.py:test_recommended_formats_genuine_unknown_format_logs_warning`
- **Reproduction Command:** `uv run python -m pytest tests/test_manifest.py:test_recommended_formats_filters_review_status_leak --no-cov`
- **Recommended Runtime Policy:** `ENRICHMENT_OR_CRITIC_LOOP` (Open generator frozen scope and update fallback brief generation to produce valid formats `["short_video"]` or `[]` instead of review state enum values)
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Add `test_fallback_brief_does_not_contain_review_status_values` asserting `recommended_formats` only contains valid `AssetType` format strings or empty list.

---

### `ERR-006`: Non-Atomic 0-Byte Storyboard JSON Write Triggers JSONDecodeError in Asset Generation
- **Stage / Scope:** Stage 6: Assets
- **Error Class:** `DATA_ENCODING_IO`
- **Severity:** High
- **Status:** `OPEN`
- **Source Evidence:** Live pipeline smoke test (`generate-assets --top 2`), `src/content_creation/platform/storage/json_repository.py:63`
- **Exception / Symptom:** `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` logged as `ERROR Failed to load Storyboard <topic_id>.json: Expecting value: line 1 column 1 (char 0)`, causing `AssetGenerationService` to skip generation due to the Storyboard Presence Gate.
- **Root Cause Location:** `src/content_creation/platform/storage/json_repository.py:34-36` (`with open(file_path, "w")` truncates target JSON directly before serialization completes instead of writing atomically via temporary file and replace), combined with unhandled 0-byte deserialization in `json_repository.py:59-64` and presence gate skip in `src/content_creation/application/asset_generation_service.py:66-72`.
- **Affected Tests / Callsites:** None (discovered during dynamic CLI smoke testing)
- **Reproduction Command:** `uv run python -c "from pathlib import Path; p = Path('data/storyboards/test.json'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(''); from content_creation.storage.local import LocalStorage; s = LocalStorage(Path('.')); print(s.get_storyboard('test'))"`
- **Recommended Runtime Policy:** `DEFENSIVE_IO_FIX` (Adopt atomic write via temp file + `os.replace` in `JsonRepository.save`, and validate file size > 0 before calling `json.load`)
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add `test_load_storyboard_handles_empty_or_truncated_file` verifying that 0-byte or corrupted JSON files trigger defensive handling or clean error logging without aborting asset generation.

---

### `ERR-007`: Scoring Component Float Rounding Drift Violates Score Consistency Invariant
- **Stage / Scope:** Stage 2: Scoring
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Low
- **Status:** `OPEN`
- **Source Evidence:** Live pipeline smoke test (`score-topics` validation log), `src/content_creation/scoring/validation.py:49`
- **Exception / Symptom:** Validation warning: `Score inconsistency: priority_score (65.75) != sum of components (65.76)` (and `57.02 != 57.01`, `53.48 != 53.49`, `54.02 != 54.01`, `55.16 != 55.17`, `52.02 != 52.01`).
- **Root Cause Location:** `src/content_creation/scoring/base.py:108` sums raw unrounded floats and rounds the total (`priority_score = round(min(total_score, 100.0), 2)`), while line 115 rounds individual rule contributions independently (`round(score, 2)`). The sum of rounded components diverges by $\pm 0.01$ from the rounded sum, triggering `ScoreConsistencyRule` in `src/content_creation/scoring/validation.py:48`.
- **Affected Tests / Callsites:** None (flagged during `score-topics` validation logging)
- **Reproduction Command:** `uv run python -c "from content_creation.scoring.engine import ScoringEngine; from content_creation.scoring.config import ScoringConfig; from content_creation.models.topic import TopicItem; t = TopicItem(id='test', title='Test topic', url='https://example.com', source='arxiv', category='paper', raw_text='A '*100); e = ScoringEngine(ScoringConfig()); scored = e.score_item(t); print('priority:', scored.priority_score, 'sum:', sum([scored.student_usefulness_score, scored.novelty_score, scored.credibility_score, scored.explainability_score, scored.hook_potential_score]))"`
- **Recommended Runtime Policy:** `ENRICHMENT_OR_CRITIC_LOOP` (Define `priority_score` strictly as the sum of rounded component scores or permit floating epsilon $\ge 0.02$ in `ScoreConsistencyRule`)
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add `test_scoring_float_consistency` asserting `priority_score` strictly equals the sum of rounded component scores across 100 randomized topic payloads.

---

### `ERR-008`: Teaser RSS Feed Items Discarded Prematurely by Insufficient Text Filter
- **Stage / Scope:** Stage 2: Scoring
- **Error Class:** `QUALITY_GROUNDING`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** Live pipeline smoke test (`score-topics` execution summary), `src/content_creation/scoring/engine.py:252-254`
- **Exception / Symptom:** 290 out of 2,048 topics rejected as `insufficient_text` when `raw_text < 100 chars`, discarding flagship posts (`GPT-4o System Card`, `Introducing OpenAI o1`, `Prompt Caching in the API`).
- **Root Cause Location:** `src/content_creation/scoring/engine.py:252` (`if len(item.raw_text) < 100: rejected_items.append(self._reject(item, "insufficient_text"))`). RSS feeds that supply only short synopsis blurbs or titles are rejected before content enrichment or article scraping can execute.
- **Affected Tests / Callsites:** None (observed on live dataset)
- **Reproduction Command:** `uv run python -c "from content_creation.scoring.engine import ScoringEngine; from content_creation.scoring.config import ScoringConfig; from content_creation.models.topic import TopicItem; t = TopicItem(id='test', title='Introducing OpenAI o1', url='https://openai.com/index/o1', source='openai', category='release', raw_text='Short teaser'); e = ScoringEngine(ScoringConfig()); res = e.score_items([t]); print(res['rejected'][0].rejection_reason)"`
- **Recommended Runtime Policy:** `ENRICHMENT_OR_CRITIC_LOOP` (Route short-text topics through full-text HTML body scraper / enrichment before applying scoring rejection filter)
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add `test_short_teaser_flagged_for_enrichment` asserting that topics with short raw_text but high-credibility sources trigger an enrichment fetch rather than immediate rejection.

---

### `ERR-009`: CLI Subcommand Drift vs Documentation for Content Intelligence and Storyboards
- **Stage / Scope:** CLI Entrypoint
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `README.md:445, 448`, `src/content_creation/cli.py:56-215`
- **Exception / Symptom:** `usage: cli.py [-h] ... cli.py: error: argument command: invalid choice: 'generate-ci' (choose from ...)` and `invalid choice: 'generate-storyboards'`.
- **Root Cause Location:** `src/content_creation/cli.py:56-215` omits subparsers for `generate-ci` and `generate-storyboards`, even though `WorkflowActionExecutor` implements `generate_ci` and `generate_storyboards` and `README.md` documents both commands as standard pipeline steps 4 and 5.
- **Affected Tests / Callsites:** None (operator workflow CLI invocation)
- **Reproduction Command:** `uv run python -m content_creation.cli generate-ci --top 5`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX` (Add `generate-ci` and `generate-storyboards` CLI subparsers and wire them to `ContentIntelligenceService` and `StoryboardService` or update documentation to match active CLI grammar)
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add CLI tests in `tests/test_cli.py` invoking `generate-ci --help` and `generate-storyboards --help` and verifying exit code 0.

---

### `ERR-010`: AppContainer Sandbox Permission Denial on Storage Directory Writeability Probe
- **Stage / Scope:** Infra / Tooling
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:146`, live pytest sweep within AppContainer sandbox
- **Exception / Symptom:** `PermissionError: [WinError 13] Access is denied: '[USER_HOME]/.../.write_test_*'` -> `Error: Storage base directory ... is not writeable`, causing CLI commands and tests to exit with code 1.
- **Root Cause Location:** `src/content_creation/storage/local.py:64-70` (`_verify_writeable`) tests writeability by creating a temporary file directly in `self.base_dir` (repository root). Under Windows AppContainer sandboxes, child processes are granted write permissions to `data/` or temp directories, but not to the repository root directory itself.
- **Affected Tests / Callsites:**
  - `tests/test_cli.py:TestCLI::test_status_command`
  - `tests/test_cli.py:TestCLI::test_collect_command_real`
  - `tests/test_cli.py:TestCLI::test_collect_command_all`
  - `tests/test_cli.py:TestCLI::test_plan_week_default_date_uses_unshadowed_timedelta`
- **Reproduction Command:** `uv run python -m pytest tests/test_cli.py --no-cov`
- **Recommended Runtime Policy:** `CROSS_PLATFORM_GUARD` (Probe writeability within `data/` directory instead of repository root, or gracefully fallback when running in sandboxed execution environments)
- **QA Coverage Status:** `COVERED`
- **QA Test Directive:** Ensure `LocalStorage._verify_writeable` checks `base_dir / "data"` or respects sandbox temp redirection without aborting on repository root write restriction.

---

### `ERR-011`: Non-UTF-8 CP1252 Smart Quotes in Staged Feed JSON Files Trigger Decoding Warnings
- **Stage / Scope:** Stage 1: Ingestion
- **Error Class:** `DATA_ENCODING_IO`
- **Severity:** Low
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/handoffs/fix-phase1a-core-defects.md:101-103`, `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:131-135` (Advisory #2)
- **Exception / Symptom:** `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 360: invalid start byte` logged across 1,519 staged JSON files during `cli status`.
- **Root Cause Location:** `src/content_creation/storage/local.py:98-100` (`LocalStorage._read_json`) and ingestion collectors saving raw feed summaries containing Windows-1252/cp1252 encoded characters (e.g. em-dashes `0x97`, smart quotes) without normalizing to UTF-8.
- **Affected Tests / Callsites:** None (operational friction during CLI status checks)
- **Reproduction Command:** `uv run python -m content_creation.cli status`
- **Recommended Runtime Policy:** `DEFENSIVE_IO_FIX` (Open files with `encoding="utf-8", errors="replace"` in `LocalStorage._read_json` and sanitize raw feed text at ingestion)
- **QA Coverage Status:** `UNCOVERED`
- **QA Test Directive:** Add test in `tests/test_storage.py` loading a staged JSON file encoded with cp1252 bytes and asserting clean decoding without `UnicodeDecodeError`.

---

### `ERR-012`: CLI Monolithic Main Function Variable Scope Collisions Under Strict Typing
- **Stage / Scope:** CLI Entrypoint
- **Error Class:** `CODE_STATIC_TYPING`
- **Severity:** Medium
- **Status:** `OPEN`
- **Source Evidence:** `docs/audit/handoffs/fix-phase1a-core-defects.md:68-71`, `docs/audit/verification/fix-phase1a-core-defects-f738dc9.md:29, 136-139` (Advisory #3)
- **Exception / Symptom:** 127 `mypy --strict` errors reported when type checking `src/content_creation/cli.py`.
- **Root Cause Location:** `src/content_creation/cli.py:224-1760` (`def main() -> int:`). Monolithic 1,500+ line procedure re-uses the same local variable names (`service`, `repo`, `summary`, `report`, `result`) across 32 distinct `elif args.command == ...` branches with conflicting types.
- **Affected Tests / Callsites:** Gate 2 ratchet static type checking
- **Reproduction Command:** `uv run mypy src/content_creation/cli.py --strict`
- **Recommended Runtime Policy:** `CODE_REFACTOR_FIX` (Decompose `main()` into dedicated subcommand handler functions or refactor to Typer modular commands as planned for Phase 2)
- **QA Coverage Status:** `PARTIAL`
- **QA Test Directive:** Add CI ratchet test enforcing mypy error count on `cli.py` does not exceed 127 and decreases as subcommand blocks are decomposed into separate modules.

---

## 5. Anticipated Stage Risks

### `RISK-001`: Live LLM Provider Quota Exhaustion & Rate Limits
- **Stage / Scope:** Stage 3: Briefs
- **Error Class:** `TRANSPORT_TRANSIENT`
- **Severity:** High
- **Anchored Code Path:** `src/content_creation/inference/manager.py:70`, `src/content_creation/inference/providers/gemini.py:71`
- **Risk Description:** High-concurrency generation bursts without rate-limiting delays trigger HTTP 429 quota exhaustion on Gemini API endpoints.
- **Recommended Policy:** `RETRY_BACKOFF_FALLBACK` (Exponential jittered backoff with automatic fallback to OpenRouter).
- **QA Test Directive:** Mock 429 response from `GeminiProvider` and assert seamless failover to secondary provider without pipeline abort.

---

### `RISK-002`: Malformed Markdown Code Fences in LLM Synthesis Outputs
- **Stage / Scope:** Stage 4: Content Intelligence
- **Error Class:** `SCHEMA_VALIDATION`
- **Severity:** Medium
- **Anchored Code Path:** `src/content_creation/generation/brief.py:46`, `src/content_creation/domains/content_intelligence/generator.py:48`, `src/content_creation/domains/storyboard/generator.py:53`
- **Risk Description:** LLM outputting JSON wrapped in markdown fences (````json ... ````) or conversational commentary triggers `json.JSONDecodeError` in generator parsing.
- **Recommended Policy:** `GUIDED_SCHEMA_REPAIR` (Defensive markdown fence stripping, JSON regex extraction, and schema validation before triggering fallback).
- **QA Test Directive:** Test `ContentIntelligenceGenerator` and `StoryboardGenerator` against synthetic responses containing markdown fences, trailing commentary, and unescaped quotes.

---

### `RISK-003`: Unchecked API Token Budget Consumption During High-Volume Batches
- **Stage / Scope:** Stage 6: Asset Generation
- **Error Class:** `BUDGET_QUOTA_CONFIG`
- **Severity:** High
- **Anchored Code Path:** `src/content_creation/inference/manager.py:25`, `src/content_creation/application/asset_generation_service.py:86`
- **Risk Description:** Uncapped multi-format asset generation across large topic batches exhausts account token budgets mid-run, aborting downstream stages.
- **Recommended Policy:** `FAIL_FAST_NO_RETRY` (Pre-flight token budget validator that calculates estimated batch cost and aborts before LLM dispatch).
- **QA Test Directive:** Implement pre-flight token budget validator in `AssetGenerationService` that calculates estimated batch cost and aborts before LLM dispatch.

---

### `RISK-004`: In-Memory Event Bus Isolation Across Worker Daemon Subprocesses
- **Stage / Scope:** Stage 12: Event Store
- **Error Class:** `STATE_WORKFLOW_CONCURRENCY`
- **Severity:** Medium
- **Anchored Code Path:** `src/content_creation/events/bus.py:11`, `src/content_creation/jobs/worker_daemon.py:35`
- **Risk Description:** Process-bound singleton `_EVENT_BUS` in background worker processes drops event delivery to UI subscriber threads and SSE streaming server.
- **Recommended Policy:** `DETERMINISTIC_STATE_FIX` (Route background job events through durable `SQLiteEventRepository` or inter-process event subscriber rather than relying solely on in-process memory bus).
- **QA Test Directive:** Add test verifying background job completion events are persisted to `SQLiteEventRepository` and picked up by main process SSE subscribers.

---

### `RISK-005`: POSIX Signal Handling Incompatibility in Windows Background Worker Daemon
- **Stage / Scope:** Stage 15: Jobs & Locks
- **Error Class:** `ENVIRONMENT_PLATFORM`
- **Severity:** Medium
- **Anchored Code Path:** `src/content_creation/jobs/worker_daemon.py:35`
- **Risk Description:** Signal handlers using `SIGTERM` or `SIGQUIT` fail on Windows OS process termination, leaving stale resource locks in `data/jobs.db`.
- **Recommended Policy:** `CROSS_PLATFORM_GUARD` (Register Windows console control handlers and enforce heartbeat TTL timeouts in `LockManager`).
- **QA Test Directive:** Test `WorkerDaemon` graceful shutdown under Windows console termination events and verify `LockManager` releases all held locks on process exit.
