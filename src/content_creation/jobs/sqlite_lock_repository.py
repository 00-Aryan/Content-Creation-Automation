"""SQLite implementation of the LockRepository interface."""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import UUID

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.lock_repository import LockRepository


class SQLiteLockRepository(LockRepository):
    """SQLite repository for managing cooperative resource locks."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _to_model(self, row: tuple) -> ResourceLock:
        """Map a database row to a ResourceLock domain model."""
        (
            lock_id,
            lock_type,
            resource_id,
            owner_job_id,
            status,
            acquired_at,
            last_heartbeat,
            released_at,
            metadata_json,
        ) = row

        metadata = json.loads(metadata_json) if metadata_json else {}

        def parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                return datetime.fromisoformat(dt_str)
            except ValueError:
                return None

        return ResourceLock(
            lock_id=UUID(lock_id),
            lock_type=LockType(lock_type),
            resource_id=resource_id,
            owner_job_id=UUID(owner_job_id),
            status=LockStatus(status),
            acquired_at=datetime.fromisoformat(acquired_at),
            last_heartbeat=datetime.fromisoformat(last_heartbeat),
            released_at=parse_dt(released_at),
            metadata=metadata,
        )

    def _to_row(self, lock: ResourceLock) -> tuple:
        """Map a ResourceLock domain model to a database row tuple."""
        def format_dt(dt: Optional[datetime]) -> Optional[str]:
            if not dt:
                return None
            return dt.isoformat()

        return (
            str(lock.lock_id),
            lock.lock_type.value,
            lock.resource_id,
            str(lock.owner_job_id),
            lock.status.value,
            format_dt(lock.acquired_at),
            format_dt(lock.last_heartbeat),
            format_dt(lock.released_at),
            json.dumps(lock.metadata),
        )

    def acquire_lock(self, lock: ResourceLock) -> ResourceLock:
        """Atomically acquire an active resource lock using BEGIN IMMEDIATE transaction isolation."""
        try:
            self.conn.execute("BEGIN IMMEDIATE;")
            cursor = self.conn.cursor()

            # 1. Double check if lock already active (database index provides constraint, but we check here too)
            cursor.execute(
                """
                SELECT COUNT(*) FROM locks
                WHERE lock_type = ? AND resource_id = ? AND status = 'ACTIVE'
                """,
                (lock.lock_type.value, lock.resource_id),
            )
            active_count = cursor.fetchone()[0]
            if active_count > 0:
                self.conn.rollback()
                raise ValueError(
                    f"Lock target collision: Resource {lock.resource_id} is already locked by type {lock.lock_type}."
                )

            # 2. Insert active lock
            row = self._to_row(lock)
            cursor.execute(
                """
                INSERT INTO locks (
                    lock_id, lock_type, resource_id, owner_job_id, status,
                    acquired_at, last_heartbeat, released_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            self.conn.commit()
            return lock

        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise ValueError(f"Concurrency lock failure: Resource is already locked (IntegrityError): {e}")
        except Exception:
            self.conn.rollback()
            raise

    def release_lock(self, lock_id: UUID) -> ResourceLock:
        try:
            self.conn.execute("BEGIN IMMEDIATE;")
            cursor = self.conn.cursor()

            cursor.execute("SELECT * FROM locks WHERE lock_id = ?", (str(lock_id),))
            row = cursor.fetchone()
            if not row:
                self.conn.rollback()
                raise ValueError(f"Lock {lock_id} does not exist.")

            lock = self._to_model(row)
            if not lock.is_active():
                self.conn.rollback()
                raise ValueError(f"Lock {lock_id} is not in ACTIVE state.")

            now_str = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                UPDATE locks
                SET status = ?, released_at = ?
                WHERE lock_id = ?
                """,
                (LockStatus.RELEASED.value, now_str, str(lock_id)),
            )
            self.conn.commit()

            cursor.execute("SELECT * FROM locks WHERE lock_id = ?", (str(lock_id),))
            return self._to_model(cursor.fetchone())

        except Exception:
            self.conn.rollback()
            raise

    def get_lock(self, lock_id: UUID) -> Optional[ResourceLock]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM locks WHERE lock_id = ?", (str(lock_id),))
        row = cursor.fetchone()
        if not row:
            return None
        return self._to_model(row)

    def get_lock_owner(self, lock_type: LockType, resource_id: str) -> Optional[UUID]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT owner_job_id FROM locks
            WHERE lock_type = ? AND resource_id = ? AND status = 'ACTIVE'
            """,
            (lock_type.value, resource_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return UUID(row[0])

    def is_locked(self, lock_type: LockType, resource_id: str) -> bool:
        return self.get_lock_owner(lock_type, resource_id) is not None

    def list_active_locks(self) -> List[ResourceLock]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM locks WHERE status = 'ACTIVE'")
        rows = cursor.fetchall()
        return [self._to_model(row) for row in rows]

    def release_stale_locks(self, timeout_seconds: int) -> Dict[str, Any]:
        """Audit ACTIVE locks and expire them if heartbeats are stale."""
        try:
            self.conn.execute("BEGIN IMMEDIATE;")
            cursor = self.conn.cursor()

            now = datetime.now(timezone.utc)
            cursor.execute("SELECT * FROM locks WHERE status = 'ACTIVE'")
            active_rows = cursor.fetchall()

            expired_count = 0
            released_resources = []

            for row in active_rows:
                lock = self._to_model(row)
                diff = (now - lock.last_heartbeat).total_seconds()
                if diff > timeout_seconds:
                    # Stale lock identified -> Expire it
                    now_str = now.isoformat()
                    cursor.execute(
                        """
                        UPDATE locks
                        SET status = ?, released_at = ?
                        WHERE lock_id = ?
                        """,
                        (LockStatus.EXPIRED.value, now_str, str(lock.lock_id)),
                    )
                    expired_count += 1
                    released_resources.append(f"{lock.lock_type.value}:{lock.resource_id}")

            self.conn.commit()
            return {
                "expired_count": expired_count,
                "released_resources": released_resources,
            }

        except Exception:
            self.conn.rollback()
            raise

    def heartbeat(self, lock_id: UUID) -> None:
        cursor = self.conn.cursor()
        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE locks
            SET last_heartbeat = ?
            WHERE lock_id = ? AND status = 'ACTIVE'
            """,
            (now_str, str(lock_id)),
        )
        self.conn.commit()

    def delete_lock(self, lock_id: UUID) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM locks WHERE lock_id = ?", (str(lock_id),))
        self.conn.commit()
        return cursor.rowcount > 0
