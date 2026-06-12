# TASK-031: Remove structural marker tokens from final script output

**Phase:** 12.2  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Remove internal structural marker tokens such as `(F)`, `(K)`, and `(C)` from final script output shown to the operator or saved as publishable script text, while preserving useful internal generation metadata where appropriate.

## Scope

### Files to modify

- `src/content_creation/generation/script.py` — inspect where script sections are assembled and add the smallest correct cleanup so final script copy does not contain `(F)`, `(K)`, or `(C)` marker tokens.
- `src/content_creation/ui/pages/5_asset_workshop.py` — modify only if the leak is purely display-layer and the stored script object should remain unchanged.
- `tests/test_script_storyboard_integration.py` — add or update focused regression coverage for script output marker cleanup.
- `tests/` — add focused tests only if the existing script/storyboard integration test file is not the correct location.

### Files to create

- `docs/phase-12.2-script-token-cleanup.md` — record the marker leak evidence, root cause, chosen cleanup layer, and validation results.

### Files to NOT touch

All other files.

## Constraints

- Do not perform broad UI cleanup in this task.
- Do not fix `needs_review` thumbnail pollution in this task.
- Do not change approval state-machine behavior in this task.
- Do not change timestamp formatting in this task.
- Do not change platform-aware content generation in this task.
- Do not modify `prompts/` unless diagnostics prove the prompt is the only correct fix. If prompt modification appears necessary, stop and document findings first.
- `src/content_creation/generation/` is normally frozen. For this task, changes inside `src/content_creation/generation/script.py` are allowed only to remove structural marker leakage from final script output.
- `src/content_creation/models/` remains frozen. Do not modify model files unless absolutely necessary; if necessary, stop and document why.
- Preserve existing public interfaces unless an existing test proves the interface is incorrect.
- Do not delete the meaning of the generated sentence. Only remove standalone marker tokens.
- Do not remove normal parenthetical content that is not one of the known structural markers.
- The cleanup must be deterministic.
- The full test suite must not drop below the current baseline of 986 passing tests.

## Implementation Steps

1. Run baseline validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=no -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   986 passed
   ```

   Exact count may be higher, but must not be lower.

2. Confirm the current token leak from generated scripts:

   ```bash
   python3 - <<'PY'
   import json
   import pathlib
   import re

   marker_re = re.compile(r"\((F|K|C)\)")
   scripts = list(pathlib.Path("data/scripts").glob("*.json"))

   print("Script files checked:", len(scripts))

   leaked = []
   for f in scripts:
       try:
           d = json.loads(f.read_text())
       except Exception as e:
           print("ERROR:", f, e)
           continue

       content = json.dumps(d, ensure_ascii=False)
       if marker_re.search(content):
           leaked.append(f)

   print("Files with marker leaks:", len(leaked))
   for f in leaked[:10]:
       d = json.loads(f.read_text())
       print("---", f)
       print(str(d)[:900])
   PY
   ```

3. Read the likely implementation files before changing anything:

   ```bash
   sed -n '1,260p' src/content_creation/generation/script.py
   sed -n '1,260p' src/content_creation/ui/pages/5_asset_workshop.py
   sed -n '1,260p' tests/test_script_storyboard_integration.py
   ```

4. Search for marker-token logic and script assembly paths:

   ```bash
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     -E "\(F\)|\(K\)|\(C\)|script_sections|raw_script|short_video" \
     prompts src tests docs/tasks | head -120
   ```

5. Diagnose the correct cleanup layer.

   Preferred fix order:

   1. Clean at script asset assembly time if markers are internal planning annotations leaking into final publishable text.
   2. Clean at display/render time only if stored assets are intentionally raw but UI must show publishable copy.
   3. Do not alter prompts unless the generator is explicitly instructed to emit these markers as final content and no safer output-layer cleanup exists.

6. Write diagnostics to:

   ```text
   docs/phase-12.2-script-token-cleanup.md
   ```

   The diagnostic file must include:

   ```markdown
   # Phase 12.2 Script Token Cleanup

   ## Baseline

   - Test count before change:
   - Script files checked:
   - Files with `(F)(K)(C)` marker leaks before change:

   ## Root Cause

   Explain exactly where the markers enter final script output.

   ## Fix Strategy

   Explain whether cleanup was applied in generation, UI display, or another layer, and why.

   ## Post-Fix Evidence

   - Test count after change:
   - Files with marker leaks after change:
   - Regression tests added or updated:

   ## Risk Notes

   Mention any remaining generation-quality issue that should be handled in a later task.
   ```

7. Implement the smallest correct fix.

   The fixed behavior must satisfy:

   - final script sections do not contain standalone `(F)`, `(K)`, or `(C)` tokens
   - final copied/displayed script text does not contain standalone `(F)`, `(K)`, or `(C)` tokens
   - normal parentheses are preserved, for example `(2024)`, `(optional)`, `(step 1)`
   - sentence spacing remains clean after marker removal
   - script generation remains deterministic
   - missing optional fields do not crash script rendering or serialization

8. Add or update tests.

   At minimum, tests must prove:

   - script output containing `"This matters. (F) Next point. (K)"` is cleaned to readable text
   - standalone marker tokens are removed from all final script sections
   - normal parenthetical text is preserved
   - existing script/storyboard integration still passes

9. Run targeted validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest tests/test_script_storyboard_integration.py --tb=short -q
   ```

10. Run a broader relevant test pass:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest tests --tb=short -q -k "script or storyboard or asset or generation"
    ```

11. Run full validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    Expected result:

    ```text
    986 passed
    ```

    Exact count may be higher, but must not be lower.

12. Re-run marker leak check:

    ```bash
    python3 - <<'PY'
    import json
    import pathlib
    import re

    marker_re = re.compile(r"\((F|K|C)\)")
    scripts = list(pathlib.Path("data/scripts").glob("*.json"))

    leaked = []
    for f in scripts:
        try:
            d = json.loads(f.read_text())
        except Exception as e:
            print("ERROR:", f, e)
            continue

        content = json.dumps(d, ensure_ascii=False)
        if marker_re.search(content):
            leaked.append(f)

    print("Script files checked:", len(scripts))
    print("Files with marker leaks:", len(leaked))

    if leaked:
        print("Examples:")
        for f in leaked[:10]:
            print("-", f)
        raise SystemExit("FAIL: script marker tokens still leak into saved script output")

    print("PASS: no standalone (F)(K)(C) markers found in saved script output")
    PY
    ```

13. Update `docs/phase-12.2-script-token-cleanup.md` with post-fix evidence.

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -m py_compile src/content_creation/generation/script.py

uv run python -m pytest tests/test_script_storyboard_integration.py --tb=short -q

uv run python -m pytest tests --tb=short -q -k "script or storyboard or asset or generation"

uv run python -m pytest --tb=short -q 2>&1 | tail -3

python3 - <<'PY'
import json
import pathlib
import re

marker_re = re.compile(r"\((F|K|C)\)")
scripts = list(pathlib.Path("data/scripts").glob("*.json"))

leaked = []
for f in scripts:
    d = json.loads(f.read_text())
    content = json.dumps(d, ensure_ascii=False)
    if marker_re.search(content):
        leaked.append(f)

print("Script files checked:", len(scripts))
print("Files with marker leaks:", len(leaked))

if leaked:
    for f in leaked[:10]:
        print("-", f)
    raise SystemExit("FAIL: script marker tokens still leak into saved script output")

print("PASS: no standalone (F)(K)(C) markers found in saved script output")
PY
```

## Success Criteria

- [ ] Root cause of script marker token leakage is documented.
- [ ] Final script output no longer contains standalone `(F)`, `(K)`, or `(C)` marker tokens.
- [ ] Normal parenthetical text remains preserved.
- [ ] Script output spacing remains readable after cleanup.
- [ ] Regression tests cover marker cleanup.
- [ ] `docs/phase-12.2-script-token-cleanup.md` contains before/after evidence.
- [ ] Full test suite shows at least 986 passed.
- [ ] No unrelated UI cleanup is included.
- [ ] No prompt changes are made unless explicitly justified in diagnostics.
- [ ] No `needs_review`, timestamp, enum-label, or approval-state fixes are included.

## Depends On

TASK-030

## Commit Message

```text
fix(scripts): remove structural marker tokens from final output (TASK-031)
```
