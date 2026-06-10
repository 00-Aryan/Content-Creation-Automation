# TASK-012: Create `docs/project-context.md` — project north star document

**Phase:** 11.9.4
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-07
**Completed:** 2026-06-10
**Requires approval:** NO

---

## Source References
- Phase: 11.9.4 Automation Validation
- Missing file identified in: `docs/backlog/issues.md` § ISSUE-D09
- Referenced by: `drift-check` skill (reads `docs/project-context.md`)

## Objective
Create `docs/project-context.md` — the project north star document that `drift-check` reads to assess goal alignment. Currently this file does not exist, so drift-check cannot perform its most important check.

## Context
The `drift-check` skill's first step is to read `docs/project-context.md` for the primary mission. This file is missing from the repo. Without it, the goal guardian has no goals to guard. This also resolves ISSUE-D09 (inconsistent maturity documentation) by creating a single source of truth for what this project is and where it's going.

## Scope

### Files to create
- `docs/project-context.md`

### Files to NOT touch
Everything else.

## Constraints
- Document the project as it actually is today — not aspirationally
- Long-term goals section must be honest about the timeline (personal tool for 2026, potential product after)
- Keep it under 80 lines — this is a reference document, not a novel

## Implementation Steps

1. Create `docs/project-context.md` with this content:

```markdown
# Project Context — Content Creation Automation Platform

## What This Is

A production-grade, source-grounded AI pipeline that transforms ML/AI research
(arXiv, RSS feeds) into educational content assets for students and ML practitioners.

Every content claim traces to a source. Every asset requires human approval.
No auto-publishing without explicit operator action. Zero hallucination tolerance.

## Primary Mission

Make the platform a reliable, low-maintenance, observable content operation
that a solo operator runs with minimal manual effort while preserving editorial
quality and source integrity.

## Current State (as of 2026-06-07)

- Pipeline: ingestion → scoring → brief → 4 generators → manifest → review → planning → analytics
- Test suite: 950 passing, 16 known pre-existing failures (SSE integration tests)
- Infrastructure: Streamlit operator console, event bus, job queue, worker daemon,
  audit trail, metrics, notifications, SSE streaming
- Security: CI/CD, secret scanning, pre-commit hooks, logging filter
- Deployment: Render (content-creation-automation.onrender.com)

## Architecture Invariants (never change without explicit decision)

- All actions go through WorkflowActionExecutor → ActionAvailabilityEngine → ReviewTransitionEngine
- UI layer never accesses repositories or services directly
- No auto-publishing — human approval required at every asset
- Source grounding is non-negotiable — every claim must trace to input content
- Local-first data storage (data/ directory, gitignored)

## Near-Term Goals (2026)

1. Green test suite — fix 16 SSE failures → 0 failures
2. Observability — health endpoints, structured logs, operator diagnoses without code
3. Operator Console V2 — web dashboard replacing CLI for daily use
4. FastAPI layer — clean API boundary between UI and domain

## Long-Term Goals (2027+, conditional on performance)

1. Platform publishing — LinkedIn first, Twitter later
2. Image generation — Gemini for thumbnail creation
3. RAG deduplication — avoid covering the same topics repeatedly
4. Multi-language content generation
5. If the platform performs exceptionally: explore freelance/product path

## What Success Looks Like

The operator spends 10 minutes per week: reviews approved content in a browser,
clicks publish. The pipeline handles everything else autonomously and reliably.
```

## Validation

```bash
test -f docs/project-context.md && echo "PASS: file exists" || echo "FAIL"
wc -l docs/project-context.md | awk '{if ($1 <= 80) print "PASS: under 80 lines"; else print "FAIL: too long"}'
grep -q "Primary Mission" docs/project-context.md && echo "PASS: mission present" || echo "FAIL"
grep -q "Architecture Invariants" docs/project-context.md && echo "PASS: invariants present" || echo "FAIL"
```

## Success Criteria
- [ ] `docs/project-context.md` exists
- [ ] Contains Primary Mission, Architecture Invariants, Near-Term Goals
- [ ] Under 80 lines
- [ ] No source files modified

## Depends On
None

## Blocks
None

## Commit Message
```
docs(context): create project-context.md as north star for drift-check and planning (TASK-012)
```