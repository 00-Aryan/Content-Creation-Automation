from pydantic import BaseModel
from typing import List, Literal
from .brief import ReviewStatus


class NewsletterSection(BaseModel):
    section_name: Literal["what_happened", "why_it_matters", "student_takeaway"]
    content: str


class Newsletter(BaseModel):
    topic_id: str
    subject_line: str
    sections: List[NewsletterSection]
    cta: str
    claims_used: List[str]
    source_links: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str