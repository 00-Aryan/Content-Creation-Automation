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
