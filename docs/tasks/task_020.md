# TASK-020: Fix idempotent brief generation for populated target files

**Phase:** 12.0  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-11  
**Completed:** 2026-06-11  
**Requires approval:** NO  

## Objective

Fix the E2E pipeline failure where the `generate-briefs` stage fails with `Target asset file is already populated.` when a brief artifact already exists.

## Context

The Streamlit E2E pipeline now reaches the brief generation stage but fails before Content Intelligence.

Observed UI pipeline summary:

- collect: success
  - count: 512
- score: success
  - scored_count: 5723
  - rejected_count: 277
- generate-briefs: failure
  - error: `Brief generation failed: ['Target asset file is already populated.']`

This indicates the pipeline is trying to generate or save a brief for a topic whose target brief file already exists and is populated.

The current `BriefGenerationService.run()` checks only:

```python
brief_file = ctx.storage.briefs_dir / f"{item.id}.json"
if brief_file.exists():
    skipped_count += 1
    continue
```

But the pipeline still reaches a lower-level write failure:

```text
Target asset file is already populated.
```

So either:

1. the service-level existence check is not aligned with the actual storage path used by `ctx.storage.save_brief()`;
2. the file exists but is not being detected correctly;
3. `save_brief()` uses a different file path or atomic write target;
4. workflow state and artifact state are diverged;
5. duplicate scored topics with the same final brief target are being selected;
6. the generator creates a brief whose `topic_id` differs from the scored item ID.

This is an idempotency bug. Re-running the E2E pipeline should skip existing briefs cleanly, not fail.

## Scope

### Files to inspect

- `src/content_creation/application/brief_generation_service.py`
- `src/content_creation/storage/`
- `src/content_creation/generation/brief.py`
- `src/content_creation/models/brief.py`
- `src/content_creation/application/pipeline_run_service.py`
- existing tests for brief generation and pipeline reruns

### Files allowed to modify

- `src/content_creation/application/brief_generation_service.py`
- tests for brief generation idempotency
- tests for E2E pipeline rerun behavior

### Files frozen unless absolutely necessary

- `src/content_creation/generation/brief.py`
- `src/content_creation/models/brief.py`
- prompt files
- storage internals

Do not modify frozen files unless inspection proves the bug cannot be fixed at the application-service layer.

## Investigation Steps

1. Inspect `BriefGenerationService.run()`.

2. Inspect `ctx.storage.save_brief()` and confirm the exact target path it writes to.

3. Compare the service-level skip path:

   ```python
   ctx.storage.briefs_dir / f"{item.id}.json"
   ```

   with the actual path used by `save_brief()`.

4. Inspect `generate_brief()` and confirm the generated `Brief.topic_id` always equals the source scored item ID.

5. Identify which topic triggers `Target asset file is already populated.` by adding temporary local diagnostics if needed.

6. Do not commit diagnostic prints.

7. Determine whether existing populated brief files should be counted as skipped.

8. Confirm whether workflow state should be marked completed when a valid brief already exists but workflow state is missing or stale.

## Implementation Requirements

1. Brief generation must be idempotent.

2. If a valid brief artifact already exists for a selected scored topic, `BriefGenerationService` must skip it cleanly.

3. If the brief artifact exists but workflow state is missing/stale, the service may reconcile workflow state if the existing architecture already supports that pattern.

4. The service must not call `generate_brief()` for topics whose brief artifact already exists and is readable.

5. The service must not call `ctx.storage.save_brief()` when the target brief file is already populated.

6. If `generate_brief()` returns a `Brief` whose `topic_id` differs from the source scored item ID, record a structured failure and do not save it.

7. A single already-populated target file must not fail the entire batch.

8. Existing valid behavior for new brief generation must remain unchanged.

9. Do not change scoring.

10. Do not change topic collection.

11. Do not change Content Intelligence generation in this task.

12. Do not bypass the architecture:

    Operator / CLI / Job  
    → WorkflowActionExecutor  
    → ActionAvailabilityEngine  
    → ReviewTransitionEngine  
    → Application Services  
    → Storage

## Expected Fix Shape

Prefer a minimal application-service fix in `BriefGenerationService`.

The service should use storage-level reads where possible instead of manually guessing file paths.

Preferred behavior:

```python
existing_brief = ctx.storage.get_brief(item.id)
if existing_brief is not None:
    skipped_count += 1
    continue
```

Then keep the file existence check as a fallback only if needed.

When generating:

```python
brief = generate_brief(item, ctx.prompt_registry, api_key)

if brief.topic_id != item.id:
    failures.append(
        BriefFailure(
            topic_id=item.id,
            error=f"Generated brief topic_id mismatch: expected {item.id}, got {brief.topic_id}",
        )
    )
    continue

ctx.storage.save_brief(brief)
generated_briefs.append(brief)
```

If `ctx.storage.save_brief()` still raises `Target asset file is already populated.`, catch that specific exception and treat it as an idempotent skip only after confirming the brief can be loaded from storage.

Example behavior:

```python
except Exception as e:
    if "Target asset file is already populated" in str(e):
        existing_brief = ctx.storage.get_brief(item.id)
        if existing_brief is not None:
            skipped_count += 1
            continue
    logger.error(...)
    failures.append(...)
```

## Required Test Coverage

Add or update tests proving:

1. Existing brief artifact is skipped.

2. Re-running brief generation does not raise when selected topic already has a brief.

3. A generated brief with mismatched `topic_id` is not saved and is recorded as failure.

4. Existing successful brief generation behavior still passes.

## Validation Commands

Run tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q
```

Run artifact diagnostics:

```bash
python3 -c "
from pathlib import Path

for folder in [
    'data/scored',
    'data/briefs',
    'data/content_intelligence',
    'data/storyboards',
    'data/scripts',
    'data/carousels',
    'data/newsletters',
    'data/thumbnails',
    'data/manifests'
]:
    p = Path(folder)
    count = len(list(p.glob('*.json'))) if p.exists() else 0
    print(folder, count)
"
```

Run the Streamlit app:

```bash
uv run streamlit run src/content_creation/ui/app.py
```

In the UI:

1. Open the `app` page.
2. Keep `Top items` as `5`.
3. Leave `Source ID Filter` empty.
4. Click `Run Full Pipeline`.

## Success Criteria

- [ ] Streamlit app does not crash.
- [ ] E2E pipeline does not fail at `generate-briefs` because of `Target asset file is already populated.`
- [ ] Existing brief artifacts are skipped cleanly.
- [ ] New brief artifacts can still be generated when missing.
- [ ] The pipeline reaches `generate-content-intelligence`.
- [ ] At least one brief remains visible in the brief viewer.
- [ ] Tests pass with at least the existing baseline count.
- [ ] No debug prints are committed.
- [ ] No scoring or collection behavior changes are made.

## Commit Message

```bash
fix(pipeline): make brief generation idempotent for populated targets (TASK-020)
```