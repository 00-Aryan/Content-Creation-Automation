"""Abstract Job Repository definition."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from content_creation.jobs.models import Job, JobResult, JobStatus


class JobRepository(ABC):
    """Abstract interface defining operations on Job persistence."""

    @abstractmethod
    def create_job(self, job: Job) -> Job:
        """Persist a new job in the store.

        Raises:
            ValueError: If the job already exists or state is invalid.
        """
        pass

    @abstractmethod
    def get_job(self, job_id: UUID) -> Optional[Job]:
        """Retrieve a job by its unique ID.

        Returns None if not found.
        """
        pass

    @abstractmethod
    def update_job(self, job: Job) -> Job:
        """Update an existing job in the store.

        This method updates all fields of the job. It must raise a ValueError
        if the job does not exist, or if it violates transition rules or terminal invariants.
        """
        pass

    @abstractmethod
    def delete_job(self, job_id: UUID) -> bool:
        """Delete a job from the store.

        Returns True if deleted, False if not found.
        """
        pass

    @abstractmethod
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        correlation_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> List[Job]:
        """Filter and list jobs in the store."""
        pass

    @abstractmethod
    def enqueue_job(self, job_id: UUID) -> Job:
        """Transition a job from PENDING/BLOCKED to QUEUED.

        Updates queued_at and resets run_after.
        """
        pass

    @abstractmethod
    def claim_next_job(self, worker_id: str) -> Optional[Job]:
        """Claim the next eligible QUEUED job.

        Finds the oldest, highest priority QUEUED job that is eligible to run
        (run_after is null or <= current time). Updates status to RUNNING,
        sets started_at and last_heartbeat.

        This call must be atomic (e.g. wrapped in BEGIN IMMEDIATE).
        """
        pass

    @abstractmethod
    def heartbeat(self, job_id: UUID) -> None:
        """Update last_heartbeat timestamp.

        Only updates if the status is currently RUNNING.
        """
        pass

    @abstractmethod
    def complete_job(self, job_id: UUID, result: JobResult) -> Job:
        """Mark a job as successfully COMPLETED.

        Saves execution result, sets completed_at, releases any active locks.
        """
        pass

    @abstractmethod
    def fail_job(self, job_id: UUID, error_message: str) -> Job:
        """Mark a job as permanently FAILED.

        Saves error message, sets completed_at, releases any active locks.
        """
        pass

    @abstractmethod
    def cancel_job(self, job_id: UUID) -> Job:
        """Mark a job as CANCELLED.

        Only valid if the job is not already in a terminal state.
        Saves cancellation reason (if any) or sets completed_at.
        """
        pass

    @abstractmethod
    def schedule_retry(self, job_id: UUID, backoff_seconds: float, error_message: str) -> Job:
        """Increment retry_count, transition to RETRYING, and calculate run_after."""
        pass

    @abstractmethod
    def recover_stale_jobs(self, timeout_seconds: int = 30) -> Dict[str, int]:
        """Audit RUNNING jobs with stale heartbeats.

        Reschedules to QUEUED if they have remaining retries (incrementing retry_count),
        otherwise transitions them to FAILED.

        Returns:
            Dict[str, int]: E.g., {"rescheduled": X, "failed": Y}
        """
        pass

    @abstractmethod
    def cleanup_old_jobs(self) -> Dict[str, int]:
        """Prune old terminal jobs based on retention limits:

        - COMPLETED: 7 days
        - FAILED: 30 days
        - CANCELLED: 30 days

        Returns:
            Dict[str, int]: E.g., {"deleted": X}
        """
        pass
