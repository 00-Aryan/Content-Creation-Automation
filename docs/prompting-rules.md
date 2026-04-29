# Prompting Rules & Guardrails

This document defines how AI coding agents (Claude Code, Gemini CLI) should behave when working in this repository.

## Core Mandates
- **Plan Before Action:** Always use the appropriate "plan mode" or provide a clear strategy before making code changes.
- **Anti-Assumption:** Never guess a field name, a directory path, or a configuration value. If it's not documented, ask or search.
- **Anti-Hallucination:**
    - Do not implement logic that invents source data.
    - If a source field is missing, use `unknown`.
    - Content generation prompts must strictly limit the AI to the provided source text.
- **Traceability:** Maintain the link between raw source data and normalized/generated outputs at every step.

## Implementation Boundaries (Week 1)
- Focus exclusively on:
    - Repository skeleton and CLI.
    - Source collectors (RSS/Atom).
    - Normalization to `TopicItem` schema.
    - Local storage management.
- **Do not** implement scoring, summarization, or script generation yet.

## Behavior with Missing Data
- If a mandatory field cannot be found during normalization, log it as a warning and mark the field as `unknown`.
- Do not "clean" or "hallucinate" missing publication dates; use the current date only as a fallback for `ingested_at`, not `published_at`.

## Expectations for Code
- **Tests:** Every new module or collector must have a corresponding test in `tests/`.
- **Logging:** Use Python's `logging` module. Log important transitions (e.g., "Fetched 5 items from arXiv", "Rejected 1 duplicate").
- **Types:** Use type hints for all function signatures and class definitions.
- **CLI:** All features must be accessible via the `content_creation.cli` entry point.

## Validation Cycle
1. **Research:** Understand the existing code and docs.
2. **Plan:** Describe what you will do.
3. **Act:** Implement the change surgically.
4. **Validate:** Run tests and verify outputs manually or via script.
