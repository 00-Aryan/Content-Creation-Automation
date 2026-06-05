# Architecture Reference: SQLite Connection Lifecycle Hardening (Phase 11.9.3)

This document details the hardening of SQLite connection lifecycles across the `content_creation` pipeline and test suites. The goal of this change was to guarantee deterministic connection closure and completely eliminate all `ResourceWarning: unclosed database` warnings without altering business behavior or database schemas.

---

## 1. Files Modified

The following files were modified to achieve strict SQLite resource cleanup:

### Core Repositories
* [`src/content_creation/audit/sqlite_repository.py`](file:///home/aryan/May-2026/Content-Creation/src/content_creation/audit/sqlite_repository.py)
* [`src/content_creation/events/store/sqlite_repository.py`](file:///home/aryan/May-2026/Content-Creation/src/content_creation/events/store/sqlite_repository.py)
* [`src/content_creation/metrics/sqlite_repository.py`](file:///home/aryan/May-2026/Content-Creation/src/content_creation/metrics/sqlite_repository.py)

### Operations Dashboard
* [`src/content_creation/ui/pages/6_operations_dashboard.py`](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/pages/6_operations_dashboard.py)

### Test Suites
* [`tests/jobs/test_claiming.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_claiming.py)
* [`tests/jobs/test_events_system.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_events_system.py)
* [`tests/jobs/test_heartbeat.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_heartbeat.py)
* [`tests/jobs/test_lock_contention.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_lock_contention.py)
* [`tests/jobs/test_lock_manager.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_lock_manager.py)
* [`tests/jobs/test_lock_recovery.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_lock_recovery.py)
* [`tests/jobs/test_lock_repository.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_lock_repository.py)
* [`tests/jobs/test_queue_claiming.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_queue_claiming.py)
* [`tests/jobs/test_queue_consistency.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_queue_consistency.py)
* [`tests/jobs/test_queue_engine.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_queue_engine.py)
* [`tests/jobs/test_queue_metrics.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_queue_metrics.py)
* [`tests/jobs/test_queue_retry.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_queue_retry.py)
* [`tests/jobs/test_recovery_locks.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_recovery_locks.py)
* [`tests/jobs/test_recovery_startup.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_recovery_startup.py)
* [`tests/jobs/test_recovery_supervisor.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_recovery_supervisor.py)
* [`tests/jobs/test_sqlite_repository.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_sqlite_repository.py)
* [`tests/jobs/test_worker_daemon.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_worker_daemon.py)
* [`tests/jobs/test_worker_locking.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_worker_locking.py)
* [`tests/jobs/test_worker_retry_flow.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_worker_retry_flow.py)
* [`tests/jobs/test_worker_shutdown.py`](file:///home/aryan/May-2026/Content-Creation/tests/jobs/test_worker_shutdown.py)
* [`tests/test_audit.py`](file:///home/aryan/May-2026/Content-Creation/tests/test_audit.py)
* [`tests/test_event_persistence.py`](file:///home/aryan/May-2026/Content-Creation/tests/test_event_persistence.py)
* [`tests/test_metrics.py`](file:///home/aryan/May-2026/Content-Creation/tests/test_metrics.py)
* [`tests/test_notification_service.py`](file:///home/aryan/May-2026/Content-Creation/tests/test_notification_service.py)
* [`tests/test_notification_streaming.py`](file:///home/aryan/May-2026/Content-Creation/tests/test_notification_streaming.py)
* [`tests/test_notification_subscribers.py`](file:///home/aryan/May-2026/Content-Creation/tests/test_notification_subscribers.py)

---

## 2. Root Causes of Connection Leaks

The database connection leaks originated from three primary patterns:

1. **Thread-Local Connections in Repositories (`threading.local`)**:
   * *Issue*: `SQLiteAuditRepository`, `SQLiteEventRepository`, and `SQLiteMetricRepository` leverage thread-local caching to manage multi-threaded SQLite connections safely. However, calling `.close()` on the main thread only cleared the connection object for the main thread. Connections opened by other concurrent worker threads remained cached in their respective thread-local scopes. When the threads or repositories were finalized, the garbage collector released them implicitly, generating `ResourceWarning: unclosed database`.
   * *Resolution*: Equipped each repository with a thread-safe connection registry (`self._all_conns` + `self._lock`). Any connection created in `_get_conn` is registered. The public `.close()` method now clears the thread-local state and iterates over all registered connection instances, closing them explicitly.

2. **Operations Dashboard Temporary Connections**:
   * *Issue*: The streamlit page `6_operations_dashboard.py` opened multiple sqlite3 connections directly on physical SQLite files to initialize schemas and read snapshots (`job_conn`, `lock_conn`, `event_conn`, `notif_conn`, `metrics_conn`, `audit_conn`). If an exception was raised, or after a successful render, these connections were left open.
   * *Resolution*: Wrapped all connection creation and repository initialization inside a `try...finally` block. The `finally` block explicitly closes all temporary connection handles and calls `.close()` on the instantiated repositories.

3. **Leaked Pytest Fixtures and Direct Connections**:
   * *Issue*: Numerous pytest fixtures (such as `db_conn` and `repo`) instantiated sqlite3 connections and returned them directly. Pytest did not close them, leaving them to be GC'd at interpreter exit. Furthermore, tests that created `SQLiteEventRepository` or `SQLiteAuditRepository` directly in the test body (for thread-safety or concurrency checks) never called `.close()` on the repositories, leaving internal connections open.
   * *Resolution*: 
     * Refactored connection-yielding fixtures to use `yield` instead of `return`, followed by an explicit `conn.close()` or `repo.close()` teardown action.
     * Wrapped test body code using direct connection instantiations inside `try...finally` blocks to guarantee that `.close()` is called regardless of assertion success or failure.

---

## 3. Fixes Applied

### Repository Connection Tracking Pattern
Implemented connection tracing registry in all thread-local database repositories:
```python
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._all_conns = []
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=10.0,
            )
            self._local.conn = conn
            with self._lock:
                self._all_conns.append(conn)
        return self._local.conn

    def close(self) -> None:
        """Close all database connections created by this repository."""
        with self._lock:
            conns = list(self._all_conns)
            self._all_conns.clear()
        for conn in conns:
            try:
                conn.close()
            except Exception:
                pass
        if hasattr(self._local, "conn"):
            self._local.conn = None
```

### Pytest Fixture Teardown Pattern
Refactored pytest fixtures to guarantee resource cleanup post-execution:
```python
@pytest.fixture
def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()
```

---

## 4. ResourceWarning Verification

### Baseline Execution (Before Changes)
* **Total Warnings**: 342 warnings.
* **Database Resource Warnings**: Highly prevalent. Running tests with `-W error::ResourceWarning` resulted in test runner termination during teardown and final garbage collection phases due to unclosed database connections.

### Verification Execution (After Changes)
* **Total Warnings**: 2 warnings.
* **Database Resource Warnings**: **0 warnings** (completely eliminated).
* **Remaining Warnings**:
  * 1 x `DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17` from the external `google.genai` SDK.
  * 1 x `ResourceWarning: unclosed file <_io.TextIOWrapper name='/tmp/pytest-of-aryan/...'` relating to temporary filesystem cleanups by pytest.

---

## 5. Final Test Count

All tests passed successfully post-cleanup:
* **Final Test Count**: 958 tests passed.
* **Status**: 100% successful execution, completely clean SQLite connection lifecycles.
