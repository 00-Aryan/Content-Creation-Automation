# TASK-042: Add YouTube Shorts script generator

**Phase:** 12.3 Platform-Aware Content
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-22
**Completed:** 2026-06-22
**Requires approval:** NO
**GitHub Issue:** #7

---

## Objective

Upgrade the existing `short_video` generation path to produce structured, YouTube Shorts-specific production segments while preserving compatibility with the existing script pipeline.

---

## Context

The repository already has a canonical `Script` model, `ScriptGenerator`, prompt registration, storage repository, application service, workflow lookup, and UI rendering path for `short_video`. Creating a second Shorts generator or storage type would duplicate the pipeline and introduce competing representations.

The current script representation only stores a hook, plain string sections, and a CTA. The Phase 12.3 contract also requires timed visual directions, audio or sound-effect directions, and exact spoken narration. TASK-042 adds this structured representation while retaining `script_sections` for existing consumers.

The normative constraints in Sections 1–3 of `docs/platform/youtube-shorts-content-contract.md` take precedence over its abbreviated example, which does not satisfy the documented 50–58 second duration.

---

## Source References

- GitHub issue: #7
- Platform contract: `docs/platform/youtube-shorts-content-contract.md`
- Source-grounding contract: `docs/platform/source-grounding-contract.md`
- Existing generator: `src/content_creation/generation/script.py`
- Existing model: `src/content_creation/models/script.py`

---


## Required Scope

### Files to create

- `tests/test_youtube_shorts_generation.py`

### Files to modify

- `src/content_creation/models/script.py`
- `src/content_creation/models/__init__.py`
- `src/content_creation/generation/script.py`
- `prompts/short_video.md`
- `tests/test_generation_scaffold.py`
- `tests/test_script_storyboard_integration.py`
- `WORK_QUEUE.md`
- `docs/tasks/task_042.md`

### Files to read but not modify

- `docs/platform/youtube-shorts-content-contract.md`
- `docs/platform/source-grounding-contract.md`
- `src/content_creation/application/asset_generation_service.py`
- `src/content_creation/storage/local.py`
- `src/content_creation/domains/script/repository.py`
- `src/content_creation/ui/pages/5_asset_workshop.py`
- `src/content_creation/prompts/registry.py`

### Files and directories not allowed

- `.github/workflows/`
- `pyproject.toml`
- `uv.lock`
- `data/`
- `src/content_creation/application/`
- `src/content_creation/storage/`
- `src/content_creation/workflow/`
- `src/content_creation/ui/`
- `src/content_creation/prompts/registry.py`
- other platform models or generators
- any `__pycache__/` directory
- any `.pyc` file

---

## Implementation Requirements

### 1. Add structured Shorts segment model

Add `YouTubeShortsSegment` to `src/content_creation/models/script.py`.

Required fields:

- `section`
- `time_range`
- `visual`
- `audio`
- `spoken`

`section` must support these values:

- `hook`
- `context`
- `explanation`
- `payoff`
- `cta`

Repeated middle-section values are allowed.

All values must remain serializable through the existing JSON repository.

Export `YouTubeShortsSegment` from `src/content_creation/models/__init__.py`.

---

### 2. Extend Script without breaking persisted assets

Add:

    shorts_segments: List[YouTubeShortsSegment]

Use an empty-list default factory so previously persisted scripts that do not contain this field remain readable.

Do not remove or rename:

- `hook`
- `script_sections`
- `cta`
- `claims_used`
- `source_links`
- `review_status`

---

### 3. Upgrade only the short_video generation path

For `format="short_video"`:

- parse `shorts_segments` from generated JSON
- clean structural markers from `visual`, `audio`, and `spoken`
- require a hook segment first
- require a CTA segment last
- require non-empty production and spoken fields
- preserve the brief source URL in `source_links`
- preserve storyboard-owned hook, CTA, and claims
- synchronize the first segment narration with the final hook
- synchronize the last segment narration with the final CTA
- derive `script_sections` from middle segment narration
- force `NEEDS_REVIEW` when structured Shorts output is missing or malformed

For `carousel` and `newsletter`, preserve existing behavior without changing their output contracts.

---

### 4. Preserve compatibility

Existing consumers must continue to receive:

- top-level `hook`
- middle narration in `script_sections`
- top-level `cta`

Do not change storage paths, manifest mapping, application-service routing, workflow actions, or UI rendering in this task.

TASK-043 will use `shorts_segments` for the three-column preview.

---

### 5. Update the Shorts prompt

Update `prompts/short_video.md` to request schema-valid JSON containing:

- `hook`
- `shorts_segments`
- `cta`
- `claims_used`
- `review_status`

The prompt must require:

- timed segments covering approximately 50–58 seconds
- 130–150 total spoken words
- visual direction for every segment
- audio or SFX direction for every segment
- short spoken sentences
- immediate technical hook
- CTA as the final segment
- no generic greeting
- no structural marker leakage
- no invented claims
- source-field attribution in `claims_used`

Do not request Markdown output from the model.

---

### 6. Add focused tests

Create `tests/test_youtube_shorts_generation.py`.

Required coverage:

1. valid structured Shorts response
2. segment fields are parsed into models
3. legacy `script_sections` are derived from middle narration
4. source URL preservation
5. storyboard hook and CTA synchronization
6. marker cleanup across visual, audio, and spoken fields
7. missing segments force `NEEDS_REVIEW`
8. malformed segments force fallback
9. first segment must be hook
10. last segment must be CTA
11. non-short-video generation remains unchanged
12. previously persisted Script payloads without `shorts_segments` remain valid

Update existing script fixtures only as necessary to reflect the new structured short-video response.

All inference calls must be mocked.

---

## Constraints

- Do not introduce a second Shorts generator.
- Do not create a second script storage type.
- Do not add UI behavior.
- Do not add publishing behavior.
- Do not add an LLM-as-judge.
- Do not add platform-wide deterministic quality scoring.
- Do not claim page-level or sentence-level source verification.
- Basic schema and fallback enforcement are permitted; broader quality gates belong to Phase 12.4.
- Preserve all existing non-short-video behavior.

---

## Validation Commands

Run targeted tests:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest       tests/test_youtube_shorts_generation.py       tests/test_generation_scaffold.py       tests/test_script_storyboard_integration.py       -q

Run affected service and persistence tests:

    uv run python -m pytest       tests/test_asset_generation_service.py       tests/test_manifest.py       tests/test_storage_integration.py       -q

Run the full suite:

    uv run python -m pytest --tb=short -q

Run formatting and scope checks:

    git diff --check
    git diff --name-only

---

## Success Criteria

- [x] `YouTubeShortsSegment` exists and is exported.
- [x] `Script` remains backward compatible with stored payloads.
- [x] The canonical `ScriptGenerator` emits structured Shorts segments.
- [x] Hook and CTA segment narration stays synchronized with top-level fields.
- [x] `script_sections` remains available for existing consumers.
- [x] Missing or malformed structured Shorts output is routed to review.
- [x] Non-short-video generation behavior remains unchanged.
- [x] Source URL preservation remains intact.
- [x] Focused tests pass.
- [x] Full test suite passes without regression.
- [x] No files outside declared scope were modified.

---

## Depends On

TASK-040

---

## Blocks

TASK-043

---

## Commit Message

    feat(platform): add YouTube Shorts script generator (TASK-042)

---

## Notes

The existing contract's example ends at 28 seconds and is not authoritative for duration. Implement against the explicit structural constraints: 50–58 seconds, 130–150 spoken words, timed visual/audio/spoken segments, and a final CTA.
