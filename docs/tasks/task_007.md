# TASK-007: Add Gitleaks secret scan to CI workflow

**Phase:** 11.9.3
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-06
**Completed:** 2026-06-07
**Requires approval:** NO

## Objective
Block any push that contains a committed API key by adding Gitleaks scanning to the CI workflow.

## Scope

### Files to modify
- `.github/workflows/ci.yml` — add `secret-scan` job

### Files to NOT touch
All source files, existing `test` job in the workflow

## Implementation Steps
1. Open `.github/workflows/ci.yml`
2. Add after the closing of the `test` job (same indentation level):
```yaml
  secret-scan:
    name: Secret Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Validation
```bash
python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); assert 'secret-scan' in d['jobs']; print('PASS')"
```

## Success Criteria
- [x] `.github/workflows/ci.yml` defines a `secret-scan` job

## Depends On
TASK-006

## Commit Message
```
security(ci): add Gitleaks secret scanning job to CI workflow (TASK-007)
```
