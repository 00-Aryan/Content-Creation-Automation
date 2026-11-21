from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

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


class PublishingConfigSnapshot(BaseModel):
    """Snapshot of publishing configuration rules at calendar generation time (SCHEMA-003)."""
    model_config = ConfigDict(extra="allow")

    weekly_targets: Optional[Dict[str, int]] = None
    scheduling_rules: Optional[Dict[str, Union[int, bool, str]]] = None
    diversity_rules: Optional[Dict[str, Union[int, bool, str]]] = None

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            if val is not None:
                return val
        if self.__pydantic_extra__ and key in self.__pydantic_extra__:
            return self.__pydantic_extra__[key]
        return default

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None and (not self.__pydantic_extra__ or key not in self.__pydantic_extra__):
            if not hasattr(self, key) or getattr(self, key) is None:
                raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            if self.__pydantic_extra__ is None:
                self.__pydantic_extra__ = {}
            self.__pydantic_extra__[key] = value

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        if hasattr(self, key) and getattr(self, key) is not None:
            return True
        return bool(self.__pydantic_extra__ and key in self.__pydantic_extra__)


class WeeklyCalendar(BaseModel):
    week_start: str  # ISO-8601 date of Monday
    week_end: str  # ISO-8601 date of Sunday
    posts: List[ScheduledPost]
    total_posts: int
    format_counts: Dict[str, int]  # e.g. {"short_video": 3}
    topics_used: List[str]  # unique topic_ids
    generated_at: str
    config_snapshot: PublishingConfigSnapshot = Field(default_factory=PublishingConfigSnapshot)