# TASK-026: Auto-load `.env` at Streamlit app startup

**Phase:** 12.2
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

---

## Source References
- Confirmed issue: running `uv run streamlit run src/content_creation/ui/app.py`
  without first exporting GEMINI_API_KEY causes brief generation to fail with
  "API key not found for provider 'gemini'"

---

## Objective
Call `load_dotenv()` at Streamlit app startup so the `.env` file is read automatically, eliminating the need to manually export environment variables before running the app.

---

## Context
`python-dotenv` is already in `pyproject.toml` dependencies. The `.env` file exists and is gitignored. The `.env.example` template was added in TASK-001. But `load_dotenv()` is not called in the Streamlit entry point, so environment variables from `.env` are not loaded when the app starts via Streamlit. The operator must manually `export GEMINI_API_KEY=...` before every run, which is error-prone.

---

## Scope

### Files to modify
- `src/content_creation/ui/app.py`
  — add `load_dotenv()` call near the top, before any service initialization

### Files to NOT touch
All other files. `credentials.py` already handles env lookup correctly.

---

## Constraints
- Read `src/content_creation/ui/app.py` fully before making any change
- Add `load_dotenv()` as early as possible — before any service client is created
- If `dotenv` is not already imported in the file, add the import
- Do NOT change any other logic in app.py

---

## Implementation Steps

1. Read `src/content_creation/ui/app.py` fully.

2. Find the imports section at the top of the file.

3. Add these lines as early as possible in the file (before any service initialization):
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # Load .env file so GEMINI_API_KEY and others are available
   ```

4. If `load_dotenv` is already imported but not called, just add the call.

5. Verify the import does not conflict with anything else in the file.

---

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Confirm load_dotenv is now called in app.py
grep -n "load_dotenv" src/content_creation/ui/app.py
# Expected: at least one line showing the import and one showing the call

# Syntax check
python3 -c "
import ast
src = open('src/content_creation/ui/app.py').read()
try:
    ast.parse(src)
    print('PASS: syntax OK')
except SyntaxError as e:
    print(f'FAIL: {e.lineno}: {e.msg}')
"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
# Expected: ≥ 985 passed
```

---

## Success Criteria
- [ ] `load_dotenv()` is called in `src/content_creation/ui/app.py`
- [ ] `from dotenv import load_dotenv` is present
- [ ] No other logic in app.py was changed
- [ ] Test suite shows ≥ 985 passed

---

## Depends On
None

## Blocks
None

---

## Commit Message
```
fix(ui): auto-load .env at Streamlit startup so API keys load without manual export (TASK-026)
```