"""Domain tests for SQLite WAL-mode concurrency, busy timeout, and multi-subsystem transactions.

Covers:
- ARCH-001: Consolidated WAL-mode content_factory.db persistence architecture
- RISK-001: Multi-reader / single-writer non-blocking concurrency under simulated contention
- PERF-001: Elimination of locking bottlenecks and verified busy timeout backoff
"""

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from content_creation.platform.storage.database import (
    create_connection,
    init_content_factory_db,
)


class TestWALConcurrencyAndReaders:
    """Verify WAL mode allows concurrent reader connections while writer commits."""

    def test_wal_concurrent_readers_while_writer_active(self, tmp_path: Path) -> None:
        """Covers ARCH-001 & RISK-001: Readers read unhindered while writer transaction is open."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        writer_conn = create_connection(db_file)
        reader_conn1 = create_connection(db_file)
        reader_conn2 = create_connection(db_file)

        try:
            # Seed initial event
            now_iso = datetime.now(timezone.utc).isoformat()
            writer_conn.execute(
                "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (str(uuid4()), "initial_event", "test", "seed", "c-0", now_iso),
            )
            writer_conn.commit()

            # Verify initial count seen by readers
            assert reader_conn1.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 1
            assert reader_conn2.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 1

            # Writer opens transaction and inserts 5 events without committing
            writer_conn.execute("BEGIN IMMEDIATE;")
            for i in range(5):
                writer_conn.execute(
                    "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    (str(uuid4()), f"staged_event_{i}", "test", "writer", f"c-{i+1}", now_iso),
                )

            # Concurrent readers query simultaneously while writer transaction is uncommitted
            # In WAL mode, snapshot isolation ensures readers see committed state (1) without blocking
            assert reader_conn1.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 1
            assert reader_conn2.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 1

            # Writer commits
            writer_conn.commit()

            # Now readers immediately see all 6 events without lock errors
            assert reader_conn1.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 6
            assert reader_conn2.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 6
        finally:
            writer_conn.close()
            reader_conn1.close()
            reader_conn2.close()

    def test_wal_multi_threaded_readers_and_writer(self, tmp_path: Path) -> None:
        """Covers ARCH-001 & PERF-001: Multi-threaded readers and active writer execute concurrently."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        reader_exceptions: list[Exception] = []
        stop_readers = threading.Event()
        total_writes = 40

        def reader_worker(reader_id: int) -> None:
            conn = create_connection(db_file)
            try:
                while not stop_readers.is_set():
                    # Readers repeatedly query counts and aggregates
                    row = conn.execute("SELECT COUNT(*), MAX(value) FROM metrics;").fetchone()
                    assert row is not None
                    time.sleep(0.005)
            except Exception as exc:
                reader_exceptions.append(exc)
            finally:
                conn.close()

        # Start 4 concurrent reader threads
        threads = [
            threading.Thread(target=reader_worker, args=(i,), daemon=True)
            for i in range(4)
        ]
        for t in threads:
            t.start()

        # Main thread acts as writer
        writer_conn = create_connection(db_file)
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            for i in range(total_writes):
                writer_conn.execute(
                    "INSERT INTO metrics (id, metric_name, metric_type, value, created_at) "
                    "VALUES (?, ?, ?, ?, ?);",
                    (str(uuid4()), "pipeline_throughput", "gauge", float(i), now_iso),
                )
                writer_conn.commit()
                time.sleep(0.005)
        finally:
            writer_conn.close()
            stop_readers.set()
            for t in threads:
                t.join(timeout=3.0)

        assert not reader_exceptions, f"Readers encountered exceptions: {reader_exceptions}"

        # Final verification: exactly 40 metrics exist in database
        check_conn = create_connection(db_file)
        try:
            count = check_conn.execute("SELECT COUNT(*) FROM metrics;").fetchone()[0]
            assert count == total_writes
        finally:
            check_conn.close()


class TestBusyTimeoutContention:
    """Verify SQLite busy timeout behavior under simulated write lock contention."""

    def test_busy_timeout_waits_and_succeeds_under_contention(self, tmp_path: Path) -> None:
        """Covers ARCH-001 & windows-python-hygiene Rule 5: 5000ms busy_timeout waits for lock release."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn1 = create_connection(db_file)
        conn2 = create_connection(db_file)

        # Confirm busy_timeout is set to 5000ms
        timeout_val = conn2.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert int(timeout_val) == 5000

        # Conn 1 acquires exclusive lock
        conn1.execute("BEGIN EXCLUSIVE;")

        def release_lock_later() -> None:
            time.sleep(0.25)
            conn1.commit()
            conn1.close()

        release_thread = threading.Thread(target=release_lock_later, daemon=True)
        release_thread.start()

        t0 = time.time()
        # Conn 2 attempts to acquire lock; with 5000ms busy_timeout it should block,
        # wait ~0.25s for Conn 1 to release, and then succeed
        conn2.execute("BEGIN IMMEDIATE;")
        elapsed = time.time() - t0

        try:
            assert elapsed >= 0.20, f"Expected backoff wait, but took only {elapsed:.3f}s"
            assert elapsed < 4.0, f"Wait exceeded expected release window: {elapsed:.3f}s"

            now_iso = datetime.now(timezone.utc).isoformat()
            conn2.execute(
                "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (str(uuid4()), "contention_resolved", "test", "conn2", "c-busy", now_iso),
            )
            conn2.commit()
        finally:
            conn2.close()
            release_thread.join(timeout=2.0)

        # Verify event was written
        verify_conn = create_connection(db_file)
        try:
            assert verify_conn.execute("SELECT COUNT(*) FROM events;").fetchone()[0] == 1
        finally:
            verify_conn.close()

    def test_busy_timeout_exceeded_raises_operational_error(self, tmp_path: Path) -> None:
        """Covers ARCH-001: OperationalError: database is locked when contention exceeds timeout."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn1 = create_connection(db_file)
        conn2 = create_connection(db_file)

        # Lower busy_timeout on conn2 to 150ms to test timeout exhaustion
        conn2.execute("PRAGMA busy_timeout=150;")

        conn1.execute("BEGIN EXCLUSIVE;")
        try:
            t0 = time.time()
            with pytest.raises(sqlite3.OperationalError) as exc_info:
                conn2.execute("BEGIN IMMEDIATE;")
            elapsed = time.time() - t0

            assert "database is locked" in str(exc_info.value).lower()
            assert elapsed >= 0.10, f"Timeout triggered too fast: {elapsed:.3f}s"
        finally:
            conn1.commit()
            conn1.close()
            conn2.close()


class TestMultiSubsystemAtomicTransaction:
    """Verify all 6 subsystem tables participate cleanly in atomic workflows."""

    def test_multi_subsystem_atomic_workflow_transaction(self, tmp_path: Path) -> None:
        """Covers ARCH-001 & RISK-001: Atomic multi-table workflow across all 6 tables."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn = create_connection(db_file)
        try:
            job_id = str(uuid4())
            lock_id = str(uuid4())
            event_id = str(uuid4())
            notif_id = str(uuid4())
            metric_id = str(uuid4())
            audit_id = str(uuid4())
            corr_id = f"corr-{uuid4()}"
            now_iso = datetime.now(timezone.utc).isoformat()

            conn.execute("BEGIN TRANSACTION;")

            # 1. jobs
            conn.execute(
                """
                INSERT INTO jobs (job_id, job_type, status, priority, action_id, operator_id,
                                  target_type, target_id, payload_json, created_at, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (job_id, "video_synthesis", "COMPLETED", 50, "synthesize", "worker-1",
                 "topic", "top-123", "{\"res\": \"1080p\"}", now_iso, corr_id),
            )

            # 2. locks
            conn.execute(
                """
                INSERT INTO locks (lock_id, lock_type, resource_id, owner_job_id, status,
                                  acquired_at, last_heartbeat, released_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (lock_id, "topic_lock", "top-123", job_id, "RELEASED", now_iso, now_iso, now_iso),
            )

            # 3. events
            conn.execute(
                """
                INSERT INTO events (id, event_name, category, source, correlation_id,
                                    entity_type, entity_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (event_id, "topic_synthesized", "workflow", "worker-1", corr_id,
                 "topic", "top-123", "{\"duration_sec\": 45}", now_iso),
            )

            # 4. notifications
            conn.execute(
                """
                INSERT INTO notifications (notification_id, title, message, severity, category,
                                          status, timestamp, correlation_id, event_id, entity_type, entity_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (notif_id, "Synthesis Complete", "Video generated for top-123", "INFO",
                 "pipeline", "UNREAD", now_iso, corr_id, event_id, "topic", "top-123"),
            )

            # 5. metrics
            conn.execute(
                """
                INSERT INTO metrics (id, metric_name, metric_type, value, created_at,
                                     entity_type, entity_id, dimensions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (metric_id, "synthesis_duration_seconds", "gauge", 45.2, now_iso,
                 "topic", "top-123", "{\"channel\": \"youtube_shorts\"}"),
            )

            # 6. audit
            conn.execute(
                """
                INSERT INTO audit (id, timestamp, actor_type, actor_id, action_type,
                                   entity_type, entity_id, event_type, correlation_id,
                                   previous_state, new_state, metadata_json, source, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (audit_id, now_iso, "system", "worker-1", "complete_synthesis",
                 "topic", "top-123", "topic_synthesized", corr_id,
                 "PROCESSING", "COMPLETED", "{\"engine\": \"ffmpeg\"}", "workflow", "INFO"),
            )

            conn.commit()
        finally:
            conn.close()

        # Open separate connection and verify all 6 tables populated with matching correlation_id
        verify_conn = create_connection(db_file)
        try:
            for table_name in ("jobs", "events", "notifications", "audit"):
                row = verify_conn.execute(
                    f"SELECT correlation_id FROM {table_name} WHERE correlation_id = ?;",
                    (corr_id,),
                ).fetchone()
                assert row is not None, f"Expected row in {table_name} for correlation_id {corr_id}"

            # Check locks and metrics
            lock_row = verify_conn.execute("SELECT owner_job_id FROM locks WHERE lock_id = ?;", (lock_id,)).fetchone()
            assert lock_row is not None
            assert lock_row["owner_job_id"] == job_id

            metric_row = verify_conn.execute("SELECT value FROM metrics WHERE id = ?;", (metric_id,)).fetchone()
            assert metric_row is not None
            assert metric_row["value"] == 45.2
        finally:
            verify_conn.close()


class TestWALCheckpointAndCrashRecovery:
    """Verify WAL file checkpointing and automatic replay on connection re-opening."""

    def test_wal_checkpoint_truncate_and_passive(self, tmp_path: Path) -> None:
        """Covers ARCH-001 & windows-python-hygiene Rule 5: Checkpointing flushes WAL cleanly."""
        db_file = tmp_path / "data" / "content_factory.db"
        init_content_factory_db(db_file)

        conn = create_connection(db_file)
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            for i in range(20):
                conn.execute(
                    "INSERT INTO events (id, event_name, category, source, correlation_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    (str(uuid4()), f"chk_event_{i}", "test", "chk", f"c-{i}", now_iso),
                )
            conn.commit()

            # Execute PASSIVE checkpoint: should return (0, log_size, checkpointed_count)
            # busy flag (first column) must be 0 (no lock contention preventing checkpoint)
            res_passive = conn.execute("PRAGMA wal_checkpoint(PASSIVE);").fetchone()
            assert res_passive[0] == 0, f"Expected busy=0 in passive checkpoint, got {res_passive}"

            # Execute TRUNCATE checkpoint: truncates WAL file to 0 bytes
            res_truncate = conn.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchone()
            assert res_truncate[0] == 0, f"Expected busy=0 in truncate checkpoint, got {res_truncate}"
        finally:
            conn.close()

        # Reopen connection, verify all 20 rows preserved
        new_conn = create_connection(db_file)
        try:
            count = new_conn.execute("SELECT COUNT(*) FROM events;").fetchone()[0]
            assert count == 20
        finally:
            new_conn.close()
