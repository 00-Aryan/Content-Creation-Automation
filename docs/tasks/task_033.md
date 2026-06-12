# TASK-033: Replace raw terminal-state errors with operator-friendly messages

**Phase:** 12.2  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Replace raw workflow terminal-state errors such as `The artifact is already in a terminal state.` with clear operator-facing messages and prevent redundant approval/rejection actions where possible.

## Scope

### Files to modify

- `src/content_creation/ui/pages/5_asset_workshop.py` — handle terminal-state approval/rejection failures with readable operator messages and avoid showing raw internal exception text.
- `src/content_creation/workflow/action_availability_engine.py` — inspect only; modify only if action availability should block redundant terminal-state actions before UI submission.
- `src/content_creation/workflow/review_transition_engine.py` — inspect only; modify only if the domain-layer error contract needs a clearer typed reason or message.
- `tests/` — add or update focused tests for terminal-state action handling and operator-facing message behavior.

### Files to create

- `docs/phase-12.2-terminal-state-message-cleanup.md` — record current raw error behavior, root cause, chosen fix layer, and validation evidence.

### Files to NOT touch

All other files.

## Constraints

- Do not weaken workflow state protection. Terminal-state artifacts must remain protected from invalid transitions.
- Do not allow re-approval or re-rejection of already-terminal artifacts unless an existing workflow rule explicitly permits it.
- Do not bypass `WorkflowActionExecutor`, `ActionAvailabilityEngine`, or `ReviewTransitionEngine`.
- UI must not access repositories or services directly.
- Prefer preventing invalid actions through availability/disabled UI state if the existing architecture supports it.
- If the invalid action still reaches execution, show a clean operator-facing message instead of raw internal text.
- Do not fix raw enum labels in this task.
- Do not fix timestamp formatting in this task.
- Do not change thumbnail generation, script generation, scoring, or prompt behavior in this task.
- Do not modify frozen directories:
  - `src/content_creation/models/`
  - `src/content_creation/generation/`
  - `prompts/`
- Preserve existing public interfaces unless a test proves the interface is already incorrect.
- Full test suite must not drop below the current baseline of 987 passing tests.

## Implementation Steps

1. Run baseline validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=no -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   987 passed
   ```

   Exact count may be higher, but must not be lower.

2. Locate terminal-state error sources:

   ```bash
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "terminal state|already.*terminal|ArtifactLifecycleState|ReviewTransition|can_transition|approve|reject" \
     src/content_creation/workflow src/content_creation/ui tests | head -220
   ```

3. Read the relevant files before changing anything:

   ```bash
   sed -n '1,280p' src/content_creation/ui/pages/5_asset_workshop.py
   sed -n '1,320p' src/content_creation/workflow/action_availability_engine.py
   sed -n '1,320p' src/content_creation/workflow/review_transition_engine.py
   ```

4. Find existing tests for workflow action availability and review transitions:

   ```bash
   find tests -type f | grep -Ei 'workflow|availability|transition|review|asset|workshop'
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "terminal state|already.*terminal|ActionAvailabilityEngine|ReviewTransitionEngine|APPROVED|REJECTED" \
     tests | head -220
   ```

5. Reproduce or identify the raw operator-facing behavior.

   Check whether the raw message comes from:

   - `ActionAvailabilityEngine`
   - `ReviewTransitionEngine`
   - `WorkflowActionExecutor`
   - `5_asset_workshop.py` generic exception rendering
   - status/action button rendering logic

6. Write diagnostics to:

   ```text
   docs/phase-12.2-terminal-state-message-cleanup.md
   ```

   The diagnostic file must include:

   ```markdown
   # Phase 12.2 Terminal-State Message Cleanup

   ## Baseline

   - Test count before change:
   - Raw message observed or source located:
   - Affected UI/action path:

   ## Root Cause

   Explain exactly why raw terminal-state text reaches the operator.

   ## Fix Strategy

   Explain whether the fix was applied in UI handling, action availability, transition handling, or a combination.

   ## Post-Fix Evidence

   - Test count after change:
   - Tests added or updated:
   - Operator-facing message after change:

   ## Risk Notes

   Mention any remaining UX issue that belongs in a later task.
   ```

7. Implement the smallest correct fix.

   Required behavior:

   - Already-approved assets should not show a confusing approval failure.
   - Already-rejected assets should not show a confusing rejection failure.
   - If an operator attempts an invalid terminal-state transition, the message should be readable, for example:
     - `This asset is already approved. No further approval is needed.`
     - `This asset is already rejected. No further rejection is needed.`
     - `This asset is already in a final review state. Choose a different asset or reset it through a supported workflow.`
   - Internal/domain errors may still be logged for debugging.
   - Raw exception/internal policy text must not be displayed directly in the Streamlit UI.

8. Add or update tests.

   At minimum, tests must prove:

   - terminal-state artifacts remain protected from invalid transitions
   - the operator-facing message is readable and does not expose raw internal text
   - already-approved approval action is handled safely
   - already-rejected rejection action is handled safely
   - existing workflow transition tests still pass

9. Run targeted validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest tests --tb=short -q -k "workflow or availability or transition or review or asset"
   ```

10. Run full validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    Expected result:

    ```text
    987 passed
    ```

    Exact count may be higher, but must not be lower.

11. Update `docs/phase-12.2-terminal-state-message-cleanup.md` with post-fix evidence.

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -m py_compile src/content_creation/ui/pages/5_asset_workshop.py
python3 -m py_compile src/content_creation/workflow/action_availability_engine.py
python3 -m py_compile src/content_creation/workflow/review_transition_engine.py

uv run python -m pytest tests --tb=short -q -k "workflow or availability or transition or review or asset"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Success Criteria

- [ ] Root cause of raw terminal-state message exposure is documented.
- [ ] Terminal-state workflow protection remains intact.
- [ ] Already-approved approval attempts are blocked or handled with a readable message.
- [ ] Already-rejected rejection attempts are blocked or handled with a readable message.
- [ ] Raw internal text such as `The artifact is already in a terminal state.` is not displayed directly to the operator.
- [ ] Tests cover terminal-state action handling.
- [ ] `docs/phase-12.2-terminal-state-message-cleanup.md` contains before/after evidence.
- [ ] Full test suite shows at least 987 passed.
- [ ] No enum-label, timestamp, thumbnail, scoring, script, or prompt changes are included.

## Depends On

TASK-032

## Commit Message

```text
fix(ui): replace terminal-state errors with readable messages (TASK-033)
```
