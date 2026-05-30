"""Content Intelligence v1 model."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel

from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId


class TopicType(str, Enum):
    PAPER = "paper"
    REPO = "repo"
    RELEASE = "release"
    CONCEPT = "concept"
    NEWS = "news"
    TOOL = "tool"
    UNKNOWN = "unknown"


class EmotionalRegister(str, Enum):
    AWE = "awe"
    URGENCY = "urgency"
    SURPRISE = "surprise"
    CLARITY = "clarity"
    CONCERN = "concern"
    EXCITEMENT = "excitement"


HookType = Literal["question", "bold_claim", "contrast", "statistic"]


class Hook(BaseModel):
    hook_text: str
    hook_type: HookType
    source_field: str


class ContrastPair(BaseModel):
    before: str
    after: str


class ContentIntelligence(BaseModel):
    # Identity
    topic_id: TopicId
    generated_at: str
    review_status: ReviewStatus = ReviewStatus.DRAFT

    # Quality assessment (additive — Optional for backward compat with existing stored data)
    quality_status: Optional[str] = None  # "ready" | "degraded" | "blocked"

    # Deterministic
    topic_type: TopicType
    timeliness_hook: str  # empty string if evergreen

    # LLM-generated
    primary_hook: Hook
    secondary_hook: Hook
    story_angle: str
    curiosity_gap: str
    contrast_pair: ContrastPair
    emotional_register: EmotionalRegister
