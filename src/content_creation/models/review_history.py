"""Review history model for tracking editorial review actions."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from content_creation.shared.enums import ReviewStatus


class ReviewHistoryEntry(BaseModel):
    """A single review action recorded in the audit trail."""

    topic_id: str
    asset_type: str
    action: str
    previous_status: Optional[ReviewStatus] = None
    new_status: ReviewStatus
    notes: Optional[str] = None
    timestamp: str = ""

    def model_post_init(self, __context) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
