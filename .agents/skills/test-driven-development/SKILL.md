---
name: test-driven-development
description: Enforce strict Red-Green-Refactor cycles and domain-isolated pytest contracts. Load whenever implementing net-new domain logic, algorithms, parsers, filter builders, or bug fixes (especially greenfield modules like gaming_clips and Phase 3 LangGraph nodes).
---

# Test-Driven Development (TDD)

Essential Red-Green-Refactor discipline and test architecture to guarantee that domain contracts, algorithms, and bug fixes are verified by deterministic, offline automated tests before code is merged.

## The Iron Law of Red-Green-Refactor

Never write production code without an observed failing test. Always follow the three phases:

1. **Red (Failing Contract Test)**:
   - Write a minimal test in `tests/test_<module>.py` exercising the expected input/output contract or boundary condition before writing production logic.
   - Run the test using `pytest` and confirm it fails.
   - **Crucial**: Verify the failure is caused by the missing implementation or unmet assertion—never by an `ImportError`, typo, or fixture setup crash.
2. **Green (Minimal Implementation)**:
   - Write only the simplest, cleanest production code necessary to make the failing test pass.
   - Do not implement speculative features, unrequested parameters, or unneeded abstractions.
   - Run `pytest` to confirm the test passes cleanly.
3. **Refactor (Clean Code under Green)**:
   - Clean up implementation: simplify logic, eliminate duplication, and enforce strict typing.
   - Keep tests green at every micro-step. Run the full scoped suite to verify zero regressions.

```python
# Pattern: Domain contract test before production implementation
def test_filter_gaming_clips_by_retention(tmp_path: Path) -> None:
    # 1. Arrange: deterministic synthetic input
    samples = [{"clip_id": "c1", "retention_score": 0.85}, {"clip_id": "c2", "retention_score": 0.40}]
    # 2. Act: invoke domain function under test
    selected = select_top_retained_clips(samples, min_score=0.70)
    # 3. Assert: verify strict contract output
    assert len(selected) == 1
    assert selected[0]["clip_id"] == "c1"
```

## Anti-Rationalization Table

Reject common developer rationalizations that bypass test-first discipline:

| Rationalization | Reality & Enforcement |
| :--- | :--- |
| *"Too simple to test first"* | Simple code contains hidden boundary bugs. A 60-second test locks the contract permanently. |
| *"I'll add the tests after"* | Post-hoc tests test what was built, not what was required, and suffer from confirmation bias. |
| *"Mocking everything is faster"* | Over-mocking tests the mocks, not the code. Prefer offline domain fixtures over deep mocks. |
| *"Keep going without running pytest"* | Unverified changes accumulate compound errors. Execute `pytest` on every micro-iteration. |

## Domain-Named Test Architecture

All tests must follow repository conventions:

- **Domain-Scoped Files**: Place tests strictly in domain files matching the target module (`tests/test_<module>.py`). Never create phase-numbered test files (e.g., `test_phase2.py`).
- **Offline & Deterministic Fixtures**: Use `pytest`'s `tmp_path` for file operations and synthetic in-memory buffers (NumPy arrays, JSON dicts). Tests must run fully offline without network access.
- **Contract Isolation**: Test public API boundaries, schemas, and state transitions. Do not test private implementation trivia.
- **Node & Graph Testing**: For LangGraph nodes or generators, test nodes as isolated pure functions using input state dicts and verify returned partial state updates.

## Quick Verification Checklist

Before marking any implementation complete, verify:
1. **[ ] Red Confirmed**: Saw the test fail initially with the expected assertion error.
2. **[ ] Minimal Green**: Production code contains only logic necessary to pass the test.
3. **[ ] Domain File**: Test resides in `tests/test_<module>.py` using offline fixtures (`tmp_path`).
4. **[ ] Isolated Contracts**: LangGraph nodes or domain modules tested with synthetic fixtures.
5. **[ ] Suite Green**: Scoped test suite passes with zero regressions (`uv run python -m pytest tests/test_<module>.py -q`).
