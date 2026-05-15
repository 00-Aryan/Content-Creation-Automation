from pydantic import BaseModel
from typing import List, Literal
from .brief import ReviewStatus


class Script(BaseModel):
    topic_id: str
    format: Literal["short_video", "carousel", "newsletter"]
    hook: str
    script_sections: List[str]
    cta: str
    claims_used: List[str]
    source_links: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str