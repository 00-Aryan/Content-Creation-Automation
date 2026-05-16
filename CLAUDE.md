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
1. `docs/architecture.md`
2. `docs/schema.md`
3. `docs/prompting-rules.md`
4. `docs/voice-and-style.md`
5. `docs/project-context.md`

## Current Pipeline State

- **Weeks 1–4** of the roadmap are implemented: ingestion through scoring, brief generation, multi-format generators, local asset storage, manifests, posting planner, dry-run validation, and analytics metadata.
- **Week 4 complete.**
- **125 tests** passing with `uv run python -m pytest`.
- **Generators:** `generate_brief()` in `generation/brief.py`; class-based `ScriptGenerator`, `CarouselGenerator`, `NewsletterGenerator`, and `ThumbnailGenerator` in `generation/script.py`, `generation/carousel.py`, `generation/newsletter.py`, and `generation/thumbnail.py` (Gemini JSON → Pydantic models, shared retry pattern).
- **Manifest system:** `ManifestBuilder` and `TopicManifest` / `AssetEntry` (`src/content_creation/manifest.py`, `models/manifest.py`) — per-topic asset index and `ready_for_planner`.
- **Analytics layer:** `PostAnalytics`, `PerformanceSnapshot` (`models/analytics.py`) — post-level metrics placeholders linked to scheduled assets.
- **Dry-run workflow:** `DryRunValidator`, `DryRunReport` (`planning/dryrun.py`, `models/dryrun.py`) — pre-publish validation for a weekly calendar.
- **Posting planner:** `PostingPlanner`, `WeeklyCalendar` (`planning/planner.py`, `models/calendar.py`) — 7-day selection from approved manifests using `config/publishing.yaml`.
- **CLI commands (see `cli.py`):** `collect`, `status`, `list-topics`, `validate-items`, `score-topics`, `review-scores`, `scoring-dashboard`, `generate-briefs`, `build-manifest`, `build-all-manifests`, `plan-week`, `dry-run`, `init-analytics`, `update-analytics`, `review-assets`.

## Week 5 Scope

**Frozen unless explicitly approved:** all Pydantic models under `src/content_creation/models/`, all generator implementations and `generation/__init__.py` exports, all files under `prompts/`, all planning modules (`planning/`), the analytics layer, and all of `docs/` **except** when a schema or documentation change is explicitly approved and coordinated with model updates (schema edits always go through `docs/schema.md` plus dependent code).

**Allowed (future work only):** RAG module, platform connectors, web dashboard.

## Coding Expectations
- Always provide a plan before implementing complex logic.
- Add tests for all new functionality in `tests/`.
- Ask for clarification if a schema field or architectural decision is ambiguous.
- Do not implement features outside the current phase (see `docs/project-context.md` and `TASK_SPEC.md`).
- Use `datetime.now(timezone.utc)` (timezone-aware UTC), not `datetime.utcnow()`, in new or touched code.
- New generators must follow the **`CarouselGenerator` class pattern**: `__init__(api_key, prompt_dir)`, `self._client`, prompt path(s), `generate(brief) -> model`, Gemini `gemini-2.5-flash`, retry/backoff on 429, JSON parse and `ReviewStatus` mapping where applicable.
- New storage methods must follow existing **`save_brief` / `list_briefs`** conventions: explicit `data/<kind>/` paths, JSON read/write, logging on failure, types aligned with models.
