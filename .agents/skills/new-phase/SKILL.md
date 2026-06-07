# SKILL: new-phase

## TRIGGER
$new-phase <phase description>
If no description given, ask: "What is this phase's objective in 1-3 sentences?"

## READS LOCAL FILES ONLY — no GitHub fetching
cat WORK_QUEUE.md          → find highest task number, check for queue debt
cat TASK_SPEC.md           → current project state
ls docs/tasks/             → confirm which task cards already exist
ls docs/architecture/      → find most recent phase report
cat docs/backlog/issues.md → open issues to consider

## QUEUE DEBT FIRST
If WORK_QUEUE.md references any TASK-NNN that has no file in docs/tasks/:
create those missing cards before adding new phase tasks.

## TASK RULES (max 5 tasks per phase)
Each task must be:
- Atomic: one deliverable
- Bounded: explicit file list
- Verifiable: bash command with clear PASS/FAIL output
- Small: under 2 hours
- Ordered: dependencies declared

## TASK CARD FORMAT
Create docs/tasks/task_NNN.md for each task using this structure:

# TASK-NNN: <title max 60 chars>
**Phase:** X.X.X
**Status:** PENDING
**Priority:** CRITICAL|HIGH|MEDIUM|LOW
**Created:** YYYY-MM-DD
**Completed:** —
**Requires approval:** YES|NO

## Objective
One sentence.

## Scope
### Files to create
### Files to modify
### Files to NOT touch

## Implementation Steps
1. Exact step
2. Exact step

## Validation
```bash
export UV_CACHE_DIR=/tmp/uv-cache
<task-specific check>
```

## Success Criteria
- [ ] criterion

## Depends On
## Blocks

## Commit Message
```
type(scope): description (TASK-NNN)
```

## PUSH
After writing all task cards locally, push everything in one call:
mcp__github.push_files
  message: "docs(tasks): add task cards for Phase X.X.X"
  files: [all new task_NNN.md files + updated WORK_QUEUE.md]

## REPORT
Phase: <name>
Tasks created: TASK-NNN → TASK-NNN
Files pushed: <list>
Run $run-next-task to begin.
