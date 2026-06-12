# TASK-035: Format ISO timestamps into readable UI display text

**Phase:** 12.2  
**Status:** DONE  
**Priority:** MEDIUM  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Replace raw ISO 8601 timestamp display such as `2026-05-19T11:11:24.481514+00:00` with readable operator-facing date/time text in UI pages.

## Scope

### Files to modify

- `src/content_creation/ui/pages/3_brief_viewer.py` — inspect and fix only if raw timestamps are displayed.
- `src/content_creation/ui/pages/4_storyboard.py` — inspect and fix only if raw timestamps are displayed.
- `src/content_creation/ui/pages/5_asset_workshop.py` — inspect and fix raw generated/updated timestamp display.
- `src/content_creation/ui/pages/6_operations_dashboard.py` — inspect and fix only if raw job/artifact timestamps are displayed.
- `src/content_creation/ui/components/` — add or update a small timestamp formatting helper if repeated formatting is needed across pages.
- `tests/` — add or update focused tests for timestamp display formatting.

### Files to create

- `docs/phase-12.2-timestamp-display-cleanup.md` — record raw timestamp evidence, root cause, fix strategy, and validation evidence.

### Files to NOT touch

All other files.

## Constraints

- This is a display-layer cleanup task only.
- Do not change serialized timestamp values in JSON files.
- Do not change model schemas.
- Do not change generation timestamps or storage behavior.
- Do not change workflow transition behavior.
- Do not change review status display behavior from TASK-034 except where timestamp formatting is colocated.
- Do not fix Streamlit deprecation warnings in this task.
- Do not fix layout stretching in this task.
- Do not modify frozen directories:
  - `src/content_creation/models/`
  - `src/content_creation/generation/`
  - `prompts/`
- UI must not access repositories or services directly.
- Preserve existing architecture: UI routes through existing client/application/workflow layers.
- Missing, malformed, or timezone-less timestamps must not crash the UI.
- Full test suite must not drop below the current baseline of 993 passing tests.

## Implementation Steps

1. Run baseline validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=no -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   993 passed
   ```

   Exact count may be higher, but must not be lower.

2. Locate raw timestamp rendering in UI code:

   ```bash
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "generated_at|created_at|updated_at|completed_at|started_at|timestamp|isoformat|strftime|datetime" \
     src/content_creation/ui tests | head -260
   ```

3. Inspect likely UI pages:

   ```bash
   sed -n '1,340p' src/content_creation/ui/pages/3_brief_viewer.py
   sed -n '1,360p' src/content_creation/ui/pages/4_storyboard.py
   sed -n '1,420p' src/content_creation/ui/pages/5_asset_workshop.py
   sed -n '1,420p' src/content_creation/ui/pages/6_operations_dashboard.py
   ```

4. Check whether a UI helper already exists:

   ```bash
   find src/content_creation/ui -maxdepth 3 -type f | sort
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "format_.*time|format_.*date|display_.*time|display_.*date|human.*time|status_label" \
     src/content_creation/ui tests | head -220
   ```

5. Diagnose whether raw ISO timestamps are shown from:

   - asset `generated_at`
   - brief/storyboard timestamps
   - manifest timestamps
   - job/operation timestamps
   - direct `str(timestamp)` rendering
   - direct dictionary display

6. Write diagnostics to:

   ```text
   docs/phase-12.2-timestamp-display-cleanup.md
   ```

   The diagnostic file must include:

   ```markdown
   # Phase 12.2 Timestamp Display Cleanup

   ## Baseline

   - Test count before change:
   - Raw timestamp fields found:
   - Affected UI pages:

   ## Root Cause

   Explain exactly why raw ISO timestamps reached the operator.

   ## Fix Strategy

   Explain where timestamp formatting was applied and why.

   ## Post-Fix Evidence

   - Test count after change:
   - Tests added or updated:
   - Example operator-facing timestamp after change:

   ## Risk Notes

   Mention any remaining time-zone or localization decision that belongs in a later task.
   ```

7. Implement the smallest correct fix.

   Preferred strategy:

   - Create or update a UI-only helper if more than one page needs timestamp formatting.
   - Keep formatting local if only one page is affected.
   - Do not modify model or storage code.

   Required behavior:

   - `2026-05-19T11:11:24.481514+00:00` displays as readable text such as `May 19, 2026, 11:11 AM UTC`.
   - Date-only values remain readable.
   - Missing values display as `Not available` or a similarly clear label.
   - Invalid timestamp strings do not crash the UI.
   - Raw ISO strings with `T`, microseconds, or `+00:00` should not be shown directly when displayed as metadata.
   - Existing serialized JSON remains unchanged.

8. Add or update tests.

   At minimum, tests must prove:

   - timezone-aware ISO timestamp formats into readable text
   - ISO timestamp with microseconds formats into readable text
   - missing timestamp does not crash
   - malformed timestamp does not crash
   - formatted output does not contain raw `T11:11:24.481514+00:00` style text

9. Run targeted validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest tests --tb=short -q -k "ui or timestamp or date or time or status or dashboard or asset or storyboard or brief"
   ```

10. Run full validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    Expected result:

    ```text
    993 passed
    ```

    Exact count may be higher, but must not be lower.

11. Update `docs/phase-12.2-timestamp-display-cleanup.md` with post-fix evidence.

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -m py_compile src/content_creation/ui/pages/3_brief_viewer.py
python3 -m py_compile src/content_creation/ui/pages/4_storyboard.py
python3 -m py_compile src/content_creation/ui/pages/5_asset_workshop.py
python3 -m py_compile src/content_creation/ui/pages/6_operations_dashboard.py

uv run python -m pytest tests --tb=short -q -k "ui or timestamp or date or time or status or dashboard or asset or storyboard or brief"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Success Criteria

- [ ] Root cause of raw ISO timestamp display is documented.
- [ ] UI pages no longer display raw ISO timestamp strings for operator-facing metadata.
- [ ] Timestamps display in readable text such as `May 19, 2026, 11:11 AM UTC`.
- [ ] Missing timestamps do not crash the UI.
- [ ] Malformed timestamps do not crash the UI.
- [ ] Serialized timestamp values remain unchanged.
- [ ] Tests cover timestamp formatting behavior.
- [ ] `docs/phase-12.2-timestamp-display-cleanup.md` contains before/after evidence.
- [ ] Full test suite shows at least 993 passed.
- [ ] No workflow, generation, scoring, prompt, layout, or Streamlit deprecation changes are included.

## Depends On

TASK-034

## Commit Message

```text
fix(ui): format timestamps for readable display (TASK-035)
```
