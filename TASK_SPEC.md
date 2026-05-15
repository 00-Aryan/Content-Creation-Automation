# TASK_SPEC: Post–Week 3 Project State

## Status

- **Week 1:** Complete (ingestion, collectors, staged/scored storage, topic models).
- **Week 2:** Complete (scoring engine and config, validation, brief generation via Gemini, scoring-related CLI).
- **Week 3:** Complete (voice and style documentation, multi-format generators, manifest builder, extended storage and models).
- **Week 4:** Not started.
- **Current test count:** 81 passing (`uv run python -m pytest`).
- **Current branch:** `week2-feature-planning` (rename or rebase when Week 4 work starts if this no longer matches active development).

## Week 3 Deliverables (completed)

Source layout as implemented today (one line each):

**Generation (`src/content_creation/generation/`)**

- `brief.py` — `generate_brief()` for educational briefs from scored topics (Gemini, retries).
- `script.py` — `ScriptGenerator`: short-video / carousel / newsletter prompt paths, Gemini, `Script` output.
- `carousel.py` — `CarouselGenerator`: `carousel.md`, Gemini, `Carousel` / `CarouselSlide` output.
- `newsletter.py` — `NewsletterGenerator`: `newsletter.md`, Gemini, `Newsletter` output.
- `thumbnail.py` — `ThumbnailGenerator`: `thumbnail.md`, Gemini, `ThumbnailPrompt` output with fallback fields on failure.
- `__init__.py` — exports `ScriptGenerator`, `ThumbnailGenerator`, `CarouselGenerator`, `NewsletterGenerator`.

**Models (`src/content_creation/models/`)**

- `brief.py` — `Brief`, `ReviewStatus`.
- `script.py` — `Script` (format literals, review status).
- `carousel.py` — `Carousel`, `CarouselSlide`.
- `newsletter.py` — `Newsletter`, `NewsletterSection`.
- `thumbnail.py` — `ThumbnailPrompt`.
- `manifest.py` — `TopicManifest`, `AssetEntry`.
- `topic.py` — `TopicItem`, `ScoredTopicItem`, enums (ingestion/scoring).
- `__init__.py` — public model exports.

**Manifest system**

- `src/content_creation/manifest.py` — `ManifestBuilder.build()` / `build_all()`, asset presence and `review_status`, `ready_for_planner`.

**Storage (`src/content_creation/storage/local.py`)**

- Paths and save/load for `briefs`, `scripts`, `carousels`, `newsletters`, `thumbnails`, `manifests`; `list_briefs`, `get_scored`, `save_manifest`, etc., aligned with pipeline stages.

**CLI (`src/content_creation/cli.py`)**

- `generate-briefs`, `build-manifest`, `build-all-manifests` wired to storage and `ManifestBuilder`.

**Prompts (`prompts/`)**

- `summarize.md`, `short_video.md`, `carousel.md`, `newsletter.md`, `thumbnail.md` — templates for brief and asset generators.

**Docs**

- `docs/voice-and-style.md` — voice and style rules for generated copy (referenced by contributors and agents).

**Config**

- `config/scoring.yaml`, `config/feeds.yaml` — scoring weights and feed ingestion (unchanged layout; Week 4 adds publishing config).

## Week 4 Implementation Items

Pulled from `content-factory-implementation-plan.md` (Week 4 section):

- **Posting planner** — `config/publishing.yaml`, cadence and diversity rules, `planning/` (or equivalent) module for 7-day / 30-day selection from approved assets.
- **Review and approval state machine** — explicit transitions (e.g. draft → reviewed → approved), pre-schedule validation guards.
- **Dry-run publishing workflow** — private 7-day cycle, exported planner and checklist, no auto-post.
- **Analytics-ready metadata layer** — placeholders for views, saves, clicks, etc.; post IDs linked to asset IDs.
- **GitHub release documentation** — release notes, env and config documentation, contribution notes, tag readiness (e.g. `v0.1.0`).

## Known Technical Debt

- `datetime.utcnow()` deprecation warnings in `generation/brief.py` and `generation/script.py` — prefer `datetime.now(timezone.utc)` before Week 4.
- RAG-style enhancements (semantic deduplication, analogy reuse tracking) noted for future; **not** Week 4 scope.
- Full image-generation API integration deferred; Gemini free tier is the documented direction when thumbnail visuals are implemented beyond prompt JSON.

## Files Likely to Change in Week 4

- `config/publishing.yaml` (new).
- New `planning/` package (or similarly named module) under `src/content_creation/`.
- New `review/` or validation extensions for approval workflow.
- `src/content_creation/cli.py` — planner and review/report commands.
- `src/content_creation/storage/local.py` — planner exports, analytics sidecar paths if added.
- `README.md`, `TASK_SPEC.md`, `CLAUDE.md`, and selectively `docs/project-context.md` for release notes (schema changes still go through `docs/schema.md` with model updates).

## Critical Rules (carry forward)

- Never invoke bare `python` for project work — always `uv run python`.
- Never use `gemini-2.0-flash` — always `gemini-2.5-flash` for generation calls.
- Never change `docs/schema.md` without updating all dependent Pydantic models and tests.
- When using Claude Code, paste file contents upfront for accuracy.
- Split Claude Code prompts by file — target at most 2–3 files per prompt to reduce context errors.
