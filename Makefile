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
