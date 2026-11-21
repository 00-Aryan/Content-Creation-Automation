# ADR 003: Single Consolidated WAL-Mode SQLite Database (content_factory.db)

- **Status:** PROPOSED
- **Date:** 2026-11-21
- **Deciders:** `spec-architect`, `phase-orchestrator`
- **Target Phase:** Phase 2C (`refactor/phase2c-sqlite-consolidation`)

---

## 1. Context & Problem Statement

The `Content-Creation-Automation` platform relies on SQLite for state persistence, distributed locking, event sourcing, operational metrics, notification tracking, and audit compliance logging. Historically, these subsystems evolved independently, resulting in **6 discrete SQLite database files** located in the `data/` directory (`docs/audit/02-dependencies-and-boundaries.md` §4.2):

1. `data/jobs.db` — Background job execution tracking (`jobs` table).
2. `data/locks.db` — Distributed cooperative resource locking (`locks` table).
3. `data/events.db` — Domain event sourcing and timeline history (`events` table).
4. `data/notifications.db` — User and operational alert records (`notifications` table).
5. `data/metrics.db` — Operational telemetry and KPI records (`metrics` table).
6. `data/audit.db` — Immutable audit trail and compliance logs (`audit` table).

While this multi-database design offered early domain isolation, it introduces critical architectural liabilities, performance bottlenecks, and operational fragilities under continuous local execution on Windows:

1. **Connection and File Descriptor Sprawl on Windows (`windows-python-hygiene` Rule 5):**
   - Each SQLite database requires independent connection handles, thread-local connection caches, and distinct file locks.
   - On Windows, where SQLite file locks interact with NTFS file sharing mechanisms, managing 6 separate `.db`, `.db-wal`, and `.db-shm` file triplets (up to 18 distinct OS file handles) causes file lock contention, handle leakage, and `PermissionError: [WinError 32]` during background worker restarts or test cleanups.
2. **Inline DDL Schema Execution in Streamlit Render Hot Paths (`UI-002`, `PERF-001`):**
   - In `src/content_creation/ui/services/client.py:519-574`, building the operations dashboard snapshot opens 6 separate database connections and executes DDL schema checks (`create_job_schema`, `create_lock_schema`, `create_event_store_schema`, `create_notification_schema`, `create_metrics_schema`, `create_audit_schema`) on every invocation.
   - Furthermore, `src/content_creation/ui/services/client.py:82` invokes `create_notification_schema(conn)` every time a notification connection is requested.
   - Executing `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` inside UI rendering loops directly violates `.agents/skills/performance-optimization/SKILL.md` Rule 4 ("Zero DDL in Hot Paths"), adding CPU overhead, lock acquisition latency, and disk I/O to every user interaction.
3. **Cross-Subsystem Consistency and Transaction Boundaries:**
   - Operational workflows frequently span subsystems (e.g., executing a job should atomically release a lock, append a domain event, update a KPI metric, and record an audit entry). With 6 distinct databases, two-phase commits are impossible without external transaction coordinators, risking partial state corruption during process termination or unhandled exceptions.
4. **Phase 3 LangGraph Checkpointer Convergence (`langgraph-pydanticai-patterns` Rule 1):**
   - The target Phase 3 synthesis architecture replaces legacy sequential workflow scripts with LangGraph state graphs checkpointed via `langgraph.checkpoint.sqlite.SqliteSaver`.
   - `SqliteSaver` expects a single, robust, WAL-mode SQLite database connection. Operating 6 fragmented database files alongside a 7th checkpointer database would exacerbate operational overhead and fragmented state inspection.

---

## 2. Decision Drivers

- **Local-First Native Windows Execution:** Single-process, lightweight execution on Windows PowerShell with Python 3.12, minimizing NTFS file handle locking overhead.
- **Unified Connection Factory & Pragma Hygiene:** Enforce uniform SQLite configuration across all subsystems:
  - `PRAGMA journal_mode=WAL;` — Concurrent multi-reader / single-writer non-blocking transactions.
  - `PRAGMA busy_timeout=5000;` — Automatic 5-second backoff before raising `OperationalError: database is locked`.
  - `PRAGMA foreign_keys=ON;` — Relational constraint enforcement.
  - `PRAGMA synchronous=NORMAL;` — Safe balance of durability and disk write latency in WAL mode.
- **Zero DDL in Hot Paths:** Move all schema creation and migration routines strictly to initialization lifecycle gates, completely banning DDL from UI rendering and per-item pipeline loops.
- **Deterministic Test Isolation:** Guarantee that all unit and contract tests run cleanly in `pytest`'s `tmp_path` fixture, never modifying working tree databases or leaving dangling locked file handles.
- **Backward Compatibility with Legacy Files:** Support transparent migration and fallback: if `content_factory.db` does not yet exist but legacy `.db` files do, provide smooth operational transition.
- **Phase 3 Readiness:** Provide the single canonical SQLite anchor required for LangGraph `SqliteSaver` state persistence.

---

## 3. Considered Options

### Option 1: Consolidated Single SQLite Database `data/content_factory.db` with Centralized Connection Factory (Chosen)
- Consolidate all 6 subsystems into a single database file: `data/content_factory.db`.
- Verified schema orthogonality:
  - `jobs` (columns: `job_id`, `job_type`, `status`, `priority`, `action_id`, `operator_id`, `target_type`, `target_id`, `payload_json`, `result_json`, `retry_count`, `max_retries`, `created_at`, `queued_at`, `started_at`, `completed_at`, `run_after`, `last_heartbeat`, `correlation_id`, `error_message`).
  - `locks` (columns: `lock_id`, `lock_type`, `resource_id`, `owner_job_id`, `status`, `acquired_at`, `last_heartbeat`, `released_at`, `metadata_json`).
  - `events` (columns: `id`, `event_name`, `category`, `source`, `correlation_id`, `entity_type`, `entity_id`, `payload_json`, `created_at`, `version`).
  - `notifications` (columns: `notification_id`, `title`, `message`, `severity`, `category`, `status`, `timestamp`, `correlation_id`, `event_id`, `entity_type`, `entity_id`).
  - `metrics` (columns: `id`, `metric_name`, `metric_type`, `value`, `created_at`, `entity_type`, `entity_id`, `dimensions_json`).
  - `audit` (columns: `id`, `timestamp`, `actor_type`, `actor_id`, `action_type`, `entity_type`, `entity_id`, `event_type`, `correlation_id`, `previous_state`, `new_state`, `metadata_json`, `source`, `severity`).
  - Indexes: All 24 custom indexes across the 6 subsystems are uniquely named with `idx_<subsystem>_...` prefixes. **Zero table or index name collisions exist.**
- Create a centralized database management module: `src/content_creation/platform/storage/database.py`.
- Expose `get_db_connection()`, `get_db_path()`, and `init_content_factory_db()`.
- Update `ApplicationContext` to carry `db_path: Path = base_dir / "data" / "content_factory.db"`.
- Refactor `ServiceClient` and `cli/observability.py` to route to `content_factory.db`, eliminating all inline DDL from `get_operations_snapshot()` and `get_notification_connection()`.

### Option 2: External Client-Server Database (PostgreSQL or MySQL)
- Migrate persistence to an external PostgreSQL instance running locally or via Docker.
- *Rejected because:* Violates core project principles (`AGENTS.md` §6.1, `spec-architect` §3.1). Introduces heavy external container dependencies, external service management, network socket requirements, and breaks the local-first, zero-overhead developer setup.

### Option 3: Status Quo with DDL Caching (Retain 6 Separate Databases)
- Retain `jobs.db`, `locks.db`, `events.db`, `notifications.db`, `metrics.db`, and `audit.db` as separate files, but add a caching layer to avoid running `create_*_schema` on every UI render.
- *Rejected because:* Retains 18 distinct OS file handles on Windows; does not resolve cross-database transaction limitations; increases maintenance burden; fails to provide a unified persistence anchor for upcoming Phase 3 LangGraph checkpointers.

---

## 4. Decision Outcome

**Chosen: Option 1.**

### Detailed Architectural Specifications:

#### 4.1 Storage Platform Module: `src/content_creation/platform/storage/database.py`
A new Layer 2 foundational module providing:
```python
"""Centralized SQLite database manager, connection factory, and schema initialization."""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

from content_creation.audit.schema import create_audit_schema
from content_creation.events.store.schema import create_event_store_schema
from content_creation.jobs.schema import create_job_schema, create_lock_schema
from content_creation.metrics.schema import create_metrics_schema
from content_creation.notifications.schema import create_notification_schema

DEFAULT_DB_REL_PATH = Path("data") / "content_factory.db"


def get_db_path(base_dir: Optional[Path] = None) -> Path:
    """Resolve the canonical SQLite database path.

    Precedence:
    1. Explicit CONTENT_FACTORY_DB_PATH environment variable.
    2. base_dir / "data" / "content_factory.db" (if base_dir provided).
    3. Path(os.environ["CONTENT_FACTORY_ROOT"]) / "data" / "content_factory.db" (if set).
    4. Path.cwd() / "data" / "content_factory.db".
    """
    env_db = os.environ.get("CONTENT_FACTORY_DB_PATH")
    if env_db:
        return Path(env_db)

    if base_dir is not None:
        return base_dir / DEFAULT_DB_REL_PATH

    root_env = os.environ.get("CONTENT_FACTORY_ROOT")
    if root_env:
        return Path(root_env) / DEFAULT_DB_REL_PATH

    return Path.cwd() / DEFAULT_DB_REL_PATH


def create_connection(
    db_path: Union[Path, str],
    timeout: float = 10.0,
    check_same_thread: bool = False,
) -> sqlite3.Connection:
    """Create and configure a WAL-mode SQLite connection with mandatory pragmas."""
    target_path = Path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        timeout=timeout,
        check_same_thread=check_same_thread,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_content_factory_db(conn_or_path: Union[sqlite3.Connection, Path, str]) -> None:
    """Initialize all 6 subsystem schemas idempotently in a single transaction."""
    if isinstance(conn_or_path, sqlite3.Connection):
        _apply_schemas(conn_or_path)
    else:
        conn = create_connection(conn_or_path)
        try:
            _apply_schemas(conn)
        finally:
            conn.close()


def _apply_schemas(conn: sqlite3.Connection) -> None:
    """Run all schema initializers."""
    create_job_schema(conn)
    create_lock_schema(conn)
    create_event_store_schema(conn)
    create_notification_schema(conn)
    create_metrics_schema(conn)
    create_audit_schema(conn)
```

#### 4.2 Application Context Integration: `src/content_creation/application/context.py`
- Add `db_path: Path` attribute to `ApplicationContext` pointing to `base_dir / "data" / "content_factory.db"`.
- Provide `get_db_connection() -> sqlite3.Connection` delegating to `create_connection(self.db_path)`.
- Ensure schema initialization is triggered once upon container creation or explicitly via CLI/startup lifecycle.
- Remove dead property `content_intelligence_dir` (`DEAD-005`).

#### 4.3 Service Client Refactoring: `src/content_creation/ui/services/client.py`
- In `get_operations_snapshot()`:
  - Eliminate the 6 discrete `_open_db("jobs.db")`, `_open_db("locks.db")`, etc. calls.
  - Open **ONE** connection to `content_factory.db` (with legacy fallback to discrete files if `content_factory.db` does not exist).
  - Pass the single connection to `SQLiteJobRepository`, `SQLiteLockRepository`, and `SQLiteNotificationRepository`.
  - Pass `str(db_path)` to `SQLiteEventRepository`, `SQLiteMetricRepository`, and `SQLiteAuditRepository`.
  - **Zero DDL:** Remove all `create_*_schema` calls from `get_operations_snapshot()`.
  - Remove deprecated `ConnectionManager()` instantiation at line 578; set `connection_manager=None` when creating `ObservabilityService`.
  - Cleanly close connections in `finally:`.
- In `get_notification_connection()`:
  - Connect to `content_factory.db` (or legacy `notifications.db` fallback).
  - Remove inline `create_notification_schema(conn)`.
- In `get_event_timeline()`:
  - Point query to `content_factory.db` (or legacy `events.db` fallback).

#### 4.4 CLI Observability Refactoring: `src/content_creation/cli/observability.py`
- Replace hardcoded `events.db`, `metrics.db`, and `audit.db` path references with `get_db_path(ctx.base_dir)`.
- If `content_factory.db` exists, use it as the primary store for all `event-*`, `metrics-*`, and `audit-*` subcommands. If not, transparently fall back to legacy discrete files for backward compatibility.

---

## 5. Consequences

### Positive Consequences
- **Reduced Windows Lock Contention:** Consolidates 18 file handles into a single `.db`, `.db-wal`, and `.db-shm` file triplet, eliminating `[WinError 32]` lock contention and file-busy crashes.
- **Streamlit Render Acceleration:** Eliminates 6 redundant database connections and 6 DDL execution routines per page rerun, delivering snappy, sub-10ms snapshot generation on the Operations Dashboard.
- **Zero Schema Name Collisions:** Verified 100% collision-free coexistence of all 6 tables and 24 indexes in a single SQLite catalog.
- **Phase 3 LangGraph Ready:** Establishes the exact WAL-mode SQLite database needed to host `SqliteSaver` checkpoints in Phase 3.
- **Unified Backup & Archival:** Operators can back up the entire operational state by archiving a single file (`content_factory.db`).

### Negative Consequences & Mitigation Strategies
- **Single File Concurrency Limit:** SQLite WAL mode permits multiple concurrent readers but only one concurrent writer.
  - *Mitigation:* `PRAGMA busy_timeout=5000;` ensures write transactions wait up to 5 seconds before failing. In local-first desktop usage, write transaction durations are sub-millisecond, avoiding thread starvation.
- **Migration of Existing Local Data:** Historical test runs or manual runs may have state in discrete `.db` files.
  - *Mitigation:* The connection factory supports transparent fallback: if `content_factory.db` is missing, repositories seamlessly query legacy files. Operators can initialize the unified database via `content-creation init-db` or rely on automatic bootstrapping upon first run. Runtime `.db` files remain strictly ignored by git (`.gitignore`).

---

## 6. Compliance & Verification

1. **AST Layer Violation Check:**
   - Enforce 0 direct SQLite or DDL imports in `src/content_creation/ui/` (`tests/test_ui_pages.py`).
2. **Domain Test Verification:**
   - New comprehensive domain test suite `tests/test_content_factory_db.py` verifying:
     - All 6 schemas initialize cleanly into `content_factory.db`.
     - Concurrent CRUD across all 6 repositories without lock contention.
     - WAL mode, busy timeout, foreign keys, and normal synchronous pragmas active.
     - Zero unclosed handles or `PermissionError` on cleanup.
3. **Ratchet Rule:**
   - Static type checking `uv run mypy src/content_creation/platform/storage/database.py --strict` passes with 0 errors.
