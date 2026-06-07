# TASK-004: Create `SECURITY.md` responsible disclosure policy

**Phase:** 11.9.3
**Status:** DONE
**Priority:** LOW
**Created:** 2026-06-06
**Completed:** 2026-06-07
**Requires approval:** NO

## Objective
Create SECURITY.md so security issues are reported privately rather than as public GitHub issues.

## Scope

### Files to create
- `SECURITY.md` (repository root)

### Files to modify
None

### Files to NOT touch
All source files, all test files, README.md

## Implementation Steps
1. Create `SECURITY.md` in repo root with this content:
```markdown
# Security Policy

## Reporting a Vulnerability
Do not open a public GitHub issue for security vulnerabilities.
Use GitHub's private vulnerability reporting: Security tab → Report a vulnerability.
Or email the maintainer via the address associated with [@00-Aryan](https://github.com/00-Aryan).
Response within 7 days. Confirmed issues patched before public disclosure.

## In Scope
- Committed credentials or API keys
- Credential leakage via logs, events, or audit records
- Unauthorised access to operator console (Phase 2+)

## Out of Scope
- Dev/test environment only issues
- Issues requiring physical access
```

## Validation
```bash
test -f SECURITY.md && echo "PASS" || echo "FAIL"
grep -q "Report a vulnerability" SECURITY.md && echo "PASS" || echo "FAIL"
```

## Success Criteria
- [x] `SECURITY.md` exists with private reporting instructions

## Depends On
None

## Commit Message
```
docs(security): add SECURITY.md responsible disclosure policy (TASK-004)
```
