"""Cooperative Lock Manager for Content Ingestion & Synthesis Factory."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.lock_repository import LockRepository


class LockManager:
    """Coordinator orchestration managing target locks via LockRepository persistence."""

    def __init__(self, repository: LockRepository) -> None:
        self._repo = repository

    def _create_lock_object(self, lock_type: LockType, resource_id: str, owner_job_id: UUID) -> ResourceLock:
        """Helper to create a fresh ResourceLock in the ACTIVE status."""
        now = datetime.now(timezone.utc)
        return ResourceLock(
            lock_id=uuid4(),
            lock_type=lock_type,
            resource_id=resource_id,
            owner_job_id=owner_job_id,
            status=LockStatus.ACTIVE,
            acquired_at=now,
            last_heartbeat=now,
        )

    def acquire_topic_lock(self, owner_job_id: UUID, topic_id: str) -> ResourceLock:
        """Acquire an active exclusive lock on a topic resource."""
        lock = self._create_lock_object(LockType.TOPIC, topic_id, owner_job_id)
        res = self._repo.acquire_lock(lock)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_lock_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_lock_event(
                event_type=EventType.LOCK_ACQUIRED,
                lock_id=res.lock_id,
                lock_type="TOPIC",
                resource_id=topic_id,
                owner_job_id=owner_job_id,
                correlation_id=str(uuid4()),
            )
            bus.publish(evt)
        except Exception:
            pass
        return res

    def acquire_manifest_lock(self, owner_job_id: UUID, topic_id: str) -> ResourceLock:
        """Acquire an active exclusive lock on a topic manifest compilation."""
        lock = self._create_lock_object(LockType.MANIFEST, topic_id, owner_job_id)
        res = self._repo.acquire_lock(lock)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_lock_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_lock_event(
                event_type=EventType.LOCK_ACQUIRED,
                lock_id=res.lock_id,
                lock_type="MANIFEST",
                resource_id=topic_id,
                owner_job_id=owner_job_id,
                correlation_id=str(uuid4()),
            )
            bus.publish(evt)
        except Exception:
            pass
        return res

    def acquire_calendar_lock(self, owner_job_id: UUID, week_start: str) -> ResourceLock:
        """Acquire an active exclusive lock on a week planning calendar."""
        lock = self._create_lock_object(LockType.CALENDAR, week_start, owner_job_id)
        res = self._repo.acquire_lock(lock)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_lock_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_lock_event(
                event_type=EventType.LOCK_ACQUIRED,
                lock_id=res.lock_id,
                lock_type="CALENDAR",
                resource_id=week_start,
                owner_job_id=owner_job_id,
                correlation_id=str(uuid4()),
            )
            bus.publish(evt)
        except Exception:
            pass
        return res

    def release_lock(self, lock_id: UUID) -> ResourceLock:
        """Release a held lock by ID."""
        res = self._repo.release_lock(lock_id)
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_lock_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_lock_event(
                event_type=EventType.LOCK_RELEASED,
                lock_id=res.lock_id,
                lock_type=res.lock_type.value,
                resource_id=res.resource_id,
                owner_job_id=res.owner_job_id,
                correlation_id=str(uuid4()),
            )
            bus.publish(evt)
        except Exception:
            pass
        return res

    def heartbeat(self, lock_id: UUID) -> None:
        """Send heartbeat for a held lock to keep it active."""
        self._repo.heartbeat(lock_id)

    def is_locked(self, lock_type: LockType, resource_id: str) -> bool:
        """Check if the resource is currently locked by any job."""
        return self._repo.is_locked(lock_type, resource_id)

    def get_lock_owner(self, lock_type: LockType, resource_id: str) -> Optional[UUID]:
        """Fetch the job ID currently owning the resource lock."""
        return self._repo.get_lock_owner(lock_type, resource_id)

    def release_stale_locks(self, timeout_seconds: int) -> Dict[str, Any]:
        """Identify and expire zombie locks that missed heartbeat thresholds."""
        return self._repo.release_stale_locks(timeout_seconds)

    def list_active_locks(self) -> List[ResourceLock]:
        """List all active resource locks."""
        return self._repo.list_active_locks()
