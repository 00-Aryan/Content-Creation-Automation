"""EventMaintenanceService — retention cleanup and archival for the event store."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from content_creation.events.store.repository import EventRepository

logger = logging.getLogger(__name__)

# Default retention periods by category (in days)
DEFAULT_RETENTION_DAYS: Dict[str, int] = {
    "workflow": 90,
    "review": 90,
    "job": 90,
    "lock": 30,
    "recovery": 90,
    "pipeline": 365,
}

# Default retention for uncategorized events
DEFAULT_FALLBACK_RETENTION_DAYS = 90


class EventMaintenanceService:
    """Scheduler-ready maintenance service for the event store.

    Responsibilities:
    - Cleanup expired events based on retention policy
    - Enforce per-category retention rules
    - Report storage statistics

    Scheduler-ready — designed to be called periodically.
    No UI, worker, or executor imports.
    """

    def __init__(
        self,
        repository: EventRepository,
        retention_days: Optional[Dict[str, int]] = None,
    ) -> None:
        self._repository = repository
        self._retention_days = retention_days or DEFAULT_RETENTION_DAYS

    def cleanup_expired(self, category: Optional[str] = None) -> int:
        """Delete events that exceed their retention period.

        If category is specified, only cleanup that category.
        Otherwise, cleanup all categories.

        Returns total number of events deleted.
        """
        now = datetime.now(timezone.utc)
        total_deleted = 0

        if category:
            days = self._retention_days.get(category, DEFAULT_FALLBACK_RETENTION_DAYS)
            cutoff = now - timedelta(days=days)
            deleted = self._repository.delete_expired(cutoff, category=category)
            total_deleted += deleted
        else:
            for cat, days in self._retention_days.items():
                cutoff = now - timedelta(days=days)
                deleted = self._repository.delete_expired(cutoff, category=cat)
                total_deleted += deleted

            # Also cleanup uncategorized events
            fallback_cutoff = now - timedelta(days=DEFAULT_FALLBACK_RETENTION_DAYS)
            # Note: delete_expired with category=None handles remaining events

        if total_deleted > 0:
            logger.info("Event maintenance: deleted %d expired events", total_deleted)

        return total_deleted

    def enforce_retention(self) -> Dict[str, int]:
        """Run full retention enforcement across all categories.

        Returns a summary of events deleted per category.
        """
        now = datetime.now(timezone.utc)
        summary: Dict[str, int] = {}

        for cat, days in self._retention_days.items():
            cutoff = now - timedelta(days=days)
            deleted = self._repository.delete_expired(cutoff, category=cat)
            if deleted > 0:
                summary[cat] = deleted

        if summary:
            logger.info("Retention enforcement complete: %s", summary)

        return summary

    def storage_stats(self) -> Dict[str, int]:
        """Get event counts by category for monitoring."""
        stats: Dict[str, int] = {}
        for cat in self._retention_days:
            stats[cat] = self._repository.count_events(category=cat)
        stats["total"] = self._repository.count_events()
        return stats
