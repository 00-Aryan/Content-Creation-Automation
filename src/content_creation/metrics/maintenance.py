"""MetricsMaintenanceService — retention cleanup and compaction for the metrics store."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from content_creation.metrics.repository import MetricRepository

logger = logging.getLogger(__name__)

# Default retention periods (in days)
DEFAULT_RETENTION_DAYS = 90
DEFAULT_COMPACTED_RETENTION_DAYS = 365


class MetricsMaintenanceService:
    """Scheduler-ready maintenance service for the metrics store.

    Responsibilities:
    - Cleanup expired metrics based on retention policy
    - Enforce retention rules
    - Report storage statistics

    Scheduler-ready — designed to be called periodically.
    No UI, worker, or executor imports.
    """

    def __init__(
        self,
        repository: MetricRepository,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self._repository = repository
        self._retention_days = retention_days

    def cleanup_expired(self) -> int:
        """Delete metrics that exceed the retention period.

        Returns total number of metrics deleted.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self._retention_days)
        deleted = self._repository.delete_expired(cutoff)

        if deleted > 0:
            logger.info("Metrics maintenance: deleted %d expired metrics", deleted)

        return deleted

    def storage_stats(self) -> Dict[str, int]:
        """Get metric counts for monitoring."""
        total = self._repository.count_metrics()
        return {
            "total_metrics": total,
            "retention_days": self._retention_days,
        }

    def enforce_retention(self) -> Dict[str, int]:
        """Run full retention enforcement.

        Returns a summary of cleanup results.
        """
        deleted = self.cleanup_expired()
        return {"deleted": deleted}
