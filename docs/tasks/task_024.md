# TASK-024: Explain non-approved manifest assets in blocking reasons

**Phase:** 12.1
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

## Objective

Fix manifest readiness reporting so a manifest cannot show:

```text
Overall Status: PARTIAL
Ready for Planner?: NO
Blocking Reasons: None
```

when one or more non-skipped assets are not approved.

## Confirmed Evidence

The E2E pipeline completes successfully.

The selected manifest for topic:

```text
468a4a589f8d4a953bda8ae2a95bcf1d563f328b0000660a5ce2437a9d3f16c1
```

contains:

```json
{
  "assets": {
    "brief": {
      "status": "approved"
    },
    "script": {
      "status": "approved"
    },
    "carousel": {
      "status": "approved"
    },
    "newsletter": {
      "status": "approved"
    },
    "thumbnail": {
      "status": "draft"
    }
  },
  "overall_status": "partial",
  "blocking_reasons": [],
  "ready_for_planner": false
}
```

This is internally inconsistent.

If `ready_for_planner` is `false`, the manifest must explain why.

The root cause is in `ManifestBuilder.build()`:

* `ready_for_planner` requires all non-skipped assets to be `approved`.
* `blocking_reasons` only records `missing`, `rejected`, and `needs_review`.
* `draft`, `reviewed`, and `unknown` can block readiness but are not reported.

## Scope

### Files to inspect

* `src/content_creation/manifest.py`
* `src/content_creation/models/manifest.py`
* `tests/test_manifest.py`
* UI manifest rendering if needed for display verification only

### Files to modify

* `src/content_creation/manifest.py`
* `tests/test_manifest.py`
* `docs/tasks/task_024.md`
* `WORK_QUEUE.md`

### Files frozen unless absolutely necessary

* `src/content_creation/application/pipeline_run_service.py`
* `src/content_creation/application/asset_generation_service.py`
* `src/content_creation/ui/`
* `src/content_creation/inference/`
* prompt files
* scoring logic
* collection logic
* generation services

## Implementation Requirements

1. Do not modify the working E2E generation pipeline.

2. Do not modify provider/model/API routing.

3. Do not modify prompts.

4. Do not modify asset generation behavior.

5. Do not modify review-state transition behavior.

6. Fix only manifest readiness explanation.

7. Preserve the current `ready_for_planner` rule:

```python
ready_for_planner = all(
    asset.status == "approved"
    for asset in assets.values()
    if asset.status != "skipped"
)
```

8. Preserve `skipped` behavior: skipped assets must not block planner readiness and must not appear in `blocking_reasons`.

9. Preserve hard blocking for:

```text
missing
rejected
```

10. Preserve partial status behavior for review-stage statuses.

11. Add blocking reasons for every non-skipped asset whose status is not `approved`.

12. Required blocking reason examples:

```text
thumbnail: draft
carousel: needs_review
script: reviewed
newsletter: unknown
brief: missing
```

13. Do not add generic reasons like:

```text
Some assets are incomplete
```

The reason must identify the asset type and status.

14. Do not mark `draft` as `blocked` overall unless the existing overall status rules already do so. The expected status for approved assets plus one draft asset remains:

```text
overall_status: partial
ready_for_planner: false
blocking_reasons: ["thumbnail: draft"]
```

15. Do not treat `reviewed` as approved unless the existing domain contract explicitly says reviewed equals approved. For this task, only `approved` is planner-ready.

## Expected Fix Shape

Replace the current blocking-reason logic:

```python
blocking_reasons = []
for asset_type, asset in assets.items():
    if asset.status == "missing":
        blocking_reasons.append(f"{asset_type}: missing")
    elif asset.status == "rejected":
        blocking_reasons.append(f"{asset_type}: rejected")
    elif asset.status == "needs_review":
        blocking_reasons.append(f"{asset_type}: needs_review")
```

with status-complete logic:

```python
blocking_reasons = []
for asset_type, asset in assets.items():
    if asset.status == "skipped":
        continue
    if asset.status != "approved":
        blocking_reasons.append(f"{asset_type}: {asset.status}")
```

Keep `overall_status` logic unchanged unless tests prove the current logic is inconsistent.

## Required Tests

Update `tests/test_manifest.py` to prove:

1. A manifest with all non-skipped assets approved has:

```text
ready_for_planner == True
blocking_reasons == []
overall_status == "complete"
```

2. A manifest with one draft required asset has:

```text
ready_for_planner == False
blocking_reasons includes "thumbnail: draft"
overall_status == "partial"
```

3. A manifest with one `needs_review` asset still includes:

```text
carousel: needs_review
```

4. A manifest with one `reviewed` asset includes:

```text
script: reviewed
```

5. A manifest with one `missing` asset includes:

```text
brief: missing
```

6. A manifest with skipped optional assets does not include skipped assets in `blocking_reasons`.

7. `ready_for_planner` remains false whenever any non-skipped asset is not approved.

## Validation Commands

Run focused tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest tests/test_manifest.py --tb=short -q
```

Run full tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q
```

Run the local manifest diagnostic again:

```bash
python3 - <<'PY'
from pathlib import Path
import json

topic_id = "468a4a589f8d4a953bda8ae2a95bcf1d563f328b0000660a5ce2437a9d3f16c1"
manifest_path = Path("data/manifests") / f"{topic_id}.json"

print("manifest exists:", manifest_path.exists())
if manifest_path.exists():
    data = json.loads(manifest_path.read_text())
    print("overall_status:", data.get("overall_status"))
    print("ready_for_planner:", data.get("ready_for_planner"))
    print("blocking_reasons:", data.get("blocking_reasons"))
    print("thumbnail_status:", data.get("assets", {}).get("thumbnail", {}).get("status"))
PY
```

If the manifest file was generated before the fix, rerun manifest build or the full pipeline before expecting persisted JSON to change.

Run Streamlit:

```bash
uv run streamlit run src/content_creation/ui/app.py
```

Then open Asset Workshop and confirm:

```text
Overall Status: PARTIAL
Ready for Planner?: NO
Blocking Reasons: thumbnail: draft
```

or equivalent asset/status-specific reason.

## Success Criteria

* [x] Manifest with `thumbnail: draft` no longer shows empty `blocking_reasons`.
* [x] `Ready for Planner?: NO` always has at least one concrete reason unless all non-skipped assets are approved.
* [x] Skipped optional assets do not appear as blockers.
* [x] Approved assets do not appear as blockers.
* [x] Overall status semantics remain unchanged.
* [x] E2E generation pipeline behavior is unchanged.
* [x] Focused manifest tests pass.
* [x] Full test suite passes.
* [x] Worktree is clean after commit.

## Commit Message

```bash
fix(manifest): explain non-approved planner blockers (TASK-024)
```
