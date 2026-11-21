---
name: systematic-debugging
description: Enforce a disciplined 4-phase root-cause protocol and deterministic regression locking. Load whenever diagnosing test failures, runtime errors, Windows subprocess/FFmpeg issues, flaky behavior, or contract-verifier / qa-test-engineer BLOCK verdicts.
---

# Systematic Debugging

A disciplined, evidence-based 4-phase protocol for diagnosing failures, eliminating guess-and-check fixes, and preventing regressions across the Content Creation Automation pipeline.

## The 4-Phase Root-Cause Protocol

### Phase 1 — Reproduce & Isolate
- **Capture Exact Failure**: Run the failing target in isolation and capture the exact command, full traceback, and exit code.
- **Minimal Reproduction**: Strip away extraneous pipeline stages until only the minimal reproducing command or test case remains (e.g., `uv run python -m pytest tests/test_module.py -k "test_case"`).
- **Observe Directly**: Never form an early hypothesis or patch code before observing the failure firsthand.

### Phase 2 — Trace Data & Boundaries
- **Inspect `file:line`**: Open and read the exact source files and line numbers cited in the traceback. Do not guess what code did based on function names.
- **Trace Upstream Producers**: Find where invalid inputs or unexpected types originated. The crash site is rarely the root cause.
- **Check System Boundaries**: On Windows, audit path delimiters (`\\` vs `/`), encoding (`utf-8` vs `cp1252`), subprocess invocation (`sys.executable` vs `bash`), and file locks.

```python
# Pattern: Diagnostic boundary logging without masking
logger.debug(
    "Boundary data inspection: input_type=%s, shape=%s, payload=%r",
    type(data),
    getattr(data, "shape", None),
    data,
)
```

### Phase 3 — Single-Variable Hypothesis Test
- **Formulate Falsifiable Hypothesis**: State clearly: *"Changing X from A to B will resolve error Y because Z."*
- **Single Variable**: Change exactly one variable, argument, or branch at a time. Never bundle multiple speculative edits.
- **Two-Failure Rule**: If two consecutive fixes fail to resolve the issue, STOP patching symptoms. Back out speculative edits and re-examine architectural assumptions, data contracts, and caller expectations.

### Phase 4 — Regression Lock
- **Deterministic Regression Test**: Write an automated test in `tests/test_<module>.py` reproducing the exact failure before applying the final fix.
- **Verify Both Sides**: Confirm the test fails on unpatched code and passes cleanly once the fix is applied.
- **Zero Workarounds**: Never silence errors with bare `except:`, arbitrary `time.sleep()`, or heuristic fallbacks that mask contract violations.

```python
# Pattern: Deterministic regression test locking root-cause fix
def test_regression_windows_path_normalization(tmp_path: Path) -> None:
    raw_path = str(tmp_path / "clip_01.mp4")
    normalized = normalize_media_path(raw_path)
    assert "\\" not in normalized or os.name == "nt"
    assert Path(normalized).exists() or not normalized.endswith("/")
```

## Anti-Patterns to Reject

| Anti-Pattern | Why It Fails & What to Do Instead |
| :--- | :--- |
| **Shotgun Debugging** | Modifying multiple lines simultaneously hides what actually worked; make single-variable changes. |
| **Symptom Masking** | Catching generic `Exception` and returning `None` lets corrupted state propagate; fix the producer. |
| **Sleep Pacing** | Adding `time.sleep(0.5)` masks race conditions without solving them; use synchronization or monotonic keys. |
| **Guess-and-Check** | Editing code without inspecting traceback lines wastes cycles; read the cited `file:line` first. |

## Quick Verification Checklist

Before reporting an issue resolved, verify:
1. **[ ] Clean Reproduction**: Identified the exact command and captured the original traceback.
2. **[ ] Root Cause Traced**: Verified the upstream origin of invalid data or boundary mismatch.
3. **[ ] Single Variable Tested**: Verified the targeted fix without introducing unrelated changes.
4. **[ ] Regression Test Locked**: Added a deterministic test in `tests/test_<module>.py` proving the fix.
5. **[ ] Zero Masking**: Confirmed no bare `except:` blocks or arbitrary delays were introduced.
