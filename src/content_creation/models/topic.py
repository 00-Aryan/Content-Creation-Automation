"""TopicItem model and schema definitions."""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from content_creation.shared.types import TopicId


class TopicStatus(str, Enum):
    """Possible statuses for a TopicItem."""
    RAW = "raw"
    STAGED = "staged"
    SCORED = "scored"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW = "review"


class TopicCategory(str, Enum):
    """Categories for topics as defined in Week 1 schema."""
    PAPER = "paper"
    REPO = "repo"
    RELEASE = "release"
    CONCEPT = "concept"
    NEWS = "news"
    TOOL = "tool"
    UNKNOWN = "unknown"


class TopicMetadata(BaseModel):
    """Structured topic metadata with dynamic field support (SCHEMA-001, SCHEMA-002)."""
    model_config = ConfigDict(extra="allow")

    source_type: Optional[str] = None
    feed_id: Optional[str] = None
    published_date: Optional[str] = None
    recommended_formats: Optional[List[str]] = None
    student_usefulness_score: Optional[float] = None
    novelty_score: Optional[float] = None
    credibility_score: Optional[float] = None
    explainability_score: Optional[float] = None
    hook_potential_score: Optional[float] = None

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


class TopicItem(BaseModel):
    """Canonical TopicItem schema for Week 1."""
    id: TopicId
    title: str
    url: str
    source: str
    published_at: str  # ISO-8601 string
    author: Optional[str] = "unknown"
    raw_text: str
    excerpt: Optional[str] = "unknown"
    category: TopicCategory = TopicCategory.UNKNOWN
    topic_tags: List[str] = Field(default_factory=list)
    status: TopicStatus = TopicStatus.RAW
    metadata: TopicMetadata = Field(default_factory=TopicMetadata)

    @classmethod
    def generate_id(cls, url: str) -> str:
        """Generate a deterministic ID based on the URL."""
        return hashlib.sha256(url.encode()).hexdigest()

    @field_validator("published_at")
    @classmethod
    def validate_iso_date(cls, v: str) -> str:
        """Ensure published_at is a valid ISO-8601 string."""
        if v == "unknown":
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("published_at must be an ISO-8601 formatted string")

    @field_validator("author", "excerpt", mode="before")
    @classmethod
    def handle_none_and_empty(cls, v: Optional[str]) -> str:
        """Convert None or empty strings to 'unknown'."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return "unknown"
        return v


class ScoredTopicItem(TopicItem):
    """Extended TopicItem with scoring metadata for Week 2."""
    priority_score: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Week 2 categories
    student_usefulness_score: float = Field(default=0.0, ge=0.0, le=100.0)
    novelty_score: float = Field(default=0.0, ge=0.0, le=100.0)
    credibility_score: float = Field(default=0.0, ge=0.0, le=100.0)
    explainability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    hook_potential_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Legacy fields
    recency_score: float = Field(default=0.0, ge=0.0, le=100.0)
    source_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    keyword_score: float = Field(default=0.0, ge=0.0, le=100.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    scoring_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scoring_rules_fired: List[str] = Field(default_factory=list)
    validation_flags: List[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def set_scored_status(cls, v: TopicStatus) -> TopicStatus:
        """Ensure status is set to SCORED if it was RAW or STAGED."""
        if v in (TopicStatus.RAW, TopicStatus.STAGED):
            return TopicStatus.SCORED
        return v
