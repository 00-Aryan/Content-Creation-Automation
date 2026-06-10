# TASK-016: Replace silent `except Exception: pass` with `st.error()` in UI pages

**Phase:** 12.0
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-10
**Completed:** —
**Requires approval:** NO

---

## Source References
- Verification report: Phase 12.0 Pre-Task Scan § Section 7
- Confirmed locations: `4_storyboard.py:293`, `5_asset_workshop.py:314`, `6_operations_dashboard.py:114`
- Also fix any silent handlers in `3_brief_viewer.py` (now accessible after TASK-014)

---

## Objective
Replace every `except Exception: pass` or `except Exception as e: pass` in the UI pages with a visible `st.warning()` call, so the operator sees when something goes wrong instead of the UI silently doing nothing.

---

## Context
The verification scan found silent exception handlers in at least 4 UI page files. The confirmed example from `6_operations_dashboard.py`:
```python
try:
    latest_notifications = client.notification_service.list_recent(limit=1)
    if latest_notifications:
        client.publish_notification_event(latest_notifications[0])
except Exception:
    pass
```
When this fails, the operator sees nothing. There is no indication that the action failed. This makes debugging impossible and makes the app appear broken without explanation.

---

## Scope

### Files to modify
- `src/content_creation/ui/pages/3_brief_viewer.py` — read for silent handlers after TASK-014 fix
- `src/content_creation/ui/pages/4_storyboard.py` — confirmed at line 293
- `src/content_creation/ui/pages/5_asset_workshop.py` — confirmed at line 314
- `src/content_creation/ui/pages/6_operations_dashboard.py` — confirmed at line 114

### Files to NOT touch
All other files.

---

## Constraints
- Do NOT change what the try block does — only change the except clause
- Use `st.warning()` for non-critical failures (things that fail silently today)
- Use `st.error()` only for failures that leave the page in a broken state
- Do NOT expose raw Python exception details to the operator — use plain English
- Do NOT change the exception type being caught — keep `except Exception`
- The message must tell the operator what failed and what to do next (e.g., "refresh", "try again")

---

## Implementation Steps

1. Read each of the 4 files fully.

2. In each file, find every `except Exception` block where the body is `pass` or only a `pass`-equivalent (empty or comment only).

3. Replace each silent handler with the appropriate pattern:

   **For non-critical background operations** (like the notifications example):
   ```python
   except Exception as e:
       st.warning(f"A background operation failed and was skipped. ({type(e).__name__})")
   ```

   **For user-triggered actions** (button clicks, review decisions):
   ```python
   except Exception as e:
       st.error(f"Action failed. Please try again. If the issue persists, check the logs.")
       st.caption(f"Technical detail: {type(e).__name__}: {e}")
   ```

4. After editing each file, verify syntax:
   ```bash
   python3 -c "import ast; ast.parse(open('<path>').read()); print('OK: <filename>')"
   ```

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Confirm no silent handlers remain in any UI page
python3 -c "
import ast, pathlib

pages_dir = pathlib.Path('src/content_creation/ui/pages')
silent_found = []

for page in sorted(pages_dir.glob('*.py')):
    try:
        tree = ast.parse(page.read_text())
    except SyntaxError:
        print(f'SKIP (syntax error): {page.name}')
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            body = node.body
            if all(isinstance(s, ast.Pass) for s in body):
                silent_found.append(f'{page.name}:{node.lineno}')

if silent_found:
    print('FAIL: Silent handlers still present:')
    for loc in silent_found:
        print(f'  {loc}')
else:
    print('PASS: No silent except handlers found')
"

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
# Expected: ≥ 966 passed
```

---

## Success Criteria
- [ ] Zero `except Exception: pass` (or equivalent silent) handlers remain in any UI page
- [ ] Every replaced handler shows a user-facing `st.warning()` or `st.error()` message
- [ ] All 6 page files still parse without syntax errors
- [ ] Test suite shows ≥ 966 passed

---

## Depends On
TASK-014 (brief_viewer.py must be syntax-valid before its handlers can be audited)

## Blocks
None

---

## Commit Message
```
fix(ui): replace silent except handlers with st.warning/st.error in all page files (TASK-016)
```