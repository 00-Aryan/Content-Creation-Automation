from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List
from enum import Enum

class ReviewStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"

class Brief(BaseModel):
    topic_id: str
    why_it_matters: str
    plain_english_summary: List[str]
    student_takeaway: str
    analogy: str
    limitation: str
    audience_fit: str
    recommended_formats: List[str]
    source_url: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str

    @field_validator("plain_english_summary")
    @classmethod
    def must_have_three_items(cls, v):
        if len(v) != 3:
            raise ValueError("plain_english_summary must have exactly 3 items")
        return v
