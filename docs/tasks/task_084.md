# TASK-084: Repair issue-runner plan-mode task-card generation

**Phase:** Automation Foundation  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-13  
**Completed:** 2026-06-13  
**GitHub Issue:** Internal automation repair task  
**Requires approval:** YES  

## Objective

Repair issue-runner plan mode so it generates a complete, correct, issue-specific task card instead of copying stale placeholder template content.

The generated task card must be safe enough for agent execution and must include real scope, constraints, validation, and traceability derived from the GitHub issue.

## Problem

A smoke test for GitHub issue #5 generated `docs/tasks/task_040.md`, but the content was unusable.

Observed problems:

- It used stale phase text: `11.9.5 — Reliability: Fix SSE Test Failures`.
- It duplicated the title: `# TASK-040: TASK-040: Define platform content contracts`.
- It left `Files to create` empty.
- It left `Files to modify` empty.
- It left implementation steps empty.
- It left success criteria as placeholders.
- It created `.runs/` as an untracked directory, causing the next plan run to fail because the worktree became dirty.
- It did not use GitHub issue labels to infer phase, priority, source, or work type.

## Scope

### Files to modify

- `WORK_QUEUE.md`
- `scripts/issue_runner.py`
- `docs/project/ISSUE_RUNNER_STANDARD.md`

### Files to create

- `docs/tasks/task_084.md`

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

## Constraints

- Do not modify product source code.
- Do not modify tests.
- Do not modify prompts.
- Do not modify dependency files.
- Do not modify CI workflows.
- Do not modify `.gitignore` in this task.
- Do not use stale task templates if they contain unrelated phase/context placeholders.
- Do not allow generated task cards to contain unresolved placeholder text.
- Do not allow plan mode to overwrite an existing task card unless `--force` is explicitly passed.
- Do not allow plan mode to proceed if a generated card would be incomplete.
- Do not let `.runs/` make the worktree dirty after plan mode.

## Required Behavior

For GitHub issue #5 with title:

- `TASK-040: Define platform content contracts`

and labels:

- `phase:12.3`
- `type:docs`
- `type:architecture`
- `priority:high`
- `source:roadmap`

plan mode must generate:

- task card: `docs/tasks/task_040.md`
- phase: `12.3 — Platform-Aware Content`
- priority: `HIGH`
- source: `GitHub issue #5`
- branch: `issue-005-task-040-platform-content-contracts`
- run directory prefix: `.runs/issue-005-task-040-`

The generated task card must include non-placeholder content in these sections:

- Objective
- Context
- Files to create
- Files to modify
- Files to NOT touch
- Constraints
- Implementation Steps
- Validation
- Success Criteria
- Depends On
- Commit Message
- Traceability

## Implementation Requirements

1. Add or update task-card generation logic in `scripts/issue_runner.py`.

2. Remove dependence on stale template content for issue-generated task cards.

3. Add a phase-label mapping.

   Required mappings:

   - `phase:12.3` → `12.3 — Platform-Aware Content`
   - `phase:12.4` → `12.4 — LLM Quality Guardrails`
   - `phase:12.5` → `12.5 — LinkedIn Export and Publishing`
   - `phase:12.6` → `12.6 — YouTube Shorts Flow`
   - `phase:12.7` → `12.7 — Observability and Reliability`
   - `phase:12.8` → `12.8 — Portfolio Readiness`
   - `phase:deferred-polish` → `Deferred UI/Polish`
   - `phase:hardening` → `Technical Debt and Hardening`

4. Add default file-scope inference from issue title and labels.

   For TASK-040 specifically, generated scope must be:

   Files to create:

   - `docs/platform/platform-content-contracts.md`
   - `docs/platform/linkedin-content-contract.md`
   - `docs/platform/youtube-shorts-content-contract.md`
   - `docs/platform/source-grounding-contract.md`
   - `docs/platform/platform-quality-gates.md`
   - `docs/phase-12.3-platform-contracts.md`

   Files to modify:

   - `docs/project/CURRENT_STATE.md`
   - `docs/project/NEXT_ACTION.md`
   - `docs/project/PHASES.md`
   - `docs/project/ROADMAP.md`
   - `docs/project/SPRINT_PLAN.md`
   - `docs/project/DECISION_LOG.md`
   - `docs/project/BACKLOG.md`
   - `WORK_QUEUE.md`

   Files to NOT touch:

   - `src/`
   - `tests/`
   - `prompts/`
   - `data/`
   - `pyproject.toml`
   - `uv.lock`
   - `.github/workflows/`
   - `docs/tasks/task_005.md`

5. Add generic fallback behavior.

   If issue-specific scope cannot be inferred, plan mode must stop and write a clear error:

   - `Cannot infer safe file scope for this issue. Create task card manually or add scope mapping.`

   It must not generate a placeholder card.

6. Add placeholder detection.

   Plan mode must fail if generated card contains:

   - `<Specific, observable criterion`
   - `Replace this comment`
   - `Section Name`
   - `phaseXX`
   - empty `### Files to create`
   - empty `### Files to modify`
   - empty `## Implementation Steps`

7. Fix `.runs/` worktree problem without modifying `.gitignore`.

   Acceptable options:

   - store run logs under `.git/issue-runner-runs/`
   - or store run logs under `/tmp/content-creation-issue-runs/`
   - or make plan mode clean up `.runs/` if it fails before task execution

   Preferred option:

   - move run logs to `.git/issue-runner-runs/`

   Reason:

   - trace logs remain local
   - trace logs do not appear in `git status`
   - no `.gitignore` change required
   - no protected file modification needed

8. Update inspect mode.

   Inspect mode must show:

   - issue number
   - task ID
   - expected task card path
   - expected branch name
   - run log base directory
   - latest run folder if present

9. Update documentation.

   Update `docs/project/ISSUE_RUNNER_STANDARD.md` to explain:

   - task card generation rules
   - phase-label mapping
   - placeholder rejection
   - run log storage location
   - why issue number and TASK ID are different
   - how to handle issues that lack safe inferred scope

10. Update `WORK_QUEUE.md`.

   Add TASK-084 to the active queue if missing.

## Validation

Run these commands:

    bash -n scripts/issue-runner.sh
    python3 -m py_compile scripts/issue_runner.py
    python3 -m py_compile scripts/issue_scope_guard.py
    python3 -m py_compile scripts/issue_pr_body.py

Clean any failed smoke-test output first:

    rm -rf .runs
    rm -f docs/tasks/task_040.md
    git status --short

Then run:

    ./scripts/issue-runner.sh inspect --issue 5
    ./scripts/issue-runner.sh plan --issue 5 --engine agy

Expected checks:

    test "$(git branch --show-current)" = "issue-005-task-040-platform-content-contracts"
    test -f docs/tasks/task_040.md
    grep -q "12.3 — Platform-Aware Content" docs/tasks/task_040.md
    grep -q "docs/platform/platform-content-contracts.md" docs/tasks/task_040.md
    grep -q "docs/platform/linkedin-content-contract.md" docs/tasks/task_040.md
    grep -q "docs/platform/youtube-shorts-content-contract.md" docs/tasks/task_040.md
    grep -q "docs/platform/source-grounding-contract.md" docs/tasks/task_040.md
    grep -q "docs/platform/platform-quality-gates.md" docs/tasks/task_040.md
    ! grep -q "11.9.5" docs/tasks/task_040.md
    ! grep -q "phaseXX" docs/tasks/task_040.md
    ! grep -q "Replace this comment" docs/tasks/task_040.md
    ! grep -q "<Specific, observable criterion" docs/tasks/task_040.md
    git diff -- docs/tasks/task_005.md

Then cleanup smoke-test output before final task commit:

    git checkout main
    git branch -D issue-005-task-040-platform-content-contracts || true
    rm -f docs/tasks/task_040.md
    git status --short

Final full test command:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3

## Success Criteria

- [ ] Plan mode generates `docs/tasks/task_040.md`, not `docs/tasks/task_005.md`.
- [ ] Generated TASK-040 card uses phase `12.3 — Platform-Aware Content`.
- [ ] Generated TASK-040 card contains real files to create.
- [ ] Generated TASK-040 card contains real files to modify.
- [ ] Generated TASK-040 card contains real implementation steps.
- [ ] Generated TASK-040 card contains real validation commands.
- [ ] Generated TASK-040 card contains real success criteria.
- [ ] Generated card contains no stale template placeholders.
- [ ] Plan mode does not modify `docs/tasks/task_005.md`.
- [ ] Run logs no longer make `git status` dirty.
- [ ] Inspect mode reports run log storage location.
- [ ] Full test suite remains green.

## Depends On

TASK-083

## Commit Message

fix(tooling): generate issue-specific task cards in runner plan mode (TASK-084)
