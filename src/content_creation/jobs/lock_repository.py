"""Abstract Lock Repository definition."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from content_creation.jobs.lock_models import LockType, ResourceLock


class LockRepository(ABC):
    """Abstract interface defining operations on ResourceLock persistence."""

    @abstractmethod
    def acquire_lock(self, lock: ResourceLock) -> ResourceLock:
        """Atomically acquire an active resource lock.

        If a lock of the same type on the same resource is already ACTIVE,
        must raise a ValueError.
        """
        pass

    @abstractmethod
    def release_lock(self, lock_id: UUID) -> ResourceLock:
        """Release an active resource lock.

        Marks the lock as RELEASED and updates released_at.
        Raises ValueError if lock not found or already released.
        """
        pass

    @abstractmethod
    def get_lock(self, lock_id: UUID) -> Optional[ResourceLock]:
        """Fetch lock details by lock ID."""
        pass

    @abstractmethod
    def get_lock_owner(self, lock_type: LockType, resource_id: str) -> Optional[UUID]:
        """Get the owner job ID of the current active lock for the resource.

        Returns None if not locked.
        """
        pass

    @abstractmethod
    def is_locked(self, lock_type: LockType, resource_id: str) -> bool:
        """Check if a resource is currently locked by an active lock."""
        pass

    @abstractmethod
    def list_active_locks(self) -> List[ResourceLock]:
        """List all locks currently in the ACTIVE status."""
        pass

    @abstractmethod
    def release_stale_locks(self, timeout_seconds: int) -> Dict[str, Any]:
        """Identify locks with heartbeats older than timeout and transition them to EXPIRED.

        Returns:
            Dict[str, Any]: E.g., {"expired_count": X, "released_resources": List[str]}
        """
        pass

    @abstractmethod
    def heartbeat(self, lock_id: UUID) -> None:
        """Update last_heartbeat timestamp on an active lock."""
        pass

    @abstractmethod
    def delete_lock(self, lock_id: UUID) -> bool:
        """Hard delete a lock from the database."""
        pass
