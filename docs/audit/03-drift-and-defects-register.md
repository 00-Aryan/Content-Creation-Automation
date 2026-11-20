<!-- Generated on: 2026-11-20 | Commit: 5bbee8401f4d504074e10b74ada0479aff6b4813 | Auditor: pipeline-mapper -->

# Content Creation Automation: Drift and Defects Register

> **Strict Non-Prescriptive Policy:** This register documents current-state facts and evidence only. It contains zero refactoring suggestions, zero framework recommendations, and zero patch code.

## 1. Confirmed Defects and Code Bugs

| Defect ID | Severity | File & Line Number | Verbatim Symbol / Signature | Factual Defect Description | Immediate Consequence |
|:---|:---|:---|:---|:---|:---|
| `DEF-001` | High | `src/content_creation/cli.py:1350` | `sys = summary["system"]` | Inside `def main() -> int:`, the local variable assignment `sys = summary["system"]` shadows the top-level module `import sys` (`src/content_creation/cli.py:7`). In Python, local assignment marks `sys` as a local variable for the entire function scope. When an exception occurs anywhere prior to line 1350, the error handler at line 1754 (`print(f"Error: {e}", file=sys.stderr)`) attempts to access `sys` before assignment. | Raises `UnboundLocalError: cannot access local variable 'sys' where it is not associated with a value`, causing test failures in `tests/test_cli.py` (`test_status_command`, `test_collect_command_real`, `test_collect_command_all`) and preventing clean CLI error reporting. |
| `DEF-002` | Medium | `src/content_creation/events/store/sqlite_repository.py:205-206` | `"SELECT * FROM events WHERE created_at > ? OR (created_at = ? AND id > ?) ORDER BY created_at ASC LIMIT ?"` | Tie-breaking condition `(created_at = ? AND id > ?)` compares string representations of UUID4 identifiers (`str(event_id)`). When two events are created in rapid succession with identical timestamps (such as in `tests/test_event_persistence.py:292-301`), if the second event's randomly generated UUID string is lexicographically smaller than the anchor event's UUID string, the condition evaluates to `False`. | `list_after_event` returns an empty list, causing test assertions in `tests/test_event_persistence.py` (`test_list_after_event`, `test_replay_after_event`, `test_replay_after_event_for_sse`, `test_sse_recovery_no_duplicate_delivery`) to fail non-deterministically. |
| `DEF-003` | Medium | `scripts/issue_runner.py:629` | `res = subprocess.run(...)` | Spawns a subprocess attempting to execute `bash` directly. On Windows environments where `bash` is not an installed executable in the system `PATH`, Windows API `CreateProcess` fails. | Raises `OSError: [WinError 1920] The file cannot be accessed by the system`, causing 3 test failures in `tests/test_issue_runner.py` (`test_validation_sequential_failure_stops_block`, `test_validation_successful_sequential_commands_pass`, `test_validation_multiple_blocks_stop_at_first_failure`). |
| `DEF-004` | Medium | `src/content_creation/notifications/streaming/server.py:254` | `class NotificationSSEServer:` | The server binds to `0.0.0.0` or `127.0.0.1` IPv4 sockets. Tests in `tests/test_notification_streaming.py:457` connect via `HTTPConnection("localhost", port)`. On Windows, `localhost` resolves to IPv6 `::1`, resulting in connection attempts failing with access permission errors. Furthermore, the test suite's socket detection helper `_local_sockets_available()` tests only `sock.bind(("127.0.0.1", 0))` and does not test `connect()`. | Raises `PermissionError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`, causing 12 pre-existing test failures in `tests/test_notification_streaming.py`. |

---

## 2. Dead or Broken Code Paths

| Path ID | File & Line Number | Symbol / Block | Reason Dead / Broken | Evidence |
|:---|:---|:---|:---|:---|
| `DEAD-001` | `src/content_creation/workflow/workflow_action_executor.py:70` | `def fail_blocked(cls, action_id: str, blocking_code: str, message: str) -> "ActionExecutionResult":` | Unreferenced class method. `WorkflowActionExecutor.execute` instantiates `ActionExecutionResult` directly at lines 150-160 rather than invoking this factory method. | 0 AST caller references across `src/` and `tests/`. |
| `DEAD-002` | `src/content_creation/workflow/workflow_action_executor.py:749` | `elif action_id == "publish": return {"published_status": "mock_published"}, None` | Stub branch with no underlying publishing service or implementation. Returns mock dictionary. | No CLI command, UI page, or background job calls `publish`. |
| `DEAD-003` | `src/content_creation/ui/services/client.py:131, 141, 146, 156, 166, 171` | `def collect(...)`, `def brief(...)`, `def content_intelligence(...)`, `def asset_generation(...)`, `def asset_review(...)`, `def brief_review(...)` | Legacy client wrapper methods bypassed by UI pages. The UI pages directly invoke `execute_workflow_action` or specialized review services. | 0 AST callers in any of `src/content_creation/ui/pages/`. |
| `DEAD-004` | `src/content_creation/notifications/streaming/connection_manager.py:51` | `def active_client_count(self) -> int:` | Helper method for tracking active SSE clients. | 0 AST caller references in server or connection manager. |
| `DEAD-005` | `src/content_creation/application/context.py:53` | `def content_intelligence_dir(self) -> Path:` | Property on `ApplicationContext` pointing to content intelligence directory. | 0 AST caller references in any service or generator (services use `ctx.storage.content_intelligence_dir` directly). |

---

## 3. Documentation vs. Code Drift

| Drift ID | Canonical Document | Actual Code Implementation | Drift Description | Impact |
|:---|:---|:---|:---|:---|
| `DRIFT-001` | `README.md:4` | `tests/` | Badge states `Tests: 249 Passing`. Actual test suite contains 1,131 tests (1,109 passing, 22 failing). | Inaccurate representation of repository test suite scale and current pass/fail metrics. |
| `DRIFT-002` | `CLAUDE.md:23` | `tests/` | States `125 tests passing. Zero regressions permitted.`. Out of date with test suite growth. | Misleading baseline metrics in project governance documentation. |
| `DRIFT-003` | `README.md` | `src/content_creation/cli.py:56-215` | `README.md` documents 0 CLI subcommands. `cli.py` implements 32 subcommands (including `event-*`, `metrics-*`, `audit-*`, `build-manifest`, `plan-week`, `dry-run`, `init-analytics`). | Operators cannot discover operational, planning, event-replay, or telemetry commands from the main project README. |
| `DRIFT-004` | `docs/schema.md:21, 28` | `src/content_creation/models/topic.py:20` | `docs/schema.md` lists `raw`, `staged`, `scored`, `approved`, `rejected`. `TopicStatus` enum defines `REVIEW = "review"` at line 20, and `cli.py:66` exposes `--status review`. | Schema document omits the active intermediate review status. |
| `DRIFT-005` | `docs/schema.md:53-68` | `src/content_creation/models/brief.py:8-20` | `docs/schema.md` documents draft Brief Schema with `"review_status": "draft | needs_review"`. In code, `Brief` model uses `ReviewStatus` enum (`DRAFT`, `NEEDS_REVIEW`, `REVIEWED`, `APPROVED`, `REJECTED`) and defines an additional field `review_notes: Optional[str] = None`. | Persisted brief data format diverges from documented draft schema. |
| `DRIFT-006` | `docs/schema.md` | `src/content_creation/models/` | `docs/schema.md` specifies only `TopicItem` and a draft `Brief`. It omits definitions for 12 production schemas: `ScoredTopicItem`, `ContentIntelligence`, `Storyboard`, `VideoScript`, `Carousel`, `Newsletter`, `ThumbnailPrompt`, `TopicManifest`, `WeeklyCalendar`, `DryRunReport`, `PostAnalytics`, and `ReviewHistoryEntry`. | High drift between architectural data contracts and documented repository contracts. |

---

## 4. Schema & Data Format Mismatches / Untyped Leaks

| Schema ID | Model & Field | File:Line | Issue Type | Evidence |
|:---|:---|:---|:---|:---|
| `SCHEMA-001` | `TopicItem.metadata` | `src/content_creation/models/topic.py:34` | `typing.Any` leak | `metadata: Dict[str, Any] = Field(default_factory=dict)` — arbitrary unvalidated dictionary contents bypass Pydantic type validation. |
| `SCHEMA-002` | `ScoredTopicItem.metadata` | `src/content_creation/models/topic.py:75` | `typing.Any` leak | Inherits `metadata: Dict[str, Any]` from `TopicItem`. Allows untyped values to persist into `data/scored/*.json`. |
| `SCHEMA-003` | `WeeklyCalendar.config_snapshot` | `src/content_creation/models/calendar.py:23` | Untyped `dict` leak | `config_snapshot: Dict = Field(...)` — raw untyped `Dict` with no key or value typing constraints. |
| `SCHEMA-004` | `ContentIntelligence.quality_status` | `src/content_creation/domains/content_intelligence/model.py:48` | Unvalidated string leak | `quality_status: Optional[str] = None # "ready" \| "degraded" \| "blocked"` — defined as arbitrary `str` rather than an `Enum` or `Literal`. |
| `SCHEMA-005` | `AssetCheck.review_status` | `src/content_creation/models/dryrun.py:12` | Unvalidated string leak | `review_status: str` — uses unconstrained `str` instead of `ReviewStatus` enum, allowing invalid review state strings in dry run checks. |

---

## 5. Test Suite & Environment Fragility

| Test File:Line | Test Case Name | Root Cause of Fragility / Failure | Pre-Existing vs. Regressed |
|:---|:---|:---|:---|
| `tests/test_notification_streaming.py:452` | `test_server_health_endpoint` (and 11 sibling tests in file) | Windows socket permission restriction (`PermissionError: [WinError 10013]`) when binding or connecting to localhost HTTPConnection. Test fixture `_local_sockets_available` checks only ephemeral bind, not connection. | Pre-existing (documented in `AGENTS.md`). |
| `tests/test_cli.py:37` | `test_status_command` (and `test_collect_command_real`, `test_collect_command_all`) | Shadowed `sys` module in `cli.py:1350` triggers `UnboundLocalError: cannot access local variable 'sys'` inside the exception handler at `cli.py:1754`. | Pre-existing bug exposed when storage or parameter checks raise exceptions during CLI execution. |
| `tests/test_event_persistence.py:291` | `test_list_after_event` (and `test_replay_after_event`, `test_replay_after_event_for_sse`, `test_sse_recovery_no_duplicate_delivery`) | Non-deterministic test failure caused by identical timestamp creation in `_make_event` combined with random UUID4 lexicographical comparison in `sqlite_repository.py:205`. | Pre-existing logic fragility. |
| `tests/test_issue_runner.py:323` | `test_validation_sequential_failure_stops_block` (and 2 sibling tests in file) | Direct invocation of `bash` executable via `subprocess.run` fails on Windows hosts with `OSError: [WinError 1920]`. | Pre-existing cross-platform environment assumption. |

---

## 6. Unresolved Unknowns & Next Static Check Protocol

| Unknown ID | Component / Question | Why Static Analysis Stalled | Exact File or Verification Command to Confirm |
|:---|:---|:---|:---|
| `UNK-001` | Live Gemini Provider Response Validation | Static AST analysis cannot verify runtime behavior or rate limits against external Google GenAI endpoints without live network credentials. | `uv run python -c "from content_creation.inference.providers.gemini import GeminiProvider; print(GeminiProvider)"` |
| `UNK-002` | Live OpenRouter Provider Response Validation | Static AST analysis cannot verify runtime JSON schema conformances against external OpenRouter LLM endpoints without live network credentials. | `uv run python -c "from content_creation.inference.providers.openrouter import OpenRouterProvider; print(OpenRouterProvider)"` |
| `UNK-003` | Long-Running Worker Daemon Process Termination | Signal handling (`SIGTERM` / `SIGINT`) in `WorkerDaemon` (`src/content_creation/jobs/worker_daemon.py:35`) cannot be statically verified under Windows OS process management. | `uv run python -c "from content_creation.jobs.worker_daemon import WorkerDaemon; print(WorkerDaemon)"` |
