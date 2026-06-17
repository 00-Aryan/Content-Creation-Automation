# TASK-091: Integrate LinkedIn quality evaluator

**Phase:** 12.3 Platform-Aware Content
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-17
**Completed:** —
**Requires approval:** NO

---

## Source References

- LinkedIn generator: `docs/tasks/task_041.md`
- Quality model: `docs/tasks/task_089.md`
- Quality evaluator: `docs/tasks/task_090.md`

---

## Objective

Integrate the LinkedIn quality evaluator into the LinkedIn generator fallback and review-status flow.

---

## Context

After TASK-090, the evaluator can score a post, but the generator still returns posts without deterministic quality context. This task connects generation with the quality gate so weak outputs are forced into review and strong outputs keep draft status.

---

## Scope

### Files to create

None

### Files to modify

- `src/content_creation/generation/linkedin.py`
- `src/content_creation/models/linkedin.py`
- `tests/test_linkedin_generation.py`
- `WORK_QUEUE.md`
- `docs/tasks/task_091.md`

### Files to NOT touch

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

- Preserve existing fallback behavior.
- Do not make network calls in tests.
- If quality gates fail, force `review_status=NEEDS_REVIEW`.
- Do not add UI or storage integration in this task.
- Do not change prompt wording unless a test proves it is required.

---

## Implementation Steps

1. Add quality score field to `LinkedInPost` if needed.
2. Instantiate or call `LinkedInQualityEvaluator` after a post is parsed.
3. Attach quality result to the returned post.
4. Force `ReviewStatus.NEEDS_REVIEW` when quality fails.
5. Preserve `ReviewStatus.DRAFT` for valid high-quality outputs.
6. Extend existing generator tests for quality pass/fail behavior.
7. Run targeted and full validation.
8. Mark TASK-091 as DONE only after tests pass.

---

## Validation

Run:

    uv run black --check src/content_creation/generation/linkedin.py src/content_creation/models/linkedin.py tests/test_linkedin_generation.py
    uv run isort --check-only src/content_creation/generation/linkedin.py src/content_creation/models/linkedin.py tests/test_linkedin_generation.py
    uv run pytest tests/test_linkedin_generation.py tests/test_linkedin_quality.py -q
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    git diff --check

---

## Success Criteria

- [ ] LinkedIn generator attaches quality results.
- [ ] Failed quality gates force `NEEDS_REVIEW`.
- [ ] Valid outputs can remain `DRAFT`.
- [ ] Tests cover both outcomes.
- [ ] Full test suite passes at baseline count.
- [ ] No files outside declared scope were modified.

---

## Depends On

TASK-090

---

## Blocks

TASK-092

---

## Commit Message

    feat(generation): integrate LinkedIn quality evaluator (TASK-091)

---

## Notes

This task makes the generator safer but does not add UI surfacing. UI can be a later task.
