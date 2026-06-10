# TASK-001: Create `.env.example` with required environment variables

**Phase:** 11.9.3
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-05
**Completed:** —
**Requires approval:** NO

---

## Source References

- Audit finding: `docs/architecture/phase11_9_2_security_audit.md` § SEC-H1
- Backlog item: `docs/backlog/remediation_backlog.md` (High priority)
- Implementation plan: `content-factory-implementation-plan.md` § Day 1 (`.env.example` specified)

---

## Objective

Create a `.env.example` file in the repository root so contributors have a documented template of all required environment variables with no actual values.

---

## Context

The `content-factory-implementation-plan.md` specifies `.env.example` as a Day 1 deliverable, but the file was never created. Without it, anyone cloning the repository has no canonical reference for what environment variables the project requires. This creates risk: developers either miss required variables and face confusing errors, or — worse — add fallback key values directly to source code to avoid the mystery.

This is a documentation-only task. It does not change any source code.

---

## Scope

### Files to create
- `.env.example` (repository root)

### Files to modify
- None

### Files to NOT touch
- All `.py` source files
- All test files (`tests/`)
- All Pydantic models (`src/content_creation/models/`)
- All prompt templates (`prompts/`)
- `CLAUDE.md`, `GEMINI.md`, `README.md` (do not update these in this task)

---

## Constraints

- Do NOT include any actual API key values — only the variable name and `=` with no value
- Do NOT add quotes around empty values
- Comments should explain where to get each key
- Future keys (not yet used) should be commented out with `#`

---

## Implementation Steps

1. Create `.env.example` in the repository root with this exact content:

```
# Content Creation Automation — Required Environment Variables
# Copy this file to .env and fill in your values
# .env is gitignored and will never be committed

# ── Required ──────────────────────────────────────────────────────────────────

# Gemini API key — get yours free at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=

# ── Future (not yet used — uncomment when needed) ─────────────────────────────

# OpenRouter API key (Phase 3: alternative LLM provider)
# OPENROUTER_API_KEY=

# Groq API key (Phase 3: fast inference alternative)
# GROQ_API_KEY=

# Platform publishing keys (Phase 3: direct API posting)
# TWITTER_API_KEY=
# TWITTER_API_SECRET=
# LINKEDIN_ACCESS_TOKEN=
# YOUTUBE_API_KEY=
```

2. Verify the file exists and contains no actual key values:
```bash
cat .env.example | grep -v "^#" | grep "=" | grep -v "=$" && echo "WARNING: found non-empty values" || echo "PASS: all values empty"
```

---

## Validation

```bash
# Confirm file was created
test -f .env.example && echo "PASS: .env.example exists" || echo "FAIL: missing"

# Confirm no actual key values (no non-empty assignments outside comments)
python3 -c "
lines = open('.env.example').readlines()
violations = [l.strip() for l in lines if '=' in l and not l.strip().startswith('#') and l.strip().split('=',1)[1].strip()]
print('FAIL:', violations) if violations else print('PASS: no values committed')
"

# Confirm baseline test suite is unchanged
uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

---

## Success Criteria

- [ ] `.env.example` exists in repository root
- [ ] All `=` assignments have empty values (nothing after `=`)
- [ ] `GEMINI_API_KEY=` is present and uncommented
- [ ] Future keys are present but commented out
- [ ] Test suite passes at baseline count (125 passed)
- [ ] No source files were modified

---

## Depends On

None

---

## Blocks

None currently. Future TASK: update README.md to reference `.env.example` (separate task).

---

## Commit Message

```
docs(security): add .env.example template with required env vars (TASK-001)
```

---

## Notes

This is the simplest task in the security remediation backlog. Zero risk. Pure documentation.

---

## Phase 11.9.4 Drift-Check (TASK-013)
**Run date:** 2026-06-10
**Overall status:** ON TRACK

### Findings
None — project on track

### Test count at phase close
966 passed
