# TASK-087: Repair CI checks for docs-only PRs and pytest installation

**Phase:** Automation Foundation
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-13
**GitHub Issue:** Internal CI repair task
**Requires approval:** YES

## Objective

Repair GitHub Actions CI behavior so documentation-only PRs are not blocked by unrelated Python formatting debt, and ensure the legacy CI test workflow installs the test dependencies required to run pytest.

## Problem

PR #49 for TASK-040 is docs-only and verified locally, but GitHub reports two failing checks:

1. `CI/Test Suite`
2. `Code Quality/quality`

The failures are unrelated to TASK-040.

`CI/Test Suite` fails with:

    No module named pytest

This indicates the workflow environment does not install pytest or the proper test dependency group before running:

    uv run python -m pytest --tb=short -q

`Code Quality/quality` fails because it runs:

    uv run black --check src tests

and the existing repository contains broad historical Black/isort formatting debt across many Python files. TASK-040 does not modify Python files.

## Scope

### Files to modify

- `.github/workflows/ci.yml`
- `.github/workflows/code-quality.yml`

### Files to create

- `docs/tasks/task_087.md`

### Files to NOT touch

- `src/`
- `tests/`
- `scripts/`
- `prompts/`
- `data/`
- `pyproject.toml`
- `uv.lock`
- `docs/platform/`
- `docs/project/`
- `docs/tasks/task_040.md`
- `docs/tasks/task_005.md`

## Constraints

- Do not modify product source code.
- Do not modify tests.
- Do not modify scripts.
- Do not reformat Python files.
- Do not run `black .`.
- Do not run `isort .`.
- Do not change dependency files unless absolutely required and separately justified.
- Keep this task limited to GitHub Actions workflow behavior.
- Do not merge PR #49 inside this task.

## Required Behavior

1. Documentation-only PRs must not fail because of Python Black/isort debt.

2. Quality checks should either:

   - skip Python formatting checks when a PR changes only docs/Markdown/project tracking files, or
   - run formatting checks only on changed Python files.

3. The legacy CI test workflow must install dependencies in a way that includes pytest before running pytest.

4. Existing matrix test workflows that already pass must remain unchanged unless needed.

5. Secret scan and coverage behavior must not be weakened.

## Implementation Requirements

1. Inspect current workflow files.

   Review:

   - `.github/workflows/ci.yml`
   - `.github/workflows/code-quality.yml`

2. Fix `CI/Test Suite`.

   Ensure the workflow installs pytest/test dependencies before running:

       uv run python -m pytest --tb=short -q

   Preferred fixes, in order:

   - use the same dependency install command as the passing matrix test workflow
   - or use `uv sync --frozen --group dev`
   - or use the project’s documented test install command

3. Fix `Code Quality/quality`.

   Avoid global formatting failure on docs-only PRs.

   Acceptable approaches:

   - add changed-file detection and skip Black/isort/mypy when no Python files changed
   - or run Black/isort only on changed Python files
   - or path-filter the job so it only runs on Python/config workflow changes

4. Preserve security.

   Do not disable secret scanning.

5. Add clear CI output.

   When quality checks are skipped because no Python files changed, print:

       No Python files changed; skipping Python formatting checks.

6. Keep PR #49 clean.

   This task must be a separate branch/commit/PR from TASK-040.

## Validation

Run local syntax checks:

    python3 - <<'PY'
    import yaml
    from pathlib import Path
    for path in [Path(".github/workflows/ci.yml"), Path(".github/workflows/code-quality.yml")]:
        yaml.safe_load(path.read_text())
        print(f"PASS: {path}")
    PY

Run local no-source-change check:

    git diff --name-only

Expected changed files only:

    .github/workflows/ci.yml
    .github/workflows/code-quality.yml
    docs/tasks/task_087.md
    WORK_QUEUE.md

Run tests:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3

After PR is opened, verify:

    gh pr checks <TASK-087_PR_NUMBER>

Expected:

- CI/Test Suite passes
- Code Quality passes or explicitly skips Python formatting for docs-only changes
- Secret Scan passes
- Existing matrix tests pass

## Success Criteria

- [x] CI/Test Suite no longer fails with `No module named pytest`.
- [x] Docs-only PRs are not blocked by unrelated Python formatting debt.
- [x] Black/isort checks are skipped or scoped when no Python files changed.
- [x] Secret Scan remains enabled.
- [x] Existing passing test workflows remain passing.
- [x] No product source files are modified.
- [x] No test files are modified.
- [x] TASK-040 PR #49 can be rechecked or merged after CI policy repair.

## Depends On

TASK-085

## Commit Message

ci: repair docs-only PR quality gates and pytest install (TASK-087)
