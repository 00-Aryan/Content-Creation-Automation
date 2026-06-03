# Phase 5 Asset Refactor Execution Plan

## 1. Strategy Overview

### Recommended Migration Approach: Generator-by-Generator
We will perform the migration **generator-by-generator** rather than all-at-once. This minimizes the footprint of signature changes and enables isolated, incremental testing. We will enforce a strict **GO / NO-GO** checkpoint after each generator is refactored.

### Migration Order
1. **ThumbnailGenerator** (Lowest risk: Already contains optional storyboard hook overrides).
2. **NewsletterGenerator** (Medium risk: Flat structural changes, single format output).
3. **CarouselGenerator** (Medium risk: Multi-slide mapping, single format output).
4. **ScriptGenerator** (Highest risk: Dynamically maps and validates multiple sub-formats like short videos).
5. **AssetGenerationService** (Integration Stage: Transitions candidate selection from briefs to storyboards, and simplifies format mapping using `storyboard.formats_planned`).

---

## 2. Generator Migration Specifications

### Step 1: ThumbnailGenerator Migration
* **Files Affected**: `src/content_creation/generation/thumbnail.py`
* **Tests Affected**:
  * `tests/test_generation_scaffold.py`
  * `tests/test_thumbnail_storyboard_integration.py`
* **Expected Interface Change**:
  * Old: `generate(self, brief: Brief, storyboard=None) -> ThumbnailPrompt`
  * New: `generate(self, storyboard: Storyboard, brief: Brief) -> ThumbnailPrompt`
* **Rollback Approach**:
  `git checkout HEAD -- src/content_creation/generation/thumbnail.py tests/test_generation_scaffold.py tests/test_thumbnail_storyboard_integration.py`
* **GO / NO-GO Checkpoint**: Run `uv run pytest tests/test_generation_scaffold.py` and `tests/test_thumbnail_storyboard_integration.py`. Verify that the thumbnail tests pass successfully.

### Step 2: NewsletterGenerator Migration
* **Files Affected**: `src/content_creation/generation/newsletter.py`
* **Tests Affected**: `tests/test_generation_scaffold.py`
* **Expected Interface Change**:
  * Old: `generate(self, brief: Brief) -> Newsletter`
  * New: `generate(self, storyboard: Storyboard, brief: Brief) -> Newsletter`
* **Rollback Approach**:
  `git checkout HEAD -- src/content_creation/generation/newsletter.py tests/test_generation_scaffold.py`
* **GO / NO-GO Checkpoint**: Run `uv run pytest tests/test_generation_scaffold.py`. Verify that the newsletter generation tests pass successfully.

### Step 3: CarouselGenerator Migration
* **Files Affected**: `src/content_creation/generation/carousel.py`
* **Tests Affected**: `tests/test_generation_scaffold.py`
* **Expected Interface Change**:
  * Old: `generate(self, brief: Brief) -> Carousel`
  * New: `generate(self, storyboard: Storyboard, brief: Brief) -> Carousel`
* **Rollback Approach**:
  `git checkout HEAD -- src/content_creation/generation/carousel.py tests/test_generation_scaffold.py`
* **GO / NO-GO Checkpoint**: Run `uv run pytest tests/test_generation_scaffold.py`. Verify that all carousel tests pass successfully.

### Step 4: ScriptGenerator Migration (Highest Risk)
* **Files Affected**: `src/content_creation/generation/script.py`
* **Tests Affected**: `tests/test_generation_scaffold.py`
* **Expected Interface Change**:
  * Old: `generate(self, brief: Brief, format: str) -> Script`
  * New: `generate(self, storyboard: Storyboard, brief: Brief, format: str) -> Script`
* **Rollback Approach**:
  `git checkout HEAD -- src/content_creation/generation/script.py tests/test_generation_scaffold.py`
* **GO / NO-GO Checkpoint**: Run `uv run pytest tests/test_generation_scaffold.py`. Verify that all script format generation tests pass successfully.

### Step 5: AssetGenerationService Integration
* **Files Affected**: `src/content_creation/application/asset_generation_service.py`
* **Tests Affected**: `tests/test_asset_generation_service.py`
* **Expected Interface Change**: The public signature `run(self, ctx: ApplicationContext, ...)` is preserved, but internal loops list `storyboards = ctx.storage.list_storyboards()` and call refactored generators.
* **Rollback Approach**:
  `git checkout HEAD -- src/content_creation/application/asset_generation_service.py tests/test_asset_generation_service.py`
* **GO / NO-GO Checkpoint**: Run the entire project test suite `uv run pytest`. Verify that all 222 unit and E2E integration tests pass successfully.

---

## 3. Final Validation Checkpoint

* **Pre-requisite**: All generator and service refactors are complete.
* **Verification Command**: `uv run pytest`
* **E2E Smoke Test**: Validate that executing `generate-assets` on the CLI resolves candidate storyboards, generates thumbnails, carousels, scripts, and newsletters, and correctly logs workflow progression to disk.

---

## Final Verdict
**READY FOR IMPLEMENTATION**
