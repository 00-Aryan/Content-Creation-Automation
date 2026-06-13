# SDLC Standard

## 1. Requirements

- Every phase starts with a clear objective.
- Every task has a narrow scope.
- Every task defines files to modify and files to create.
- No implementation begins without acceptance criteria.
- Local automation tasks should be planned using `scripts/issue-runner.sh plan`.

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
- Run agent logic non-interactively using the issue runner.

## 4. Verification

- Run targeted tests.
- Run full suite.
- Document evidence under `.runs/`.
- Do not accept lower test baseline.
- Validate scope using `scripts/issue_scope_guard.py`.

## 5. Release

- Commit one task at a time.
- Use clear commit messages defined in the task card.
- Push only after validation.
- Create automated PRs with complete validation summaries.
- Auto-merge is blocked for security, CI, architecture, and hardening changes.
- Update project knowledge base.

## 6. Retrospective

- Record bugs found.
- Record architecture decisions.
- Convert lessons into future guardrails.
