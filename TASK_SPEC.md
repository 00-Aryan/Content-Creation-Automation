# TASK_SPEC: Post–Week 4 Project State (v0.1.0 release)

## Status

- **Week 1:** Complete (ingestion, collectors, staged/scored storage, topic models).
- **Week 2:** Complete (scoring engine and config, validation, brief generation via Gemini, scoring-related CLI).
- **Week 3:** Complete (voice and style documentation, multi-format generators, manifest builder, extended storage and models).
- **Week 4:** Complete.
- **All 4 integrity fixes:** Applied.
- **Current test count:** 125 passing (`uv run python -m pytest`).
- **Deprecation warnings:** Fixed (`datetime.now(timezone.utc)` in `generation/brief.py` and `generation/script.py`).
- **Current branch:** `week4-publishing` — ready for `v0.1.0` release tag.

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

## Week 4 Deliverables (completed)

**Config**

- `config/publishing.yaml` — weekly format targets, scheduling rules, diversity rules for the posting planner.

**Planning (`src/content_creation/planning/`)**

- `planner.py` — `PostingPlanner`: builds `WeeklyCalendar` from manifests with cadence and diversity constraints.
- `dryrun.py` — `DryRunValidator`: validates a calendar before publish; produces `DryRunReport` with asset checks and recommended actions.
- `__init__.py` — exports `PostingPlanner`, `DryRunValidator`.

**Models (`src/content_creation/models/`)**

- `calendar.py` — `ScheduledPost`, `WeeklyCalendar`.
- `dryrun.py` — `AssetCheck`, `DryRunReport`.
- `analytics.py` — `PostAnalytics`, `PerformanceSnapshot`.

**Storage (`src/content_creation/storage/local.py`)**

- Calendar, dry-run report, and analytics JSON paths; save/load helpers for planner and analytics workflows.

**CLI (`src/content_creation/cli.py`)**

- `plan-week`, `dry-run`, `init-analytics`, `update-analytics`, `review-assets`.

**Tests**

- `tests/test_planner.py`, `tests/test_dryrun.py`, `tests/test_analytics.py`, `tests/test_review.py` — planner, dry-run, analytics, and review state machine coverage.

**Release docs**

- `CLAUDE.md`, `TASK_SPEC.md` updated for v0.1.0; tag `v0.1.0` when ready.

## Future Work

1. Web dashboard
2. Multi-language support
3. Performance feedback loop
4. Image generation
5. Platform API auto-posting
6. RAG semantic deduplication

## Known Technical Debt

- RAG-style enhancements (semantic deduplication, analogy reuse tracking) — see Future Work.
- Full image-generation API integration deferred; Gemini free tier is the documented direction when thumbnail visuals are implemented beyond prompt JSON.

## Critical Rules (carry forward)

- Never invoke bare `python` for project work — always `uv run python`.
- Never use `gemini-2.0-flash` — always `gemini-2.5-flash` for generation calls.
- Never change `docs/schema.md` without updating all dependent Pydantic models and tests.
- When using Claude Code, paste file contents upfront for accuracy.
- Split Claude Code prompts by file — target at most 2–3 files per prompt to reduce context errors.
