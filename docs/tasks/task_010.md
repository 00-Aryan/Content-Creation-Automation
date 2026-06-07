# TASK-010: Add `Makefile` with common development commands

**Phase:** 11.9.4
**Status:** PENDING
**Priority:** HIGH
**Created:** 2026-06-07
**Completed:** —
**Requires approval:** NO

---

## Source References
- Phase: 11.9.4 Automation Validation

## Objective
Add a `Makefile` so common commands (`make test`, `make lint`, `make run-tasks`) don't require memorising long flags. Tests that `run-tasks.sh` correctly waits for TASK-009 before executing this task.

## Context
Currently every command requires knowing the exact invocation: `export UV_CACHE_DIR=... && uv run python -m pytest ...`. A Makefile wraps these so the operator types `make test` and that's it. This task also validates that `run-tasks.sh` correctly enforces the `Depends On: TASK-009` dependency before executing.

## Scope

### Files to create
- `Makefile` (repository root)

### Files to NOT touch
Everything else, especially `pyproject.toml`.

## Constraints
- Use `.PHONY` for all non-file targets
- All targets must set `UV_CACHE_DIR=/tmp/uv-cache` internally
- Do not add a `clean` target that deletes `data/` — pipeline output must be preserved

## Implementation Steps

1. Create `Makefile` in the repository root with this exact content:

```makefile
.PHONY: test lint format type-check run-tasks run-all dry-run security-audit

UV = uv run
UV_ENV = UV_CACHE_DIR=/tmp/uv-cache

# ── Testing ──────────────────────────────────────────────────────────────

test:
	$(UV_ENV) $(UV) python -m pytest --tb=short -q

test-fast:
	$(UV_ENV) $(UV) python -m pytest --tb=short -q -x --ignore=tests/test_notification_streaming.py

test-verbose:
	$(UV_ENV) $(UV) python -m pytest --tb=long -v

# ── Code quality ─────────────────────────────────────────────────────────

lint:
	$(UV_ENV) $(UV) ruff check src/ tests/

format:
	$(UV_ENV) $(UV) black src/ tests/
	$(UV_ENV) $(UV) isort src/ tests/

format-check:
	$(UV_ENV) $(UV) black src/ tests/ --check
	$(UV_ENV) $(UV) isort src/ tests/ --check-only

type-check:
	$(UV_ENV) $(UV) mypy src/content_creation --strict

# ── Automation ───────────────────────────────────────────────────────────

run-tasks:
	./run-tasks.sh

run-all:
	./run-tasks.sh --all

dry-run:
	./run-tasks.sh --dry

# ── Security ─────────────────────────────────────────────────────────────

security-audit:
	@echo "Run in your agent session: \$$security-audit"

pre-commit-run:
	pre-commit run --all-files
```

## Validation

```bash
test -f Makefile && echo "PASS: Makefile exists" || echo "FAIL"
grep -q "UV_CACHE_DIR" Makefile && echo "PASS: cache dir set" || echo "FAIL"
grep -q "run-tasks" Makefile && echo "PASS: automation targets present" || echo "FAIL"
make dry-run 2>&1 | head -5
```

## Success Criteria
- [ ] `Makefile` exists in repo root
- [ ] `make test` works (runs pytest with correct env)
- [ ] `make run-tasks` works (calls `./run-tasks.sh`)
- [ ] No source files modified

## Depends On
TASK-009

## Blocks
None

## Commit Message
```
chore(dev): add Makefile with test, lint, format, and automation targets (TASK-010)
```