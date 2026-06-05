# Technical Debt

This file tracks outstanding technical debt and maintenance requirements across the codebase.

- **CLI File Size & Coverage**: The primary CLI entry points have grown large and have low test coverage.
- **WorkflowActionExecutor Size & Coverage**: The `WorkflowActionExecutor` handles a large number of actions and contains complex logic with relatively low test coverage.
- **SQLite Repository Lifecycle Logic**: Multiple SQLite repositories exist and may share repeated lifecycle and connection pool management logic rather than using a consolidated utility.
- **Database Migration Framework**: Database schemas are managed ad-hoc; a formal migration framework (e.g. Alembic or custom lightweight migrations) is missing.
- **Operational Runbooks**: Operational instructions, runbooks for backups, restores, and environment migrations are currently missing.
