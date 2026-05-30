from pydantic import BaseModel
from typing import Dict, List, Literal

from content_creation.shared.types import TopicId


class ScheduledPost(BaseModel):
    day: int  # 1-7
    date: str  # ISO-8601 date string
    topic_id: TopicId
    topic_title: str
    format: Literal[
        "short_video",
        "carousel",
        "newsletter",
        "thumbnail"
    ]
    asset_path: str  # path to the asset JSON file
    source_url: str
    scheduled_at: str  # when plan was generated


class WeeklyCalendar(BaseModel):
    week_start: str  # ISO-8601 date of Monday
    week_end: str  # ISO-8601 date of Sunday
    posts: List[ScheduledPost]
    total_posts: int
    format_counts: Dict[str, int]  # e.g. {"short_video": 3}
    topics_used: List[str]  # unique topic_ids
    generated_at: str
    config_snapshot: Dict  # copy of publishing.yaml at time of generation