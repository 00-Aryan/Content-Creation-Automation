# TASK-030: Fix scoring engine differentiated topic scores

**Phase:** 12.2  
**Status:** DONE  
**Priority:** CRITICAL  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Fix the scoring engine so scored topics receive differentiated, explainable quality scores instead of collapsing to a uniform default score such as `50`.

## Scope

### Files to modify

- `src/content_creation/scoring/engine.py` — inspect and fix the scoring logic so output scores vary based on topic evidence, relevance, recency, source quality, and content potential.
- `tests/` — add or update focused scoring tests that prove the engine does not return the same score for clearly different inputs.

### Files to create

- `docs/phase-12.2-scoring-diagnostics.md` — record the current scoring behavior, root cause, implementation decision, and post-fix validation evidence.

### Files to NOT touch

All other files.

## Constraints

- Read `src/content_creation/scoring/engine.py` fully before changing anything.
- Read existing scoring-related tests before adding new tests.
- Do not change frozen directories unless absolutely necessary:
  - `src/content_creation/models/`
  - `src/content_creation/generation/`
  - `prompts/`
- If a frozen file appears necessary, stop and write findings first. Do not modify it without explicit approval.
- Preserve existing public interfaces unless a test proves the interface is already incorrect.
- Do not hard-code sample scores only to satisfy tests.
- Do not lower the test baseline. Current expected baseline is at least 985 passing tests.
- Do not add new platform-generation behavior in this task.
- Do not fix UI issues in this task.
- Do not clean `(F)(K)(C)` token leaks in this task.
- Do not fix `needs_review` placeholder pollution in this task.

## Implementation Steps

1. Run the baseline diagnostics:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=no -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   985 passed
   ```

   Exact count may be higher, but must not be lower.

2. Confirm the current scoring collapse:

   ```bash
   python3 - <<'PY'
   import json
   import pathlib

   score_files = list(pathlib.Path("data/scored").glob("*.json"))[:20]
   scores = []

   for f in score_files:
       d = json.loads(f.read_text())
       scores.append(d.get("quality_score", d.get("score", 0)))

   print("Files checked:", len(score_files))
   print("Sample scores:", scores)
   print("Unique values:", sorted(set(scores)))
   PY
   ```

3. Read the scoring engine fully:

   ```bash
   sed -n '1,260p' src/content_creation/scoring/engine.py
   ```

4. Find existing scoring tests:

   ```bash
   find tests -type f | grep -Ei 'scor|topic|quality|engine'
   ```

5. Read relevant tests before modifying code.

6. Diagnose why scores collapse to the same value.

   Likely causes to check:

   - scoring fields defaulting to constant values
   - missing feature extraction from topic metadata
   - exception fallback returning `50`
   - normalization logic clamping everything to midpoint
   - LLM score parsing failure causing fallback score
   - source fields not being passed into the scoring calculation
   - all components weighted but each component defaulting to neutral

7. Write findings to:

   ```text
   docs/phase-12.2-scoring-diagnostics.md
   ```

   The diagnostic file must include:

   ```markdown
   # Phase 12.2 Scoring Diagnostics

   ## Baseline

   - Test count before change:
   - Sample scored files checked:
   - Sample scores before change:
   - Unique score values before change:

   ## Root Cause

   Explain the exact reason scores were collapsing.

   ## Fix Strategy

   Explain what changed and why.

   ## Post-Fix Evidence

   - Test count after change:
   - Sample scores after change:
   - Unique score values after change:

   ## Risk Notes

   Mention any scoring behavior that still needs later quality validation.
   ```

8. Implement the smallest correct fix in `src/content_creation/scoring/engine.py`.

   The fixed scoring behavior must satisfy:

   - weak / incomplete / low-signal topics receive lower scores
   - strong / specific / source-backed topics receive higher scores
   - score stays within the existing expected range
   - scoring remains deterministic for the same input
   - missing optional fields do not crash scoring
   - failures are visible enough for debugging and do not silently collapse all outputs to `50`

9. Add or update tests.

   At minimum, tests must prove:

   - two clearly different topic inputs produce different scores
   - score is bounded within the expected range
   - missing optional fields do not crash scoring
   - fallback behavior does not hide systematic parsing or feature failures

10. Run targeted validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest tests --tb=short -q -k "scor or scoring or topic or quality"
    ```

11. Run full validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    Expected result:

    ```text
    985 passed
    ```

    Exact count may be higher, but must not be lower.

12. Re-run score distribution check:

    ```bash
    python3 - <<'PY'
    import json
    import pathlib

    score_files = list(pathlib.Path("data/scored").glob("*.json"))[:20]
    scores = []

    for f in score_files:
        d = json.loads(f.read_text())
        scores.append(d.get("quality_score", d.get("score", 0)))

    print("Files checked:", len(score_files))
    print("Sample scores:", scores)
    print("Unique values:", sorted(set(scores)))
    PY
    ```

13. Update `docs/phase-12.2-scoring-diagnostics.md` with post-fix evidence.

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -m py_compile src/content_creation/scoring/engine.py

uv run python -m pytest tests --tb=short -q -k "scor or scoring or topic or quality"

uv run python -m pytest --tb=short -q 2>&1 | tail -3

python3 - <<'PY'
import json
import pathlib

score_files = list(pathlib.Path("data/scored").glob("*.json"))[:20]
scores = []

for f in score_files:
    d = json.loads(f.read_text())
    scores.append(d.get("quality_score", d.get("score", 0)))

print("Files checked:", len(score_files))
print("Sample scores:", scores)
print("Unique values:", sorted(set(scores)))

if len(set(scores)) <= 1 and len(scores) > 1:
    raise SystemExit("FAIL: scoring is still collapsed to one value")

print("PASS: score distribution is differentiated")
PY
```

## Success Criteria

- [ ] Root cause of uniform score behavior is documented.
- [ ] `src/content_creation/scoring/engine.py` produces differentiated scores for clearly different topics.
- [ ] Scoring remains deterministic for identical input.
- [ ] Score values remain bounded within the existing expected range.
- [ ] Missing optional fields do not crash scoring.
- [ ] Tests prove differentiated scoring.
- [ ] `docs/phase-12.2-scoring-diagnostics.md` contains before/after evidence.
- [ ] Full test suite shows at least 985 passed.
- [ ] No frozen files are modified without explicit approval.
- [ ] No UI, generation, prompt, or platform-aware content changes are included.

## Depends On

None

## Commit Message

```text
fix(scoring): differentiate topic quality scores (TASK-030)
```
