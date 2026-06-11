# TASK-028: Update dashboard to show live pipeline artifact counts

**Phase:** 12.2
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** —
**Requires approval:** NO

---

## Source References
- UI screenshot: dashboard shows "0" for all Pipeline Queue Metrics
  (Staged Topics, Scored Topics, Briefs, Storyboards, Topic Manifests)
- Current confirmed counts: briefs=11, storyboards=8, manifests=11, scripts=8

---

## Objective
Make the dashboard Pipeline Queue Metrics show real counts from the data directories, so the operator sees the actual pipeline state instead of all zeros.

---

## Context
The dashboard screenshot shows all metrics as 0. But we know the pipeline has generated real artifacts: 11 briefs, 8 storyboards, 8 scripts, 11 manifests. The dashboard is not reading from the data directories — it may be reading from a database table that is empty, or the metric query is failing silently.

When the operator opens the app in the morning, they should see:
```
Staged Topics: 5488    Scored Topics: 5488
Briefs: 11             Storyboards: 8
```
Not zeros.

---

## Scope

### Files to modify
- `src/content_creation/ui/app.py` OR the main dashboard page
  — find where the Pipeline Queue Metrics are computed and fix the data source

### Files to NOT touch
- All backend/domain/application code
- All test files
- All other page files

---

## Constraints
- Read `src/content_creation/ui/app.py` and the main dashboard page fully before changing anything
- If the metrics come from a service call that returns 0, first understand WHY before patching
- Do NOT hardcode numbers — read from actual storage
- Acceptable fallback: if the service call fails, read directly from `pathlib.Path('data/briefs').glob('*.json')` etc. as a UI-layer fallback
- The fix must stay in the UI layer

---

## Implementation Steps

1. Read the main dashboard code (likely `src/content_creation/ui/app.py` or a dashboard component).

2. Find the Pipeline Queue Metrics section — where `Staged Topics`, `Scored Topics`, `Briefs`, etc. are computed.

3. Check what data source they use. Common causes of zeros:
   - Calling a service method that reads from a database that was never populated
   - A service call that silently fails (now caught by TASK-016 error handlers)
   - Reading from a queue/job system instead of from data directories

4. Fix the data source to read from the actual storage:
   ```python
   # Example fallback approach
   staged_count = len(list(Path('data/staged').glob('*.json')))
   scored_count = len(list(Path('data/scored').glob('*.json')))
   brief_count = len(list(Path('data/briefs').glob('*.json')))
   storyboard_count = len(list(Path('data/storyboards').glob('*.json')))
   manifest_count = len(list(Path('data/manifests').glob('*.json')))
   ```
   OR use the existing storage service if it provides these counts correctly.

5. Display the counts in the existing metric cards.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Syntax checks on modified files
python3 -c "
import ast
for path in ['src/content_creation/ui/app.py']:
    try:
        ast.parse(open(path).read())
        print(f'OK: {path}')
    except SyntaxError as e:
        print(f'FAIL: {path} line {e.lineno}: {e.msg}')
"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 985 passed
```

---

## Success Criteria
- [ ] Dashboard Pipeline Queue Metrics show non-zero counts matching actual data directories
- [ ] Counts match: staged≥5488, scored≥5488, briefs≥11, storyboards≥8
- [ ] No hardcoded numbers
- [ ] Test suite shows ≥ 985 passed

---

## Depends On
None

## Blocks
None

---

## Commit Message
```
fix(ui): show real pipeline artifact counts on dashboard instead of zeros (TASK-028)
```

---

## Agent Notes
Read the dashboard code fully first. If the service call exists and works,
use it. Only fall back to direct pathlib reads if the service consistently
returns 0 despite data existing. Do not change the service layer itself.