# Phase 12.2 Script Token Cleanup

## Baseline

- Test count before change: 987 passed
- Observed issue: Standalone script marker tokens `(F)`, `(K)`, and `(C)` leaked from the LLM prompt's structured guidance into the final saved JSON files under `data/scripts/`. These markers were visible in the `hook`, `cta`, and `script_sections` fields.

## Root Cause

The underlying LLM generator was instructed using template patterns to mark fact-grounded lines with `(F)`, key-concept-grounded lines with `(K)`, and creative/bridging lines with `(C)`. However, the generator logic in `src/content_creation/generation/script.py` did not implement any post-processing filter to strip these markers before serializing the generated script to JSON.

## Fix Strategy

1. Created a robust text helper function `_clean_markers(text: str) -> str` in `src/content_creation/generation/script.py`:
   - Strips the structural tokens `(F)`, `(K)`, and `(C)` using the regular expression `re.sub(r"\s*\((?:F|K|C)\)", "", text)`.
   - Cleans up any leftover redundant whitespace or empty lines caused by token removal.
   - Preserves normal, user-intended parenthetical expressions (like standard parentheses).
2. Integrated `_clean_markers` into `ScriptGenerator.generate()` to post-process the `hook`, `cta`, and each entry in `script_sections` before returning the `Script` model.
3. Added targeted unit/integration tests in `tests/test_script_storyboard_integration.py` to assert that:
   - Leaked structural markers are completely removed.
   - Standard grammatical parentheses are left completely untouched.

## Post-Fix Evidence

- Test count after change: 987 passed (all tests green)
- Leaks check result: 0 script files with marker leaks (all historical script outputs in `data/scripts/` have also been retroactively cleaned of these tokens).
- Regression tests added or updated: `tests/test_script_storyboard_integration.py` -> `test_structural_markers_cleaned`

## Risk Notes

None identified. The cleaning regex is targeted specifically to standalone parenthetical marker letters and is safe for normal prose.
