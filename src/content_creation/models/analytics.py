from pydantic import BaseModel
from typing import Literal, Optional

from content_creation.shared.types import TopicId


class PerformanceSnapshot(BaseModel):
    views_24h: Optional[int] = None
    views_7d: Optional[int] = None
    views_30d: Optional[int] = None
    reach_24h: Optional[int] = None
    reach_7d: Optional[int] = None
    saves: Optional[int] = None
    comments: Optional[int] = None
    cta_clicks: Optional[int] = None
    watch_time_pct: Optional[float] = None
    # 0.0-100.0, video only
    # None for non-video formats


class PostAnalytics(BaseModel):
    post_id: str  # {topic_id}_{format}_{week_start}
    topic_id: TopicId
    topic_title: str
    format: Literal[
        "short_video",
        "carousel",
        "newsletter",
        "thumbnail"
    ]
    asset_path: str
    source_url: str
    posted_at: Optional[str] = None
    # None until actually posted
    week_start: str  # week this was planned for
    performance: PerformanceSnapshot = PerformanceSnapshot()
    last_updated: str  # when this record was last modified
    notes: Optional[str] = None  # manual notes field