from pydantic import BaseModel
from typing import List
from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId


class CarouselSlide(BaseModel):
    slide_number: int
    title: str
    body: str
    visual_note: str


class Carousel(BaseModel):
    topic_id: TopicId
    slides: List[CarouselSlide]
    cta_slide: str
    claims_used: List[str]
    source_links: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str