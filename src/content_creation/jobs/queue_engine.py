"""Queue Engine orchestrating background job state transitions and scheduling."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.models import Job, JobStatus, JobType
from content_creation.jobs.repository import JobRepository


@dataclass(frozen=True)
class JobSubmissionResult:
    """Outcome of submitting a job to the Queue Engine."""

    job_id: UUID
    status: JobStatus
    created_at: datetime


@dataclass(frozen=True)
class QueueMetrics:
    """Metrics snapshot representing current queue throughput and backlog."""

    queued_count: int
    running_count: int
    retrying_count: int
    completed_count: int
    failed_count: int
    cancelled_count: int
    oldest_queued_age_seconds: float


class QueueEngine:
    """Persistence-backed engine managing asynchronous job state, scheduling, and metrics."""

    def __init__(self, repository: JobRepository, lock_manager: LockManager) -> None:
        self._repo = repository
        self._locks = lock_manager

    def submit_job(
        self,
        job_type: str,
        action_id: str,
        operator_id: str,
        target_type: str,
        target_id: str,
        payload: Dict[str, Any],
        correlation_id: str,
        priority: int = 100,
        max_retries: int = 3,
    ) -> JobSubmissionResult:
        """Validate, persist, and queue a new job unit."""
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary")

        job_id = uuid4()
        now = datetime.now(timezone.utc)

        # Instantiate job in PENDING state
        job = Job(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            priority=priority,
            created_at=now,
            operator_id=operator_id,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
            correlation_id=correlation_id,
            max_retries=max_retries,
        )

        self._repo.create_job(job)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_job_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_job_event(
                event_type=EventType.JOB_CREATED,
                job_id=job.job_id,
                job_type=job.job_type,
                status=JobStatus.PENDING.value,
                operator_id=operator_id,
                correlation_id=correlation_id,
                target_type=target_type,
                target_id=target_id,
                retry_count=0,
                max_retries=max_retries,
            )
            bus.publish(evt)
        except Exception:
            pass

        # Transition PENDING -> QUEUED
        queued_job = self._repo.enqueue_job(job_id)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_job_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_job_event(
                event_type=EventType.JOB_QUEUED,
                job_id=queued_job.job_id,
                job_type=queued_job.job_type,
                status=JobStatus.QUEUED.value,
                operator_id=queued_job.operator_id,
                correlation_id=queued_job.correlation_id,
                target_type=queued_job.target_type,
                target_id=queued_job.target_id,
                retry_count=queued_job.retry_count,
                max_retries=queued_job.max_retries,
            )
            bus.publish(evt)
        except Exception:
            pass

        return JobSubmissionResult(
            job_id=queued_job.job_id,
            status=queued_job.status,
            created_at=queued_job.created_at,
        )

    def claim_next_job(self, worker_id: str) -> Optional[Job]:
        """Claim the next eligible QUEUED/RETRYING job.

        Delegates atomicity and resource lock checking to the repository.
        """
        return self._repo.claim_next_job(worker_id)

    def schedule_retry(self, job_id: UUID, error_message: str, base_delay: float = 5.0) -> Job:
        """Schedule a job for retry after exponential backoff.

        Calculates run_after based on attempt retry_count.
        """
        job = self._repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        # Retry calculations: base_delay * (2 ** retry_count)
        # Note: retry_count in DB represents previously attempted runs.
        backoff_seconds = base_delay * (2 ** job.retry_count)

        ret = self._repo.schedule_retry(job_id, backoff_seconds, error_message)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_job_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            if ret.status == JobStatus.RETRYING:
                evt = create_job_event(
                    event_type=EventType.JOB_RETRIED,
                    job_id=ret.job_id,
                    job_type=ret.job_type,
                    status=ret.status.value,
                    operator_id=ret.operator_id,
                    correlation_id=ret.correlation_id,
                    target_type=ret.target_type,
                    target_id=ret.target_id,
                    retry_count=ret.retry_count,
                    max_retries=ret.max_retries,
                    error_message=error_message,
                )
            else:
                evt = create_job_event(
                    event_type=EventType.JOB_FAILED,
                    job_id=ret.job_id,
                    job_type=ret.job_type,
                    status=ret.status.value,
                    operator_id=ret.operator_id,
                    correlation_id=ret.correlation_id,
                    target_type=ret.target_type,
                    target_id=ret.target_id,
                    retry_count=ret.retry_count,
                    max_retries=ret.max_retries,
                    error_message=error_message,
                )
            bus.publish(evt)
        except Exception:
            pass
        return ret

    def cancel_job(self, job_id: UUID) -> Job:
        """Cancel a non-active job.

        Only allowed from PENDING, QUEUED, or RETRYING states.
        """
        job = self._repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} does not exist.")

        if job.status not in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RETRYING):
            raise ValueError(
                f"State transition forbidden: cannot cancel job in state {job.status.value}"
            )

        ret = self._repo.cancel_job(job_id)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_job_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_job_event(
                event_type=EventType.JOB_CANCELLED,
                job_id=ret.job_id,
                job_type=ret.job_type,
                status=ret.status.value,
                operator_id=ret.operator_id,
                correlation_id=ret.correlation_id,
                target_type=ret.target_type,
                target_id=ret.target_id,
                retry_count=ret.retry_count,
                max_retries=ret.max_retries,
            )
            bus.publish(evt)
        except Exception:
            pass
        return ret

    def get_queue_metrics(self) -> QueueMetrics:
        """Fetch snapshot metrics representing current queue size and oldest age."""
        all_jobs = self._repo.list_jobs()

        counts = {
            JobStatus.QUEUED: 0,
            JobStatus.RUNNING: 0,
            JobStatus.RETRYING: 0,
            JobStatus.COMPLETED: 0,
            JobStatus.FAILED: 0,
            JobStatus.CANCELLED: 0,
            JobStatus.PENDING: 0,
            JobStatus.BLOCKED: 0,
        }

        oldest_queued_time = None
        now = datetime.now(timezone.utc)

        for j in all_jobs:
            counts[j.status] += 1
            if j.status == JobStatus.QUEUED:
                queued_time = j.queued_at or j.created_at
                if oldest_queued_time is None or queued_time < oldest_queued_time:
                    oldest_queued_time = queued_time

        age = 0.0
        if oldest_queued_time:
            age = (now - oldest_queued_time).total_seconds()

        return QueueMetrics(
            queued_count=counts[JobStatus.QUEUED],
            running_count=counts[JobStatus.RUNNING],
            retrying_count=counts[JobStatus.RETRYING],
            completed_count=counts[JobStatus.COMPLETED],
            failed_count=counts[JobStatus.FAILED],
            cancelled_count=counts[JobStatus.CANCELLED],
            oldest_queued_age_seconds=max(0.0, age),
        )

    def get_pending_jobs(self) -> List[Job]:
        """Fetch all jobs currently in the PENDING status."""
        return self._repo.list_jobs(status=JobStatus.PENDING)

    def get_running_jobs(self) -> List[Job]:
        """Fetch all jobs currently in the RUNNING status."""
        return self._repo.list_jobs(status=JobStatus.RUNNING)

    def list_queued_jobs(self) -> List[Job]:
        """Fetch all jobs currently in the QUEUED status."""
        return self._repo.list_jobs(status=JobStatus.QUEUED)

    def list_running_jobs(self) -> List[Job]:
        """Fetch all jobs currently in the RUNNING status (alias)."""
        return self.get_running_jobs()

    def list_retrying_jobs(self) -> List[Job]:
        """Fetch all jobs currently in the RETRYING status."""
        return self._repo.list_jobs(status=JobStatus.RETRYING)

    def list_failed_jobs(self) -> List[Job]:
        """Fetch all jobs currently in the FAILED status."""
        return self._repo.list_jobs(status=JobStatus.FAILED)
