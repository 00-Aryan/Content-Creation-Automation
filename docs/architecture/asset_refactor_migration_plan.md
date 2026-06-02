# Asset Refactor Migration Plan

## Overview
This document outlines the migration plan to transition the `AssetGenerationService` and downstream asset generators (`ThumbnailGenerator`, `ScriptGenerator`, `CarouselGenerator`, and `NewsletterGenerator`) from consuming `Brief` to consuming `Storyboard` as their primary structural input.

Since `Storyboard` models do not duplicate base educational details (such as `plain_english_summary` or `student_takeaway`) to preserve schema integrity, all generators will adopt a dual-input signature accepting `Storyboard` as the primary layout instruction and `Brief` as the background knowledge provider.

---

## Generator Mapping & Analysis

### 1. ThumbnailGenerator
* **Brief fields currently consumed**: `topic_id`, `why_it_matters`, `plain_english_summary`, `student_takeaway`, `analogy`, `limitation`, `audience_fit`, `source_url`.
* **Storyboard fields to replace them**: `thumbnail_hook` (replaces title/analogy theme), `visual_style` (replaces generic style), `visual_metaphor` (replaces analogy).
* **Brief fields not in Storyboard**: Base educational details (`why_it_matters`, `plain_english_summary`, `student_takeaway`, `limitation`, `audience_fit`, `source_url`).
* **Prompt template modifications**: Yes. Template placeholders will transition from general analogy / style notes to storyboard-defined `{{ storyboard.thumbnail_hook }}`, `{{ storyboard.visual_metaphor }}`, and `{{ storyboard.visual_style }}`.
* **Interface modifications**: Yes. Change signature from `generate(self, brief: Brief, storyboard=None)` to `generate(self, storyboard: Storyboard, brief: Brief)`.
* **Test modifications**: Yes. Mocks must supply both `Storyboard` and `Brief` instances.
* **Risk Class**: **Low-risk migration** (overrides already exist in codebase, only signature change and test cleanup are needed).

### 2. ScriptGenerator
* **Brief fields currently consumed**: `topic_id`, `why_it_matters`, `plain_english_summary`, `student_takeaway`, `analogy`, `limitation`, `audience_fit`, `source_url`.
* **Storyboard fields to replace them**: `script_hook` (replaces analogy), `script_cta` (replaces generic CTA), `script_claims` (replaces broad summary bullets).
* **Brief fields not in Storyboard**: Base educational details (`why_it_matters`, `plain_english_summary`, `student_takeaway`, `limitation`, `audience_fit`, `source_url`).
* **Prompt template modifications**: Yes. Replaceholders like `{{ brief.analogy }}` and `{{ brief.plain_english_summary }}` should be replaced by `{{ storyboard.script_hook }}` and `{{ storyboard.script_claims }}` (rendered as bullet lists) to generate target-claims-aligned script content.
* **Interface modifications**: Yes. Change signature from `generate(self, brief: Brief, format: str)` to `generate(self, storyboard: Storyboard, brief: Brief, format: str)`.
* **Test modifications**: Yes. Tests must mock both inputs.
* **Risk Class**: **Medium-risk migration** (requires careful claims-bullet formatting helper integration).

### 3. CarouselGenerator
* **Brief fields currently consumed**: `topic_id`, `why_it_matters`, `plain_english_summary`, `student_takeaway`, `analogy`, `limitation`, `audience_fit`, `source_url`.
* **Storyboard fields to replace them**: `carousel_hook` (replaces analogy), `carousel_cta` (replaces generic CTA), `carousel_claims` (replaces broad summary), `visual_style`, `visual_metaphor`.
* **Brief fields not in Storyboard**: Base educational details (`why_it_matters`, `plain_english_summary`, `student_takeaway`, `limitation`, `audience_fit`, `source_url`).
* **Prompt template modifications**: Yes. Update placeholders to load storyboarded slide hooks, claims list, style guidelines, and visual metaphors.
* **Interface modifications**: Yes. Change signature from `generate(self, brief: Brief)` to `generate(self, storyboard: Storyboard, brief: Brief)`.
* **Test modifications**: Yes.
* **Risk Class**: **Medium-risk migration**.

### 4. NewsletterGenerator
* **Brief fields currently consumed**: `topic_id`, `why_it_matters`, `plain_english_summary`, `student_takeaway`, `analogy`, `limitation`, `audience_fit`, `source_url`, `recommended_formats`.
* **Storyboard fields to replace them**: `newsletter_hook` (replaces title/theme), `newsletter_cta` (replaces generic CTA), `newsletter_claims` (replaces broad summary).
* **Brief fields not in Storyboard**: Base educational details (`why_it_matters`, `plain_english_summary`, `student_takeaway`, `limitation`, `audience_fit`, `source_url`).
* **Prompt template modifications**: Yes. Update placeholders to reference storyboard newsletter claims and hook text.
* **Interface modifications**: Yes. Change signature from `generate(self, brief: Brief)` to `generate(self, storyboard: Storyboard, brief: Brief)`.
* **Test modifications**: Yes.
* **Risk Class**: **Medium-risk migration**.

---

## Migration Matrix

| Component | Current Input Interface | Future Input Interface |
| :--- | :--- | :--- |
| **ThumbnailGenerator** | `generate(self, brief: Brief, storyboard=None)` | `generate(self, storyboard: Storyboard, brief: Brief)` |
| **ScriptGenerator** | `generate(self, brief: Brief, format: str)` | `generate(self, storyboard: Storyboard, brief: Brief, format: str)` |
| **CarouselGenerator** | `generate(self, brief: Brief)` | `generate(self, storyboard: Storyboard, brief: Brief)` |
| **NewsletterGenerator** | `generate(self, brief: Brief)` | `generate(self, storyboard: Storyboard, brief: Brief)` |
| **AssetGenerationService**| Loops over top `Brief`s; checks formats in `brief.recommended_formats`. | Loops over top `Storyboard`s; resolves matched `Brief`s; loops over `storyboard.formats_planned`. |

---

## Execution Strategy

### Recommended Migration Order
1. **Templates Stage**: Refactor prompt templates under `prompts/` to define placeholders for storyboard fields (e.g. `{{ storyboard.script_claims }}`).
2. **Generator Interfaces**: Refactor the generators (`ThumbnailGenerator`, `ScriptGenerator`, `CarouselGenerator`, `NewsletterGenerator`) to use the new dual-signature pattern.
3. **Scaffold Tests**: Update `tests/test_generation_scaffold.py` and other test files to configure storyboard mocks.
4. **Service Integration**: Update `AssetGenerationService.run` to pull storyboard candidates from storage, load matched parent briefs, check stage resumability statuses, and loop over planned formats.
5. **Regression Verification**: Execute the full test suite (`uv run pytest`) to verify that all E2E asset generation cycles succeed.

### Breaking Changes
* Invoking a generator's `generate()` method with only a `Brief` object will result in a `TypeError`.
* Downstream asset targets are now strictly governed by `storyboard.formats_planned` instead of `brief.recommended_formats`.

### Rollback Strategy
* Execute a git checkout of original implementation files:
  `git checkout HEAD -- src/content_creation/generation/ src/content_creation/application/asset_generation_service.py`

---

## Final Verdict
**READY FOR IMPLEMENTATION**
