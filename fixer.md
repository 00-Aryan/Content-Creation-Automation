# Pipeline Fix Report

## Date: 2026-05-19

## Root Cause

All 9 manifests were `blocked` due to three issues:

1. **Briefs marked `needs_review`** — Brief generation produced valid content but the review_status was set to `needs_review` (either by the LLM or as fallback). No batch approval mechanism existed.

2. **Thumbnails missing entirely** — No CLI command existed to generate thumbnails or other assets beyond briefs. The `generate-briefs` command only produces briefs, leaving thumbnails (which are ALWAYS_REQUIRED) ungenerated.

3. **Invalid `recommended_formats` values** — The summarize prompt did not constrain the LLM's output for `recommended_formats`. The LLM produced pedagogical format names ("Lecture", "Case Study", "Technical Deep Dive") instead of platform delivery formats ("short_video", "carousel", "newsletter"). The manifest builder's `FORMAT_TO_ASSET` lookup found no matches, so all optional assets were marked `skipped`.

## Fixes Applied

| Fix | File(s) Modified | Description |
|-----|-----------------|-------------|
| Prompt constraint | `prompts/summarize.md` | Added explicit rule limiting recommended_formats to valid literals |
| Format mapping layer | `src/content_creation/manifest.py` | Added FREETEXT_TO_FORMAT dict that maps free-text to valid literals |
| Generate assets command | `src/content_creation/cli.py` | New `generate-assets` subcommand for thumbnails + format assets |
| Batch approve command | `src/content_creation/cli.py` | New `batch-approve` subcommand for non-interactive approval |
| Run pipeline command | `src/content_creation/cli.py` | New `run-pipeline` subcommand with structured logging |
| Structured logging | `src/content_creation/utils/logging.py` | Added PipelineLogger with JSON-line output |
| Storage update | `src/content_creation/storage/local.py` | Added `data/logs/` directory |

## Verification

After fixes:
- Manifests transition from `blocked` → `complete`
- `ready_for_planner` flips to `true`
- `plan-week` produces a non-empty calendar
- `dry-run` reports ready assets
- Structured log captures full pipeline execution

## Commands Added

```bash
# Generate all missing assets (thumbnails + format-specific)
uv run python -m content_creation.cli generate-assets --top 5

# Batch approve all assets non-interactively
uv run python -m content_creation.cli batch-approve --asset-type all --all

# Run full pipeline end-to-end with structured logging
uv run python -m content_creation.cli run-pipeline --top 5

# Run full pipeline with auto-approve (dev/testing only)
uv run python -m content_creation.cli run-pipeline --top 5 --auto-approve
```

## Lessons Learned

1. LLMs need explicit enum constraints in prompts — "choose from this list" not "suggest formats"
2. Always have a mapping/fallback layer between LLM output and system enums
3. Required assets (brief + thumbnail) need generation commands from day one
4. Batch operations are essential for development velocity — interactive-only review blocks testing
