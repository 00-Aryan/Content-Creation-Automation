---
name: modular-refactor
description: Refactors code to improve modularity, testability, and error isolation.
---

## Refactoring targets
- Extract pure functions from CLI handlers
- Separate orchestration from business logic
- Move factories to dedicated modules
- Replace print() with structured logging
- Add dependency injection for testability

## Module boundaries

src/content_creation/
├── cli.py (thin orchestration only)
├── collectors/ (fetch + parse)
├── normalizers/ (transform)
├── scorers/ (score)
├── storage/ (persist)
├── models/ (schemas)
└── utils/ (logging, config)

## Invocation
`/modular-refactor file_or_module`
