# TASK-089: Define LinkedIn quality score model

**Phase:** 12.3 Platform-Aware Content
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-17
**Completed:** 2026-06-18
**Requires approval:** NO

---

## Source References

- Platform contract: `docs/platform/linkedin-content-contract.md`
- Quality contract: `docs/platform/platform-quality-gates.md`
- Previous task: `docs/tasks/task_041.md`

---

## Objective

Define a structured LinkedIn quality score model that can represent deterministic evaluation results for generated LinkedIn posts.

---

## Context

TASK-041 added `LinkedInPost`, but it does not yet expose a structured quality score. The platform needs deterministic review signals before a generated asset can be trusted. This task adds the data model only; scoring logic is handled in TASK-090.

---

## Scope

### Files to create

- `src/content_creation/models/linkedin_quality.py`

### Files to modify

- `src/content_creation/models/__init__.py`
- `WORK_QUEUE.md`
- `docs/tasks/task_089.md`

### Files to NOT touch

- `src/content_creation/generation/linkedin.py`
- `prompts/linkedin_post.md`
- `.github/workflows/`
- `pyproject.toml`
- `uv.lock`
- `data/`
- UI files
- Storage files
- Manifest files
- any `__pycache__/` directory
- any `.pyc` file

---

## Constraints

- Do not implement evaluator logic in this task.
- Do not modify `LinkedInPost` unless strictly necessary.
- The model must be serializable with existing Pydantic style.
- The score must support both pass/fail gates and human-readable issue messages.

---

## Implementation Steps

1. Create `src/content_creation/models/linkedin_quality.py`.
2. Add a model for individual quality gate results.
3. Add a model for aggregate LinkedIn quality results.
4. Include fields for score, passed status, issue list, and warning list.
5. Export the model from `src/content_creation/models/__init__.py`.
6. Mark TASK-089 as DONE in its task card and queue only after validation passes.

---

## Validation

Run:

    uv run python -m py_compile src/content_creation/models/linkedin_quality.py
    uv run python -m pytest tests/test_models.py -q
    git diff --check

---

## Success Criteria

- [x] LinkedIn quality score model exists.
- [x] Model supports score, passed status, issues, warnings, and gate results.
- [x] Model is exported from `src/content_creation/models/__init__.py`.
- [x] Existing model tests pass.
- [x] No files outside declared scope were modified.

---

## Depends On

TASK-088

---

## Blocks

TASK-090

---

## Commit Message

    feat(models): add LinkedIn quality score model (TASK-089)

---

## Notes

Keep this task narrow. Evaluator rules belong in TASK-090.
