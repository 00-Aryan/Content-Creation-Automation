# Coding Standards

## Architecture Boundaries

- UI routes through existing client/application/workflow layers.
- No direct repository/service access from UI pages.
- Domain, workflow, application, and UI responsibilities must remain separate.

## Python Standards

- Prefer typed functions for new code.
- Keep functions small and testable.
- Avoid broad `except Exception` unless the error is logged and surfaced safely.
- Do not silently swallow errors.

## Testing Standards

- Every bug fix gets a regression test where practical.
- Test both success and failure paths.
- Preserve or increase full-suite baseline.
- Use targeted tests before full tests.

## Error Handling

- Operator-facing messages must be readable.
- Internal errors may be logged but not exposed raw in UI.
- Fallbacks must be explicit and test-covered.

## Content Quality

- Generated content must be source-grounded.
- No structural marker leaks.
- No placeholder pollution.
- No generic platform-agnostic output after Phase 12.3.
