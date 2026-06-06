# TASK-005: Add security constraints section to `GEMINI.md`

**Phase:** 11.9.3
**Status:** PENDING
**Priority:** LOW
**Created:** 2026-06-06
**Completed:** —
**Requires approval:** NO

## Objective
Prevent Gemini CLI from printing environment variable values by adding explicit security rules to GEMINI.md.

## Scope

### Files to modify
- `GEMINI.md` — append one section at the end

### Files to NOT touch
Everything else

## Implementation Steps
1. Read `GEMINI.md` fully
2. Append at the end:
```markdown
## Security Constraints
- Never print, echo, log, or include any environment variable value in output
- Never run `printenv`, `env`, `echo $VARIABLE`, or equivalent commands
- Never include API keys or tokens in commit messages, branch names, or files
- If you encounter a credential in any file, stop and report its location without printing the value
```

## Validation
```bash
grep -q "Security Constraints" GEMINI.md && echo "PASS" || echo "FAIL"
```

## Depends On
None

## Commit Message
```
docs(security): add security constraints to GEMINI.md (TASK-005)
```
