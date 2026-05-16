from pydantic import BaseModel
from typing import List, Optional


class AssetCheck(BaseModel):
    topic_id: str
    topic_title: str
    format: str
    asset_path: str
    review_status: str
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