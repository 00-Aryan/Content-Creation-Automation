# TASK-021: Allow idempotent batch generation through workflow gate

**Phase:** 12.0
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

## Objective

Fix the E2E pipeline failure where batch `generate_briefs` is blocked by the workflow availability gate with `Target asset file is already populated.` even though `BriefGenerationService` now skips existing briefs correctly.

## Context

`TASK-020` fixed brief generation idempotency at the service layer.

Direct service validation now passes:

```text
generated_count: 0
skipped_count: 5
failures: []
```

But the Streamlit E2E pipeline still fails at `generate-briefs`:

```text
Brief generation failed: ['Target asset file is already populated.']
```

The remaining issue is not in `BriefGenerationService`.

The pipeline path is:

```text
Streamlit app
→ ServiceClient.run_full_pipeline()
→ WorkflowActionExecutor.execute("run_pipeline", "manifest", "all", ...)
→ PipelineRunService.run()
→ WorkflowActionExecutor.execute("generate_briefs", "brief", "all", ...)
→ ActionAvailabilityEngine blocks before service dispatch
```

`WorkflowActionExecutor.execute()` resolves lifecycle state and dependencies, then calls:

```python
self._availability_engine.is_action_available(
    action_id, target_artifact_type, current_state, dependencies
)
```

before dispatching to the service.

For `generate_briefs`, `ActionAvailabilityEngine` blocks when the current state is not one of:

```python
ArtifactLifecycleState.MISSING
ArtifactLifecycleState.FAILED
ArtifactLifecycleState.REJECTED
```

and returns:

```python
BLOCKED_ASSET_ALREADY_EXISTS
```

which maps to:

```text
Target asset file is already populated.
```

This behavior is correct for a single-artifact regeneration action, but incorrect for batch idempotent generation with:

```python
target_artifact_id == "all"
```

For batch pipeline actions, existing artifacts should be skipped by the application service, not block the whole pipeline.

## Scope

### Files to inspect

* `src/content_creation/workflow/workflow_action_executor.py`
* `src/content_creation/workflow/action_availability_engine.py`
* `src/content_creation/application/pipeline_run_service.py`
* `tests/` files covering workflow executor, action availability, and pipeline execution

### Files allowed to modify

* `src/content_creation/workflow/workflow_action_executor.py`
* `src/content_creation/workflow/action_availability_engine.py` only if executor-level fix is insufficient
* tests covering workflow gate behavior for batch actions

### Files not allowed to modify

* `src/content_creation/application/brief_generation_service.py` unless inspection proves `TASK-020` introduced a bug
* `src/content_creation/generation/brief.py`
* `src/content_creation/models/brief.py`
* prompt files
* scoring engine
* collection logic
* UI files unless the bug is proven to be UI-specific

## Investigation Steps

1. Inspect `WorkflowActionExecutor.execute()` and confirm where action availability is checked before dispatch.

2. Inspect `_resolve_lifecycle_state()` behavior for:

   ```python
   artifact_type == "brief"
   topic_id == "all"
   ```

3. Inspect `_resolve_dependencies()` behavior for:

   ```python
   action_id == "generate_briefs"
   topic_id == "all"
   ```

4. Confirm whether `current_state` for batch `generate_briefs` is being resolved as an already-existing artifact state.

5. Confirm that `_dispatch_to_service()` correctly calls:

   ```python
   BriefGenerationService().run(ctx, top_n=..., api_key=...)
   ```

6. Add tests before or with the fix to reproduce the workflow-gate failure.

7. Do not add diagnostic prints to committed code.

## Implementation Requirements

1. Batch idempotent generation actions must not be blocked just because some target artifacts already exist.

2. The following batch actions with `target_artifact_id == "all"` should be allowed through the workflow gate so their services can handle skip/generate/failure logic:

   * `generate_briefs`
   * `generate_ci`
   * `generate_storyboards`
   * `generate_assets`
   * `build_all_manifests` if present in executor/action registry

3. The single-artifact behavior must remain protected:

   * For a specific topic ID, `generate_briefs` should still be blockable when the target artifact already exists unless explicit regeneration semantics exist.
   * Do not weaken approval/rejection transition safety.
   * Do not allow overwriting populated artifacts.

4. Prefer the smallest correct fix.

5. The fix should live at the workflow boundary, not inside Streamlit.

6. Do not bypass the architecture:

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

7. Do not call repositories or services directly from UI.

8. Do not disable the action availability engine globally.

9. Do not remove `BLOCKED_ASSET_ALREADY_EXISTS`.

10. Do not change scoring thresholds, source collection, prompts, or generation models.

## Expected Fix Shape

Prefer an executor-level batch bypass for known idempotent batch actions.

Example shape:

```python
BATCH_IDEMPOTENT_ACTIONS = {
    "generate_briefs",
    "generate_ci",
    "generate_storyboards",
    "generate_assets",
    "build_all_manifests",
}
```

Then in `WorkflowActionExecutor.execute()`, before calling the availability engine:

```python
is_batch_idempotent_action = (
    target_artifact_id == "all"
    and action_id in BATCH_IDEMPOTENT_ACTIONS
)
```

If `is_batch_idempotent_action` is true, allow dispatch to the application service without applying single-artifact availability blocking.

Important: dependency checks must still be preserved where meaningful. If a batch action has no valid source artifacts, the service should return generated/skipped/failure counts rather than the workflow gate blocking on a fake `"all"` artifact state.

Alternative acceptable fix:

Add explicit batch-aware semantics to `ActionAvailabilityEngine` or lifecycle resolution so that `target_artifact_id == "all"` returns a batch-safe lifecycle state for idempotent generation actions.

Do not implement both unless necessary.

## Required Test Coverage

Add or update tests proving:

1. `WorkflowActionExecutor.execute(ctx, "generate_briefs", "brief", "all", payload)` dispatches to `BriefGenerationService` instead of being blocked by `BLOCKED_ASSET_ALREADY_EXISTS`.

2. Existing brief artifacts in batch mode are skipped by the service and do not block the workflow action.

3. Single-topic `generate_briefs` still respects asset-exists blocking behavior.

4. The existing direct `BriefGenerationService` idempotency tests from `TASK-020` still pass.

5. `run_pipeline` can pass the `generate-briefs` stage when top selected topics already have briefs.

## Validation Commands

Run tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q
```

Run focused tests if available:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest tests/test_brief_generation_service.py tests/test_workflow_action_executor.py --tb=short -q
```

Run direct brief service validation:

```bash
python3 - <<'PY'
from pathlib import Path
from content_creation.application.context import ApplicationContext
from content_creation.application.brief_generation_service import BriefGenerationService

ctx = ApplicationContext.create(Path.cwd())
svc = BriefGenerationService()
res = svc.run(ctx, top_n=5)

print("generated_count:", res.generated_count)
print("skipped_count:", res.skipped_count)
print("failures:", [(f.topic_id, f.error) for f in res.failures])
PY
```

Expected output should be similar to:

```text
generated_count: 0
skipped_count: 5
failures: []
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

* [ ] Streamlit app does not crash.
* [ ] E2E pipeline no longer fails at `generate-briefs` with `Target asset file is already populated.`
* [ ] Batch `generate_briefs` dispatches to `BriefGenerationService`.
* [ ] Existing brief artifacts are skipped cleanly.
* [ ] Single-artifact overwrite protection remains intact.
* [ ] The pipeline reaches the next stage after `generate-briefs`.
* [ ] Tests pass with at least the existing baseline count.
* [ ] No debug prints are committed.
* [ ] No scoring, collection, prompt, or model behavior is changed.

## Commit Message

```bash
fix(workflow): allow idempotent batch generation actions through gate (TASK-021)
```
