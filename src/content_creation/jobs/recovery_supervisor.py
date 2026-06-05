"""Recovery Supervisor managing background job recovery, heartbeat checks, and consistency audits."""

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.lock_repository import LockRepository
from content_creation.jobs.models import Job, JobResult, JobStatus
from content_creation.jobs.queue_engine import QueueEngine
from content_creation.jobs.repository import JobRepository


@dataclass(frozen=True)
class RecoveryConfig:
    """Configuration options for the RecoverySupervisor."""

    heartbeat_timeout_seconds: int
    sweep_interval_seconds: int
    max_recovery_batch_size: int

    def __post_init__(self) -> None:
        """Validate recovery boundaries."""
        if self.heartbeat_timeout_seconds <= 0:
            raise ValueError("heartbeat_timeout_seconds must be positive")
        if self.sweep_interval_seconds <= 0:
            raise ValueError("sweep_interval_seconds must be positive")
        if self.max_recovery_batch_size <= 0:
            raise ValueError("max_recovery_batch_size must be positive")


@dataclass(frozen=True)
class RecoverySweepResult:
    """Summary of operations performed during a single recovery sweep."""

    recovered_jobs: List[str]
    failed_jobs: List[str]
    expired_locks: List[str]
    released_locks: List[str]
    skipped_jobs: List[str]
    execution_time_ms: float


@dataclass(frozen=True)
class QueueConsistencyReport:
    """Report detailing consistency anomalies within jobs and locks."""

    warnings: List[str]
    errors: List[str]
    recoverable_issues: List[Dict[str, Any]]


class RecoverySupervisor:
    """Supervisor layer identifying zombie executions, expiring locks, and validating consistency."""

    def __init__(
        self,
        repository: JobRepository,
        lock_repository: LockRepository,
        queue_engine: QueueEngine,
        config: Optional[RecoveryConfig] = None,
    ) -> None:
        self.repository = repository
        self.lock_repository = lock_repository
        self.queue_engine = queue_engine
        self.config = config or RecoveryConfig(
            heartbeat_timeout_seconds=30,
            sweep_interval_seconds=60,
            max_recovery_batch_size=10,
        )

    def recover_expired_locks(self) -> List[str]:
        """Audit ACTIVE locks and transition them to EXPIRED if heartbeats are stale."""
        now = datetime.now(timezone.utc)
        timeout_dt = now - timedelta(seconds=self.config.heartbeat_timeout_seconds)

        expired_lock_ids = []
        active_locks = self.lock_repository.list_active_locks()
        for lock in active_locks:
            if lock.last_heartbeat < timeout_dt:
                expired_lock_ids.append(str(lock.lock_id))
                try:
                    from uuid import uuid4
                    from content_creation.events.bus import get_event_bus
                    from content_creation.events.factory import create_recovery_event, create_lock_event
                    from content_creation.events.models import EventType
                    bus = get_event_bus()
                    
                    # 1. Emit lock_expired
                    evt_lock = create_lock_event(
                        event_type=EventType.LOCK_EXPIRED,
                        lock_id=lock.lock_id,
                        lock_type=lock.lock_type.value,
                        resource_id=lock.resource_id,
                        owner_job_id=lock.owner_job_id,
                        correlation_id=str(uuid4()),
                    )
                    bus.publish(evt_lock)
                    
                    # 2. Emit stale_lock_expired
                    evt_rec = create_recovery_event(
                        event_type=EventType.STALE_LOCK_EXPIRED,
                        entity_type="lock",
                        entity_id=str(lock.lock_id),
                        correlation_id=str(uuid4()),
                        details={
                            "lock_id": str(lock.lock_id),
                            "lock_type": lock.lock_type.value,
                            "resource_id": lock.resource_id,
                            "owner_job_id": str(lock.owner_job_id),
                            "last_heartbeat": lock.last_heartbeat.isoformat(),
                        }
                    )
                    bus.publish(evt_rec)
                except Exception:
                    pass

        self.lock_repository.release_stale_locks(self.config.heartbeat_timeout_seconds)
        return expired_lock_ids

    def recover_on_startup(self) -> RecoverySweepResult:
        """Perform startup sweep to clean up outstanding zombies and stale locks. Idempotent."""
        return self.run_sweep()

    def run_sweep(self) -> RecoverySweepResult:
        """Scan outstanding jobs and locks, recovering zombies and expiring stale resources."""
        start_time = time.perf_counter()

        recovered_jobs = []
        failed_jobs = []
        expired_locks = []
        released_locks = []
        skipped_jobs = []

        now = datetime.now(timezone.utc)
        running_jobs = self.repository.list_jobs(status=JobStatus.RUNNING)

        # Identify zombie RUNNING jobs
        zombie_jobs = []
        for job in running_jobs:
            base_time = job.last_heartbeat or job.started_at or job.created_at
            if (now - base_time).total_seconds() > self.config.heartbeat_timeout_seconds:
                zombie_jobs.append(job)

        to_recover = zombie_jobs[: self.config.max_recovery_batch_size]
        to_skip = zombie_jobs[self.config.max_recovery_batch_size :]

        for job in to_skip:
            skipped_jobs.append(str(job.job_id))

        for job in to_recover:
            # 1. Release active locks owned by this zombie job
            active_locks = self.lock_repository.list_active_locks()
            job_locks = [l for l in active_locks if l.owner_job_id == job.job_id]
            for lock in job_locks:
                try:
                    self.lock_repository.release_lock(lock.lock_id)
                    released_locks.append(str(lock.lock_id))
                except Exception:
                    pass

            # 2. Reschedule or fail the job based on remaining retries
            recovery_ts = datetime.now(timezone.utc).isoformat()
            if job.retry_count < job.max_retries:
                # RUNNING -> RETRYING -> QUEUED
                err_msg = f"[{recovery_ts}] Heartbeat timeout recovery (attempt {job.retry_count + 1}/{job.max_retries})"
                try:
                    self.queue_engine.schedule_retry(job.job_id, err_msg)

                    # Get refreshed status to move to QUEUED state while keeping backoff delay
                    refreshed = self.repository.get_job(job.job_id)
                    if refreshed and refreshed.status == JobStatus.RETRYING:
                        updated = dataclasses.replace(
                            refreshed,
                            status=JobStatus.QUEUED,
                            started_at=None,
                            last_heartbeat=None,
                        )
                        self.repository.update_job(updated)
                    recovered_jobs.append(str(job.job_id))
                    
                    try:
                        from content_creation.events.bus import get_event_bus
                        from content_creation.events.factory import create_recovery_event
                        from content_creation.events.models import EventType
                        bus = get_event_bus()
                        evt = create_recovery_event(
                            event_type=EventType.ZOMBIE_JOB_RECOVERED,
                            entity_type="job",
                            entity_id=str(job.job_id),
                            correlation_id=job.correlation_id,
                            details={
                                "job_id": str(job.job_id),
                                "job_type": job.job_type,
                                "action_id": job.payload.get("action_id", job.job_type.lower()),
                                "previous_status": "RUNNING",
                                "new_status": "QUEUED",
                                "retry_count": job.retry_count + 1,
                                "max_retries": job.max_retries,
                                "recovery_action": "rescheduled",
                            }
                        )
                        bus.publish(evt)
                    except Exception:
                        pass
                except Exception as e:
                    # Fallback failsafe
                    try:
                        self.repository.fail_job(job.job_id, f"Failed recovery transition: {e}")
                        failed_jobs.append(str(job.job_id))
                    except Exception:
                        pass
            else:
                # RUNNING -> FAILED
                err_msg = f"[{recovery_ts}] Heartbeat timeout recovery. Retries exhausted ({job.retry_count + 1}/{job.max_retries})."
                try:
                    self.repository.fail_job(job.job_id, err_msg)
                    failed_jobs.append(str(job.job_id))
                    
                    try:
                        from content_creation.events.bus import get_event_bus
                        from content_creation.events.factory import create_recovery_event
                        from content_creation.events.models import EventType
                        bus = get_event_bus()
                        evt = create_recovery_event(
                            event_type=EventType.ZOMBIE_JOB_RECOVERED,
                            entity_type="job",
                            entity_id=str(job.job_id),
                            correlation_id=job.correlation_id,
                            details={
                                "job_id": str(job.job_id),
                                "job_type": job.job_type,
                                "action_id": job.payload.get("action_id", job.job_type.lower()),
                                "previous_status": "RUNNING",
                                "new_status": "FAILED",
                                "retry_count": job.retry_count + 1,
                                "max_retries": job.max_retries,
                                "recovery_action": "failed",
                            }
                        )
                        bus.publish(evt)
                    except Exception:
                        pass
                except Exception:
                    pass

        # 3. Expire stale locks
        expired_lock_ids = self.recover_expired_locks()
        expired_locks.extend(expired_lock_ids)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return RecoverySweepResult(
            recovered_jobs=recovered_jobs,
            failed_jobs=failed_jobs,
            expired_locks=expired_locks,
            released_locks=released_locks,
            skipped_jobs=skipped_jobs,
            execution_time_ms=duration_ms,
        )

    def validate_queue_consistency(self) -> QueueConsistencyReport:
        """Audit jobs and locks to detect validation inconsistencies without modifying database state."""
        warnings = []
        errors = []
        recoverable_issues = []

        now = datetime.now(timezone.utc)

        all_jobs = self.repository.list_jobs()
        active_locks = self.lock_repository.list_active_locks()

        # Build job index
        job_map = {job.job_id: job for job in all_jobs}

        for job in all_jobs:
            # 1. RUNNING job with no worker heartbeat
            if job.status == JobStatus.RUNNING and job.last_heartbeat is None:
                msg = f"Job {job.job_id} is RUNNING but has no last_heartbeat timestamp."
                warnings.append(msg)
                recoverable_issues.append(
                    {
                        "type": "running_no_heartbeat",
                        "job_id": str(job.job_id),
                        "description": msg,
                    }
                )

            # 2. QUEUED job past run_after
            if job.status == JobStatus.QUEUED and job.run_after is not None and job.run_after <= now:
                msg = f"Job {job.job_id} is QUEUED but its run_after timestamp ({job.run_after.isoformat()}) has expired."
                warnings.append(msg)
                recoverable_issues.append(
                    {
                        "type": "queued_past_run_after",
                        "job_id": str(job.job_id),
                        "description": msg,
                    }
                )

            # 3. RETRYING job with expired retry window
            if job.status == JobStatus.RETRYING and job.run_after is not None and job.run_after <= now:
                msg = f"Job {job.job_id} is RETRYING but its run_after timestamp ({job.run_after.isoformat()}) has expired."
                warnings.append(msg)
                recoverable_issues.append(
                    {
                        "type": "retrying_expired_window",
                        "job_id": str(job.job_id),
                        "description": msg,
                    }
                )

        for lock in active_locks:
            owner_job = job_map.get(lock.owner_job_id)

            # 4. Lock referencing missing job
            if owner_job is None:
                msg = f"Lock {lock.lock_id} ({lock.lock_type.value}:{lock.resource_id}) references missing job {lock.owner_job_id}."
                errors.append(msg)
                recoverable_issues.append(
                    {
                        "type": "lock_missing_job",
                        "lock_id": str(lock.lock_id),
                        "owner_job_id": str(lock.owner_job_id),
                        "description": msg,
                    }
                )
            else:
                # 5. Lock owned by terminal job
                if owner_job.status.is_terminal():
                    msg = f"Lock {lock.lock_id} ({lock.lock_type.value}:{lock.resource_id}) is owned by terminal job {lock.owner_job_id} in state {owner_job.status.value}."
                    errors.append(msg)
                    recoverable_issues.append(
                        {
                            "type": "lock_owned_by_terminal_job",
                            "lock_id": str(lock.lock_id),
                            "owner_job_id": str(lock.owner_job_id),
                            "job_status": owner_job.status.value,
                            "description": msg,
                        }
                    )

        return QueueConsistencyReport(
            warnings=warnings, errors=errors, recoverable_issues=recoverable_issues
        )
