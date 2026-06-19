# WORK_QUEUE.md — Content Creation Automation Platform

**Current Phase:** 11.9.5 — Reliability: Fix SSE Test Failures
**Last updated:** 2026-06-10
**Baseline test count:** 950 passed (16 known pre-existing failures in test_notification_streaming.py — non-blocking)

---

## How This Works

- `$run-next-task` picks the first PENDING task where all `Depends On` are DONE
- `$new-phase` appends new tasks after the last entry here
- `$fix-and-continue TASK-NNN` runs a specific task directly
- Update status and date when a task completes

Status values: `PENDING` | `IN_PROGRESS` | `DONE` | `BLOCKED` | `SKIPPED`

---

## Queue

| ID | Title | Status | Priority | Depends On | Task Card |
|---|---|---|---|---|---|
| TASK-001 | Create `.env.example` with required env vars | DONE | HIGH | None | [→](docs/tasks/task_001.md) |
| TASK-002 | Extend `.gitignore` for Phase 11+ databases | DONE | HIGH | None | [→](docs/tasks/task_002.md) |
| TASK-003 | Add secret logging filter to `utils/logger.py` | BLOCKED | MEDIUM | None | [→](docs/tasks/task_003.md) |
| TASK-004 | Add `SECURITY.md` disclosure policy | DONE | LOW | None | [→](docs/tasks/task_004.md) |
| TASK-005 | Update `GEMINI.md` with security constraints | DONE | LOW | None | [→](docs/tasks/task_005.md) |
| TASK-006 | Add GitHub Actions CI workflow (tests on push) | DONE | HIGH | None | [→](docs/tasks/task_006.md) |
| TASK-007 | Add Gitleaks secret scan to CI workflow | DONE | HIGH | TASK-006 | [→](docs/tasks/task_007.md) |
| TASK-008 | Add `.pre-commit-config.yaml` with detect-secrets | DONE | MEDIUM | None | [→](docs/tasks/task_008.md) |
| TASK-009 | Update TASK_SPEC.md to Phase 11.9.4 | DONE    | HIGH | None | [→](docs/tasks/task_009.md) |
| TASK-010 | Add Makefile with dev commands | DONE    | HIGH | TASK-009 | [→](docs/tasks/task_010.md) |
| TASK-011 | Add return type hints to cli.py | DONE    | MEDIUM | None | [→](docs/tasks/task_011.md) |
| TASK-012 | Create docs/project-context.md | DONE       | HIGH | None | [→](docs/tasks/task_012.md) |
| TASK-013 | Run drift-check post Phase 11.9.3 | DONE | MEDIUM | TASK-009,TASK-010,TASK-011,TASK-012 | [→](docs/tasks/task_013.md) |
| TASK-014 | Fix IndentationError 3_brief_viewer.py:158 | DONE    | CRITICAL | None | [→](docs/tasks/task_014.md) |
| TASK-015 | Add UI syntax test to CI | DONE | HIGH | None | [→](docs/tasks/task_015.md) |
| TASK-016 | Fix silent except handlers in UI pages | DONE    | HIGH | TASK-014 | [→](docs/tasks/task_016.md) |
| TASK-017 | Add copy-to-clipboard to asset workshop | DONE    | HIGH | None | [→](docs/tasks/task_017.md) |
| TASK-018 | Trace and fix E2E pipeline brief failure | DONE    | HIGH | None | [→](docs/tasks/task_018.md) |
| TASK-019 | Fix Content Intelligence brief selection failure | DONE    | HIGH | TASK-018 | [→](docs/tasks/task_019.md) |
| TASK-020 | Fix idempotent brief generation for populated target files | DONE    | HIGH | TASK-019 | [→](docs/tasks/task_020.md) |
| TASK-021 | Allow idempotent batch generation through workflow gate | DONE    | HIGH | TASK-020 | [→](docs/tasks/task_021.md) |
| TASK-022 | Align asset generation candidates with storyboard artifacts | DONE | HIGH | TASK-021 | [→](docs/tasks/task_022.md) |
| TASK-023 | Restore Operations Dashboard job queue schema initialization | DONE | HIGH | TASK-022 | [→](docs/tasks/task_023.md) |
| TASK-024 | Explain non-approved manifest assets in blocking reasons | DONE | HIGH | TASK-023 | [→](docs/tasks/task_024.md) |
| TASK-025 | Fix misleading Worker Daemon CRITICAL alert on Operations Dashboard | DONE | HIGH | TASK-024 | [→](docs/tasks/task_025.md) |
| TASK-026 | Auto-load `.env` at Streamlit app startup | DONE | HIGH | TASK-025 | [→](docs/tasks/task_026.md) |
| TASK-027 | Restructure navigation to match morning workflow order | DONE    | HIGH | TASK-026 | [→](docs/tasks/task_027.md) |
| TASK-028 | Update dashboard to show live pipeline artifact counts | DONE    | HIGH | TASK-027 | [→](docs/tasks/task_028.md) |
| TASK-029 | Show brief content preview before approve/reject decision in Brief Viewer | DONE    | MEDIUM | TASK-028 | [→](docs/tasks/task_029.md) |
| TASK-030 | Fix scoring engine differentiated topic scores | DONE    | CRITICAL | None | [→](docs/tasks/task_030.md) |
| TASK-031 | Remove structural marker tokens from final script output | DONE    | HIGH | TASK-030 | [→](docs/tasks/task_031.md) |
| TASK-032 | Remove needs_review placeholder pollution from thumbnail output | DONE    | HIGH | TASK-031 | [→](docs/tasks/task_032.md) |
| TASK-033 | Replace raw terminal-state errors with operator-friendly messages | DONE    | HIGH | TASK-032 | [→](docs/tasks/task_033.md) |
| TASK-034 | Replace raw review enum labels with readable UI status text | DONE | MEDIUM | TASK-033 | [→](docs/tasks/task_034.md) |
| TASK-035 | Format ISO timestamps into readable UI display text | DONE    | MEDIUM | TASK-034 | [→](docs/tasks/task_035.md) |
| TASK-036 | Phase 12.2 validation sweep and knowledge base bootstrap | DONE    | HIGH | TASK-035 | [→](docs/tasks/task_036.md) |
| TASK-082 | Build issue-driven automation runner | DONE    | HIGH | TASK-036 | [→](docs/tasks/task_082.md) |
| TASK-083 | Repair issue-runner task-id mapping and trace handling | DONE    | HIGH | TASK-082 | [→](docs/tasks/task_083.md) |
| TASK-084 | Repair issue-runner plan-mode task-card generation | DONE    | HIGH | TASK-083 | [→](docs/tasks/task_084.md) |
| TASK-085 | Repair issue-runner direct-execution imports and inspect recovery | DONE | HIGH | TASK-084 | [→](docs/tasks/task_085.md) |
| TASK-041 | Add LinkedIn post generator | DONE    | HIGH | TASK-040 | [→](docs/tasks/task_041.md) |
| TASK-087 | Repair CI checks for docs-only PRs and pytest installation | DONE    | HIGH | TASK-085 | [→](docs/tasks/task_087.md) |
| TASK-088 | Create Phase 12.3 sprint task cards | DONE | HIGH | TASK-041 | [→](docs/tasks/task_088.md) |
| TASK-089 | Define LinkedIn quality score model | DONE | HIGH | TASK-088 | [→](docs/tasks/task_089.md) |
| TASK-090 | Add LinkedIn deterministic quality evaluator | DONE | HIGH | TASK-089 | [→](docs/tasks/task_090.md) |
| TASK-091 | Integrate LinkedIn quality evaluator | DONE | HIGH | TASK-090 | [→](docs/tasks/task_091.md) |
| TASK-092 | Document LinkedIn quality scoring | DONE | MEDIUM | TASK-091 | [→](docs/tasks/task_092.md) |


---

## Completed

| ID | Title | Completed | Commit |
|---|---|---|---|
| TASK-004 | Add `SECURITY.md` disclosure policy | 2026-06-07 | docs(security): add SECURITY.md responsible disclosure policy (TASK-004) |
| TASK-005 | Update `GEMINI.md` with security constraints | 2026-06-07 | docs(security): add security constraints to GEMINI.md (TASK-005) |
| TASK-006 | Add GitHub Actions CI workflow (tests on push) | 2026-06-07 | feat(ci): add GitHub Actions test suite workflow (TASK-006) |
| TASK-007 | Add Gitleaks secret scan to CI workflow | 2026-06-07 | security(ci): add Gitleaks secret scanning job to CI workflow (TASK-007) |
| TASK-008 | Add `.pre-commit-config.yaml` with detect-secrets | 2026-06-07 | security(hooks): add pre-commit config with detect-secrets (TASK-008) |
| TASK-012 | Create docs/project-context.md | 2026-06-10 | docs(context): create project-context.md as north star for drift-check and planning (TASK-012) |
| TASK-013 | Run drift-check post Phase 11.9.3 | 2026-06-10 | docs(audit): commit Phase 11.9.4 drift-check findings and advance queue to 11.9.5 (TASK-013) |
| TASK-015 | Add UI syntax test to CI | 2026-06-11 | test(ui): add parametrized syntax test for all Streamlit page files (TASK-015) |
| TASK-017 | Add copy-to-clipboard to asset workshop | 2026-06-11 | feat(ui): add copy-to-clipboard blocks to all asset types in asset workshop (TASK-017) |
| TASK-018 | Trace and fix E2E pipeline brief failure | 2026-06-11 | fix(pipeline): resolve E2E brief generation failure — source topic scoring record lookup (TASK-018) |
| TASK-021 | Allow idempotent batch generation through workflow gate | 2026-06-11 | fix(workflow): allow idempotent batch generation actions through gate (TASK-021) |
| TASK-022 | Align asset generation candidates with storyboard artifacts | 2026-06-11 | fix(pipeline): skip asset generation candidates without storyboards (TASK-022) |
| TASK-023 | Restore Operations Dashboard job queue schema initialization | 2026-06-11 | fix(ops): restore dashboard job queue schema initialization (TASK-023) |
| TASK-024 | Explain non-approved manifest assets in blocking reasons | 2026-06-11 | fix(manifest): explain non-approved planner blockers (TASK-024) |
| TASK-025 | Fix misleading Worker Daemon CRITICAL alert on Operations Dashboard | 2026-06-11 | fix(ui): show Worker Daemon as informational (not CRITICAL) when no jobs queued (TASK-025) |
| TASK-026 | Auto-load `.env` at Streamlit app startup | 2026-06-11 | fix(ui): auto-load .env at Streamlit startup so API keys load without manual export (TASK-026) |
| TASK-027 | Restructure navigation to match morning workflow order | 2026-06-11 | feat(ui): rename navigation pages to match morning workflow order (TASK-027) |
| TASK-028 | Update dashboard to show live pipeline artifact counts | 2026-06-11 | fix(ui): show real pipeline artifact counts on dashboard instead of zeros (TASK-028) |
| TASK-029 | Show brief content preview before approve/reject decision in Brief Viewer | 2026-06-11 | feat(ui): show brief content preview before approve/reject decision in Brief Viewer (TASK-029) |
| TASK-034 | Replace raw review enum labels with readable UI status text | 2026-06-12 | fix(ui): display readable review status labels (TASK-034) |
| TASK-036 | Phase 12.2 validation sweep and knowledge base bootstrap | 2026-06-12 | docs(project): close phase 12.2 and bootstrap SDLC knowledge base (TASK-036) |
| TASK-082 | Build issue-driven automation runner | 2026-06-13 | feat(tooling): add issue-driven automation runner (TASK-082) |
| TASK-083 | Repair issue-runner task-id mapping and trace handling | 2026-06-13 | chore: task-083: repair issue-runner task-id mapping and trace handling |
| TASK-084 | Repair issue-runner plan-mode task-card generation | 2026-06-13 | fix(tooling): generate issue-specific task cards in runner plan mode (TASK-084) |
| TASK-085 | Repair issue-runner direct-execution imports and inspect recovery | 2026-06-13 | fix(tooling): repair issue-runner direct execution imports (TASK-085) |
| TASK-040 | Define platform content contracts | 2026-06-13 | docs(platform): define platform content contracts for Phase 12.3 (TASK-040) |
| TASK-041 | Add LinkedIn post generator | 2026-06-14 | feat(platform): add LinkedIn post generator (TASK-041) |
| TASK-088 | Create Phase 12.3 sprint task cards | 2026-06-17 | docs(tasks): add phase 12.3 LinkedIn quality sprint cards (TASK-088) |
| TASK-089 | Define LinkedIn quality score model | 2026-06-18 | feat(models): add LinkedIn quality score model (TASK-089) |




---

## Blocked

| ID | Title | Blocked Since | Reason |
|---|---|---|
| TASK-003 | Add secret logging filter to `utils/logger.py` | 2026-06-07 | Scope mismatch: task card targets `src/content_creation/utils/logger.py`, but repository contains `src/content_creation/utils/logging.py`; card says no files to create and all other `.py` files are out of scope. |

---

## Notes

- TASK-001 through TASK-005 can run in any order (no dependencies between them)
- TASK-007 requires TASK-006 first (needs the workflow file to exist)
- After Phase 11.9.3, run `$drift-check` before starting Phase 11.9.4
- Run `$security-audit` locally to close UNVERIFIED items from the Phase 11.9.2 audit
  (SEC-C1 git history scan, SEC-C2 cli.py inspection, SEC-H5 test fixtures)
