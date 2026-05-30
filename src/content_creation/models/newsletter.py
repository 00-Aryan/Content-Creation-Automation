from pydantic import BaseModel
from typing import List, Literal
from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId


class NewsletterSection(BaseModel):
    section_name: Literal["what_happened", "why_it_matters", "student_takeaway"]
    content: str


class Newsletter(BaseModel):
    topic_id: TopicId
    subject_line: str
    sections: List[NewsletterSection]
    cta: str
    claims_used: List[str]
    source_links: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str