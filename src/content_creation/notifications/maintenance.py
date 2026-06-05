"""Notification maintenance service for cleanup and retention enforcement.

Scheduler-ready. No direct worker coupling. Repository-driven only.
"""

import logging
from typing import Dict

from content_creation.notifications.repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationMaintenanceService:
    """Handles notification lifecycle maintenance tasks.

    Capabilities:
    - Cleanup expired (old read/archived) notifications
    - Archive stale read notifications
    - Retention enforcement

    Designed to be invoked by a scheduler or cron job.
    No Streamlit, worker, or queue imports.
    """

    def __init__(
        self,
        repository: NotificationRepository,
        retention_days: int = 30,
        archive_after_days: int = 7,
    ) -> None:
        self._repository = repository
        self._retention_days = retention_days
        self._archive_after_days = archive_after_days

    def cleanup_expired(self) -> Dict[str, int]:
        """Remove read/archived notifications older than retention period.

        Returns:
            Dict with 'deleted' count.
        """
        max_age_seconds = self._retention_days * 86400
        deleted = self._repository.cleanup_expired_notifications(max_age_seconds)
        if deleted > 0:
            logger.info("Cleaned up %d expired notifications", deleted)
        return {"deleted": deleted}

    def archive_stale_read(self) -> Dict[str, int]:
        """Archive read notifications older than archive threshold.

        Returns:
            Dict with 'archived' count.
        """
        from content_creation.notifications.models import NotificationStatus
        from datetime import datetime, timezone, timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=self._archive_after_days)
        stale = self._repository.list_notifications(
            status=NotificationStatus.READ,
            limit=10000,
        )
        archived_count = 0
        for n in stale:
            if n.timestamp < cutoff:
                self._repository.archive(n.notification_id)
                archived_count += 1

        if archived_count > 0:
            logger.info("Archived %d stale read notifications", archived_count)
        return {"archived": archived_count}

    def enforce_retention(self) -> Dict[str, int]:
        """Run full maintenance cycle: archive stale reads, then cleanup expired.

        Returns:
            Dict with 'archived' and 'deleted' counts.
        """
        archive_result = self.archive_stale_read()
        cleanup_result = self.cleanup_expired()
        return {
            "archived": archive_result["archived"],
            "deleted": cleanup_result["deleted"],
        }
