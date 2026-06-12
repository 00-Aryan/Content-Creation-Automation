# TASK-032: Remove needs_review placeholder pollution from thumbnail output

**Phase:** 12.2  
**Status:** DONE  
**Priority:** HIGH  
**Created:** 2026-06-12  
**Completed:** 2026-06-12  
**Requires approval:** YES  

## Objective

Stop the literal placeholder string `needs_review` from polluting thumbnail text fields and prompt lists, while preserving `ReviewStatus.NEEDS_REVIEW` as the correct workflow status.

## Scope

### Files to modify

- `src/content_creation/generation/thumbnail.py` — fix fallback thumbnail generation so user-facing thumbnail fields do not contain literal `needs_review` placeholder text.
- `tests/` — add or update focused thumbnail generation tests proving fallback output is reviewable without placeholder pollution.

### Files to create

- `docs/phase-12.2-thumbnail-placeholder-cleanup.md` — record placeholder leak evidence, root cause, fix strategy, and validation results.

### Files to NOT touch

All other files.

## Constraints

- Do not change workflow state semantics. `ReviewStatus.NEEDS_REVIEW` must remain valid status metadata.
- Do not remove the ability to mark fallback thumbnails as needing review.
- Do not use literal `needs_review` as a user-facing value in:
  - `title_text`
  - `supporting_text`
  - `visual_metaphor`
  - `style`
  - `negative_prompt`
  - `readability_notes`
- Do not change approval-state behavior in this task.
- Do not fix raw enum labels in this task.
- Do not fix timestamp formatting in this task.
- Do not fix terminal-state UI errors in this task.
- Do not modify `prompts/` unless diagnostics prove prompt changes are required. If prompt modification appears necessary, stop and document findings first.
- `src/content_creation/models/` remains frozen. Do not modify model files unless absolutely necessary; if necessary, stop and document why.
- Keep the fix deterministic.
- Missing optional fields must not crash thumbnail fallback generation.
- The full test suite must not drop below the current baseline of 987 passing tests.

## Implementation Steps

1. Run baseline validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest --tb=no -q 2>&1 | tail -3
   ```

   Expected result:

   ```text
   987 passed
   ```

   Exact count may be higher, but must not be lower.

2. Confirm current placeholder pollution in generated thumbnails:

   ```bash
   python3 - <<'PY'
   import json
   import pathlib

   thumbnail_dirs = [
       pathlib.Path("data/thumbnails"),
       pathlib.Path("data/thumbnail_prompts"),
   ]

   files = []
   for d in thumbnail_dirs:
       if d.exists():
           files.extend(d.glob("*.json"))

   polluted = []
   for f in files:
       try:
           data = json.loads(f.read_text())
       except Exception as e:
           print("ERROR:", f, e)
           continue

       text = json.dumps(data, ensure_ascii=False)
       if "needs_review" in text:
           polluted.append(f)

   print("Thumbnail files checked:", len(files))
   print("Files containing literal needs_review:", len(polluted))

   for f in polluted[:10]:
       print("---", f)
       print(f.read_text()[:900])
   PY
   ```

3. Read the thumbnail generator fully before changing anything:

   ```bash
   sed -n '1,260p' src/content_creation/generation/thumbnail.py
   ```

4. Find existing thumbnail tests:

   ```bash
   find tests -type f | grep -Ei 'thumbnail|asset|generation|manifest'
   grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=htmlcov \
     "ThumbnailGenerator\|ThumbnailPrompt\|negative_prompt\|needs_review" \
     tests src docs/tasks | head -160
   ```

5. Diagnose whether the pollution comes from:

   - generator fallback values
   - LLM output parsing
   - prompt instructions
   - UI rendering
   - serialized historical data

6. Write diagnostics to:

   ```text
   docs/phase-12.2-thumbnail-placeholder-cleanup.md
   ```

   The diagnostic file must include:

   ```markdown
   # Phase 12.2 Thumbnail Placeholder Cleanup

   ## Baseline

   - Test count before change:
   - Thumbnail files checked:
   - Files containing literal `needs_review` before change:

   ## Root Cause

   Explain exactly where `needs_review` entered user-facing thumbnail fields.

   ## Fix Strategy

   Explain what changed and why.

   ## Post-Fix Evidence

   - Test count after change:
   - Files containing literal `needs_review` after change:
   - Regression tests added or updated:

   ## Risk Notes

   Mention whether existing historical thumbnail files still need regeneration or migration.
   ```

7. Implement the smallest correct fix in `src/content_creation/generation/thumbnail.py`.

   Required behavior:

   - `review_status=ReviewStatus.NEEDS_REVIEW` remains intact for fallback thumbnails.
   - Fallback with storyboard must use useful storyboard-derived values where available.
   - Fallback without storyboard must use neutral, operator-readable placeholders, not `needs_review`.
   - `negative_prompt` must not contain `needs_review`.
   - `readability_notes` must explain the fallback state in human-readable form.
   - Generated fallback thumbnail must remain valid under existing `ThumbnailPrompt` model constraints.

8. Add or update tests.

   At minimum, tests must prove:

   - storyboard fallback does not put literal `needs_review` in user-facing fields
   - no-storyboard fallback does not put literal `needs_review` in user-facing fields
   - `review_status` remains `ReviewStatus.NEEDS_REVIEW`
   - `negative_prompt` remains a list and does not contain `needs_review`
   - normal successful thumbnail generation behavior is not broken

9. Run targeted validation:

   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -m pytest tests --tb=short -q -k "thumbnail or asset or generation"
   ```

10. Run full validation:

    ```bash
    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q 2>&1 | tail -3
    ```

    Expected result:

    ```text
    987 passed
    ```

    Exact count may be higher, but must not be lower.

11. Re-run placeholder pollution check:

    ```bash
    python3 - <<'PY'
    import json
    import pathlib

    thumbnail_dirs = [
        pathlib.Path("data/thumbnails"),
        pathlib.Path("data/thumbnail_prompts"),
    ]

    files = []
    for d in thumbnail_dirs:
        if d.exists():
            files.extend(d.glob("*.json"))

    polluted = []
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print("ERROR:", f, e)
            continue

        text = json.dumps(data, ensure_ascii=False)
        if "needs_review" in text:
            polluted.append(f)

    print("Thumbnail files checked:", len(files))
    print("Files containing literal needs_review:", len(polluted))

    if polluted:
        print("NOTE: Existing historical files may need regeneration or migration.")
        for f in polluted[:10]:
            print("-", f)

    print("PASS: generator fallback fixed; inspect diagnostics for historical file status")
    PY
    ```

12. Update `docs/phase-12.2-thumbnail-placeholder-cleanup.md` with post-fix evidence.

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

python3 -m py_compile src/content_creation/generation/thumbnail.py

uv run python -m pytest tests --tb=short -q -k "thumbnail or asset or generation"

uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Success Criteria

- [ ] Root cause of `needs_review` placeholder pollution is documented.
- [ ] Thumbnail fallback generation no longer writes literal `needs_review` into user-facing fields.
- [ ] `ReviewStatus.NEEDS_REVIEW` remains intact as metadata.
- [ ] `negative_prompt` remains a list and does not contain `needs_review`.
- [ ] Storyboard fallback still uses storyboard-owned thumbnail fields.
- [ ] No-storyboard fallback remains valid and human-readable.
- [ ] Regression tests cover both fallback paths.
- [ ] `docs/phase-12.2-thumbnail-placeholder-cleanup.md` contains before/after evidence.
- [ ] Full test suite shows at least 987 passed.
- [ ] No approval-state, enum-label, timestamp, or terminal-state UI fixes are included.

## Depends On

TASK-031

## Commit Message

```text
fix(thumbnails): remove needs_review placeholder pollution (TASK-032)
```
