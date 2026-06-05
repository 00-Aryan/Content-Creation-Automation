"""Job domain models representing background execution entities."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class JobStatus(str, Enum):
    """Execution status for a background job."""

    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    def is_terminal(self) -> bool:
        """Return True if the status is a terminal state."""
        return self in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    def is_active(self) -> bool:
        """Return True if the status is an active (non-terminal) state."""
        return self in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.RETRYING)


class JobType(str, Enum):
    """Supported job execution classifications."""

    COLLECT = "COLLECT"
    SCORE = "SCORE"
    GENERATE_BRIEF = "GENERATE_BRIEF"
    GENERATE_CI = "GENERATE_CI"
    GENERATE_STORYBOARD = "GENERATE_STORYBOARD"
    GENERATE_ASSET = "GENERATE_ASSET"
    BUILD_MANIFEST = "BUILD_MANIFEST"
    PLAN_WEEK = "PLAN_WEEK"
    DRY_RUN = "DRY_RUN"
    RUN_PIPELINE = "RUN_PIPELINE"


@dataclass(frozen=True)
class JobResult:
    """Immutable execution summary for a completed job."""

    duration_seconds: float
    warnings: List[str] = field(default_factory=list)
    emitted_events: List[str] = field(default_factory=list)
    generated_files: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Job:
    """Immutable domain representation of an asynchronous workflow execution job."""

    job_id: UUID
    job_type: str
    status: JobStatus
    priority: int
    created_at: datetime
    operator_id: str
    target_type: str
    target_id: str
    payload: Dict[str, Any]
    correlation_id: str
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[JobResult] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    run_after: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate job constraints."""
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if not isinstance(self.status, JobStatus):
            # Safe coercion if passed string
            object.__setattr__(self, "status", JobStatus(self.status))
