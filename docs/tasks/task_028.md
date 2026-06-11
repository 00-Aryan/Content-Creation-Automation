# TASK-028: Update dashboard to show live pipeline artifact counts

**Phase:** 12.2
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** —
**Requires approval:** NO

---

## Source References

* UI screenshot: dashboard shows `0` for all Pipeline Queue Metrics:

  * Staged Topics
  * Scored Topics
  * Briefs
  * Storyboards
  * Topic Manifests
* Confirmed local data exists:

  * `data/briefs` contains generated brief JSON files
  * `data/storyboards` contains generated storyboard JSON files
  * `data/scripts` contains generated script JSON files
  * `data/manifests` contains generated manifest JSON files
* Previous attempted implementation found the real metric source in:

  * `src/content_creation/ui/services/client.py`
  * method: `ServiceClient.get_metric_counts()`

---

## Objective

Make the main dashboard Pipeline Queue Metrics show real artifact counts from the local `data/` directories instead of showing all zeros.

The operator should see the actual current pipeline state when opening the app.

Example expected behavior:

```text
Staged Topics: actual count from data/staged/*.json
Scored Topics: actual count from data/scored/*.json
Briefs: actual count from data/briefs/*.json
Storyboards: actual count from data/storyboards/*.json
Topic Manifests: actual count from data/manifests/*.json
```

Do not hardcode any numbers.

---

## Context

The dashboard currently shows all Pipeline Queue Metrics as `0`, even though the pipeline has generated real artifacts.

The main dashboard renders metric cards using a UI client call. Prior analysis found that the dashboard does not compute these values directly inside `app.py`; it calls a service/client method.

The correct fix location is therefore the UI service layer:

```text
src/content_creation/ui/services/client.py
```

This is still UI-layer code. It is not backend/domain/application logic.

The previous run attempted to update `client.py`, which was technically correct, but the task runner reverted the change because the task card incorrectly declared only `src/content_creation/ui/app.py` as in scope.

This task corrects that scope.

---

## Scope

### Files to inspect

* `src/content_creation/ui/app.py`
* `src/content_creation/ui/services/client.py`
* `src/content_creation/ui/components/status.py`
* `src/content_creation/storage/local.py`
* existing UI tests, if any

### Files to modify

* `src/content_creation/ui/services/client.py`
* `docs/tasks/task_028.md`
* `WORK_QUEUE.md`

### Files frozen unless absolutely necessary

* `src/content_creation/ui/app.py`
* `src/content_creation/ui/pages/`
* `src/content_creation/application/`
* `src/content_creation/domains/`
* `src/content_creation/inference/`
* `src/content_creation/workflow/`
* prompt files
* generation services
* scoring logic
* collection logic

---

## Constraints

1. Read `src/content_creation/ui/app.py` before changing anything.

2. Read `src/content_creation/ui/services/client.py` before changing anything.

3. Confirm how `render_metric_cards()` receives metric values.

4. Confirm where `get_metric_counts()` currently gets its data.

5. Keep the fix in the UI layer.

6. Do not hardcode counts.

7. Do not parse thousands of JSON files into Pydantic models just to count files.

8. Prefer direct file counting with `Path.glob("*.json")` for dashboard metrics because the dashboard only needs counts.

9. The metric count logic must tolerate:

   * missing directories
   * empty directories
   * invalid JSON files
   * partially generated local data

10. Invalid JSON should not break dashboard metric rendering because counting files does not require parsing their contents.

11. Do not modify backend/domain/application services.

12. Do not modify the E2E pipeline execution flow.

13. Do not modify generation behavior.

14. Do not modify prompts.

15. Do not modify test files unless a narrow existing UI/client test already covers this method and must be updated.

---

## Required Behavior

`ServiceClient.get_metric_counts()` should return counts from the actual local storage directories.

Required keys should match the existing dashboard metric card contract. Do not invent new card names unless the existing UI already expects them.

Expected source directories:

```text
data/staged
data/scored
data/briefs
data/storyboards
data/manifests
```

If the existing dashboard also displays other artifact counts, include them only if the current UI contract already expects them.

Recommended implementation approach:

```python
from pathlib import Path

def _count_json_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.glob("*.json"))
```

Use the project root or the existing `ApplicationContext` / `LocalStorage` base path if available.

If context pathing is ambiguous, use a safe fallback to the current working directory:

```python
base_dir = self.ctx.storage.base_dir if available else Path.cwd()
```

Then count:

```python
data_dir = base_dir / "data"
```

Do not use hardcoded absolute paths.

---

## Implementation Steps

1. Read the main dashboard entry point:

```bash
sed -n '1,220p' src/content_creation/ui/app.py
```

2. Read the UI client:

```bash
sed -n '1,260p' src/content_creation/ui/services/client.py
```

3. Read the metric card renderer:

```bash
sed -n '1,220p' src/content_creation/ui/components/status.py
```

4. Identify the exact return shape of `ServiceClient.get_metric_counts()`.

5. Update `ServiceClient.get_metric_counts()` so it counts JSON files directly from the corresponding `data/` directories.

6. Preserve the existing public method name and return shape.

7. Add a small private helper in `client.py` if needed:

```python
def _count_json_files(self, directory: Path) -> int:
    ...
```

8. Keep the method fast. It should count files, not load and validate all artifact JSON.

9. Do not change `render_metric_cards()` unless inspection proves the component expects a different key contract.

10. Do not modify `app.py` unless inspection proves the dashboard itself is passing the wrong object to `render_metric_cards()`.

---

## Validation

Run syntax checks:

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 - <<'PY'
import ast
from pathlib import Path

paths = [
    Path("src/content_creation/ui/services/client.py"),
    Path("src/content_creation/ui/app.py"),
    Path("src/content_creation/ui/components/status.py"),
]

for path in paths:
    try:
        ast.parse(path.read_text())
        print(f"OK: {path}")
    except SyntaxError as e:
        print(f"FAIL: {path} line {e.lineno}: {e.msg}")
        raise
PY
```

Run direct metric diagnostic:

```bash
python3 - <<'PY'
from content_creation.ui.services.client import ServiceClient

client = ServiceClient()
counts = client.get_metric_counts()

print(counts)

required = [
    "staged_topics",
    "scored_topics",
    "briefs",
    "storyboards",
    "manifests",
]

for key in required:
    print(key, counts.get(key))
PY
```

If the actual keys differ, report the real keys and ensure they match the dashboard renderer contract.

Run file-count cross-check:

```bash
python3 - <<'PY'
from pathlib import Path

for name in ["staged", "scored", "briefs", "storyboards", "manifests"]:
    path = Path("data") / name
    print(name, len(list(path.glob("*.json"))) if path.exists() else 0)
PY
```

Run full tests:

```bash
uv run python -m pytest --tb=short -q
```

Expected:

```text
>= 985 passed
```

---

## UI Validation

Run Streamlit:

```bash
uv run streamlit run src/content_creation/ui/app.py
```

Open the main dashboard and verify Pipeline Queue Metrics are no longer all zero.

Expected:

```text
Staged Topics: non-zero if data/staged has JSON files
Scored Topics: non-zero if data/scored has JSON files
Briefs: non-zero if data/briefs has JSON files
Storyboards: non-zero if data/storyboards has JSON files
Topic Manifests: non-zero if data/manifests has JSON files
```

The displayed values must match local file counts.

---

## Success Criteria

* [ ] Dashboard Pipeline Queue Metrics show real counts from local `data/` directories.
* [ ] Counts are not hardcoded.
* [ ] `ServiceClient.get_metric_counts()` remains the public metric source used by the dashboard.
* [ ] The method is fast and does not parse every JSON file into Pydantic models just to count files.
* [ ] Missing directories return `0` instead of raising.
* [ ] Invalid JSON files do not break metric count rendering.
* [ ] No backend/domain/application code is modified.
* [ ] Syntax checks pass.
* [ ] Full test suite shows `>= 985 passed`.
* [ ] `WORK_QUEUE.md` is updated from `PENDING` to `DONE` after implementation.
* [ ] Worktree is clean after commit.

---

## Depends On

```text
TASK-027
```

## Blocks

```text
TASK-029
```

---

## Commit Message

```bash
fix(ui): show real pipeline artifact counts on dashboard instead of zeros (TASK-028)
```

---

## Agent Notes

The previous run discovered that the correct technical fix belongs in:

```text
src/content_creation/ui/services/client.py
```

The task runner reverted that attempt only because the task card scope incorrectly listed `src/content_creation/ui/app.py`.

Do not force the fix into `app.py` if `app.py` only calls `client.get_metric_counts()`.

Fix the metric source where it actually lives.
