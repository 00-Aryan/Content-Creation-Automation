# TASK-015: Add `tests/test_ui_syntax.py` to catch page syntax errors in CI

**Phase:** 12.0
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-10
**Completed:** —
**Requires approval:** NO

---

## Source References
- Verification report: Phase 12.0 Pre-Task Scan § Section 4
- Root cause of TASK-014: syntax error was committed and deployed because no test checked UI pages

---

## Objective
Add a parametrized pytest test that runs `ast.parse()` on every Streamlit page file before deployment, so an IndentationError or SyntaxError in any page is caught by CI and blocks the push.

---

## Context
The test suite currently covers the domain, application, and infrastructure layers but never imports or parses the UI page files. Streamlit pages are Python scripts executed directly — not modules that get imported during normal test runs. The IndentationError in TASK-014 reached the live Render deployment because CI never checked it. This one test file would have caught it.

---

## Scope

### Files to create
- `tests/test_ui_syntax.py`

### Files to NOT touch
All other files. Do not modify existing tests.

---

## Constraints
- Use `ast.parse()` — do NOT import the page modules (importing Streamlit pages has side effects)
- Test must be parametrized so each page file appears as a separate test case in output
- Test must fail with a clear message that includes the file name, line number, and error text
- If the `src/content_creation/ui/pages/` directory does not exist, the test must skip gracefully — do not hard fail

---

## Implementation Steps

1. Verify the exact path of the UI pages directory:
   ```bash
   ls src/content_creation/ui/pages/
   ```
   Confirm it contains: `1_topic_collection.py`, `2_topic_pipeline.py`, `3_brief_viewer.py`, `4_storyboard.py`, `5_asset_workshop.py`, `6_operations_dashboard.py`

2. Create `tests/test_ui_syntax.py` with this exact content:

```python
"""
CI guard: verify all Streamlit page files parse without syntax errors.

Runs ast.parse() on every .py file in the UI pages directory.
If any file has a SyntaxError or IndentationError, the test fails
with the exact file name, line number, and error message — so it
is caught by CI before reaching the Render deployment.
"""
import ast
import pathlib

import pytest

UI_PAGES_DIR = pathlib.Path("src/content_creation/ui/pages")


def _get_page_files():
    if not UI_PAGES_DIR.exists():
        return []
    return sorted(UI_PAGES_DIR.glob("*.py"))


@pytest.mark.parametrize("page_file", _get_page_files(), ids=lambda p: p.name)
def test_page_parses_without_syntax_error(page_file: pathlib.Path) -> None:
    """Each UI page must be parseable by Python's AST.

    A SyntaxError here means the page would crash on load in Render.
    """
    source = page_file.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(page_file))
    except SyntaxError as exc:
        pytest.fail(
            f"\n\nSyntax error in {page_file.name}"
            f"\n  Line {exc.lineno}: {exc.msg}"
            f"\n  Text: {exc.text!r}"
            f"\n\nThis would crash the page on Render. Fix the indentation or syntax error."
        )
```

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Run only the new test — must show one test per page file
uv run python -m pytest tests/test_ui_syntax.py -v 2>&1

# All pages currently syntax OK except brief_viewer (fixed by TASK-014)
# After TASK-014: should show 6 PASSED
# Without TASK-014: should show 5 PASSED, 1 FAILED (brief_viewer)

# Full suite must not regress
uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 966 passed
```

---

## Success Criteria
- [ ] `tests/test_ui_syntax.py` exists
- [ ] Running it shows one parametrized test case per page file
- [ ] All currently-valid pages show PASSED
- [ ] Full suite count does not drop below 966
- [ ] No existing test files modified

---

## Depends On
None (runs independently; if brief_viewer still broken it shows 1 FAILED which is acceptable before TASK-014)

## Blocks
None

---

## Commit Message
```
test(ui): add parametrized syntax test for all Streamlit page files (TASK-015)
```