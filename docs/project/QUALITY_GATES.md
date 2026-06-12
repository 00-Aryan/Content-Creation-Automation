# Quality Gates

## Per-Task Gates

- Task card exists.
- Scope has `### Files to modify` and `### Files to create`.
- Targeted tests pass.
- Full test suite passes.
- No unrelated files modified.

## Phase Closure Gates

- All critical bugs fixed.
- Validation sweep documented.
- Knowledge base updated.
- Next phase has task plan.
- Full test suite remains green.

## Required Commands

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Current Baseline

- Minimum expected full suite: 1000 passed
