# TASK-017: Add copy-to-clipboard to generated content in `5_asset_workshop.py`

**Phase:** 12.0
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-10
**Completed:** —
**Requires approval:** —

---

## Source References
- Verification report: Phase 12.0 Pre-Task Scan § Section 6
- Confirmed: `5_asset_workshop.py` displays script, carousel, newsletter, thumbnail content but has NO copy mechanism

---

## Objective
Add a copy-to-clipboard capability to each generated content section in the asset workshop so the operator can copy the final output directly from the UI.

---

## Context
The verification scan confirmed that `5_asset_workshop.py` is the only page that shows generated content (video script, carousel, newsletter, thumbnail). However, there is no copy button anywhere. The operator has to manually select text from JSON displays or read rendered output. For the morning workflow — where the goal is to copy a LinkedIn post or YouTube script — this is the most impactful usability gap. The fix uses `st.code()` which renders a copy icon natively in Streamlit, or `st.text_area()` which allows text selection.

---

## Scope

### Files to modify
- `src/content_creation/ui/pages/5_asset_workshop.py`
  — add copy-friendly display for each asset type's key text fields

### Files to NOT touch
All other files.

---

## Constraints
- Read the ENTIRE `5_asset_workshop.py` before making changes
- Do NOT change any data fetching, generation triggering, or review decision logic
- Only change how the content is displayed — add copy-friendly wrappers
- Prefer `st.code(content, language=None)` for copyable blocks — it shows a copy icon natively
- For multi-section content (like scripts), add a copy block per logical section
- Keep the existing JSON expander displays — add copy blocks alongside them, not replacing them

---

## Implementation Steps

1. Read `src/content_creation/ui/pages/5_asset_workshop.py` fully.

2. Locate where each asset type's content is currently displayed:
   - Video script: find where `hook`, `raw_script`, or sections are rendered
   - Carousel: find where slide content is rendered
   - Newsletter: find where subject line and sections are rendered
   - Thumbnail: find where title text and visual metaphor are rendered

3. For each section, add a copyable display block immediately after the existing display:

   **For the video script hook and full script:**
   ```python
   st.markdown("**📋 Copy — Script Hook**")
   st.code(script.hook, language=None)
   
   st.markdown("**📋 Copy — Full Script**")
   st.code(script.raw_script, language=None)
   ```

   **For carousel post caption/text content:**
   ```python
   st.markdown("**📋 Copy — Carousel Caption**")
   st.code(carousel.caption or "", language=None)
   ```

   **For newsletter subject and body:**
   ```python
   st.markdown("**📋 Copy — Subject Line**")
   st.code(newsletter.subject_line, language=None)
   
   st.markdown("**📋 Copy — Newsletter Body**")
   st.code(newsletter.body_text or "", language=None)
   ```

   **For thumbnail:**
   ```python
   st.markdown("**📋 Copy — Thumbnail Title**")
   st.code(thumbnail.title_text, language=None)
   ```

   Note: Read the actual field names from the asset models before writing the code — do not assume field names. Check `src/content_creation/models/` for the actual schema.

4. Verify all field names used actually exist on the model objects. If a field has a different name than assumed above, use the correct name from the model.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Page must still parse
python3 -c "
import ast
src = open('src/content_creation/ui/pages/5_asset_workshop.py').read()
try:
    ast.parse(src)
    print('PASS: syntax OK')
except SyntaxError as e:
    print(f'FAIL: {e.lineno}: {e.msg}')
"

# Confirm st.code( appears more times than before (at least 4 new instances)
python3 -c "
src = open('src/content_creation/ui/pages/5_asset_workshop.py').read()
count = src.count('st.code(')
print(f'st.code() calls: {count}')
assert count >= 4, f'Expected at least 4 st.code() calls, found {count}'
print('PASS')
"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 966 passed
```

---

## Success Criteria
- [ ] At least 4 `st.code()` blocks added — one per asset type at minimum
- [ ] Each block shows the key copyable text for that asset type
- [ ] Existing JSON expander displays are still present (not replaced)
- [ ] Page parses without syntax errors
- [ ] Test suite shows ≥ 966 passed

---

## Depends On
None

## Blocks
None

---

## Commit Message
```
feat(ui): add copy-to-clipboard blocks to all asset types in asset workshop (TASK-017)
```

---

## Agent Notes
The critical step is Step 4 — verify actual field names before writing any code. Read the asset model classes in `src/content_creation/models/` and use the real field names. If a field you expect does not exist, check if there is a `.content`, `.text`, or `.body` equivalent. Do not assume field names.