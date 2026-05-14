"""TopicItem model and schema definitions."""

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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


class TopicItem(BaseModel):
    """Canonical TopicItem schema for Week 1."""
    id: str
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
    metadata: Dict[str, Any] = Field(default_factory=dict)

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
    scoring_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    scoring_rules_fired: List[str] = Field(default_factory=list)
    validation_flags: List[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def set_scored_status(cls, v: TopicStatus) -> TopicStatus:
        """Ensure status is set to SCORED if it was RAW or STAGED."""
        if v in (TopicStatus.RAW, TopicStatus.STAGED):
            return TopicStatus.SCORED
        return v
