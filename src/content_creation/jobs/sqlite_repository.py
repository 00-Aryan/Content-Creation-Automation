"""SQLite implementation of the JobRepository interface."""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import UUID

from content_creation.jobs.models import Job, JobResult, JobStatus
from content_creation.jobs.repository import JobRepository


class SQLiteJobRepository(JobRepository):
    """SQLite job repository handling persistence and concurrency safety."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _to_model(self, row: tuple) -> Job:
        """Map a database row to a Job domain model."""
        (
            job_id,
            job_type,
            status,
            priority,
            action_id,
            operator_id,
            target_type,
            target_id,
            payload_json,
            result_json,
            retry_count,
            max_retries,
            created_at,
            queued_at,
            started_at,
            completed_at,
            run_after,
            last_heartbeat,
            correlation_id,
            error_message,
        ) = row

        payload = json.loads(payload_json)
        result = None
        if result_json:
            res_dict = json.loads(result_json)
            result = JobResult(
                duration_seconds=res_dict["duration_seconds"],
                warnings=res_dict.get("warnings", []),
                emitted_events=res_dict.get("emitted_events", []),
                generated_files=res_dict.get("generated_files", {}),
                metadata=res_dict.get("metadata", {}),
            )

        def parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                # SQLite dates are stored as ISO strings
                return datetime.fromisoformat(dt_str)
            except ValueError:
                return None

        # Reconstruct Job object using correct type coercions
        return Job(
            job_id=UUID(job_id),
            job_type=job_type,
            status=JobStatus(status),
            priority=priority,
            operator_id=operator_id,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
            correlation_id=correlation_id,
            created_at=datetime.fromisoformat(created_at),
            queued_at=parse_dt(queued_at),
            started_at=parse_dt(started_at),
            completed_at=parse_dt(completed_at),
            result=result,
            error_message=error_message,
            retry_count=retry_count,
            max_retries=max_retries,
            run_after=parse_dt(run_after),
            last_heartbeat=parse_dt(last_heartbeat),
        )

    def _to_row(self, job: Job) -> tuple:
        """Map a Job domain model to a database row tuple."""
        result_json = None
        if job.result:
            result_json = json.dumps(
                {
                    "duration_seconds": job.result.duration_seconds,
                    "warnings": job.result.warnings,
                    "emitted_events": job.result.emitted_events,
                    "generated_files": job.result.generated_files,
                    "metadata": job.result.metadata,
                }
            )

        def format_dt(dt: Optional[datetime]) -> Optional[str]:
            if not dt:
                return None
            # Standardize on naive UTC ISO-8601 string or offset-aware representation
            return dt.isoformat()

        # Extract action_id from payload (if provided, default to job_type lower case)
        action_id = job.payload.get("action_id", job.job_type.lower())

        return (
            str(job.job_id),
            job.job_type,
            job.status.value,
            job.priority,
            action_id,
            job.operator_id,
            job.target_type,
            job.target_id,
            json.dumps(job.payload),
            result_json,
            job.retry_count,
            job.max_retries,
            format_dt(job.created_at),
            format_dt(job.queued_at),
            format_dt(job.started_at),
            format_dt(job.completed_at),
            format_dt(job.run_after),
            format_dt(job.last_heartbeat),
            job.correlation_id,
            job.error_message,
        )

    def create_job(self, job: Job) -> Job:
        cursor = self.conn.cursor()
        row = self._to_row(job)
        try:
            cursor.execute(
                """
                INSERT INTO jobs (
                    job_id, job_type, status, priority, action_id, operator_id,
                    target_type, target_id, payload_json, result_json,
                    retry_count, max_retries, created_at, queued_at,
                    started_at, completed_at, run_after, last_heartbeat,
                    correlation_id, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            self.conn.commit()
            return job
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise ValueError(f"Job with ID {job.job_id} already exists or integrity violated: {e}")

    def get_job(self, job_id: UUID) -> Optional[Job]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
        row = cursor.fetchone()
        if not row:
            return None
        return self._to_model(row)

    def update_job(self, job: Job) -> Job:
        cursor = self.conn.cursor()
        # Verify job exists and check terminal immutability
        cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (str(job.job_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Job with ID {job.job_id} does not exist.")

        db_status = JobStatus(row[0])
        if db_status.is_terminal():
            raise ValueError("State invariant violation: terminal jobs cannot be modified.")

        # Serialize updated fields
        row_data = self._to_row(job)
        # We replace all fields except job_id (which is in row_data[0] and used in WHERE)
        cursor.execute(
            """
            UPDATE jobs
            SET job_type = ?, status = ?, priority = ?, action_id = ?, operator_id = ?,
                target_type = ?, target_id = ?, payload_json = ?, result_json = ?,
                retry_count = ?, max_retries = ?, created_at = ?, queued_at = ?,
                started_at = ?, completed_at = ?, run_after = ?, last_heartbeat = ?,
                correlation_id = ?, error_message = ?
            WHERE job_id = ?
            """,
            row_data[1:] + (row_data[0],),
        )
        self.conn.commit()
        return job

    def delete_job(self, job_id: UUID) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE job_id = ?", (str(job_id),))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        correlation_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> List[Job]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if correlation_id:
            query += " AND correlation_id = ?"
            params.append(correlation_id)
        if target_type:
            query += " AND target_type = ?"
            params.append(target_type)
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [self._to_model(row) for row in rows]

    def enqueue_job(self, job_id: UUID) -> Job:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (str(job_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        db_status = JobStatus(row[0])
        if db_status.is_terminal():
            raise ValueError("Terminal jobs cannot be enqueued.")

        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, queued_at = ?, run_after = NULL
            WHERE job_id = ?
            """,
            (JobStatus.QUEUED.value, now_str, str(job_id)),
        )
        self.conn.commit()

        # Return refreshed job
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
        return self._to_model(cursor.fetchone())

    def claim_next_job(self, worker_id: str) -> Optional[Job]:
        """Claim the next eligible QUEUED/RETRYING job using BEGIN IMMEDIATE transaction lock."""
        # Start immediate transaction to prevent concurrency collision
        try:
            self.conn.execute("BEGIN IMMEDIATE;")
            cursor = self.conn.cursor()

            # Find candidates that are QUEUED or RETRYING and expired backoff
            now_str = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE status IN ('QUEUED', 'RETRYING')
                  AND (run_after IS NULL OR run_after <= ?)
                ORDER BY priority ASC, created_at ASC
                """,
                (now_str,),
            )
            candidates = cursor.fetchall()

            claimed_job = None
            for row in candidates:
                candidate = self._to_model(row)

                # Check active target lock: is another job for this target currently RUNNING?
                if candidate.target_type != "all" and candidate.target_id != "all":
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM jobs
                        WHERE target_type = ? AND target_id = ? AND status = 'RUNNING'
                        """,
                        (candidate.target_type, candidate.target_id),
                    )
                    active_lock_count = cursor.fetchone()[0]
                    if active_lock_count > 0:
                        # Target resource is busy; skip this candidate
                        continue

                # Lock acquired! Update job to RUNNING
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = ?, started_at = ?, last_heartbeat = ?
                    WHERE job_id = ?
                    """,
                    (
                        JobStatus.RUNNING.value,
                        now_str,
                        now_str,
                        str(candidate.job_id),
                    ),
                )
                self.conn.commit()

                # Refresh and load the claimed job model
                cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(candidate.job_id),))
                claimed_job = self._to_model(cursor.fetchone())
                break

            if not claimed_job:
                # No job was claimed; end transaction cleanly
                self.conn.rollback()

            return claimed_job

        except Exception:
            self.conn.rollback()
            raise

    def heartbeat(self, job_id: UUID) -> None:
        cursor = self.conn.cursor()
        now_str = datetime.now(timezone.utc).isoformat()
        # Updates heartbeat_at only if currently RUNNING
        cursor.execute(
            """
            UPDATE jobs
            SET last_heartbeat = ?
            WHERE job_id = ? AND status = 'RUNNING'
            """,
            (now_str, str(job_id)),
        )
        self.conn.commit()

    def complete_job(self, job_id: UUID, result: JobResult) -> Job:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (str(job_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        db_status = JobStatus(row[0])
        if db_status.is_terminal():
            raise ValueError("State invariant violation: terminal jobs cannot be completed.")

        now_str = datetime.now(timezone.utc).isoformat()
        result_json = json.dumps(
            {
                "duration_seconds": result.duration_seconds,
                "warnings": result.warnings,
                "emitted_events": result.emitted_events,
                "generated_files": result.generated_files,
                "metadata": result.metadata,
            }
        )

        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, completed_at = ?, result_json = ?
            WHERE job_id = ?
            """,
            (JobStatus.COMPLETED.value, now_str, result_json, str(job_id)),
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
        return self._to_model(cursor.fetchone())

    def fail_job(self, job_id: UUID, error_message: str) -> Job:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (str(job_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        db_status = JobStatus(row[0])
        if db_status.is_terminal():
            raise ValueError("State invariant violation: terminal jobs cannot be marked failed.")

        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, completed_at = ?, error_message = ?
            WHERE job_id = ?
            """,
            (JobStatus.FAILED.value, now_str, error_message, str(job_id)),
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
        return self._to_model(cursor.fetchone())

    def cancel_job(self, job_id: UUID) -> Job:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (str(job_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        db_status = JobStatus(row[0])
        if db_status.is_terminal():
            raise ValueError("Terminal jobs cannot be cancelled.")

        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, completed_at = ?
            WHERE job_id = ?
            """,
            (JobStatus.CANCELLED.value, now_str, str(job_id)),
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
        return self._to_model(cursor.fetchone())

    def schedule_retry(self, job_id: UUID, backoff_seconds: float, error_message: str) -> Job:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status, retry_count, max_retries FROM jobs WHERE job_id = ?", (str(job_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        db_status = JobStatus(row[0])
        if db_status.is_terminal():
            raise ValueError("Terminal jobs cannot be retried.")

        retry_count = row[1]
        max_retries = row[2]

        new_retry_count = retry_count + 1
        now = datetime.now(timezone.utc)

        if new_retry_count <= max_retries:
            from datetime import timedelta
            run_after_dt = now + timedelta(seconds=backoff_seconds)
            cursor.execute(
                """
                UPDATE jobs
                SET status = ?, retry_count = ?, run_after = ?, error_message = ?
                WHERE job_id = ?
                """,
                (JobStatus.RETRYING.value, new_retry_count, run_after_dt.isoformat(), error_message, str(job_id)),
            )
        else:
            # Exhausted retries -> Fail job
            cursor.execute(
                """
                UPDATE jobs
                SET status = ?, retry_count = ?, completed_at = ?, error_message = ?
                WHERE job_id = ?
                """,
                (JobStatus.FAILED.value, new_retry_count, now.isoformat(), f"Max retries exhausted. {error_message}", str(job_id)),
            )

        self.conn.commit()

        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
        return self._to_model(cursor.fetchone())

    def recover_stale_jobs(self, timeout_seconds: int = 30) -> Dict[str, int]:
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc)
        # Find active RUNNING jobs
        cursor.execute("SELECT * FROM jobs WHERE status = 'RUNNING'")
        running_rows = cursor.fetchall()

        rescheduled = 0
        failed = 0

        for row in running_rows:
            job = self._to_model(row)
            if not job.last_heartbeat:
                # If no heartbeat set yet, calculate difference from started_at
                base_time = job.started_at or job.created_at
            else:
                base_time = job.last_heartbeat

            diff = (now - base_time).total_seconds()
            if diff > timeout_seconds:
                # Zombie detected!
                new_retry = job.retry_count + 1
                if new_retry <= job.max_retries:
                    # Move back to QUEUED
                    cursor.execute(
                        """
                        UPDATE jobs
                        SET status = ?, retry_count = ?, started_at = NULL, last_heartbeat = NULL
                        WHERE job_id = ?
                        """,
                        (JobStatus.QUEUED.value, new_retry, str(job.job_id)),
                    )
                    rescheduled += 1
                else:
                    # Move to FAILED
                    cursor.execute(
                        """
                        UPDATE jobs
                        SET status = ?, retry_count = ?, completed_at = ?, error_message = ?
                        WHERE job_id = ?
                        """,
                        (
                            JobStatus.FAILED.value,
                            new_retry,
                            now.isoformat(),
                            "Worker heartbeat timeout. Interrupted and terminated.",
                            str(job.job_id),
                        ),
                    )
                    failed += 1

        self.conn.commit()
        return {"rescheduled": rescheduled, "failed": failed}

    def cleanup_old_jobs(self) -> Dict[str, int]:
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc)

        from datetime import timedelta
        # COMPLETED retention: 7 days
        completed_dt = now - timedelta(days=7)

        # FAILED & CANCELLED retention: 30 days
        failed_dt = now - timedelta(days=30)

        cursor.execute(
            "DELETE FROM jobs WHERE status = 'COMPLETED' AND completed_at < ?",
            (completed_dt.isoformat(),),
        )
        completed_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM jobs WHERE status IN ('FAILED', 'CANCELLED') AND completed_at < ?",
            (failed_dt.isoformat(),),
        )
        failed_deleted = cursor.rowcount

        self.conn.commit()
        return {"deleted": completed_deleted + failed_deleted}
