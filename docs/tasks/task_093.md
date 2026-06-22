# TASK-093: Make issue-runner completion and review automation reliable

**Phase:** Technical Debt and Hardening
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-22
**Completed:** 2026-06-22
**GitHub Issue:** #58
**Requires approval:** YES

## Objective
Harden the local issue runner so it cannot report success, create a pull request, or merge when execution is incomplete, evidence is missing, validation failed, state is stale, or the pull-request head differs from the verified commit.

## Confirmed defects from TASK-042
- `run` accepts a non-zero engine result unless output contains `TASK_FAILED:`.
- `verify` does not enforce the expected workflow state or branch.
- Validation parsing skips pytest commands and breaks multiline commands into independent lines.
- Targeted validation failures only warn.
- Full pytest verification ignores the process exit code and trusts only a parsed pass count.
- Black, isort, and mypy are not run locally before PR creation.
- Empty evidence becomes `No log available.` in a PR.
- `pr` does not require verified state and may use generic titles.
- `merge` is not pinned to the verified head SHA and does not independently require successful checks.
- Active-run state writes are not atomic.

## Files to create
- `tests/test_issue_runner.py`
- `docs/tasks/task_093.md`

## Files to modify
- `scripts/issue_runner.py`
- `scripts/issue_pr_body.py`
- `docs/project/ISSUE_RUNNER_STANDARD.md`
- `WORK_QUEUE.md`

## Files to not touch
- `.github/workflows/`
- `pyproject.toml`
- `uv.lock`
- `src/content_creation/`
- unrelated product tests
- `data/`

## Required behavior

### State and execution
- Enforce `planned -> run_completed -> verified -> pr_created -> merged` transitions.
- Require the active issue branch for run and verify.
- Refuse planning over an unrelated active run.
- Write active state atomically.
- Treat non-zero engine exit, failed nonce-bound status, missing status, stderr-only status, duplicate status, or non-final status as failure.

### Verification
- Execute complete Bash validation blocks with `bash -e -u -o pipefail` and preserve multiline commands.
- Execute pytest commands rather than skipping them.
- Fail on any task validation error and log command, exit code, stdout, and stderr.
- Run Black, isort, and mypy for changed Python files.
- Run the full pytest suite and require exit code zero plus a pass count at or above baseline.
- Write a structured verification manifest with each gate, a fingerprint of the verified changes, and the verified Git tree SHA.

### Pull request evidence
- Require verified state and current successful evidence.
- Reject missing, empty, stale, or failed evidence.
- Parse fenced or indented commit messages reliably.
- Use the validated commit message as PR title.
- Build the PR body from structured evidence and never treat `No log available.` as success.
- Keep verification evidence immutable after verify mode; record commit, push, and PR metadata separately.

### Guarded merge
- Require `pr_created` state.
- Require open, non-draft, mergeable, clean PR state.
- Require all checks for the recorded head SHA to be completed successfully.
- Refuse when PR head differs from recorded committed or pushed SHA.
- Use a head-matched squash merge without an unguarded fallback.
- Clear active state only after confirmed merge, synchronized local main, and readable final-state archive.

## Required tests
Mock all external GitHub operations. Cover non-zero engine exit, spoofed or missing nonce-bound completion signal, invalid state, wrong branch, multiline validation, pipeline and sequential Bash failure propagation, targeted pytest execution, Black/isort/mypy failures, pytest non-zero exit with a parseable pass count, forged manifests, missing evidence, commit-message parsing, stale verification fingerprint, changed file set, staged tree mismatch, changed head SHA, failed or pending checks, safe abort refusals, and successful guarded PR and merge paths.

## Acceptance criteria
- The TASK-042 failure sequence is represented by regression tests and blocked before PR creation.
- No required command failure can produce verified state.
- PR creation requires complete current evidence.
- Merge is pinned to the exact committed and pushed head SHA derived from verified content.
- Existing plan, inspect, abort, resume, and direct-execution behavior remains compatible unless strengthened above.
- Full repository tests pass.

## Depends on
TASK-085, TASK-087

## Blocks
TASK-043 automation execution until this hardening task is complete.

## Commit Message

fix(tooling): harden issue-runner completion and review automation (TASK-093)
