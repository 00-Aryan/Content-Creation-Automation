# SKILL: code-review (merged from architecture-review + code-review)
## Triggers: $code-review <file-or-module-path>

## PURPOSE
Review a file or module for correctness, architecture boundaries, security,
and code quality. Read-only — produces a report, modifies nothing.

## STEP 1 — SETUP
export UV_CACHE_DIR=/tmp/uv-cache

## STEP 2 — READ THE TARGET
Read the file or module path provided.
Also read AGENTS.md for frozen scope and architectural rules.
Also read CLAUDE.md for coding standards.

## STEP 3 — REVIEW CHECKLIST
For each file reviewed, check:
□ Does it respect the execution path (WorkflowActionExecutor → ActionAvailabilityEngine → ...)?
□ Are there any direct repository/service calls from the UI layer?
□ Are Pydantic models modified without corresponding test updates?
□ Type hints present on all public methods?
□ No environment variable values hardcoded?
□ No API keys or credentials in any string literal?
□ Are exceptions logged safely (no credential leak risk)?
□ SOLID principles — is the class doing one thing?
□ Test exists for this module?

## STEP 4 — REPORT
Produce a review with:
- FINDINGS: list of issues (CRITICAL/HIGH/MEDIUM/LOW) with file:line reference
- CLEAN: list of checks that passed
- RECOMMENDATION: one sentence — approve, approve with notes, or request changes

## WHAT NOT TO DO
Never modify any file. Never suggest changes outside the reviewed module.
