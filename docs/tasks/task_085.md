# TASK-085: Repair issue-runner direct-execution imports and inspect recovery

**Phase:** Automation Foundation
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-13
**Completed:** 2026-06-13
**GitHub Issue:** Internal automation repair task
**Requires approval:** YES

## Objective

Repair the issue runner so every mode works when invoked through:

./scripts/issue-runner.sh

The runner currently fails in inspect mode because `scripts/issue_runner.py` imports `scripts.issue_scope_guard`, but direct script execution does not reliably expose the repository root as an import package.

## Problem

After TASK-084, this command partially worked:

./scripts/issue-runner.sh inspect --issue 5

It correctly reported:

- GitHub issue number: #5
- Task ID: TASK-040
- Derived branch: issue-005-task-040-platform-content-contracts
- Run log base: .git/issue-runner-runs

Then it failed with:

ModuleNotFoundError: No module named 'scripts'

The failing import was:

from scripts.issue_scope_guard import get_changed_files

This means the runner still has module-path fragility when executed as a file instead of as a package.

## Scope

### Files to modify

- `WORK_QUEUE.md`
- `scripts/issue_runner.py`
- `docs/project/ISSUE_RUNNER_STANDARD.md`

### Files to create

- `docs/tasks/task_085.md`

### Files to NOT touch

- `.gitignore`
- `src/`
- `tests/`
- `prompts/`
- `data/`
- `pyproject.toml`
- `uv.lock`
- `.github/workflows/`
- `docs/tasks/task_005.md`
- `docs/tasks/task_040.md`

## Constraints

- Do not modify product source code.
- Do not modify tests.
- Do not modify prompts.
- Do not modify dependency files.
- Do not modify CI workflows.
- Do not modify `.gitignore`.
- Do not delete existing trace logs in `.git/issue-runner-runs`.
- Do not run issue #5 implementation.
- Do not run `full` mode.
- Do not create a PR.
- Do not merge anything.
- This task is limited to tooling reliability.

## Required Behavior

The runner must work when invoked as:

./scripts/issue-runner.sh inspect --issue 5
./scripts/issue-runner.sh plan --issue 5 --engine agy
./scripts/issue-runner.sh verify --issue 5

It must not fail because of imports.

The runner should support direct execution from the repository root without requiring:

python -m scripts.issue_runner

## Implementation Requirements

1. Add robust local import handling in `scripts/issue_runner.py`.

   Acceptable approaches:

   - add the repository root to `sys.path` at process startup
   - or import sibling modules by local path
   - or wrap imports with fallback logic

2. Fix all imports of `scripts.issue_scope_guard`.

   They should work when `issue_runner.py` is executed through the shell wrapper.

3. Inspect mode must not crash after printing active run details.

   It should show:

   - current branch
   - run log base directory
   - active run details if active_run.json exists
   - derived issue metadata if `--issue` is provided
   - changed files if available
   - clear message if no task card exists yet

4. Inspect mode must tolerate stale active runs.

   If active_run.json points to an issue branch while current branch is main, it should print a warning instead of crashing.

5. Inspect mode must not modify files.

6. Plan mode must remain blocked by dirty worktree unless `--force` is explicitly used.

7. Documentation must explain direct execution.

   Update `docs/project/ISSUE_RUNNER_STANDARD.md` with:

   - preferred command form
   - direct script invocation expectation
   - import-path reliability rule
   - inspect-mode behavior
   - stale active-run warning behavior

8. Update `WORK_QUEUE.md`.

   Add TASK-085 to active queue if missing.

## Validation

Run these commands:

    bash -n scripts/issue-runner.sh
    python3 -m py_compile scripts/issue_runner.py
    python3 -m py_compile scripts/issue_scope_guard.py
    python3 -m py_compile scripts/issue_pr_body.py

Run inspect validation:

    ./scripts/issue-runner.sh inspect --issue 5

Expected:

    command exits successfully
    no ModuleNotFoundError
    no traceback
    prints Derived Task ID: TASK-040
    prints Derived Task Card Path: docs/tasks/task_040.md
    prints Derived Branch Name: issue-005-task-040-platform-content-contracts
    prints Run Log Base Directory: .git/issue-runner-runs

Run direct Python validation:

    python3 scripts/issue_runner.py inspect --issue 5

Expected:

    command exits successfully
    no ModuleNotFoundError
    no traceback

Run final status check:

    git status --short

Final full test command:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3

## Success Criteria

- [x] `./scripts/issue-runner.sh inspect --issue 5` exits successfully.
- [x] `python3 scripts/issue_runner.py inspect --issue 5` exits successfully.
- [x] No `ModuleNotFoundError` occurs.
- [x] No traceback occurs.
- [x] Inspect mode reports TASK-040 metadata correctly.
- [x] Inspect mode handles stale active run state without crashing.
- [x] Plan mode behavior is unchanged except import reliability.
- [x] No product files are modified.
- [x] No test files are modified.
- [x] Full test suite remains green.

## Depends On

TASK-084

## Commit Message

fix(tooling): repair issue-runner direct execution imports (TASK-085)
