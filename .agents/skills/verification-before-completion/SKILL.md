---
name: verification-before-completion
description: Enforce zero-trust evidence validation and fresh test execution before claiming completion. Load before finalizing any commit, handoff report, QA report, or claiming a fix or feature works.
---

# Verification Before Completion

Zero-trust verification standard. No task, bug fix, or refactoring is complete without fresh, deterministic, verifiable command outputs executed after the final file edit.

## The Iron Law of Evidence Before Claims

Never declare that code works, tests pass, or types are clean based on assumption or past execution:

1. **Execute After Final Edit**: You must execute the exact verification command *after* the final file modification. Any subsequent edit—even a comment, whitespace, or docstring—invalidates previous verification results.
2. **Inspect Actual Output**: Directly inspect terminal stdout, stderr, and exit codes. Never assume success because no exception was immediately printed.
3. **Cite Hard Evidence**: Every completion claim or handoff report must include the exact command run, exit code, and observed counts (passed, failed, warnings).

```bash
# Required evidence capture pattern
uv run python -m pytest tests/test_<module>.py -q
# Must observe and record: "X passed, 0 failed in Y.YYs (exit code 0)"
```

## Banned Hedging Phrasing (Red Flags)

The following phrasing represents unverified assumptions and is strictly forbidden:

| Banned Hedging Phrasing | Mandatory Professional Replacement |
| :--- | :--- |
| *"Should pass now..."* | Run the command and state: *"Passed: 14 passed in 0.42s (exit 0)"*. |
| *"Probably fixed the issue..."* | Execute reproduction: *"Reproduction test now passes with exit code 0"*. |
| *"Looks clean / syntax looks good..."* | Run static checks: *"mypy returned 0 errors across 5 files"*. |
| *"Verified earlier in our session..."* | Re-run verification: *"Re-executed after final edit; test suite green"*. |
| *"Changes are too small to break tests..."* | Run baseline check: *"Executed pytest baseline: 962 passed, count preserved"*. |
| *"Tested manually in my head..."* | Run automated test: *"Executed pytest automated test suite with exit code 0"*. |

## Mandatory Verification Protocol

Before finalizing any task or handoff report, complete this structured sequence:

1. **Scoped Test Run**: Run `pytest` on the specific module or test file touched by the task. Verify a 100% pass rate.
2. **Baseline Regression Check**: On Type A tasks, run the suite baseline check (`uv run python -m pytest --tb=no -q`) to ensure total passing count did not decrease.
3. **Type & Cleanliness Gate**: If required by the task card or contract, run `uv run mypy src/content_creation --strict` and `git diff --check` to verify zero typing breaks or trailing whitespace.
4. **Handoff Evidence Block**: Format the final report with explicit command strings, exit codes, and counts:

```text
Validation Evidence:
- Command: uv run python -m pytest tests/test_gaming_clips.py -q
  Output: 18 passed in 0.35s | Exit Code: 0
- Command: uv run python -m pytest --tb=no -q
  Output: 962 passed | Baseline Preserved: Yes
- Command: git diff --check
  Output: Clean (0 whitespace errors)
```

## Quick Verification Checklist

Before reporting completion or handing off to `contract-verifier` or `qa-test-engineer`:
1. **[ ] Final Edit Timestamp**: No file edits were made after the last verification run.
2. **[ ] Exact Command Executed**: Ran the concrete test/verification command and observed stdout/stderr.
3. **[ ] Clean Exit Code**: Command returned exit code 0 without unhandled warnings or masking.
4. **[ ] Baseline Preserved**: Confirmed passing test count did not decrease from initial baseline.
5. **[ ] Zero Hedging**: Completion message cites exact counts, command strings, and exit status.
