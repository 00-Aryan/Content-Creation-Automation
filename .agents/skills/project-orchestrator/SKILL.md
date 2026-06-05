# Skill: Project Orchestrator

## Name
project-orchestrator

## Description
Determines and prepares the next correct development or auditing phase based on the current project tracking state.

## Goal
Establish the next correct step of development, verify dependency completeness, identify any blocker issues or risks, and formulate the execution instructions.

## Procedure
1. **Load Context**: Read the project control rules in `AGENTS.md` and the tracking files:
   - `docs/project/CURRENT_STATE.md`
   - `docs/project/NEXT_ACTION.md`
   - `docs/project/PHASES.md`
   - `docs/project/BACKLOG.md`
   - `docs/project/RISKS.md`
   - `docs/project/TECH_DEBT.md`
2. **Analysis**:
   - Determine if the next action specified in `docs/project/NEXT_ACTION.md` matches the user's intent.
   - Cross-check against the roadmap (`docs/project/ROADMAP.md`) and status tracking (`docs/project/PHASES.md`).
   - Identify any active blockers or unresolved risks/dependencies.
3. **Planning & Preparation**:
   - Formulate the detailed execution instructions for the next phase.
   - List all target files that will require modification or creation.
4. **Update Tracking**:
   - Update `docs/project/NEXT_ACTION.md` if the target phase or details have changed or evolved.
5. **Output**: Present the recommended roadmap direction and execution details.

## Constraints
- **ReadOnly**: Do not modify application source code or tests.
- **Strict Adherence**: The next phase selection must respect state constraints and dependencies.

## Output Format
Produce a structured markdown analysis containing:
- **Selected Phase**: The ID and title of the target phase.
- **Rationale**: Why this phase is next and how it matches the current state.
- **Dependencies**: Any preceding work that must be completed.
- **Blockers**: Active issues that prevent this phase from starting.
- **Execution Prompt**: The suggested instructions to feed to the developer agent to run the phase.
- **Files to Update**: Expected target files to be modified.
