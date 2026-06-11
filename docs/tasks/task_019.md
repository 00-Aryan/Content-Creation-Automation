# TASK-019: Fix Content Intelligence brief selection failure

**Phase:** 12.0  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-11  
**Completed:** 2026-06-11  
**Requires approval:** NO  

## Objective

Fix the E2E pipeline failure where the `generate-content-intelligence` stage fails with `Brief is missing.` even though brief artifacts already exist in `data/briefs`.

## Context

The Streamlit E2E pipeline now reaches the Content Intelligence stage.

Observed local pipeline summary:

- collect: success
- score: success
  - scored_count: 5211
  - rejected_count: 277
- generate-briefs: success
  - generated_count: 1
  - skipped_count: 4
  - failed_count: 0
- generate-content-intelligence: failure
  - error: `Content Intelligence generation failed: ['Brief is missing.']`

Current local artifact counts:

- `data/scored`: 5488
- `data/briefs`: 11
- `data/content_intelligence`: 10
- `data/storyboards`: 6
- `data/scripts`: 6
- `data/carousels`: 3
- `data/newsletters`: 1
- `data/thumbnails`: 9
- `data/manifests`: 10

This means scoring and brief generation are working. The current failure is not caused by `insufficient_text`, OpenAI source quality, Gemini key configuration, or Streamlit startup behavior.

The likely issue is candidate selection or validation mismatch between:

- `src/content_creation/application/content_intelligence_service.py`
- `src/content_creation/domains/content_intelligence/generator.py`
- brief model/storage shape

## Scope

### Files to inspect

- `src/content_creation/application/content_intelligence_service.py`
- `src/content_creation/domains/content_intelligence/generator.py`
- `src/content_creation/models/brief.py`
- `src/content_creation/storage/`
- existing tests related to content intelligence and pipeline execution

### Files allowed to modify

- `src/content_creation/application/content_intelligence_service.py`
- tests for content intelligence service or E2E pipeline behavior

### Files frozen unless absolutely necessary

- `src/content_creation/domains/content_intelligence/generator.py`
- `src/content_creation/models/brief.py`
- prompt files
- generation/domain logic

Do not modify frozen files unless inspection proves the bug is impossible to fix at the application-service layer.

## Investigation Steps

1. Inspect `ContentIntelligenceService.run()` and confirm how it selects candidate briefs.

2. Inspect `ContentIntelligenceGenerator.generate()` and identify the exact condition that raises or returns `Brief is missing.`.

3. Inspect one failing brief artifact from `data/briefs`.

4. Confirm whether the brief object passed into `ContentIntelligenceGenerator.generate()` is:

   - `None`
   - missing required fields
   - using empty strings for required fields
   - incompatible with the generator's expected schema
   - not the same topic ID as the selected scored topic

5. Add temporary local diagnostics only if needed. Do not commit debug prints.

6. Determine whether the correct fix is:

   - skipping invalid/missing brief artifacts before generator invocation
   - improving candidate filtering in `ContentIntelligenceService`
   - preventing already-completed CI topics from being selected incorrectly
   - aligning service-level candidate selection with actual available brief artifacts

## Implementation Requirements

1. `ContentIntelligenceService.run()` must never pass a missing or invalid brief into the generator.

2. If a brief artifact exists but is invalid, the service must record a structured failure for that topic and continue processing other candidates.

3. Existing completed CI artifacts must be skipped cleanly.

4. Existing behavior must be preserved for valid briefs.

5. The E2E pipeline must not fail the whole Content Intelligence stage if only one candidate brief is invalid and other candidates are skipped or valid.

6. Do not add new product features.

7. Do not refactor unrelated pipeline stages.

8. Do not change scoring thresholds.

9. Do not change OpenAI/arXiv collection behavior.

10. Do not bypass the architecture:

    Operator / CLI / Job  
    → WorkflowActionExecutor  
    → ActionAvailabilityEngine  
    → ReviewTransitionEngine  
    → Application Services  
    → Storage

## Expected Fix Shape

Prefer a minimal application-service fix.

The service should filter or guard candidates before calling:

```python
ci = generator.generate(
    brief=brief,
    topic_category=candidate["topic_category"],
    published_at=candidate["published_at"],
)
```

The guard should make the failure explicit and non-fatal for the batch.

Expected behavior:

- If `brief is None`: append `ContentIntelligenceFailure(topic_id=..., error="Brief is missing.")` and continue.
- If required brief content fields are empty: append a clear failure and continue.
- If CI already exists for the topic: increment `skipped_count` and continue.
- If generator fails for one topic: record failure and continue.
- The returned `ContentIntelligenceGenerationResult` should accurately report generated, skipped, and failed items.

The top-level pipeline should continue as successful when Content Intelligence has no generated items but only skipped already-complete items and no hard service-level crash occurs.

## Validation Commands

Run these commands exactly:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q
```

Then run local artifact diagnostics:

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

Then run the Streamlit app:

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
- [ ] E2E pipeline reaches Content Intelligence without `Brief is missing.` crashing the full run.
- [ ] `generate-content-intelligence` either generates at least one item or cleanly skips already-existing CI artifacts.
- [ ] Existing content intelligence artifacts remain readable.
- [ ] At least one brief remains visible in the brief viewer.
- [ ] No scoring threshold changes were made.
- [ ] No collection source changes were made.
- [ ] Tests pass with at least the existing baseline count.
- [ ] No debug prints are committed.

## Commit Message

```bash
fix(pipeline): handle missing brief during content intelligence generation (TASK-019)
```