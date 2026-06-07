# TASK-011: Add missing return type hints to CLI entry point functions

**Phase:** 11.9.4
**Status:** PENDING
**Priority:** MEDIUM
**Created:** 2026-06-07
**Completed:** —
**Requires approval:** NO

---

## Source References
- Phase: 11.9.4 Automation Validation

## Objective
Add explicit return type annotations to public functions in `src/content_creation/cli.py` that are currently missing them. Tests that `run-tasks.sh` correctly handles a Type A (source code) task — running pytest baseline before and after.

## Context
`AGENTS.md` requires type hints on all public methods. Some CLI entry point functions currently lack return type annotations. This is a safe, non-behaviour-changing fix that exercises the full Type A path: baseline check → implementation → validation → pytest re-run → commit.

## Scope

### Files to modify
- `src/content_creation/cli.py` — add return type annotations to public functions only

### Files to NOT touch
- All test files
- All other source files
- All models (`src/content_creation/models/`)
- All generators (`src/content_creation/generation/`)
- `prompts/`

## Constraints
- Only add type annotations — do not change any logic, control flow, or variable names
- If a function returns nothing, annotate as `-> None`
- If a function returns a value, use the correct existing type — do not introduce new imports unless the type already exists in the file
- If all functions already have type hints, add them to any `__init__` methods that are missing them

## Implementation Steps

1. Read `src/content_creation/cli.py` fully.

2. Find every `def` that is:
   - Public (does not start with `_`)
   - Missing a return type annotation (`-> type`)

3. Add the appropriate return type to each:
   - Functions that return nothing: `-> None`
   - Functions that return a value: use the correct type from what the function actually returns

4. Do not change any other lines.

5. Verify the file parses correctly:
   ```bash
   export UV_CACHE_DIR=/tmp/uv-cache
   uv run python -c "import ast; ast.parse(open('src/content_creation/cli.py').read()); print('PASS: syntax valid')"
   ```

## Validation

```bash
export UV_CACHE_DIR=/tmp/uv-cache

# Confirm syntax is valid
uv run python -c "import ast; ast.parse(open('src/content_creation/cli.py').read()); print('PASS: syntax valid')"

# Confirm no public functions are missing return types
uv run python -c "
import ast, sys
tree = ast.parse(open('src/content_creation/cli.py').read())
missing = [
    n.name for n in ast.walk(tree)
    if isinstance(n, ast.FunctionDef)
    and not n.name.startswith('_')
    and n.returns is None
]
if missing:
    print('FAIL: missing return types:', missing)
    sys.exit(1)
print('PASS: all public functions have return types')
"

# Full test suite — must stay at ≥ 950
uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Success Criteria
- [ ] All public functions in `cli.py` have return type annotations
- [ ] File parses without syntax errors
- [ ] Test suite shows ≥ 950 passed
- [ ] Only `src/content_creation/cli.py` was modified

## Depends On
None

## Blocks
None

## Commit Message
```
fix(types): add missing return type annotations to cli.py public functions (TASK-011)
```

## Agent Notes
This is the first Type A task via `run-tasks.sh`. If pytest runs before and after, and the count stays at 950+, the Type A path is validated. If all public functions already have type hints, add them to any `__init__` in the file instead and adjust the commit message accordingly.