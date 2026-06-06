---
name: code-review
description: Review current code changes for correctness, maintainability, test coverage, regressions, and architectural drift.
---

# Skill: Code Review

## Name
code-review

## Description
Executes a high-level senior engineering review focusing on code style, typing compliance, testing gaps, and maintainability.

## Goal
Identify areas of code complexity, missing test coverage, or maintainability bottlenecks and document them as a backlog, ensuring no behavioral modifications are introduced.

## Procedure
1. **Target Selection**: Define the directories or modules to review (e.g., `src/content_creation/workflow`).
2. **Analysis**:
   - Inspect typing completeness (type hints on all functions).
   - Evaluate code complexity (nested loops, large functions, violations of single responsibility).
   - Look for proper exception handling and correct use of time-aware UTC datetimes.
3. **Test Alignment Check**: Cross-check with test directories to ensure major functions have corresponding test coverages.
4. **Draft Backlog**: Compile improvements into a structured backlog.
5. **No Modifications**: Do NOT make code changes. Code changes must be handled in dedicated tasks.

## Constraints
- **Preserve Behavior**: Do not rewrite logic under the guise of "cleaning it up".
- **Read-Only**: This skill is strictly read-only and analytical.

## Output Format
A code review report:
- **Scope reviewed**: Module or directories analyzed.
- **Strength Analysis**: What the module does well (e.g., clean interfaces, robust tests).
- **Maintainability Backlog**: A categorized list of proposed tasks (Style, Type Hints, Coverage, Refactoring) with details of files, line numbers, and justification.
