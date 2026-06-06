---
name: branch-review
description: Reviews feature branches for scope compliance, modularity, testability, and schema adherence in the content-creation repository.
---

## When to use
- After implementing a feature branch
- Before merging to main/develop
- When debugging unexpected behavior
- When reviewing AI-generated code

## Review checklist
1. **Scope compliance**: Only Week N logic, no future features
2. **Schema discipline**: No undocumented fields, no drift
3. **Modularity**: Clear separation of concerns
4. **Testability**: Unit tests for pure functions, integration tests for pipelines
5. **Traceability**: Full audit trail from raw to scored/output
6. **Error isolation**: Failures point to specific stages
7. **Config-driven**: No hardcoding outside tests

## Output format
Always use the 9-section review format:
1. Branch summary
2. Critical issues
3. Medium issues
4. Modularity review
5. Scope compliance
6. Schema/traceability
7. Test coverage
8. Merge recommendation
9. Exact revisions

## Invocation
Use `/branch-review` in any feature branch context.
