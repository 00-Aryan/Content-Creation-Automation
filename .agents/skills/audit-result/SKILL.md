# Skill: Audit Result

## Name
audit-result

## Description
Audits the results and deliverables of the most recently executed development phase or task to ensure schema, testing, and architectural integrity.

## Goal
Verify that all phase claims are true, no regressions are introduced, and architectural boundaries are fully respected.

## Procedure
1. **Gather Deliverables**: Identify all files created, modified, or deleted during the phase by reading the phase report and running `git status`.
2. **Review Code & Architecture**: Verify that new code does not breach the core architectural boundaries set in `AGENTS.md` (e.g., UI directly accessing repositories, worker calling services directly).
3. **Run Validation Checks**:
   - Run the linting checks (`uv run black --check src tests`, etc.).
   - Run the full test suite (`uv run pytest`) to ensure all tests are green.
4. **Compare Claims**: Inspect the contents of modified files and verify that the changes correspond exactly to the phase requirements and report claims.
5. **Report Violations**: Document any architecture, linting, or functional mismatches, and list remaining risks.

## Constraints
- **Independent Stance**: Be objective. Do not assume the phase was implemented correctly because a test passed.
- **Strict Boundaries**: Check that event subscribers do not mutate state and secrets are not logged or stored.

## Output Format
A markdown report under `docs/audit/` or returned directly to the user:
- **Audit Summary**: High-level result (PASS/FAIL).
- **Scope Alignment**: Verification of whether the changes matched the phase scope.
- **Architectural Boundary Check**: Specific confirmation of the 9 boundaries from `AGENTS.md`.
- **Findings & Mismatches**: List of any gaps or issues found.
- **Action Plan**: Recommendations for resolving violations.
