# TASK-013: Run `$drift-check` post Phase 11.9.3 and commit findings

**Phase:** 11.9.4
**Status:** PENDING
**Priority:** MEDIUM
**Created:** 2026-06-07
**Completed:** —
**Requires approval:** NO

---

## Source References
- Phase: 11.9.4 Automation Validation

## Objective
Run the `$drift-check` skill after Phase 11.9.3 completion and commit its findings to `docs/backlog/issues.md`. Validates that the full `--all` flag execution of `run-tasks.sh` completes cleanly after TASK-009 through TASK-012 are done.

## Context
This is the final task of Phase 11.9.4. If `run-tasks.sh --all` reaches this task and executes it successfully, it means: the queue parsing works, dependency ordering works, Type A and Type B paths both work, and all five tasks committed cleanly. The drift-check run also confirms the project is on track before entering Phase 11.9.5.

## Scope

### Files to modify
- `docs/backlog/issues.md` — append the drift-check findings section
- `WORK_QUEUE.md` — update phase header to reflect 11.9.4 complete (if drift-check passes)

### Files to NOT touch
Everything else.

## Constraints
- Run `$drift-check` as a sub-step — read its output and transcribe findings
- Do not manually write fake findings — use actual output from the skill
- If drift-check reports CRITICAL drift: record it accurately, do not suppress it

## Implementation Steps

1. Run the drift-check skill:
   ```
   $drift-check
   ```

2. Read the full output. Extract:
   - Overall status (ON TRACK / MINOR DRIFT / SIGNIFICANT DRIFT / CRITICAL DRIFT)
   - Any specific findings (DRIFT-001, DRIFT-002, etc.)
   - Test count result
   - Any new issues identified

3. Open `docs/backlog/issues.md` and append a new section at the bottom:

```markdown
---

## Phase 11.9.4 Drift-Check (TASK-013)
**Run date:** <today>
**Overall status:** <status from drift-check output>

### Findings
<paste each DRIFT-NNN finding, or write "None — project on track">

### Test count at phase close
950 passed, 16 known pre-existing failures (test_notification_streaming.py)
```

4. If `WORK_QUEUE.md` has a phase header line, update it to:
   ```
   **Current Phase:** 11.9.5 — Reliability: Fix SSE Test Failures
   ```

## Validation

```bash
grep -q "Phase 11.9.4 Drift-Check" docs/backlog/issues.md && echo "PASS: findings recorded" || echo "FAIL"
grep -q "11.9.5" WORK_QUEUE.md && echo "PASS: queue updated" || echo "FAIL"
```

## Success Criteria
- [ ] `docs/backlog/issues.md` contains the drift-check findings section
- [ ] `WORK_QUEUE.md` references Phase 11.9.5 as next
- [ ] No source files modified

## Depends On
TASK-009, TASK-010, TASK-011, TASK-012

## Blocks
None

## Commit Message
```
docs(audit): commit Phase 11.9.4 drift-check findings and advance queue to 11.9.5 (TASK-013)
```

## Agent Notes
This task depends on all four previous tasks being DONE. If `run-tasks.sh --all` reaches this task, it means the full automation pipeline worked. That is the validation goal of Phase 11.9.4.

If drift-check is not available as a skill (returns error), run these manual checks instead:
- git log --oneline -10
- uv run python -m pytest --tb=no -q 2>&1 | tail -3
- git grep -r "AIza" src/ --include="*.py"
Record the output as the findings.