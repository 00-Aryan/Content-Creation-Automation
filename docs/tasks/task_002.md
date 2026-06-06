# TASK-002: Extend `.gitignore` to cover Phase 11+ database files

**Phase:** 11.9.3
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-06
**Completed:** 2026-06-07
**Requires approval:** NO

## Source References
- Audit finding: `docs/architecture/phase11_9_2_security_audit.md` § SEC-H2

## Objective
Add `*.db`, `*.sqlite`, `*.sqlite3` rules to `.gitignore` so Phase 11+ custom-named SQLite databases (jobs.db, events.db, audit.db, metrics.db) are never committed.

## Context
Current `.gitignore` only covers `db.sqlite3`. Phase 11 systems create databases with custom names. Running `git add .` would commit them, exposing all workflow state.

## Scope

### Files to create
None

### Files to modify
- `.gitignore` — add three lines after the `db.sqlite3` line

### Files to NOT touch
All `.py` files, all test files, all other config files

## Constraints
Add exactly these three lines immediately after `db.sqlite3`. Do not reorder anything else.

## Implementation Steps
1. Open `.gitignore` and find the line containing `db.sqlite3`
2. Insert immediately after it:
   *.db
   *.sqlite
   *.sqlite3
3. Verify: `grep -n "\.db\|\.sqlite" .gitignore`

## Validation
```bash
export UV_CACHE_DIR=/tmp/uv-cache
echo "test" > jobs.db
git check-ignore -v jobs.db && echo "PASS" || echo "FAIL"
rm jobs.db
```

## Success Criteria
- [ ] `.gitignore` contains `*.db`
- [ ] `git check-ignore jobs.db` returns a match
- [ ] No source files modified

## Depends On
None

## Blocks
None

## Commit Message
```
chore(security): extend .gitignore for Phase 11+ database files (TASK-002)
```
