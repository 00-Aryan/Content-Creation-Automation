# SDLC Standard

## 1. Requirements

- Every phase starts with a clear objective.
- Every task has a narrow scope.
- Every task defines files to modify and files to create.
- No implementation begins without acceptance criteria.

## 2. Design

- Respect architecture boundaries.
- UI must not access repositories or services directly.
- Workflow changes must preserve state protection.
- Generation changes must preserve source grounding.

## 3. Implementation

- Small, isolated tasks.
- No opportunistic refactors.
- No unrelated cleanup inside feature tasks.
- Deterministic behavior where possible.

## 4. Verification

- Run targeted tests.
- Run full suite.
- Document evidence.
- Do not accept lower test baseline.

## 5. Release

- Commit one task at a time.
- Use clear commit messages.
- Push only after validation.
- Update project knowledge base.

## 6. Retrospective

- Record bugs found.
- Record architecture decisions.
- Convert lessons into future guardrails.
