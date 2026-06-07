# TASK-006: Add GitHub Actions CI workflow for test suite

**Phase:** 11.9.3
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-06
**Completed:** 2026-06-07
**Requires approval:** NO

## Objective
Run the test suite automatically on every push and PR so regressions are caught before merging.

## Scope

### Files to create
- `.github/workflows/ci.yml`

### Files to NOT touch
All source files, all test files, existing `.github/` files

## Implementation Steps
1. Create `.github/workflows/ci.yml`:
```yaml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  test:
    name: Test Suite
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv python install 3.12
      - run: uv sync --frozen
      - run: |
          export UV_CACHE_DIR=/tmp/uv-cache
          uv run python -m pytest --tb=short -q
        env:
          GEMINI_API_KEY: ""
```

## Validation
```bash
python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); assert 'test' in d['jobs']; print('PASS')"
```

## Success Criteria
- [x] `.github/workflows/ci.yml` exists and defines a `test` job

## Depends On
None

## Blocks
TASK-007

## Commit Message
```
feat(ci): add GitHub Actions test suite workflow (TASK-006)
```
