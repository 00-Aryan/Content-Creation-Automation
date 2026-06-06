---
name: run-phase
description: Execute a defined project phase from the roadmap while preserving scope, constraints, validation, and audit trail.
---

# Skill: Run Phase

## Name
run-phase

## Description
Executes a single approved development phase or feature scope exactly as described in the requirements.

## Goal
Implement the changes specified for the current phase, verify correctness, and produce a phase report without introducing external scope creep.

## Procedure
1. **Load Instructions**: Read the root-level `AGENTS.md` and phase specifications (e.g., `TASK_SPEC.md` or implementation plans).
2. **Context Gathering**: Read the relevant documentation in `docs/` and inspect files related to the target scope.
3. **Plan Formulation**: Document the proposed implementation steps inside the workspace before starting code changes.
4. **Execution**: Apply surgical edits to the codebase. Ensure code is typed, clean, and adheres to the architecture.
5. **Validation**: Run the full test suite (`uv run pytest`) and check for lint or type errors.
6. **Reporting**: Document all changes and validations in a phase report file.
7. **Halt**: Stop execution and request user review.

## Constraints
- **Zero Scope Creep**: Do not modify files outside the approved phase scope.
- **No Refactoring**: Avoid refactoring existing systems unless explicitly instructed.
- **Dependencies**: Do not introduce any new external packages without approval.

## Output Format
A markdown report under `docs/architecture/` or as requested by the user, formatted as follows:
- **Findings**: Current state audit or context.
- **Files Created**: List of new files.
- **Files Modified**: List of changed files.
- **Test Results**: Output summary of the tests run.
- **Security Check**: Verification of secret hygiene and command usage.
- **Next Steps**: Handover for the next phase.
