# SKILL: drift-check
## Trigger: `$drift-check`

Read this file completely before executing.

---

## PURPOSE

Verify that the project has not drifted from its goals, architecture, and constraints.

This is a READ-ONLY skill. It produces a drift report. It changes nothing.
Run this after any large phase, before major decisions, or whenever something feels off.

---

## WHAT "DRIFT" MEANS

Drift is when the codebase, task queue, or recent work moves away from:

1. **Goal drift** — Work that doesn't serve the primary mission
   (reliable, source-grounded educational content pipeline for ML/AI students)

2. **Architecture drift** — Code that violates the declared execution path
   (bypassing WorkflowActionExecutor, UI accessing repositories directly, etc.)

3. **Scope drift** — A task touched files it wasn't supposed to touch

4. **Complexity drift** — New dependencies, new abstractions, or new patterns
   that weren't justified by a task card

5. **Quality drift** — Test count dropped, coverage dropped, type hints removed

6. **Security drift** — A new secret surface was introduced, or a security
   finding from an audit was silently abandoned

---

## EXECUTION SEQUENCE

### Step 1 — Load the project's stated goals

Read in order:
1. `docs/project-context.md` — primary mission and long-term vision
2. `AGENTS.md` — architectural rules and frozen scopes
3. `CLAUDE.md` — coding standards and constraints
4. `TASK_SPEC.md` — current project state and milestone

Extract and note:
- The stated primary goal (one sentence)
- All frozen scopes listed in AGENTS.md § 8
- All DO NOT rules from AGENTS.md § 3

---

### Step 2 — Read recent work history

```bash
# Last 20 commits
git log --oneline -20

# Files changed in the last 10 commits
git log --name-only --oneline -10
```

Read `WORK_QUEUE.md` — review all tasks marked DONE.

---

### Step 3 — Run integrity checks

**Check A — Test count**
```bash
uv run python -m pytest --tb=short -q 2>&1 | tail -3
```
Compare to the baseline in `TASK_SPEC.md`. Flag if lower.

**Check B — Frozen scope integrity**
```bash
# Check if frozen model files were recently modified
git log --oneline -- src/content_creation/models/
git log --oneline -- prompts/
git log --oneline -- docs/schema.md
```
Flag any commit that modified a frozen file without a recorded approval.

**Check C — Secret hygiene**
```bash
# Check for hardcoded key patterns in Python files
git grep -r "AIza[A-Za-z0-9_-]\{10,\}" -- "*.py" "*.yaml" "*.yml" "*.json" "*.md"

# Check for non-empty fallbacks on env var reads
git grep -n 'os\.environ\.get.*GEMINI.*"[A-Za-z0-9]' -- "*.py"

# Confirm .env is not tracked
git ls-files .env
```

**Check D — Architecture boundary**
```bash
# Streamlit imports in non-UI layers (should return nothing)
git grep -r "import streamlit" -- src/content_creation/ \
  --exclude-dir=ui --exclude-dir=app --exclude-dir=streamlit

# Direct repository access from UI layer (pattern scan)
git grep -r "Repository\|Storage\(\)" -- src/content_creation/ui/ 2>/dev/null || true
```

**Check E — Dependency creep**
```bash
# Show current dependencies vs last known good state
cat pyproject.toml | grep -A 20 "\[project\]" | grep "dependencies" -A 15
```
Flag any new dependency not referenced in a task card.

**Check F — Open issues abandoned**

Read `docs/backlog/issues.md`.
Flag any CRITICAL or HIGH issue that has been OPEN for more than 14 days
without a corresponding PENDING or IN_PROGRESS task in `WORK_QUEUE.md`.

---

### Step 4 — Check WORK_QUEUE alignment

Read `WORK_QUEUE.md`.

For each recent DONE task: does the work it describes align with the project goal?
For PENDING tasks: are they ordered sensibly (CRITICAL before LOW)?
For BLOCKED tasks: has the blocker been noted and is someone tracking it?

---

### Step 5 — Produce the drift report

Output in this exact format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$drift-check REPORT
Date: <today>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRIMARY GOAL:
"<the one-sentence mission from project-context.md>"

━━ CHECK RESULTS ━━━━━━━━━━━━━━━━━━━━

A  Test Count:         PASS | DRIFT  (NNN vs baseline NNN)
B  Frozen Scopes:      PASS | DRIFT  (<details if drift>)
C  Secret Hygiene:     PASS | DRIFT  (<details if drift>)
D  Architecture:       PASS | DRIFT  (<details if drift>)
E  Dependencies:       PASS | DRIFT  (<details if drift>)
F  Open Issues:        PASS | DRIFT  (<details if drift>)
Q  Queue Alignment:    PASS | DRIFT  (<details if drift>)

━━ OVERALL ━━━━━━━━━━━━━━━━━━━━━━━━━

STATUS: ON TRACK | MINOR DRIFT | SIGNIFICANT DRIFT | CRITICAL DRIFT

━━ FINDINGS ━━━━━━━━━━━━━━━━━━━━━━━━

[Only populated if DRIFT found]

DRIFT-001 [CRITICAL|HIGH|MEDIUM|LOW]
What drifted: <description>
Where:        <file or commit reference>
Risk:         <what breaks or degrades if unaddressed>
Recommended:  <one-sentence fix — do NOT implement, only recommend>

━━ RECOMMENDED NEXT ACTIONS ━━━━━━━━

[Only if drift found]
1. <action> — addresses DRIFT-001
2. <action> — addresses DRIFT-002

If no drift: "Project is on track. No action required."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Step 6 — If CRITICAL drift found

Do not silently continue. Add to `docs/backlog/issues.md`:

```markdown
## ISSUE-NNN: <drift title>
**Severity:** CRITICAL
**Identified:** <date>
**Source:** $drift-check run on <date>
**Status:** OPEN

<drift description and recommended resolution>
```

---

## WHAT NOT TO DO

- Do NOT fix any drift — only report it
- Do NOT modify any source file
- Do NOT commit anything
- Do NOT suppress findings to avoid uncomfortable reports
- Do NOT mark tests as passing if they are not
