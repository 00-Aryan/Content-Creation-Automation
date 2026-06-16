from typing import List

from pydantic import BaseModel, field_validator

from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId


class LinkedInPost(BaseModel):
    topic_id: TopicId
    hook: str
    post_body: str
    takeaway: str
    cta: str
    hashtags: List[str]
    source_reference: str
    source_links: List[str]
    claims_used: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str

    @field_validator("hashtags")
    @classmethod
    def must_have_three_to_five_items(cls, v):
        if not (3 <= len(v) <= 5):
            raise ValueError("hashtags must have between 3 and 5 items")
        return v
