# TASK-027: Restructure navigation to match morning workflow order

**Phase:** 12.2
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

---

## Source References
- UI screenshot analysis: navigation has 7 items in wrong order for operator workflow
- Operator morning workflow: Collect → Review → Generate → Output

---

## Objective
Rename and reorder the Streamlit navigation pages so they match the operator's actual morning workflow, making it obvious what to do next at each step.

---

## Context
Current navigation (from screenshots):
```
app
topic collection
topic pipeline
brief viewer
storyboard
asset workshop
operations dashboard
```

This doesn't match how the operator thinks. The operator thinks in steps:
1. Collect new topics
2. Review and approve topics/briefs
3. Generate content for approved items
4. See and copy the final output

The page names and order create confusion about what to do first and what comes next.

---

## Scope

### Files to modify
Read ALL files in `src/content_creation/ui/pages/` first, then rename
only the page display names (the string in `st.set_page_config` or the
filename prefix that Streamlit shows in the sidebar).

Do NOT restructure the actual code or move functionality between pages.
Only change: display names and page order (via filename prefix numbers).

### Files to NOT touch
- `src/content_creation/ui/app.py` (unless display name is set there)
- All backend/domain/application code
- All test files

---

## Constraints
- Read ALL 6 page files before making any changes
- Only change the page title / display label shown in the sidebar
- Do NOT change any functionality — only the label the sidebar shows
- If renaming files is needed for ordering, do so carefully and update any imports
- The Streamlit page order is controlled by the numeric prefix (1_, 2_, etc.) —
  keep those prefixes consistent with the new order

---

## Implementation Steps

1. Read all 6 page files fully:
   - `1_topic_collection.py`
   - `2_topic_pipeline.py`
   - `3_brief_viewer.py`
   - `4_storyboard.py`
   - `5_asset_workshop.py`
   - `6_operations_dashboard.py`

2. Read `src/content_creation/ui/app.py` to understand how pages are registered.

3. Map current pages to new names that reflect the workflow step:

   | Current name | New display name |
   |---|---|
   | app (main) | 🏠 Dashboard |
   | topic collection | 📥 1. Collect |
   | topic pipeline | ⚙️ 2. Score & Filter |
   | brief viewer | 📝 3. Review Briefs |
   | storyboard | 🗂️ 4. Storyboard |
   | asset workshop | ✍️ 5. Content Output |
   | operations dashboard | 🔧 System Health |

4. Change only the display name in each page file. In Streamlit, this is
   typically set via `st.set_page_config(page_title="...")` near the top of
   each file, or via the filename itself.

5. Do NOT rename files if it would break imports. Only change the
   `st.set_page_config(page_title=...)` value in each page file.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# All pages still parse
python3 -c "
import ast, pathlib
for p in sorted(pathlib.Path('src/content_creation/ui/pages').glob('*.py')):
    try:
        ast.parse(p.read_text())
        print(f'OK: {p.name}')
    except SyntaxError as e:
        print(f'FAIL: {p.name} line {e.lineno}: {e.msg}')
"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 985 passed
```

---

## Success Criteria
- [ ] All 6 pages have updated display names reflecting the workflow step
- [ ] All 6 pages still parse without syntax errors
- [ ] No functionality was changed — only display labels
- [ ] Test suite shows ≥ 985 passed

---

## Depends On
None

## Blocks
None

---

## Commit Message
```
feat(ui): rename navigation pages to match morning workflow order (TASK-027)
```

---

## Agent Notes
If `st.set_page_config` is not present in a page file, add it near the top
with only `page_title` set. Do not set `layout` or other config values unless
they already exist in the file.