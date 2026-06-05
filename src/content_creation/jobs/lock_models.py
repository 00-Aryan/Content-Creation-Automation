"""Lock-related domain models and enums."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class LockType(str, Enum):
    """Supported resource lock categories."""

    TOPIC = "TOPIC"
    MANIFEST = "MANIFEST"
    CALENDAR = "CALENDAR"


class LockStatus(str, Enum):
    """State of a resource lock."""

    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ResourceLock:
    """Immutable domain representation of a resource lock."""

    lock_id: UUID
    lock_type: LockType
    resource_id: str
    owner_job_id: UUID
    status: LockStatus
    acquired_at: datetime
    last_heartbeat: datetime
    released_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate lock model constraints."""
        if not self.resource_id or not self.resource_id.strip():
            raise ValueError("resource_id cannot be empty")
        if not self.owner_job_id:
            raise ValueError("owner_job_id cannot be empty")
        if not self.acquired_at:
            raise ValueError("acquired_at is required")
        if not isinstance(self.lock_type, LockType):
            object.__setattr__(self, "lock_type", LockType(self.lock_type))
        if not isinstance(self.status, LockStatus):
            object.__setattr__(self, "status", LockStatus(self.status))

    def is_active(self) -> bool:
        """Return True if the lock is currently active."""
        return self.status == LockStatus.ACTIVE

    def is_released(self) -> bool:
        """Return True if the lock has been released."""
        return self.status == LockStatus.RELEASED

    def is_expired(self) -> bool:
        """Return True if the lock has expired due to worker heartbeat timeout."""
        return self.status == LockStatus.EXPIRED
