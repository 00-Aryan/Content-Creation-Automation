"""Domain tests for consolidated SQLite database manager (database.py).

Verifies single WAL-mode SQLite database persistence, unified schema initialization,
mandatory connection pragmas, multi-subsystem coexistence, and legacy fallback.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from content_creation.application.context import ApplicationContext
from content_creation.cli.observability import _resolve_subsystem_db
from content_creation.platform.storage.database import (
    create_connection,
    get_db_path,
    init_content_factory_db,
)


class TestDatabasePathResolution:
    """Verify database path resolution under various configurations."""

    def test_default_db_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify fallback to cwd/data/content_factory.db when no env/args given."""
        monkeypatch.delenv("CONTENT_FACTORY_DB_PATH", raising=False)
        monkeypatch.delenv("CONTENT_FACTORY_ROOT", raising=False)
        expected = Path.cwd() / "data" / "content_factory.db"
        assert get_db_path() == expected

    def test_db_path_with_base_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify base_dir argument takes precedence over cwd and root env."""
        monkeypatch.delenv("CONTENT_FACTORY_DB_PATH", raising=False)
        expected = tmp_path / "data" / "content_factory.db"
        assert get_db_path(base_dir=tmp_path) == expected

    def test_db_path_with_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify CONTENT_FACTORY_DB_PATH overrides everything."""
        custom_db = tmp_path / "custom" / "my_custom.db"
        monkeypatch.setenv("CONTENT_FACTORY_DB_PATH", str(custom_db))
        assert get_db_path(base_dir=tmp_path / "ignored") == custom_db

    def test_db_path_with_root_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify CONTENT_FACTORY_ROOT env var resolution when base_dir is None."""
        monkeypatch.delenv("CONTENT_FACTORY_DB_PATH", raising=False)
        monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
        expected = tmp_path / "data" / "content_factory.db"
        assert get_db_path() == expected


class TestConnectionFactoryPragmas:
    """Verify create_connection configures mandatory SQLite pragmas."""

    def test_create_connection_pragmas(self, tmp_path: Path) -> None:
        """Verify WAL mode, busy timeout, foreign keys, and synchronous pragmas."""
        db_file = tmp_path / "test_pragmas.db"
        conn = create_connection(db_file)
        try:
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert str(journal_mode).lower() == "wal"

            busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
            assert int(busy_timeout) == 5000

            foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert int(foreign_keys) == 1

            synchronous = conn.execute("PRAGMA synchronous;").fetchone()[0]
            # 1 = NORMAL in SQLite PRAGMA synchronous
            assert int(synchronous) == 1
        finally:
            conn.close()

    def test_row_factory_is_sqlite_row(self, tmp_path: Path) -> None:
        """Verify row_factory is set to sqlite3.Row for dict-like access."""
        db_file = tmp_path / "test_row.db"
        conn = create_connection(db_file)
        try:
            assert conn.row_factory is sqlite3.Row
        finally:
            conn.close()

    def test_create_connection_creates_parent_directories(self, tmp_path: Path) -> None:
        """Verify nested parent directories are created automatically."""
        nested_db = tmp_path / "deep" / "nested" / "dir" / "test.db"
        assert not nested_db.parent.exists()
        conn = create_connection(nested_db)
        try:
            assert nested_db.parent.exists()
        finally:
            conn.close()


class TestUnifiedSchemaInitialization:
    """Verify all 6 subsystem schemas initialize cleanly and idempotently."""

    def test_init_content_factory_db_creates_all_six_tables(self, tmp_path: Path) -> None:
        """Verify jobs, locks, events, notifications, metrics, and audit tables exist."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn = create_connection(db_file)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = {row[0] for row in cursor.fetchall()}
            expected_tables = {"jobs", "locks", "events", "notifications", "metrics", "audit"}
            assert expected_tables.issubset(tables)
        finally:
            conn.close()

    def test_init_content_factory_db_is_idempotent(self, tmp_path: Path) -> None:
        """Verify calling init_content_factory_db multiple times does not error or duplicate."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)
        init_content_factory_db(db_file)  # Second invocation must succeed cleanly

        conn = create_connection(db_file)
        try:
            init_content_factory_db(conn)  # Third invocation on active connection
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            count = cursor.fetchone()[0]
            assert count >= 6
        finally:
            conn.close()

    def test_index_uniqueness_and_no_collision(self, tmp_path: Path) -> None:
        """Verify all custom indexes across 6 subsystems coexist without name collision."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn = create_connection(db_file)
        try:
            cursor = conn.execute(
                "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';"
            )
            indexes = cursor.fetchall()
            index_names = [row["name"] for row in indexes]
            # Verify no duplicate index names
            assert len(index_names) == len(set(index_names))
            # Verify we have indexes across all 6 tables
            indexed_tables = {row["tbl_name"] for row in indexes}
            assert {"jobs", "locks", "events", "notifications", "metrics", "audit"}.issubset(indexed_tables)
        finally:
            conn.close()


class TestMultiSubsystemConcurrentCRUD:
    """Verify simultaneous multi-subsystem operations in single database."""

    def test_concurrent_crud_across_subsystems(self, tmp_path: Path) -> None:
        """Verify writing and reading across jobs, events, and audit tables simultaneously."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn1 = create_connection(db_file)
        conn2 = create_connection(db_file)
        try:
            job_id = str(uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()

            # Connection 1: Insert job and event
            conn1.execute(
                """
                INSERT INTO jobs (job_id, job_type, status, action_id, operator_id, target_type, target_id, payload_json, created_at, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (job_id, "script_generation", "COMPLETED", "gen_script", "op1", "topic", "t1", "{}", now_iso, "corr-1"),
            )
            conn1.execute(
                """
                INSERT INTO events (id, event_name, category, source, correlation_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (str(uuid4()), "job_completed", "workflow", "worker", "corr-1", now_iso),
            )
            conn1.commit()

            # Connection 2: Read job, insert audit record
            job_row = conn2.execute("SELECT * FROM jobs WHERE job_id = ?;", (job_id,)).fetchone()
            assert job_row is not None
            assert job_row["status"] == "COMPLETED"

            audit_id = str(uuid4())
            conn2.execute(
                """
                INSERT INTO audit (id, timestamp, actor_type, actor_id, action_type, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (audit_id, now_iso, "operator", "op1", "approve_topic", "corr-1"),
            )
            conn2.commit()

            # Connection 1: Verify audit record written by connection 2
            audit_row = conn1.execute("SELECT * FROM audit WHERE id = ?;", (audit_id,)).fetchone()
            assert audit_row is not None
            assert audit_row["actor_id"] == "op1"
        finally:
            conn1.close()
            conn2.close()


class TestApplicationContextIntegration:
    """Verify ApplicationContext integration with database factory."""

    def test_context_db_path_and_connection(self, tmp_path: Path) -> None:
        """Verify ctx.db_path points to content_factory.db and get_db_connection works."""
        ctx = ApplicationContext.create(tmp_path)
        assert ctx.db_path == tmp_path / "data" / "content_factory.db"

        init_content_factory_db(ctx.db_path)
        conn = ctx.get_db_connection()
        try:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            assert "jobs" in tables
            assert "notifications" in tables
        finally:
            conn.close()


class TestTransparentFallback:
    """Verify transparent fallback between content_factory.db and legacy discrete files."""

    def test_cli_fallback_to_legacy_when_content_factory_missing(self, tmp_path: Path) -> None:
        """Verify _resolve_subsystem_db falls back to legacy file when legacy exists."""
        ctx = ApplicationContext.create(tmp_path)
        legacy_events = tmp_path / "data" / "events.db"
        legacy_events.parent.mkdir(parents=True, exist_ok=True)
        legacy_events.write_text("LEGACY", encoding="utf-8")

        resolved = _resolve_subsystem_db(ctx, "events.db")
        assert resolved == legacy_events

    def test_cli_prefers_content_factory_db_when_both_exist(self, tmp_path: Path) -> None:
        """Verify _resolve_subsystem_db prefers content_factory.db when it exists."""
        ctx = ApplicationContext.create(tmp_path)
        legacy_events = tmp_path / "data" / "events.db"
        legacy_events.parent.mkdir(parents=True, exist_ok=True)
        legacy_events.write_text("LEGACY", encoding="utf-8")

        cf_db = tmp_path / "data" / "content_factory.db"
        cf_db.write_text("CONSOLIDATED", encoding="utf-8")

        resolved = _resolve_subsystem_db(ctx, "events.db")
        assert resolved == cf_db


class TestIdempotentInitializationPreservesExistingData:
    """Verify init_content_factory_db called repeatedly does not corrupt or wipe existing data."""

    def test_reinit_preserves_rows_across_all_six_tables(self, tmp_path: Path) -> None:
        """Covers ARCH-001 & RISK-001: Repeated re-initialization does not alter existing rows."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = create_connection(db_file)
        try:
            # Insert 1 row in each of the 6 tables
            conn.execute(
                "INSERT INTO jobs (job_id, job_type, status, action_id, operator_id, target_type, target_id, payload_json, created_at, correlation_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                ("job-1", "test_job", "QUEUED", "act-1", "op-1", "topic", "top-1", "{}", now_iso, "corr-reinit"),
            )
            conn.execute(
                "INSERT INTO locks (lock_id, lock_type, resource_id, owner_job_id, status, acquired_at, last_heartbeat) "
                "VALUES (?, ?, ?, ?, ?, ?, ?);",
                ("lock-1", "res_lock", "top-1", "job-1", "ACQUIRED", now_iso, now_iso),
            )
            conn.execute(
                "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                ("event-1", "topic_queued", "test", "worker", "corr-reinit", now_iso),
            )
            conn.execute(
                "INSERT INTO notifications (notification_id, title, message, severity, category, status, timestamp, correlation_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                ("notif-1", "Job Queued", "Job has been queued", "INFO", "pipeline", "UNREAD", now_iso, "corr-reinit"),
            )
            conn.execute(
                "INSERT INTO metrics (id, metric_name, metric_type, value, created_at) "
                "VALUES (?, ?, ?, ?, ?);",
                ("metric-1", "queue_latency_ms", "counter", 15.5, now_iso),
            )
            conn.execute(
                "INSERT INTO audit (id, timestamp, actor_type, actor_id, action_type, correlation_id) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                ("audit-1", now_iso, "user", "admin", "create_job", "corr-reinit"),
            )
            conn.commit()

            # Multiple invocations on active connection
            for _ in range(3):
                init_content_factory_db(conn)

            # Close connection and run multiple invocations on path
            conn.close()
            for _ in range(3):
                init_content_factory_db(db_file)

            # Re-open and verify every table still has exactly 1 row with exact data
            verify_conn = create_connection(db_file)
            try:
                for table in ("jobs", "locks", "events", "notifications", "metrics", "audit"):
                    count = verify_conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
                    assert count == 1, f"Table {table} expected 1 row after re-init, found {count}"

                job = verify_conn.execute("SELECT * FROM jobs WHERE job_id = 'job-1';").fetchone()
                assert job["status"] == "QUEUED"
                assert job["action_id"] == "act-1"

                lock = verify_conn.execute("SELECT * FROM locks WHERE lock_id = 'lock-1';").fetchone()
                assert lock["owner_job_id"] == "job-1"

                event = verify_conn.execute("SELECT * FROM events WHERE id = 'event-1';").fetchone()
                assert event["event_name"] == "topic_queued"

                notif = verify_conn.execute("SELECT * FROM notifications WHERE notification_id = 'notif-1';").fetchone()
                assert notif["title"] == "Job Queued"

                metric = verify_conn.execute("SELECT * FROM metrics WHERE id = 'metric-1';").fetchone()
                assert metric["value"] == 15.5

                audit = verify_conn.execute("SELECT * FROM audit WHERE id = 'audit-1';").fetchone()
                assert audit["actor_id"] == "admin"
            finally:
                verify_conn.close()
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


class TestZeroDDLInHotPaths:
    """Verify ServiceClient and notification connections execute zero DDL in hot paths."""

    def test_get_operations_snapshot_zero_ddl(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Covers UI-002 & PERF-001: get_operations_snapshot executes zero DDL statements."""
        import content_creation.platform.storage.database as db_mod
        from content_creation.ui.services.client import ServiceClient, get_context, get_notification_db

        get_context.clear()
        get_notification_db.clear()
        monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)

        cf_db = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(cf_db)

        executed_statements: list[str] = []

        def trace_sql(statement: str) -> None:
            clean = statement.strip()
            if clean:
                executed_statements.append(clean)

        orig_create_conn = db_mod.create_connection

        def traced_create_connection(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            conn = orig_create_conn(*args, **kwargs)
            conn.set_trace_callback(trace_sql)
            return conn

        monkeypatch.setattr(db_mod, "create_connection", traced_create_connection)

        client = ServiceClient()
        snapshot = client.get_operations_snapshot()
        assert snapshot is not None

        ddl_statements = [
            stmt for stmt in executed_statements
            if any(stmt.upper().startswith(kw) for kw in ("CREATE", "DROP", "ALTER"))
        ]
        assert not ddl_statements, f"Found unexpected DDL statements in get_operations_snapshot: {ddl_statements}"
        assert len(executed_statements) > 0, "Expected non-DDL queries to be traced during snapshot"

    def test_get_notification_db_zero_ddl_when_db_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Covers UI-002 & PERF-001: get_notification_db executes zero DDL when content_factory.db exists."""
        import content_creation.platform.storage.database as db_mod
        from content_creation.ui.services.client import get_notification_db

        get_notification_db.clear()
        monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)

        cf_db = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(cf_db)

        executed_statements: list[str] = []

        def trace_sql(statement: str) -> None:
            clean = statement.strip()
            if clean:
                executed_statements.append(clean)

        orig_create_conn = db_mod.create_connection

        def traced_create_connection(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            conn = orig_create_conn(*args, **kwargs)
            conn.set_trace_callback(trace_sql)
            return conn

        monkeypatch.setattr(db_mod, "create_connection", traced_create_connection)

        notif_conn = get_notification_db()
        try:
            ddl_statements = [
                stmt for stmt in executed_statements
                if any(stmt.upper().startswith(kw) for kw in ("CREATE", "DROP", "ALTER"))
            ]
            assert not ddl_statements, f"Found unexpected DDL in get_notification_db: {ddl_statements}"
        finally:
            notif_conn.close()
            get_notification_db.clear()


class TestMultiSubsystemIntegrityConstraints:
    """Verify relational integrity, primary keys, and mandatory fields in unified database."""

    def test_primary_key_uniqueness_enforced_across_tables(self, tmp_path: Path) -> None:
        """Covers ARCH-001: Primary key duplicates raise IntegrityError across all tables."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = create_connection(db_file)
        try:
            # 1. jobs duplicate PK
            conn.execute(
                "INSERT INTO jobs (job_id, job_type, status, action_id, operator_id, target_type, target_id, payload_json, created_at, correlation_id) "
                "VALUES ('dup-job', 't', 'QUEUED', 'a', 'op', 'top', '1', '{}', ?, 'c');",
                (now_iso,),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO jobs (job_id, job_type, status, action_id, operator_id, target_type, target_id, payload_json, created_at, correlation_id) "
                    "VALUES ('dup-job', 't', 'QUEUED', 'a', 'op', 'top', '1', '{}', ?, 'c');",
                    (now_iso,),
                )

            # 2. events duplicate PK
            conn.execute(
                "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                "VALUES ('dup-evt', 'e', 'cat', 'src', 'c', ?);",
                (now_iso,),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                    "VALUES ('dup-evt', 'e', 'cat', 'src', 'c', ?);",
                    (now_iso,),
                )

            # 3. notifications duplicate PK
            conn.execute(
                "INSERT INTO notifications (notification_id, title, message, severity, category, status, timestamp, correlation_id) "
                "VALUES ('dup-notif', 't', 'm', 'INFO', 'c', 'UNREAD', ?, 'c');",
                (now_iso,),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO notifications (notification_id, title, message, severity, category, status, timestamp, correlation_id) "
                    "VALUES ('dup-notif', 't', 'm', 'INFO', 'c', 'UNREAD', ?, 'c');",
                    (now_iso,),
                )
        finally:
            conn.close()

    def test_not_null_constraints_enforced(self, tmp_path: Path) -> None:
        """Covers ARCH-001: Mandatory NOT NULL fields are strictly enforced."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = create_connection(db_file)
        try:
            # locks: last_heartbeat is NOT NULL
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO locks (lock_id, lock_type, resource_id, owner_job_id, status, acquired_at, last_heartbeat) "
                    "VALUES ('l-bad', 'res', 'r-1', 'j-1', 'ACQUIRED', ?, NULL);",
                    (now_iso,),
                )

            # notifications: correlation_id is NOT NULL
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO notifications (notification_id, title, message, severity, category, status, timestamp, correlation_id) "
                    "VALUES ('n-bad', 't', 'm', 'INFO', 'cat', 'UNREAD', ?, NULL);",
                    (now_iso,),
                )
        finally:
            conn.close()

