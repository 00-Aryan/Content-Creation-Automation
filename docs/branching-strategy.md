# Branching Strategy

This project uses a branch-per-feature model to support parallel development and clear contracts.

## Branch Naming Convention
- `main`: Stable, production-ready code.
- `feature/[feature-name]`: Short-lived branches for specific tasks.
- `fix/[bug-name]`: Critical bug fixes.

**Examples:**
- `feature/bootstrap-project`
- `feature/source-ingestion`
- `feature/topic-scoring`

## Branch Roles
- **main:** The source of truth. All merges to `main` must pass tests and documentation review.
- **feature branches:** Where implementation happens. These should be scoped to a single module (e.g., collectors, scorers).

## Parallel Work Rules
1. **Schema First:** Schemas in `docs/schema.md` must be agreed upon before starting parallel branches that depend on them.
2. **Independent Modules:** Avoid cross-module dependencies within the same turn. If `feature/scoring` depends on `feature/ingestion`, the latter must be merged or a stable interface must be provided.
3. **Frequent Sync:** Rebase feature branches from `main` regularly to avoid large merge conflicts.

## Merge Checklist
Before merging a feature branch into `main`, ensure:
- [ ] Code follows the style guide and is properly typed.
- [ ] Tests cover the new functionality.
- [ ] Shared schemas are respected or updated (with approval).
- [ ] `docs/` are updated if architectural changes were made.
- [ ] All "anti-hallucination" rules are followed in generation logic.

## Schema Changes
- If a branch requires a schema change, it must be updated in `docs/schema.md` as part of the PR.
- Other active branches must be notified to rebase and accommodate the change.
