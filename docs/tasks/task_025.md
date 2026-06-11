# TASK-025: Fix misleading Worker Daemon CRITICAL alert on Operations Dashboard

**Phase:** 12.2
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

---

## Source References
- Handoff doc: Phase 12.1 remaining observations § 1. Worker Daemon alert

---

## Objective
Change the Worker Daemon health status from CRITICAL to a non-alarming state when no jobs are queued, so the operator does not think the system is broken during normal manual Streamlit operation.

---

## Context
The Operations Dashboard shows:
```
Worker Daemon: UNKNOWN
[CRITICAL] No active workers
```
This is misleading. When running the app manually via Streamlit without a background daemon, having no active workers is the expected state — it only becomes a real problem when there are jobs queued that cannot be processed. The CRITICAL severity makes the operator think something is broken when everything is actually fine.

---

## Scope

### Files to modify
- `src/content_creation/ui/pages/6_operations_dashboard.py`
  — change Worker Daemon health check logic to distinguish between
  "no workers AND no queued jobs" (acceptable) vs
  "no workers AND jobs are queued" (actual problem)

### Files to NOT touch
All other files. Do not modify the WorkerDaemon class itself.

---

## Constraints
- Read the entire `6_operations_dashboard.py` before making any change
- Do NOT change any other health check — only the Worker Daemon section
- Do NOT modify the WorkerDaemon class or any infrastructure code
- The fix must be in the UI layer only — just change how the status is displayed

---

## Implementation Steps

1. Read `src/content_creation/ui/pages/6_operations_dashboard.py` fully.

2. Find the section that renders the Worker Daemon health check. It likely calls
   something like `client.get_worker_status()` or reads from a health check response.

3. Find where the CRITICAL alert for "No active workers" is displayed.

4. Change the logic to:
   ```python
   # Check if any jobs are actually queued or running
   # If no jobs are waiting, "no active workers" is acceptable
   # Only show CRITICAL if jobs are queued but no worker can process them
   
   if no_active_workers and no_queued_jobs:
       # Show as INFO or WARNING, not CRITICAL
       st.info("ℹ️ Worker Daemon: No active workers (no jobs queued — this is normal for manual operation)")
   elif no_active_workers and has_queued_jobs:
       # This is the real problem
       st.error("⚠️ Worker Daemon: No active workers but jobs are queued — pipeline may be stalled")
   ```

5. If the dashboard cannot easily determine queued job count, at minimum change
   the display from CRITICAL to WARNING with a note:
   ```
   Worker Daemon: Not running (expected in manual operation mode)
   ```

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -c "
import ast
src = open('src/content_creation/ui/pages/6_operations_dashboard.py').read()
try:
    ast.parse(src)
    print('PASS: syntax OK')
except SyntaxError as e:
    print(f'FAIL: {e.lineno}: {e.msg}')
"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 985 passed
```

---

## Success Criteria
- [ ] Worker Daemon no longer shows CRITICAL when no jobs are queued
- [ ] The change is only in the UI display layer — no infrastructure code modified
- [ ] `6_operations_dashboard.py` passes syntax check
- [ ] Test suite shows ≥ 985 passed

---

## Depends On
None

## Blocks
None

---

## Commit Message
```
fix(ui): show Worker Daemon as informational (not CRITICAL) when no jobs queued (TASK-025)
```