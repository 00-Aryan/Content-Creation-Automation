---
name: content-factory-workflow
description: Guides the complete Week N implementation workflow for content-creation.
---

## Week N pattern
1. `/branch-review` current state
2. Implement one pipeline stage
3. `/test-planner` for new stage
4. `/modular-refactor` if needed
5. `/branch-review` before merge

## Schema evolution
- Never add undocumented fields
- Use `unknown` for missing data
- Preserve raw payloads always
- Make scoring deterministic and configurable

## Invocation
`/content-factory-workflow week=N` or `/content-factory-workflow stage=ingestion|scoring|briefs`
