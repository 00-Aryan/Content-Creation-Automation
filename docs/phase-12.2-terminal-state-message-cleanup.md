# Phase 12.2 Terminal-State Message Cleanup

## Baseline

- Test count before change: 987 passed
- Raw message observed or source located: "The artifact is already in a terminal state." from `ActionAvailabilityEngine` and "Terminal state: {from_status.value} has no outgoing transitions" from `ReviewTransitionEngine`.
- Affected UI/action path: Radio buttons for asset decisions in `src/content_creation/ui/pages/5_asset_workshop.py` and backend action application in `client.py` -> `WorkflowActionExecutor`.

## Root Cause

When an operator attempts to approve/reject an asset that is already in a terminal state (APPROVED or REJECTED), the action availability engine blocks the action with `BLOCKED_ALREADY_TERMINAL`, which resolves to the raw error string "The artifact is already in a terminal state.". If this check is bypassed or fails at the transition stage, `ReviewTransitionEngine` produces "Terminal state: <status> has no outgoing transitions". These raw messages are propagated back up through the client and displayed directly to the operator in the Streamlit UI.

## Fix Strategy

The fix is applied across multiple layers to ensure robustness:
1. **UI layer (`5_asset_workshop.py`)**: Disable decision radio buttons if the asset is already in a terminal state, and display clear info boxes indicating the status.
2. **Action Availability layer (`action_availability_engine.py`)**: Dynamically format the blocking message in `get_blocking_reasons` based on whether the current state is APPROVED or REJECTED, returning operator-friendly messages.
3. **Action Execution layer (`workflow_action_executor.py`)**: Map transition engine validation errors containing "Terminal state" to the operator-friendly messages.
4. **Validation**: Add unit tests in `tests/workflow/` to verify these operator-friendly messages when attempting invalid transitions on terminal-state artifacts.

## Post-Fix Evidence

- Test count after change:
- Tests added or updated:
- Operator-facing message after change:

## Risk Notes

None identified.
