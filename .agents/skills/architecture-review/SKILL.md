# Skill: Architecture Review

## Name
architecture-review

## Description
Performs architectural consolidation audits or targeted architectural reviews to detect boundary violations, code duplication, and alignment with engineering guidelines.

## Goal
Identify drift from architectural boundaries, boundary violations (e.g. UI layer accessing db directly), code duplication (e.g. repeated SQLite repository connection logic), update the scorecard, and populate the backlog with recommendations.

## Procedure
1. **Load Guidelines**: Read the architectural boundaries in `AGENTS.md` and standard project documents under `docs/project/`.
2. **Inspection**:
   - Trace the component boundaries (e.g. UI layer, workflow engine, repository layer).
   - Scan for violations of the strict constraints (e.g., subscribers mutating state, stream handlers containing db transactions, direct SQL queries outside repo).
   - Check file sizes and complexity of major modules (e.g., `WorkflowActionExecutor`).
3. **Scorecard Assessment**:
   - Assess components against the scorecard categories.
   - Update `docs/project/ARCHITECTURE_HEALTH.md` with updated ratings and rationales.
4. **Log Backlog & Tech Debt**:
   - Convert findings into structured issues (Critical, High, Medium, Low).
   - Append findings to `docs/project/BACKLOG.md` and/or `docs/project/TECH_DEBT.md`.
5. **Reporting**: Produce the final architecture audit report.

## Constraints
- **Zero Code Mutations**: Do not change any application behavior or write code changes. This is a read-only audit skill.
- **Objectivity**: Rate components strictly according to architectural standards and validation checks.

## Output Format
Create a structured markdown audit report containing:
- **Scope Reviewed**: Target modules and source files analyzed.
- **Findings Table**: List of issues classified by Severity (Critical/High/Medium/Low), location, and description.
- **Updated Scorecard**: Current state of the scorecard ratings.
- **Logged Actions**: Reference to newly added backlog and tech debt IDs.
