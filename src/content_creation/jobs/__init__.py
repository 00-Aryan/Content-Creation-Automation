"""Background job execution models, lock managers, queue engines, and persistence adapters."""

from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
from content_creation.jobs.repository import JobRepository
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_repository import SQLiteJobRepository

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.lock_repository import LockRepository
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository
from content_creation.jobs.lock_manager import LockManager

from content_creation.jobs.queue_engine import QueueEngine, JobSubmissionResult, QueueMetrics

__all__ = [
    "Job",
    "JobResult",
    "JobStatus",
    "JobType",
    "JobRepository",
    "SQLiteJobRepository",
    "create_schema",
    "LockStatus",
    "LockType",
    "ResourceLock",
    "LockRepository",
    "SQLiteLockRepository",
    "LockManager",
    "QueueEngine",
    "JobSubmissionResult",
    "QueueMetrics",
]
