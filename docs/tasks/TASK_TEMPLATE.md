# TASK-NNN: <Short imperative title — max 60 characters>

**Phase:** <e.g., 11.9.3>
**Status:** PENDING
**Priority:** CRITICAL | HIGH | MEDIUM | LOW
**Created:** YYYY-MM-DD
**Completed:** —
**Requires approval:** YES | NO

---

## Source References
<!-- Every task must trace back to its origin. Fill all that apply. -->

- Phase plan: `docs/architecture/phaseXX_X_plan.md` § Section Name
- Audit finding: `docs/architecture/phaseXX_X_security_audit.md` § SEC-XXX
- Backlog item: `docs/backlog/remediation_backlog.md` § TASK-NNN
- Issue: `docs/backlog/issues.md` § ISSUE-NNN

---

## Objective
<!-- One sentence only. What does this task achieve and why does it matter? -->

---

## Context
<!-- 2–4 sentences. Why this task exists. What it prevents or enables. -->
<!-- What other tasks or systems does it connect to? -->

---

## Scope

### Files to create
<!-- List full paths relative to repo root, or write "None" -->

### Files to modify
<!-- List full paths relative to repo root with brief note of what changes -->
<!-- or write "None" -->

### Files to NOT touch
<!-- Be explicit. List every category that is off-limits for this task. -->
- All `.py` source files (unless explicitly listed above)
- All test files (`tests/`)
- All Pydantic models (`src/content_creation/models/`)
- All prompt templates (`prompts/`)
- All schema documentation (`docs/schema.md`)

---

## Constraints
<!-- Rules specific to this task that override or extend AGENTS.md rules. -->

---

## Implementation Steps
<!-- Numbered. Concrete. Every step is unambiguous. -->
<!-- An agent must be able to execute these without asking questions. -->

1. 
2. 
3. 

---

## Validation
<!-- Commands to confirm the task was done correctly. -->
<!-- Must be copy-pasteable. Must produce clear pass/fail output. -->

```bash
# Baseline test suite — must match or exceed before-count
uv run python -m pytest --tb=short -q 2>&1 | tail -3

# Task-specific verification
# Replace this comment with actual commands
```

---

## Success Criteria
<!-- Checkbox list. Agent checks each before marking DONE. -->

- [ ] <Specific, observable criterion 1>
- [ ] <Specific, observable criterion 2>
- [ ] Test suite passes at baseline count (no regression)
- [ ] No files outside declared scope were modified

---

## Depends On
<!-- Task IDs that must be DONE before this task can start. -->
<!-- Write "None" if this task has no prerequisites. -->

None

---

## Blocks
<!-- Task IDs that cannot start until this task is DONE. -->
<!-- Write "None" if nothing depends on this task. -->

None

---

## Commit Message
<!-- Exact message to use. Follow the format: type(scope): description (TASK-NNN) -->

```
type(scope): description (TASK-NNN)
```

---

## Notes
<!-- Optional: risks, implementation complexity, things to watch out for. -->
<!-- Also: record approvals here if Requires approval is YES. -->
<!-- Format: "Approved by: <name> on <date> — <what was approved>" -->
