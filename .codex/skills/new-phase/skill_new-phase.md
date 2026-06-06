# SKILL: new-phase
## Trigger: `$new-phase`

Read this file completely before executing.

---

## PURPOSE

You will be given a phase description — either inline text or a reference to a phase plan document.

Your job is to:
1. Parse it into individual, atomic, executable task cards
2. Write each task to `docs/tasks/task_NNN.md`
3. Add all tasks to `WORK_QUEUE.md` in dependency order
4. Update `docs/backlog/issues.md` with any issues or risks identified
5. Report what was created

This skill creates documentation only. It does NOT execute any task.
Do NOT modify any source code. Do NOT run any tests.

---

## INPUT FORMATS

You accept the phase description in any of these forms:

**Form A — Inline text** (user pastes description after trigger):
```
$new-phase
Phase 11.9.3 — CI/CD and Security Remediation

Tasks:
1. Create .env.example
2. Add *.db to .gitignore
3. Add GitHub Actions secret scan workflow
...
```

**Form B — File reference**:
```
$new-phase docs/architecture/phase11_9_3_plan.md
```

**Form C — Audit reference** (create tasks from an audit document):
```
$new-phase from-audit docs/architecture/phase11_9_2_security_audit.md
```
When given an audit, create one task per CONFIRMED finding (🔴) in priority order.
Skip NOTED (🟡) and UNVERIFIED (⚠️) findings — they need human verification first.

---

## EXECUTION SEQUENCE

### Step 1 — Read existing queue

Open `WORK_QUEUE.md`.
Find the highest existing task number (e.g., TASK-007).
All new tasks start from the next number (e.g., TASK-008).

---

### Step 2 — Read project context

Open these files to understand constraints before writing tasks:
- `AGENTS.md` — rules and frozen scopes
- `TASK_SPEC.md` — current project state
- `docs/project-context.md` — long-term goals

---

### Step 3 — Decompose the phase into atomic tasks

Each task must be:
- **Atomic** — one clear deliverable, not a list of things
- **Bounded** — explicit file scope
- **Verifiable** — has a test or check that confirms success
- **Small** — ideally under 2 hours of work for a senior developer

If a phase description contains a large task, split it. Example:
"Add CI/CD pipeline" → split into:
- TASK-008: Create `.github/workflows/tests.yml` (run pytest on push)
- TASK-009: Add Gitleaks secret scanning step to existing workflow
- TASK-010: Add pre-commit config

---

### Step 4 — Write each task card

Create `docs/tasks/task_NNN.md` for each task using the template below exactly.
Fill every section. Do not leave sections empty.

```markdown
# TASK-NNN: <Short imperative title, max 60 chars>

**Phase:** <phase number, e.g., 11.9.3>
**Status:** PENDING
**Priority:** CRITICAL | HIGH | MEDIUM | LOW
**Created:** <today's date YYYY-MM-DD>
**Completed:** —
**Requires approval:** YES | NO

## Source References
<!-- Link back to where this task originated -->
- Phase plan: `<path>` § <section>
- Audit finding: `<path>` § <finding ID> (if applicable)
- Backlog item: `docs/backlog/remediation_backlog.md` § TASK-NNN (if applicable)

## Objective
<!-- One sentence: what this task achieves and why it matters -->

## Context
<!-- 2-4 sentences: why this task exists, what problem it solves, what it connects to -->

## Scope

### Files to create
<!-- List exact paths, or write "None" -->

### Files to modify
<!-- List exact paths with what changes, or write "None" -->

### Files to NOT touch
<!-- Be specific. List modules, directories, or patterns that are out of scope -->
- All `.py` source files (unless this task explicitly modifies one)
- All test files
- All Pydantic models (`src/content_creation/models/`)
- All prompt templates (`prompts/`)

## Constraints
<!-- Rules specific to this task that the agent must follow -->

## Implementation Steps
<!-- Numbered, concrete steps. Specific enough that an agent cannot misinterpret them -->
1. 
2. 
3. 

## Validation
<!-- Commands to run. Must be copy-pasteable and produce clear pass/fail output -->
\```bash
# Run full test suite — must match or exceed baseline
uv run python -m pytest --tb=short -q 2>&1 | tail -3

# Task-specific check
<specific verification command>
\```

## Success Criteria
<!-- Bullet list of what DONE looks like. Agent checks each one before marking DONE -->
- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] Test suite passes at baseline count

## Depends On
<!-- Task IDs that must be DONE before this can start, or "None" -->

## Blocks
<!-- Task IDs that cannot start until this is DONE, or "None" -->

## Commit Message
\```
type(scope): description (TASK-NNN)
\```

## Notes
<!-- Optional: risks, known complexity, things to watch for -->
```

---

### Step 5 — Update WORK_QUEUE.md

Append all new tasks to `WORK_QUEUE.md` in dependency order (tasks with no dependencies first, then tasks that depend on them).

For each task, add a row to the queue table:

```markdown
| TASK-NNN | <title> | PENDING | <priority> | <depends_on> | `docs/tasks/task_NNN.md` |
```

---

### Step 6 — Update docs/backlog/issues.md

For each issue, risk, or technical debt item identified while decomposing the phase, add an entry to `docs/backlog/issues.md`:

```markdown
## ISSUE-NNN: <title>
**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Identified:** <date>
**Source:** <where this was found>
**Status:** OPEN

<description of the issue, its risk, and suggested resolution>
```

---

### Step 7 — Report

Output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$new-phase COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase:         <phase name>
Tasks created: TASK-NNN through TASK-NNN (<count> tasks)
Issues added:  <count> to docs/backlog/issues.md
Queue updated: WORK_QUEUE.md

Task breakdown:
  TASK-NNN — <title> [CRITICAL] depends on: None
  TASK-NNN — <title> [HIGH]     depends on: TASK-NNN
  ...

Run $run-next-task to begin execution.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## WHAT NOT TO DO

- Do NOT execute any task — only create the task cards
- Do NOT modify any source code
- Do NOT run tests (this is documentation-only work)
- Do NOT combine multiple phase objectives into one task card
- Do NOT write vague implementation steps — every step must be actionable
- Do NOT leave "Depends On" or "Blocks" empty — write "None" explicitly
