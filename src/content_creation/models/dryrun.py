from typing import List, Literal, Optional, Union
from pydantic import BaseModel

from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId

DryRunReviewStatus = Union[ReviewStatus, Literal["missing", "error", "unknown"]]


class AssetCheck(BaseModel):
    topic_id: TopicId
    topic_title: str
    format: str
    asset_path: str
    review_status: DryRunReviewStatus
    is_ready: bool  # True only if status == "approved"
    warning: Optional[str] = None  # None if ready, reason if not


class DryRunReport(BaseModel):
    week_start: str
    week_end: str
    total_scheduled: int
    ready_count: int  # approved assets
    warning_count: int  # non-approved but included
    blocked_count: int  # missing assets
    checks: List[AssetCheck]
    warnings: List[str]  # human readable warning messages
    recommended_actions: List[str]  # what to do before publishing
    generated_at: str