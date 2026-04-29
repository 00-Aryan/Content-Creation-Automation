# CLAUDE.md - Project Instructions

## Project Overview
`content-creation` is a source-grounded content factory for ML/AI students. It prioritizes factual accuracy and student relevance over volume.

## Core Rules
- **Anti-Hallucination:** Never invent facts. Use `unknown` for missing data.
- **Traceability:** Maintain provenance from source to final asset.
- **Schema Discipline:** Strictly adhere to `docs/schema.md`.
- **Branch Isolation:** Work within the assigned feature branch scope.
- **Style:** Clean, typed Python code. Use `logging` for observability.

## Files to Read First
1. `docs/project-context.md`
2. `docs/schema.md`
3. `docs/prompting-rules.md`

## Coding Expectations
- Always provide a plan before implementing complex logic.
- Add tests for all new functionality in `tests/`.
- Ask for clarification if a schema field or architectural decision is ambiguous.
- Do not implement features outside the current phase (see `docs/project-context.md`).
