---
name: fix-and-verify
description: Fix a scoped defect, run relevant verification, and report the exact change, proof, and remaining risk.
---

# Skill: Fix and Verify

## Name
fix-and-verify

## Description
A targeted debugging and remediation skill designed to fix specific test failures, warnings, or audit issues with minimal code footprint.

## Goal
Resolve a targeted bug or warning while introducing zero unrelated changes or refactoring, validating the fix against the specific test first and then the full test suite.

## Procedure
1. **Identify the Issue**: Locate the failing test case, warning trigger, or audit finding in the codebase.
2. **Reproduce**: Run the specific test class or test file using a targeted command (e.g., `uv run pytest tests/jobs/test_claiming.py -k test_name`).
3. **Plan the Fix**: Formulate the smallest possible logical change to resolve the issue.
4. **Implement**: Apply the targeted fix. Ensure no unrelated lines or systems are touched.
5. **Verify Targeted**: Run the specific test case again to confirm the fix works.
6. **Verify System-Wide**: Run the full test suite (`uv run pytest`) to ensure no regressions were introduced.
7. **Document**: Record the root cause, description of the fix, and verification commands.

## Constraints
- **Strict Scope**: Do not clean up unrelated code or perform formatting changes outside of the target file/function.
- **No Refactoring**: Keep the change minimal and focused. Do not rewrite surrounding logic.

## Output Format
A summary of the fix returned to the user:
- **Issue**: Description of the bug, warning, or audit finding.
- **Root Cause**: Explanation of why the issue occurred.
- **Resolution**: Code diff or explanation of the changes made.
- **Verification Summary**: Commands executed and verification output (confirming targeted test and full test suite passed).
