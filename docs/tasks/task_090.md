# TASK-090: Add LinkedIn deterministic quality evaluator

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
- Quality model: `docs/tasks/task_089.md`
- Previous generator: `docs/tasks/task_041.md`

---

## Objective

Add a deterministic evaluator that scores LinkedIn posts against platform-specific quality gates.

---

## Context

The LinkedIn prompt asks for constraints such as hook quality, readable paragraph length, single CTA, hashtag count, source preservation, and no hype language. Prompt instructions alone are insufficient. This task adds deterministic checks that can be tested without an LLM call.

---

## Scope

### Files to create

- `src/content_creation/generation/linkedin_quality.py`
- `tests/test_linkedin_quality.py`

### Files to modify

- `src/content_creation/generation/__init__.py`
- `WORK_QUEUE.md`
- `docs/tasks/task_090.md`

### Files to NOT touch

- `src/content_creation/generation/linkedin.py`
- `src/content_creation/models/linkedin.py`
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

- The evaluator must be deterministic.
- No LLM call is allowed in evaluator tests.
- Do not integrate evaluator into the generator in this task.
- Keep all thresholds explicit and easy to tune.
- Return structured issue messages rather than raw booleans.

---

## Implementation Steps

1. Create `LinkedInQualityEvaluator`.
2. Check hashtag count is between 3 and 5.
3. Check CTA has exactly one prompt or question.
4. Check total post length is within the hard limit.
5. Check hook is present and concise.
6. Check source links/source reference are present.
7. Check banned hype words are not present.
8. Add tests for pass and fail cases.
9. Export evaluator from `src/content_creation/generation/__init__.py`.
10. Mark TASK-090 as DONE only after targeted tests pass.

---

## Validation

Run:

    uv run black --check src/content_creation/generation/linkedin_quality.py tests/test_linkedin_quality.py
    uv run isort --check-only src/content_creation/generation/linkedin_quality.py tests/test_linkedin_quality.py
    uv run pytest tests/test_linkedin_quality.py -q
    git diff --check

---

## Success Criteria

- [ ] Deterministic LinkedIn evaluator exists.
- [ ] Evaluator tests cover pass and fail cases.
- [ ] Evaluator has no LLM dependency.
- [ ] Evaluator returns structured score output.
- [ ] No files outside declared scope were modified.

---

## Depends On

TASK-089

---

## Blocks

TASK-091

---

## Commit Message

    feat(generation): add LinkedIn quality evaluator (TASK-090)

---

## Notes

Keep integration out of this task. TASK-091 wires the evaluator into generation.
