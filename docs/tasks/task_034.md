# TASK-034: Replace raw review enum labels with readable UI status text

**Phase:** 12.2  
**Status:** DONE  
**Priority:** MEDIUM  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Replace raw review/status enum labels such as `ReviewStatus.APPROVED`, `ReviewStatus.NEEDS_REVIEW`, or similar internal enum representations with readable operator-facing labels in the UI.

## Scope

### Files to modify

- `src/content_creation/ui/pages/5_asset_workshop.py` — replace raw asset review status display with readable labels or badges.
- `src/content_creation/ui/pages/4_storyboard.py` — inspect and fix only if storyboard review status also displays raw enum strings.
- `tests/` — add or update focused tests for status label formatting if existing UI/helper tests support it.

### Files to create

- `docs/phase-12.2-review-status-label-cleanup.md` — record enum-label leak evidence, root cause, fix strategy, and validation evidence.

### Files to NOT touch

All other files.

## Constraints

- This is a display-layer cleanup task only.
- Do not change `ReviewStatus` enum definitions.
- Do not change serialized status values.
- Do not change workflow transition rules.
- Do not change approval/rejection behavior.
- Do not change terminal-state error handling from TASK-033.
- Do not fix timestamp formatting in this task.
- Do not change scoring, script generation, thumbnail generation, or prompts.
- Do not modify frozen directories:
  - `src/content_creation/models/`
  - `src/content_creation/generation/`
  - `prompts/`
- UI must not access repositories/services directly.
- Preserve current architecture: UI routes through existing client/application/workflow layers.
- Full test suite must not drop below the current baseline of 989 passing tests.

## Implementation Steps

1. Run baseline validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=no -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   989 passed
   ```

   Exact count may be higher, but must not be lower.

2. Locate raw enum/status rendering:

   ```bash
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "ReviewStatus|review_status|status.*write|status.*markdown|st\\.|badge|APPROVED|REJECTED|NEEDS_REVIEW" \
     src/content_creation/ui tests | head -240
   ```

3. Read likely UI files before changing anything:

   ```bash
   sed -n '1,380p' src/content_creation/ui/pages/5_asset_workshop.py
   sed -n '1,320p' src/content_creation/ui/pages/4_storyboard.py
   ```

4. Find whether a status formatting helper already exists:

   ```bash
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "format.*status|status.*label|status.*badge|ReviewStatus" \
     src/content_creation/ui src/content_creation/shared tests | head -220
   ```

5. Diagnose the correct display fix.

   Preferred strategy:

   - Use a small local helper if the issue is limited to one page.
   - Use an existing UI helper if one already exists.
   - Avoid creating a new shared module unless repeated status formatting is clearly duplicated across multiple UI pages.

6. Write diagnostics to:

   ```text
   docs/phase-12.2-review-status-label-cleanup.md
   ```

   The diagnostic file must include:

   ```markdown
   # Phase 12.2 Review Status Label Cleanup

   ## Baseline

   - Test count before change:
   - Raw enum/status labels found:
   - Affected UI pages:

   ## Root Cause

   Explain exactly why raw enum/status values reached the operator.

   ## Fix Strategy

   Explain where display formatting was applied and why.

   ## Post-Fix Evidence

   - Test count after change:
   - Tests added or updated:
   - Operator-facing labels after change:

   ## Risk Notes

   Mention any remaining UI display cleanup that belongs in a later task.
   ```

7. Implement the smallest correct fix.

   Required behavior:

   - `ReviewStatus.APPROVED` displays as `Approved`.
   - `ReviewStatus.REJECTED` displays as `Rejected`.
   - `ReviewStatus.NEEDS_REVIEW` displays as `Needs review`.
   - Plain string values like `"approved"` also display as `Approved`.
   - Unknown or missing status values should not crash the UI.
   - Internal enum values must remain unchanged in data models and workflow logic.

8. Add or update tests where practical.

   At minimum, tests should prove formatting behavior for:

   - enum instance values
   - plain string values
   - missing/unknown values
   - no raw `ReviewStatus.` prefix in formatted output

9. Run targeted validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest tests --tb=short -q -k "ui or storyboard or asset or status or review"
   ```

10. Run full validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    Expected result:

    ```text
    989 passed
    ```

    Exact count may be higher, but must not be lower.

11. Update `docs/phase-12.2-review-status-label-cleanup.md` with post-fix evidence.

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -m py_compile src/content_creation/ui/pages/5_asset_workshop.py
python3 -m py_compile src/content_creation/ui/pages/4_storyboard.py

uv run python -m pytest tests --tb=short -q -k "ui or storyboard or asset or status or review"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Success Criteria

- [ ] Root cause of raw enum/status label exposure is documented.
- [ ] Asset Workshop no longer displays raw enum labels like `ReviewStatus.APPROVED`.
- [ ] Storyboard page is either fixed or documented as unaffected.
- [ ] Status labels are readable: `Approved`, `Rejected`, `Needs review`.
- [ ] Unknown or missing status values do not crash the UI.
- [ ] Tests cover status formatting where practical.
- [ ] `docs/phase-12.2-review-status-label-cleanup.md` contains before/after evidence.
- [ ] Full test suite shows at least 989 passed.
- [ ] No workflow, generation, scoring, prompt, timestamp, or terminal-state behavior changes are included.

## Depends On

TASK-033

## Commit Message

```text
fix(ui): display readable review status labels (TASK-034)
```
