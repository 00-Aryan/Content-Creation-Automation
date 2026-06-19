# TASK-092: Document LinkedIn quality scoring

**Phase:** 12.3 Platform-Aware Content
**Status:** DONE
**Priority:** MEDIUM
**Created:** 2026-06-17
**Completed:** 2026-06-19
**Requires approval:** NO

---

## Source References

- LinkedIn contract: `docs/platform/linkedin-content-contract.md`
- Quality gates: `docs/platform/platform-quality-gates.md`
- Quality model: `docs/tasks/task_089.md`
- Quality evaluator: `docs/tasks/task_090.md`
- Generator integration: `docs/tasks/task_091.md`

---

## Objective

Document the LinkedIn quality scoring rules, score interpretation, and example pass/fail outputs.

---

## Context

After quality scoring is implemented, operators and future agents need to understand why LinkedIn posts pass or fail. This task creates documentation and examples only. It does not change code behavior.

---

## Scope

### Files to create

- `docs/platform/linkedin-quality-scoring.md`

### Files to modify

- `WORK_QUEUE.md`
- `docs/tasks/task_092.md`

### Files to NOT touch

- All `.py` source files
- All test files under `tests/`
- Prompt templates under `prompts/`
- `.github/workflows/`
- `pyproject.toml`
- `uv.lock`
- `data/`
- any `__pycache__/` directory
- any `.pyc` file

---

## Constraints

- Documentation must match implemented evaluator behavior.
- Do not invent gates that are not implemented.
- Include at least one passing example and one failing example.
- Keep the document operator-facing, not purely developer-facing.

---

## Implementation Steps

1. Create `docs/platform/linkedin-quality-scoring.md`.
2. Explain each quality gate.
3. Explain score interpretation.
4. Add one passing example.
5. Add one failing example with issue messages.
6. Cross-reference LinkedIn content contract and quality gates.
7. Mark TASK-092 as DONE only after docs are validated.

---

## Validation

Run:

    test -f docs/platform/linkedin-quality-scoring.md
    grep -n "LinkedIn Quality Scoring\|Passing example\|Failing example" docs/platform/linkedin-quality-scoring.md
    git diff --check
    git diff --name-only

---

## Success Criteria

- [x] LinkedIn quality scoring document exists.
- [x] Document explains all implemented gates.
- [x] Document includes pass and fail examples.
- [x] Document does not describe unimplemented behavior.
- [x] No files outside declared scope were modified.

---

## Depends On

TASK-091

---

## Blocks

None

---

## Commit Message

    docs(platform): document LinkedIn quality scoring (TASK-092)

---

## Notes

This is the Day 2 documentation closeout task.
