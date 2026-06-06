---
name: phase-closeout
description: Close a project phase by verifying deliverables, tests, docs, risks, and next-phase readiness.
---

# Skill: Phase Closeout

## Name
phase-closeout

## Description
Finalizes and closes out a completed development phase by updating the project tracking system and documenting the completion.

## Goal
Verify all phase deliverables, ensure tests pass, update status tables, migrate the next action, log new risks or backlog items, and output the final phase completion summary.

## Procedure
1. **Verification**:
   - Check that a phase implementation report exists under `docs/architecture/`.
   - Verify that the test suite runs and passes (`uv run pytest`).
2. **Update Status**:
   - Update `docs/project/PHASES.md` to mark the current phase as **Completed** and record the completion date.
   - Update `docs/project/CURRENT_STATE.md` with the new project status, updated test count, and latest completed phase.
3. **Transition Next Action**:
   - Update `docs/project/NEXT_ACTION.md` with the details of the next upcoming phase.
4. **Log New Findings**:
   - Add any new backlog items identified during the phase to `docs/project/BACKLOG.md`.
   - Add any new technical debt or risks to `docs/project/TECH_DEBT.md` and `docs/project/RISKS.md`.
5. **Reporting**: Summarize the completion.

## Constraints
- **State Integrity**: Do not close a phase unless the validation tests have fully passed.
- **Scope**: Do not modify application source code during closeout operations.

## Output Format
Create a completion report summarizing:
- **Phase Closed**: Name and details of the completed phase.
- **Verification Result**: Test execution stats and validation details.
- **Tracking Changes**: List of files updated under `docs/project/`.
- **Newly Identified Items**: Summarized backlog, debt, or risks introduced/logged.
