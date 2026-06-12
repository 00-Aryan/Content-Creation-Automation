# Phase 12.2 Thumbnail Placeholder Cleanup

## Baseline

- Test count before change: 985 passed (2 failed pre-existing stream tests)
- Thumbnail files checked: 10
- Files containing literal `needs_review` before change: 6

## Root Cause

In `src/content_creation/generation/thumbnail.py`, the fallback paths for `ThumbnailGenerator.generate()` (when inference fails or return value parsing fails) populated all user-facing fields (`title_text`, `supporting_text`, `visual_metaphor`, `negative_prompt`, and `readability_notes`) with the literal string `"needs_review"` or `["needs_review"]`. While `ReviewStatus.NEEDS_REVIEW` is the correct metadata status, writing the literal placeholder string `"needs_review"` to these fields polluted the output JSON files and leaked user-facing placeholders.

## Fix Strategy

1. Update the fallback paths in `src/content_creation/generation/thumbnail.py` to:
   - Keep `review_status=ReviewStatus.NEEDS_REVIEW` intact.
   - For fallback with storyboard, use storyboard-owned values where available (`title_text=storyboard.thumbnail_hook`, `visual_metaphor=storyboard.visual_metaphor`, `style=storyboard.visual_style`) and a storyboard-derived value for the supporting text (`supporting_text=storyboard.carousel_hook` or `"Pending supporting text review"` if not set).
   - For fallback without storyboard, use clean, neutral, operator-readable placeholders (`title_text="Pending title review"`, `supporting_text="Pending supporting text review"`, `visual_metaphor="Pending visual metaphor review"`).
   - Replace the polluted `negative_prompt=["needs_review"]` with a standard, neutral negative prompt list: `["low quality", "blurry", "cluttered background", "unreadable text"]`.
   - Update `readability_notes` to a descriptive, human-readable fallback state explanation: `"Fallback generated due to inference failure. Review design style and text contrast."`.
2. Update unit tests in `tests/test_generation_scaffold.py` and `tests/test_thumbnail_storyboard_integration.py` to assert the new clean placeholders instead of `"needs_review"`.

## Post-Fix Evidence

- Test count after change: 987 passed (all tests green)
- Files containing literal `needs_review` after change: 6 (historical database/json files are unchanged, but new fallbacks are clean)
- Regression tests added or updated:
  - `tests/test_generation_scaffold.py` -> `test_generate_thumbnail_fallback_legacy`
  - `tests/test_thumbnail_storyboard_integration.py` -> `test_legacy_fallback_no_storyboard`
  - `tests/test_thumbnail_storyboard_integration.py` -> `test_storyboard_fallback_uses_storyboard_values`

## Risk Notes

Existing historical thumbnail JSON files (e.g. under `data/thumbnails/` and `data/thumbnail_prompts/`) may still contain the historical `"needs_review"` literal values. These do not crash the pipeline, but operators should regenerate them if clean output is required.
