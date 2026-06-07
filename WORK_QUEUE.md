# WORK_QUEUE.md — Content Creation Automation Platform

**Current Phase:** 11.9.3 — Security Remediation & CI/CD
**Last updated:** 2026-06-07
**Baseline test count:** 950 passed (16 known failing in test_notification_streaming.py — pre-existing, non-blocking)

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
| TASK-007 | Add Gitleaks secret scan to CI workflow | PENDING | HIGH | TASK-006 | [→](docs/tasks/task_007.md) |
| TASK-008 | Add `.pre-commit-config.yaml` with detect-secrets | PENDING | MEDIUM | None | [→](docs/tasks/task_008.md) |

---

## Completed

| ID | Title | Completed | Commit |
|---|---|---|---|
| TASK-004 | Add `SECURITY.md` disclosure policy | 2026-06-07 | docs(security): add SECURITY.md responsible disclosure policy (TASK-004) |
| TASK-005 | Update `GEMINI.md` with security constraints | 2026-06-07 | docs(security): add security constraints to GEMINI.md (TASK-005) |
| TASK-006 | Add GitHub Actions CI workflow (tests on push) | 2026-06-07 | feat(ci): add GitHub Actions test suite workflow (TASK-006) |

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
