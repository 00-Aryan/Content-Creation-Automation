from pydantic import BaseModel
from typing import List
from .brief import ReviewStatus


class CarouselSlide(BaseModel):
    slide_number: int
    title: str
    body: str
    visual_note: str


class Carousel(BaseModel):
    topic_id: str
    slides: List[CarouselSlide]
    cta_slide: str
    claims_used: List[str]
    source_links: List[str]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str