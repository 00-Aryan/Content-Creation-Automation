# TASK-040: Define platform content contracts

**Phase:** 12.3 — Platform-Aware Content
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-13
**Completed:** 2026-06-13
**Requires approval:** YES

---

## Traceability

- GitHub issue: GitHub issue #5
- Phase target: 12.3 — Platform-Aware Content
- Source: GitHub issue #5

---

## Objective

Define precise output contracts before implementing platform generators.

---

## Context

This task defines platform-specific content contracts to ensure generated content meets format, style, and quality constraints before ingestion. It establishes schemas for LinkedIn and YouTube Shorts. This enables platform-aware generation and validation, ensuring downstream publishing tools can consume assets without formatting errors.

---

## Scope

### Files to create

- docs/platform/platform-content-contracts.md
- docs/platform/linkedin-content-contract.md
- docs/platform/youtube-shorts-content-contract.md
- docs/platform/source-grounding-contract.md
- docs/platform/platform-quality-gates.md
- docs/phase-12.3-platform-contracts.md

### Files to modify

- docs/project/CURRENT_STATE.md
- docs/project/NEXT_ACTION.md
- docs/project/PHASES.md
- docs/project/ROADMAP.md
- docs/project/SPRINT_PLAN.md
- docs/project/DECISION_LOG.md
- docs/project/BACKLOG.md
- WORK_QUEUE.md

### Files to NOT touch

- src/
- tests/
- prompts/
- data/
- pyproject.toml
- uv.lock
- .github/workflows/
- docs/tasks/task_005.md

---

## Constraints

Do not modify Python code or write tests. Do not touch prompts or schemas outside of the listed docs. Keep all contracts aligned with the roadmap and SDLC standard.

---

## Implementation Steps

1. Create the platform content contract directory and write the core contract document detailing shared requirements.
2. Define the LinkedIn content contract including character limits, tone, and formatting constraints.
3. Define the YouTube Shorts content contract specifying scripts, thumbnails, duration, and structure.
4. Define the source grounding contract ensuring trace logging requirements for all claims.
5. Create the platform quality gates document listing checks required before assets are ready for export.
6. Create the phase summary detailing the platform contracts defined.
7. Update project tracking documentation: CURRENT_STATE.md, NEXT_ACTION.md, PHASES.md, ROADMAP.md, SPRINT_PLAN.md, DECISION_LOG.md, BACKLOG.md, and WORK_QUEUE.md.

---

## Validation

```bash
# Baseline test suite — must match or exceed before-count
uv run python -m pytest --tb=short -q 2>&1 | tail -3

# Task-specific verification
# Verify all created documents exist
test -f docs/platform/platform-content-contracts.md
test -f docs/platform/linkedin-content-contract.md
test -f docs/platform/youtube-shorts-content-contract.md
test -f docs/platform/source-grounding-contract.md
test -f docs/platform/platform-quality-gates.md
test -f docs/phase-12.3-platform-contracts.md

# Verify tracked project files are modified
git status --short docs/project/
```

---

## Success Criteria

- [ ] Platform content contracts are fully defined in docs/platform/
- [ ] Mappings and gates are documented for both LinkedIn and YouTube Shorts
- [ ] Project documentation is updated to reflect Phase 12.3 progress
- [ ] Test suite passes at baseline count (no regression)
- [ ] No files outside declared scope were modified

---

## Depends On

TASK-036

---

## Blocks

None

---

## Commit Message

```
docs(platform): define platform content contracts for Phase 12.3 (TASK-040)
```

---

## Notes

None
