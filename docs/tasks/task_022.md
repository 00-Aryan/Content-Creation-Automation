# TASK-022: Align asset generation candidates with storyboard artifacts

**Phase:** 12.0
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

## Objective

Fix the E2E pipeline failure where `generate-assets` crashes because `AssetGenerationService` selects a brief that does not have a corresponding storyboard artifact.

## Confirmed Evidence

The Streamlit full pipeline now reaches the asset generation stage.

Current successful stages:

```text
generate-briefs:
  generated_count: 0
  skipped_count: 5
  failed_count: 0
  success: true

generate-content-intelligence:
  generated_count: 0
  skipped_count: 5
  failed_count: 0
  success: true

generate-storyboards:
  generated_count: 0
  skipped_count: 5
  failed_count: 0
  success: true
```

Current failing stage:

```text
generate-assets:
  error: Required Storyboard artifact is missing for topic 2b20a8623e337127048f0d029f4dfe51230b69a63b20b1f4b48449b61c1b3ff5.
```

Local artifact diagnostic confirms this topic has partial downstream artifacts but no storyboard:

```text
topic: 2b20a8623e337127048f0d029f4dfe51230b69a63b20b1f4b48449b61c1b3ff5
data/briefs True 577
data/content_intelligence True 678
data/storyboards False -
data/thumbnails True 577
data/scripts True 482
data/carousels False -
data/newsletters False -
```

Top brief diagnostic confirms the asset service candidate set includes briefs without storyboards:

```text
topic_id: 2b20a8623e337127048f0d029f4dfe51230b69a63b20b1f4b48449b61c1b3ff5
storyboard_exists: False
recommended_formats: ['needs_review']

topic_id: f23a20ac073764cabf8cba6dafe9b21d2cec0b6bf5421a2d48539137fb394046
storyboard_exists: False
recommended_formats: ['needs_review']
```

This is not an inference provider issue.

This is not an OpenRouter issue.

This is not a brief generation issue.

This is an asset generation candidate-selection issue.

## Scope

### Files to inspect

* `src/content_creation/application/asset_generation_service.py`
* `src/content_creation/application/pipeline_run_service.py`
* `src/content_creation/storage/local.py`
* tests covering asset generation service
* tests covering full pipeline execution

### Files allowed to modify

* `src/content_creation/application/asset_generation_service.py`
* tests for asset generation candidate selection
* tests for E2E pipeline stage behavior

### Files not allowed to modify

* inference provider code
* OpenRouter provider code
* Gemini provider code
* prompts
* scoring engine
* collection logic
* brief generation service
* content intelligence service
* storyboard service
* UI files unless a UI-specific bug is proven

## Investigation Steps

1. Inspect `AssetGenerationService.run()`.

2. Confirm that it currently does:

```python
briefs = ctx.storage.list_briefs()
briefs.sort(key=lambda b: b.generated_at, reverse=True)
briefs = briefs[:top_n]
```

3. Confirm that it raises immediately when storyboard is missing:

```python
storyboard = ctx.storage.get_storyboard(brief.topic_id)
if storyboard is None:
    raise ValueError(...)
```

4. Confirm whether asset generation is always batch-oriented or if it also supports single-topic generation.

5. Identify existing tests for asset generation.

6. Add or update tests to reproduce the current failure with:

* one valid brief with storyboard
* one stale brief without storyboard
* `top_n > 1`

7. Do not commit debug prints.

## Implementation Requirements

1. `AssetGenerationService.run()` must not crash the entire batch because one selected brief has no storyboard.

2. Asset generation candidates must be aligned with storyboard availability.

3. A brief without a storyboard must be skipped in batch asset generation.

4. The service must continue processing other briefs that do have storyboards.

5. Missing storyboard skips must increment `skipped_count`, not `failed_count`, because the asset service cannot generate assets without its required upstream artifact.

6. The service must not create fake storyboards.

7. The service must not call asset generators with `storyboard=None`.

8. The service must preserve existing behavior for briefs that have valid storyboards.

9. Existing asset overwrite protection must remain intact.

10. Existing workflow stage-completion checks must remain intact.

11. Do not change provider/model/API routing.

12. Do not change prompts.

13. Do not change scoring or collection behavior.

14. Do not bypass the architecture:
    
15. Do not generate placeholder, fallback, dummy, or generic assets when storyboard is missing. Missing upstream artifacts must cause the topic to be skipped, not synthesized.

```text
Operator / CLI / Job
    ↓
WorkflowActionExecutor
    ↓
ActionAvailabilityEngine
    ↓
ReviewTransitionEngine
    ↓
Application Services
    ↓
Storage
```

## Expected Fix Shape

Prefer a minimal fix inside `AssetGenerationService`.

Replace hard failure on missing storyboard with batch-safe skip behavior.

Current failing behavior:

```python
storyboard = ctx.storage.get_storyboard(brief.topic_id)
if storyboard is None:
    raise ValueError(
        f"Required Storyboard artifact is missing for topic {brief.topic_id}. "
        "Asset generation cannot proceed without a valid Storyboard."
    )
```

Expected behavior:

```python
storyboard = ctx.storage.get_storyboard(brief.topic_id)
if storyboard is None:
    logger.warning(
        "Skipping asset generation for %s because storyboard artifact is missing.",
        brief.topic_id,
    )
    skipped += 1
    continue
```

Optional improvement if consistent with existing service semantics:

Filter eligible candidates before applying `top_n`:

```python
all_briefs = ctx.storage.list_briefs()
all_briefs.sort(key=lambda b: b.generated_at, reverse=True)

eligible_briefs = []
missing_storyboard_count = 0

for brief in all_briefs:
    storyboard = ctx.storage.get_storyboard(brief.topic_id)
    if storyboard is None:
        missing_storyboard_count += 1
        continue
    eligible_briefs.append((brief, storyboard))
    if len(eligible_briefs) >= top_n:
        break
```

Then generate assets only from `eligible_briefs`.

Do not implement both approaches unless tests prove it is necessary.

Preferred final behavior:

* stale briefs without storyboards are skipped
* valid briefs with storyboards are processed
* `generate-assets` returns successfully if there are no generator failures
* `skipped_count` includes missing-storyboard skips and already-existing asset skips
* `failed_count` is reserved for actual asset generation failures

## Required Test Coverage

Add or update tests proving:

1. A brief without a storyboard does not crash batch asset generation.

2. A missing storyboard increments `skipped_count`.

3. Other briefs with valid storyboards are still processed.

4. Asset generators are never called with `storyboard=None`.

5. Existing generated assets are still skipped cleanly.

6. Existing valid asset generation behavior remains unchanged.

7. The E2E pipeline no longer fails at `generate-assets` solely because one old brief has no storyboard.

## Validation Commands

Run the full test suite:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q
```

Run focused tests if available:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest tests/test_asset_generation_service.py --tb=short -q
```

Run the local diagnostic again:

```bash
python3 - <<'PY'
from pathlib import Path
from content_creation.application.context import ApplicationContext

ctx = ApplicationContext.create(Path.cwd())

briefs = ctx.storage.list_briefs()
briefs.sort(key=lambda b: b.generated_at, reverse=True)

print("Top 10 briefs by generated_at:")
for b in briefs[:10]:
    storyboard = ctx.storage.get_storyboard(b.topic_id)
    print()
    print("topic_id:", b.topic_id)
    print("generated_at:", b.generated_at)
    print("storyboard_exists:", storyboard is not None)
    print("recommended_formats:", b.recommended_formats)
PY
```

Run the Streamlit app from a shell where API keys are exported:

```bash
uv run streamlit run src/content_creation/ui/app.py
```

In the UI:

1. Open the `app` page.
2. Keep `Top items` as `5`.
3. Leave `Source ID Filter` empty.
4. Click `Run Full Pipeline`.

## Success Criteria

* [ ] Streamlit app does not crash.
* [ ] E2E pipeline does not fail at `generate-assets` because of a missing storyboard for one stale brief.
* [ ] Missing storyboard candidates are skipped, not treated as hard batch failures.
* [ ] Valid briefs with storyboards still generate or skip assets correctly.
* [ ] Asset generators are not called with `storyboard=None`.
* [ ] Existing asset overwrite protection remains intact.
* [ ] Provider/model/API logic is unchanged.
* [ ] Tests pass with at least the existing baseline count.
* [ ] No debug prints are committed.
- [ ] No placeholder/generic assets are created to make the pipeline pass.
- [ ] Every generated asset is traceable to a real storyboard artifact.

## Commit Message

```bash
fix(pipeline): skip asset generation candidates without storyboards (TASK-022)
```
