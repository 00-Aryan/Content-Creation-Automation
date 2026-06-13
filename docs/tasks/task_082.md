# TASK-082: Build issue-driven automation runner

**Phase:** Automation Foundation  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-13  
**GitHub Issue:** Internal automation task  
**Requires approval:** YES  

## Objective

Build a local issue-driven automation runner that turns one GitHub issue into one controlled branch, task card, agent run, scope check, test run, commit, pushed branch, and pull request.

The runner should reduce repeated manual work across the 50+ GitHub issues while preserving traceability and safety.

## Scope

### Files to modify

- `WORK_QUEUE.md`
- `docs/project/QUALITY_GATES.md`
- `docs/project/SDLC_STANDARD.md`

### Files to create

- `scripts/issue-runner.sh`
- `scripts/issue_runner.py`
- `scripts/issue_scope_guard.py`
- `scripts/issue_pr_body.py`
- `docs/project/ISSUE_RUNNER_STANDARD.md`

### Files to NOT touch

- `src/`
- `tests/`
- `prompts/`
- `data/`
- `pyproject.toml`
- `uv.lock`
- `.github/workflows/`

## Constraints

- This is infrastructure only.
- Do not modify product source code.
- Do not modify tests.
- Do not modify prompts.
- Do not modify generated data.
- Do not modify dependencies.
- Do not modify CI workflows.
- Do not directly merge to `main`.
- Do not directly close GitHub issues.
- PR body must use `Closes #ISSUE`.
- Runner must block on scope violations.
- Runner must preserve run logs under `.runs/`.
- Runner must support `agy` and `codex` engines.
- Runner must default to `agy`.
- Runner must stop before merge unless explicit merge mode is used.
- Runner must refuse dirty worktrees before starting a new issue.
- Runner must refuse unexpected modified files unless the task card is explicitly updated first.

## Implementation Steps

1. Create shell entrypoint:

   - `scripts/issue-runner.sh`

2. Create Python controller:

   - `scripts/issue_runner.py`

3. Create scope guard:

   - `scripts/issue_scope_guard.py`

4. Create PR body generator:

   - `scripts/issue_pr_body.py`

5. Create documentation:

   - `docs/project/ISSUE_RUNNER_STANDARD.md`

6. Add runner modes:

   - `plan`
   - `run`
   - `verify`
   - `pr`
   - `merge`
   - `full`
   - `inspect`
   - `abort`
   - `resume`

7. Implement `plan` mode.

   It must:

   - read GitHub issue content using `gh issue view`
   - create or verify issue branch
   - create a task card
   - not modify product code

8. Implement `run` mode.

   It must:

   - invoke selected engine
   - support `--engine agy`
   - support `--engine codex`
   - default to `agy`
   - stop if task card is missing

9. Implement `verify` mode.

   It must:

   - read task-card file scope
   - compare changed files against allowed files
   - run shell syntax checks
   - run Python compile checks
   - run full pytest suite

10. Implement `pr` mode.

   It must:

   - commit only after scope check passes
   - push the issue branch
   - create PR using `gh pr create`
   - include `Closes #ISSUE` in PR body
   - include validation evidence in PR body

11. Implement `merge` mode.

   It must:

   - refuse if issue is labelled security, CI, architecture, or hardening
   - refuse if checks failed
   - refuse if working tree is dirty
   - use squash merge only
   - delete branch after merge
   - pull latest `main`

12. Implement `full` mode.

   It must execute:

   - preflight
   - plan
   - run
   - verify
   - pr
   - stop before merge unless explicit merge flag is passed

13. Implement trace logs.

   Each run should create:

   - `.runs/issue-<number>-<timestamp>/issue.json`
   - `.runs/issue-<number>-<timestamp>/task_card_before.md`
   - `.runs/issue-<number>-<timestamp>/task_card_after.md`
   - `.runs/issue-<number>-<timestamp>/allowed_files.txt`
   - `.runs/issue-<number>-<timestamp>/changed_files.txt`
   - `.runs/issue-<number>-<timestamp>/scope_check.txt`
   - `.runs/issue-<number>-<timestamp>/targeted_tests.log`
   - `.runs/issue-<number>-<timestamp>/full_tests.log`
   - `.runs/issue-<number>-<timestamp>/commit.txt`
   - `.runs/issue-<number>-<timestamp>/pr.txt`
   - `.runs/issue-<number>-<timestamp>/agent_output.log`

14. Update project docs.

   Update:

   - `docs/project/QUALITY_GATES.md`
   - `docs/project/SDLC_STANDARD.md`

   Add the issue-runner workflow and guardrails.

15. Update `WORK_QUEUE.md`.

   Add TASK-082 to the active queue.

## Validation

Run these commands:

    bash -n scripts/issue-runner.sh
    python3 -m py_compile scripts/issue_runner.py
    python3 -m py_compile scripts/issue_scope_guard.py
    python3 -m py_compile scripts/issue_pr_body.py

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3

## Success Criteria

- [ ] `scripts/issue-runner.sh` exists.
- [ ] `scripts/issue_runner.py` exists.
- [ ] `scripts/issue_scope_guard.py` exists.
- [ ] `scripts/issue_pr_body.py` exists.
- [ ] `docs/project/ISSUE_RUNNER_STANDARD.md` exists.
- [ ] Runner supports `plan`.
- [ ] Runner supports `run`.
- [ ] Runner supports `verify`.
- [ ] Runner supports `pr`.
- [ ] Runner supports `merge`.
- [ ] Runner supports `full`.
- [ ] Runner supports `inspect`.
- [ ] Runner supports `abort`.
- [ ] Runner supports `resume`.
- [ ] Runner can create a linked branch from an issue.
- [ ] Runner can generate a task card from issue content.
- [ ] Runner can check changed files against task-card scope.
- [ ] Runner can create a PR body with `Closes #ISSUE`.
- [ ] Runner preserves trace logs under `.runs/`.
- [ ] Runner refuses dirty worktree.
- [ ] Runner refuses unexpected modified files.
- [ ] Runner does not merge unless explicit merge mode is used.
- [ ] Auto-merge is blocked for security, CI, architecture, and hardening issues.
- [ ] Full test suite remains green.
- [ ] Documentation explains the workflow clearly.

## Depends On

TASK-036

## Commit Message

feat(tooling): add issue-driven automation runner (TASK-082)
