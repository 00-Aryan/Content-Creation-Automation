# AGENTS.md — Agent Instruction Set & Governance Manual

This document provides stable guidance and instructions for autonomous AI agents (such as Antigravity, Codex, and Claude-style agents) working on the Content Creation Automation platform.

## 1. Project Overview
The Content Creation Automation platform is an editorial-first, source-grounded content factory designed for educational ML/AI material. It implements a structured multi-stage pipeline:
`Topic Ingestion -> Scoring -> Briefs -> Content Intelligence -> Storyboards -> Assets -> Manifests -> Calendar Planning -> Verification`
This pipeline is driven by a custom workflow engine, job queuing system, event broker, notification layer (including SSE streaming), metrics collection, and audit logging.

## 2. Setup & Test Commands
All development must use the following standard commands:
- **Environment Setup**:
  ```bash
  uv sync --all-extras --dev
  ```
- **Run Full Test Suite**:
  ```bash
  uv run pytest
  ```
- **Run Quality & Lint Checks**:
  ```bash
  uv run black --check src tests
  uv run isort --check-only src tests
  uv run mypy src
  ```

## 3. Core Architectural Boundaries & Rules
Agents must strictly respect the following engineering and architectural constraints:

1. **UI Decoupling**: The UI layer (e.g., Streamlit views) must not access database repositories, raw file stores, or low-level components directly. All operations must go through the appropriate API, service, or mediator layers.
2. **Worker Decoupling**: Workers in the job queue system must not call upstream or downstream services directly. They must use specified interfaces and state managers.
3. **Action Execution Gate**: All workflow actions must be routed through and executed by the `WorkflowActionExecutor`. Direct state modification is prohibited.
4. **Availability Guard**: The `ActionAvailabilityEngine` acts as the final gate to determine if a workflow action is currently valid for a given topic or asset state.
5. **State Transition Ownership**: The `ReviewTransitionEngine` uniquely owns and manages all review and approval state transitions.
6. **Subscribers are Read-Only**: Event subscribers must never mutate workflow state. They are strictly side-effect handlers (e.g., logging, notifying).
7. **Event-Driven Telemetry**: All metrics, notifications, and audit records must originate from published events, maintaining the audit trail decoupled from the core business logic.
8. **Secret Protection**: Secrets (e.g., API keys, database credentials) must never be logged, persisted in databases or files, or included in event payloads.
9. **Refactoring Discipline**: No broad or structural refactors of existing components without explicit phase approval. Work must remain scoped to the assigned task.

## 4. Phase Workflow & Execution
When tasked with executing a development phase, agents must follow the Plan-Act-Validate cycle:
1. **Plan**: Inspect current implementation, read relevant schemas, and document the proposed changes before editing code.
2. **Act**: Implement minimal, surgical changes. Keep changes clean and fully typed.
3. **Validate**: Run the full test suite (`uv run pytest`) and verify that zero regressions are introduced.
4. **Report**: Create a phase execution report detailing files modified, tests run, and validation outcomes.

## 5. Coding & Style Rules (Do's & Don'ts)
- **DO** write explicit type hints for all function parameters and return types.
- **DO** use `datetime.now(timezone.utc)` for time-aware UTC datetimes. Never use `datetime.utcnow()`.
- **DO** use standard Python `logging` for observability.
- **DO NOT** use SQLAlchemy or any alternate ORM. Use the Supabase client directly where database access is required.
- **DO NOT** add new packages to `pyproject.toml` without documentation and explicit user approval.
- **DO NOT** leave bare `except:` statements. Always catch specific exceptions and handle or log them properly.

## 6. Commit Rules
- All commits should be small and logical.
- Commit messages must follow conventional commits formatting (e.g., `feat(workflow): add action availability gates` or `fix(db): resolve connection pool leak`).

## 7. Security Rules
- **API Keys**: Never hardcode API keys or credentials. Use environment variables managed via `python-dotenv`.
- **Data Safety**: Ensure SQLite database files (`.db`), local JSON storage keys, and credentials/secrets are excluded from git. The following files/patterns must be ignored:
  - `.env` and `.env.*` (except `.env.example`)
  - `*.pem`, `*.key`, `*.crt`
  - `secrets.toml`, `.streamlit/secrets.toml`
  - `data/secrets/`
  - `credentials.json`, `token.json`
- **Terminal Safety**: AI agents must only execute verified commands. No commands accessing external networks (e.g., `curl`, `wget`) should be executed without explicit user supervision.

## 8. Project Control Rules

Before any implementation:
1. Read `docs/project/CURRENT_STATE.md`
2. Read `docs/project/NEXT_ACTION.md`
3. Read `docs/project/PHASES.md`
4. Read `docs/project/BACKLOG.md`
5. Read `docs/project/RISKS.md`

After any phase:
1. Run tests
2. Update `docs/project/PHASES.md`
3. Update `docs/project/CURRENT_STATE.md`
4. Update `docs/project/NEXT_ACTION.md`
5. Update `docs/project/BACKLOG.md` if findings appeared
6. Update `docs/project/RISKS.md` if risks appeared
7. Create phase report

Do not start a new phase if `docs/project/NEXT_ACTION.md` conflicts with the user request. Ask for confirmation.

