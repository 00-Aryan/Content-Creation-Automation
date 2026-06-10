# TASK-018: Trace and fix E2E pipeline brief generation failure

**Phase:** 12.0
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-10
**Completed:** —
**Requires approval:** YES

---

## Source References
- Pipeline run failure shown in screenshot: `"error": "Brief generation failed: ['The source topic has no scoring record.']"`
- Verification report: Phase 12.0 Pre-Task Scan § Section 2
- Confirmed: brief_generation_service.py filters by `TopicStatus.SCORED` but the error still triggers in E2E run

---

## Objective
Find the exact code that produces the error message `"The source topic has no scoring record."`, understand why it fires during E2E pipeline execution, and fix the root cause.

---

## Context
The E2E pipeline run (Image 4 from UI screenshots) shows:
- collect: 1622 items, success
- score: 1350 scored, 272 rejected, success
- generate-briefs: FAILED — `"Brief generation failed: ['The source topic has no scoring record.']"`

The verification scan found that `brief_generation_service.py` already filters items by `TopicStatus.SCORED` before calling `generate_brief()`. This means the error is NOT from that code path. There must be a different code path used by the E2E pipeline orchestration. This task traces it and fixes it.

**Requires approval: YES** — because the fix may require changing service or orchestration logic. The agent must stop after producing findings and proposed fix, and wait for approval before implementing.

---

## Scope

### Investigation scope (read only until approval)
- Find: the file and function that produces the string `"The source topic has no scoring record."`
- Find: the E2E pipeline orchestration code that calls the brief generation stage
- Find: where the topic ID is passed and how it is looked up
- Compare: standalone `brief_generation_service.py` call vs E2E call

### Files to modify (only after approval)
- TBD — determined by investigation findings

### Files to NOT touch (ever)
- `src/content_creation/models/` (frozen)
- `src/content_creation/generation/` (frozen)
- Any test file

---

## Constraints
- Do NOT implement any fix before reporting findings and receiving approval
- Search for the exact error string first — do not assume where it is
- The fix must not change the `ScoredTopicItem` schema or the `Brief` schema

---

## Implementation Steps

### Phase 1 — Trace the error (do this, then STOP and report)

1. Search the entire codebase for the exact error message string:
   ```bash
   grep -r "source topic has no scoring record" src/ --include="*.py" -n
   ```
   Report: exact file path and line number where this string is defined.

2. Read that file fully. Understand what condition triggers the error. Paste the relevant code block.

3. Find the E2E pipeline orchestration entry point:
   ```bash
   grep -r "generate.briefs\|generate_briefs\|run_pipeline\|e2e\|orchestrat" src/ --include="*.py" -l
   ```
   Read the most relevant file. Find the code path that calls brief generation in the E2E context.

4. Compare the E2E call vs the standalone `brief_generation_service.py` call:
   - Does the E2E path pass a different type (TopicItem vs ScoredTopicItem)?
   - Does it use a different storage lookup?
   - Does it skip the `TopicStatus.SCORED` filter?

5. Identify the exact mismatch. Write a 3-sentence explanation of why the error occurs.

### Phase 2 — Propose the fix (report this, do NOT implement yet)

6. Write a precise description of the fix:
   - Which file and line to change
   - What the change is (exact before/after code)
   - Why this fixes the problem without breaking other paths

7. Print:
   ```
   FINDINGS COMPLETE — AWAITING APPROVAL
   
   Root cause: [your 3-sentence explanation]
   
   Proposed fix:
   File: [path]
   Line: [number]
   Before: [code]
   After: [code]
   
   Risk: [what could break if this change is wrong]
   ```

### Phase 3 — Implement (only after explicit approval recorded in Agent Notes)

8. Apply the fix exactly as proposed.
9. Run validation.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# After fix: brief generation service must process scored items without error
python3 -c "
from pathlib import Path
import json

# Check scored items exist
scored_dir = Path('data/scored')
count = len(list(scored_dir.glob('*.json')))
print(f'Scored items on disk: {count}')
assert count > 0, 'No scored items found'
print('PASS: scored data exists for brief generation')
"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 966 passed
```

---

## Success Criteria (Phase 3 only)
- [ ] Root cause identified with exact file:line reference
- [ ] Fix implemented in the correct file
- [ ] Test suite shows ≥ 966 passed
- [ ] E2E pipeline brief generation stage no longer produces the error message

---

## Depends On
None (investigation is independent)

## Blocks
None

---

## Commit Message
```
fix(pipeline): resolve E2E brief generation failure — source topic scoring record lookup (TASK-018)
```

---

## Agent Notes
STOP after Phase 1 and Phase 2. Print the full findings and proposed fix. Do NOT proceed to Phase 3 until this task card's Notes section has been updated with: "APPROVED by operator on [date]".

The investigation is the most important part. Do not guess the fix — trace the actual code path first.