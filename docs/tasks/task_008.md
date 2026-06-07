# TASK-008: Add `.pre-commit-config.yaml` with detect-secrets

**Phase:** 11.9.3
**Status:** DONE
**Priority:** MEDIUM
**Created:** 2026-06-06
**Completed:** 2026-06-07
**Requires approval:** NO

## Objective
Catch staged credentials before they enter a commit by configuring pre-commit hooks.

## Scope

### Files to create
- `.pre-commit-config.yaml`
- `.secrets.baseline`

### Files to NOT touch
All source files, all test files, `pyproject.toml`

## Implementation Steps
1. Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: end-of-file-fixer
```
2. Create `.secrets.baseline`:
```json
{"version": "1.5.0", "plugins_used": [], "filters_used": [], "results": {}, "generated_at": ""}
```

## Validation
```bash
python3 -c "import yaml; d=yaml.safe_load(open('.pre-commit-config.yaml')); assert any('detect-secrets' in r['repo'] for r in d['repos']); print('PASS')"
test -f .secrets.baseline && echo "PASS" || echo "FAIL"
```

## Success Criteria
- [ ] `.pre-commit-config.yaml` exists with detect-secrets
- [ ] `.secrets.baseline` exists

## Depends On
None

## Commit Message
```
security(hooks): add pre-commit config with detect-secrets (TASK-008)
```
