# TASK-014: Fix IndentationError in `3_brief_viewer.py` line 158

**Phase:** 12.0
**Status:** DONE
**Priority:** CRITICAL
**Created:** 2026-06-10
**Completed:** 2026-06-10
**Requires approval:** NO

---

## Source References
- Verification report: Phase 12.0 Pre-Task Scan § Section 1
- Deployed error: `IndentationError: unexpected indent` at line 158 on Render

---

## Objective
Fix the `with st.status(...)` block at line 158 that is indented one level too deep, which crashes the entire Brief Viewer page on load.

---

## Context
`3_brief_viewer.py` line 158 has a `with st.status(...)` block indented at the wrong level — it is inside the `BriefDecision(...)` constructor call indentation instead of being a sibling to it inside the `if st.button(...)` block. Python cannot parse the file at all, so the page shows a raw traceback on Render. This is the single highest-priority fix in the codebase.

---

## Scope

### Files to modify
- `src/content_creation/ui/pages/3_brief_viewer.py`
  — dedent the `with st.status(...)` block starting at line 158 by exactly 4 spaces

### Files to NOT touch
All other files.

---

## Constraints
- Read the ENTIRE file before making any change
- Change ONLY the indentation of the `with` block and its contents — no logic changes
- Do NOT change the content of any string, variable name, or function call
- Confirm the fix using `ast.parse()` before finishing

---

## Implementation Steps

1. Read `src/content_creation/ui/pages/3_brief_viewer.py` fully.

2. Locate the block starting at line 158. Confirmed offending pattern from verification:
   ```python
   if st.button("Apply Brief Review Decision", type="primary", use_container_width=True):
       decision = BriefDecision(
           status=status_map[review_action],
           notes=review_notes if review_notes else None,
       )
           with st.status("Applying brief review decision...", expanded=True) as status:
               try:
   ```
   The `with st.status(...)` line and everything inside it is indented 12 spaces (3 levels). It should be indented 8 spaces (2 levels — inside the `if` block).

3. Dedent `with st.status(...)` and its entire contents by 4 spaces. The corrected structure must be:
   ```python
   if st.button("Apply Brief Review Decision", type="primary", use_container_width=True):
       decision = BriefDecision(
           status=status_map[review_action],
           notes=review_notes if review_notes else None,
       )
       with st.status("Applying brief review decision...", expanded=True) as status:
           try:
   ```

4. Read the full corrected block to confirm the indentation is consistent throughout — the `try`, `except`, and all `st.write` and `status.update` calls inside the `with` block must also be dedented by exactly 4 spaces.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Must return OK — not SyntaxError
python3 -c "
import ast
src = open('src/content_creation/ui/pages/3_brief_viewer.py').read()
try:
    ast.parse(src)
    print('PASS: file parses without syntax errors')
except SyntaxError as e:
    print(f'FAIL: SyntaxError at line {e.lineno}: {e.msg}')
"

# Full test suite must hold at baseline
uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: 966 passed
```

---

## Success Criteria
- [ ] `ast.parse()` on the file returns no errors
- [ ] Line 158 and its block are at the correct indentation level
- [ ] No logic, variable names, or string content was changed
- [ ] Test suite shows ≥ 966 passed

---

## Depends On
None

## Blocks
TASK-016 (brief_viewer.py error handlers can only be fixed after syntax is valid)

---

## Commit Message
```
fix(ui): fix IndentationError in 3_brief_viewer.py line 158 — brief review flow unblocked (TASK-014)
```

---

## Agent Notes
After applying the fix, read the repaired block in full and verify the indentation visually before committing. The block spans roughly lines 158–180. All lines in the block must shift left by exactly 4 spaces.