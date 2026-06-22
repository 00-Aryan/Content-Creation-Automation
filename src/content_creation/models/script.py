from typing import Any, List, Literal

from pydantic import BaseModel, Field, field_validator

from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId

ScriptFormat = Literal["short_video", "carousel", "newsletter"]


class YouTubeShortsSegment(BaseModel):
    section: Literal["hook", "context", "explanation", "payoff", "cta"]
    time_range: str
    visual: str
    audio: str
    spoken: str

    @field_validator(
        "section", "time_range", "visual", "audio", "spoken", mode="before"
    )
    @classmethod
    def val_non_empty_str(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("String cannot be empty or whitespace only")
        return stripped


class Script(BaseModel):
    topic_id: TopicId
    format: ScriptFormat
    hook: str
    script_sections: List[str]
    cta: str
    claims_used: List[str]
    source_links: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str
    shorts_segments: List[YouTubeShortsSegment] = Field(default_factory=list)
