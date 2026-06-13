# TASK-083: Repair issue-runner task-id mapping and trace handling

**Phase:** Automation Foundation
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-13
**GitHub Issue:** Internal automation repair task
**Requires approval:** YES

## Objective

Repair the issue-driven automation runner so it correctly maps a GitHub issue number to the task ID embedded in the issue title.

Example:

- GitHub issue number: 5
- GitHub issue title: TASK-040: Define platform content contracts
- Correct task card: docs/tasks/task_040.md
- Correct branch: issue-005-task-040-platform-content-contracts
- Correct run directory prefix: .runs/issue-005-task-040-

The runner must not confuse GitHub issue numbers with internal TASK numbers.

## Scope

### Files to modify

- `WORK_QUEUE.md`
- `scripts/issue_runner.py`
- `docs/project/ISSUE_RUNNER_STANDARD.md`
- `.gitignore`

### Files to create

- `docs/tasks/task_083.md`

### Files to NOT touch

- `src/`
- `tests/`
- `prompts/`
- `data/`
- `pyproject.toml`
- `uv.lock`
- `.github/workflows/`
- `docs/tasks/task_005.md`

## Problem

During runner smoke testing, running plan mode for GitHub issue #5 created branch `issue-5` and looked for `docs/tasks/task_005.md`.

This is incorrect because GitHub issue #5 is titled `TASK-040: Define platform content contracts`.

The runner currently appears to derive task file paths from the GitHub issue number instead of extracting the internal TASK ID from the issue title.

## Required Behavior

The runner must extract the internal task ID from issue titles matching this pattern:

- `TASK-040: Define platform content contracts`
- `TASK-083: Repair issue-runner task-id mapping and trace handling`

For GitHub issue #5, the runner must derive:

- issue number: `5`
- issue number padded: `005`
- task ID: `040`
- task code: `TASK-040`
- task card path: `docs/tasks/task_040.md`
- branch name: `issue-005-task-040-platform-content-contracts`
- run directory prefix: `.runs/issue-005-task-040-`

If the issue title does not contain `TASK-XXX`, the runner must stop with a clear error unless an explicit fallback flag exists.

Do not silently fall back to issue number.

## Implementation Requirements

1. Add a helper that extracts task metadata from issue JSON.

   It must derive:

   - issue number
   - padded issue number
   - task number
   - padded task number
   - task code
   - slug
   - task card path
   - branch name
   - run directory name prefix

2. Update plan mode.

   Plan mode must:

   - fetch issue JSON
   - extract task ID from issue title
   - create the correct branch name
   - create the correct task card path
   - create the correct run folder path
   - write issue.json
   - write task_card_before.md only if a task card exists
   - never read or overwrite an unrelated historical task card

3. Update run mode.

   Run mode must:

   - locate task card by extracted TASK ID
   - refuse to run if the task card does not match the issue title task ID
   - refuse to use task_005.md for GitHub issue #5

4. Update verify mode.

   Verify mode must:

   - locate task card by extracted TASK ID
   - run scope guard against the correct task card
   - report both GitHub issue number and TASK ID

5. Update PR mode.

   PR mode must:

   - locate task card by extracted TASK ID
   - create PR body using GitHub issue number for `Closes #5`
   - keep commit/task references as `TASK-040`

6. Update inspect mode.

   Inspect mode should be useful before a run exists.

   It should:

   - show current branch
   - show whether .runs exists
   - show latest run for the issue if any
   - if no run exists, say no run exists without failing
   - if `--issue` is provided and `gh` exists, show issue title and derived task ID

7. Add `.runs/` to `.gitignore`.

8. Update runner documentation.

   Update `docs/project/ISSUE_RUNNER_STANDARD.md` to explain:

   - GitHub issue number is not the same as TASK ID
   - issue title must contain TASK-XXX
   - branch naming convention
   - run directory naming convention
   - PR closing convention uses GitHub issue number
   - task cards use TASK ID

9. Update `WORK_QUEUE.md`.

   Add TASK-083 to the active queue if missing.

## Validation

Run these commands:

    bash -n scripts/issue-runner.sh
    python3 -m py_compile scripts/issue_runner.py
    python3 -m py_compile scripts/issue_scope_guard.py
    python3 -m py_compile scripts/issue_pr_body.py
    ./scripts/issue-runner.sh inspect --issue 5
    ./scripts/issue-runner.sh plan --issue 5 --engine agy
    test "$(git branch --show-current)" = "issue-005-task-040-platform-content-contracts"
    test -f .runs/issue-005-task-040-*/issue.json
    test -f docs/tasks/task_040.md
    test ! -f docs/tasks/task_005.md.modified
    git status --short

Then cleanup the smoke-test branch before final commit if plan mode created issue #5 branch during validation.

Final full test command:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3

## Success Criteria

- [ ] GitHub issue #5 maps to TASK-040.
- [ ] Plan mode no longer creates branch `issue-5`.
- [ ] Plan mode creates branch `issue-005-task-040-platform-content-contracts`.
- [ ] Plan mode creates or uses `docs/tasks/task_040.md`.
- [ ] Plan mode does not read or modify `docs/tasks/task_005.md`.
- [ ] Run mode uses TASK ID, not issue number.
- [ ] Verify mode uses TASK ID, not issue number.
- [ ] PR mode uses TASK ID for task artifacts and GitHub issue number for `Closes #5`.
- [ ] Inspect mode is useful before any run exists.
- [ ] `.runs/` is ignored by git.
- [ ] Full test suite remains green.

## Depends On

TASK-082

## Commit Message

fix(tooling): map GitHub issues to task IDs in issue runner (TASK-083)
