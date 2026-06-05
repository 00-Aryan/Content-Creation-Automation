# Phase 11.9.4 — CI/CD Foundation

This document outlines the design and implementation of the production CI/CD foundation for the Content Creation Automation platform.

## Workflows Created

Three GitHub Actions workflows have been created under `.github/workflows/`:

1. **Tests Workflow (`tests.yml`)**:
   - Runs the full test suite using `pytest` across Python versions `3.12` and `3.14`.
   - Uses `astral-sh/setup-uv` to manage dependency installation and caching.
   - Triggers on pushes and pull requests targeting the main development branches.

2. **Coverage Workflow (`coverage.yml`)**:
   - Executes the test suite with coverage collection.
   - Generates HTML and XML coverage reports.
   - Uploads both the HTML report directory (`htmlcov/`) and XML file (`coverage.xml`) as artifacts for external systems or manual inspection.

3. **Code Quality Workflow (`quality.yml`)**:
   - Executes code formatting and static analysis checks on every push and pull request.
   - Checks code formatting using `black --check`.
   - Checks import order consistency using `isort --check-only`.
   - Checks static type compliance using `mypy`.

## Commands Used

The workflows are built around `uv` for package management and virtual environment execution:

- **Dependency Installation**:
  ```bash
  uv sync --all-extras --dev
  ```
- **Test Execution**:
  ```bash
  uv run pytest
  ```
- **Coverage Generation**:
  ```bash
  uv run pytest --cov=src/content_creation --cov-report=xml --cov-report=html
  ```
- **Code Quality Checks**:
  ```bash
  uv run black --check src tests
  uv run isort --check-only src tests
  uv run mypy src
  ```

## Python Version Choice

- **Python 3.12**: Selected as the baseline stable version for production, representing the primary deployment target.
- **Python 3.14**: Included in the testing matrix to proactively identify compatibility issues, deprecations, and ensure future compatibility with Python 3.14 features. The workspace is already hardened against Python 3.14 deprecations (e.g., SQLite connection cleanup and thread limits).

## Current Quality Tool Gaps

During the audit of `pyproject.toml`, the following gaps were identified:
- **Ruff**: Not yet configured or declared in the project dev dependencies. Ruff can consolidate Black, Isort, Flake8, and other linters into a single, high-performance tool.
- **Bandit**: Not yet included for security vulnerability scanning.
- **Pydocstyle / Flake8**: No strict docstring or style checks are currently active outside of Black formatting.

> [!NOTE]
> Ruff and Bandit are not yet added as dependencies in this phase to prevent undocumented changes to `pyproject.toml` and avoid runtime package conflicts.

## Future Quality Gate Plan

To address these gaps, the following roadmap is proposed:
1. **Dependency Addition**: Add `ruff` and `bandit` to the dev dependencies group in `pyproject.toml`.
2. **Quality Integration**: Integrate Ruff linting (`uv run ruff check`) and Bandit analysis (`uv run bandit -r src/`) into `.github/workflows/quality.yml`.
3. **Strict Quality Gates**: Enforce zero-warning policies for linting and formatting.
4. **Coverage Gates**: Once stable coverage thresholds are established, configure `pytest-cov` to fail builds if coverage falls below a specified limit (e.g., 90%).
