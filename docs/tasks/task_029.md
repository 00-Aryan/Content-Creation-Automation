# TASK-029: Show brief content preview before approve/reject decision in Brief Viewer

**Phase:** 12.2
**Status:** DONE
**Priority:** MEDIUM
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

---

## Source References
- UI screenshot analysis: brief viewer has approve/reject but no visible content summary
- Verified brief structure: briefs have `why_it_matters`, `topic_id` fields
  with real substantive content

---

## Objective
Display the key brief fields (`why_it_matters` and at least one content preview field) prominently in the Brief Viewer before the approve/reject decision UI, so the operator can make an informed decision without hunting through raw JSON.

---

## Context
The brief viewer was fixed (IndentationError in TASK-014). Now the approve/reject flow works syntactically. But the operator still needs to see the actual content of the brief before deciding to approve or reject it. Currently, the content may be buried in a JSON expander. A brief like "Mobile GUI Agents have the potential to revolutionize how we interact with mobile applications, but current evaluation methods are flawed..." should be prominently visible.

From the verified brief structure, the key fields are:
- `why_it_matters` — the "hook" explaining relevance
- Likely also: `summary`, `key_points`, `source_url`, or similar

---

## Scope

### Files to modify
- `src/content_creation/ui/pages/3_brief_viewer.py`
  — add a content preview section above the approve/reject UI

### Files to NOT touch
All other files.

---

## Constraints
- Read `3_brief_viewer.py` fully before making any change
- Read one actual brief JSON file to confirm the real field names:
  ```bash
  python3 -c "import json,pathlib; d=json.loads(list(pathlib.Path('data/briefs').glob('*.json'))[0].read_text()); print(list(d.keys()))"
  ```
- Use ONLY fields that actually exist in the brief schema — do not assume field names
- Add the preview section ABOVE the existing approve/reject controls
- Keep the existing JSON expander — add the preview alongside it, not replacing it
- Do NOT change the approve/reject logic

---

## Implementation Steps

1. Read `src/content_creation/ui/pages/3_brief_viewer.py` fully.

2. Run this to see the actual brief fields:
   ```bash
   python3 -c "
   import json, pathlib
   briefs = list(pathlib.Path('data/briefs').glob('*.json'))
   if briefs:
       d = json.loads(briefs[0].read_text())
       print('Fields:', list(d.keys()))
       for k, v in d.items():
           if isinstance(v, str) and len(v) > 20:
               print(f'  {k}: {v[:100]!r}')
   "
   ```

3. Find the section in the page where a selected brief is displayed and where the approve/reject controls appear.

4. Add a brief summary section above the approve/reject controls using the real fields:
   ```python
   # Show brief content before the review decision
   st.markdown("### 📄 Brief Summary")
   
   if hasattr(brief, 'why_it_matters') and brief.why_it_matters:
       st.info(f"**Why it matters:** {brief.why_it_matters}")
   
   # Add other substantive fields using actual field names discovered in step 2
   # e.g. summary, key_points, source_url — only if they exist
   ```

5. Confirm the approve/reject UI still appears below the preview.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -c "
import ast
src = open('src/content_creation/ui/pages/3_brief_viewer.py').read()
try:
    ast.parse(src)
    print('PASS: syntax OK')
except SyntaxError as e:
    print(f'FAIL: {e.lineno}: {e.msg}')
"

# Confirm why_it_matters (or equivalent) appears in the page
grep -n "why_it_matters\|summary\|preview" src/content_creation/ui/pages/3_brief_viewer.py | head -10

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 985 passed
```

---

## Success Criteria
- [x] Brief Viewer shows key content (at minimum `why_it_matters`) before the review decision
- [x] Used only real field names confirmed from actual brief files
- [x] Approve/reject controls still present and unchanged
- [x] Page parses without syntax errors
- [x] Test suite shows ≥ 985 passed

---

## Depends On
TASK-014 (brief_viewer.py syntax fix — already done)

## Blocks
None

---

## Commit Message
```
feat(ui): show brief content preview before approve/reject decision in Brief Viewer (TASK-029)
```