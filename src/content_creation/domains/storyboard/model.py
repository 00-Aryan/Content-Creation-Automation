"""Storyboard v1 model — flat schema, frozen."""

from typing import List, Literal, Optional

from pydantic import BaseModel

from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId

VisualStyle = Literal[
    "clean_minimal",
    "bold_typographic",
    "diagram_overlay",
    "metaphor_illustration",
]


class Storyboard(BaseModel):
    topic_id: TopicId
    generated_at: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    review_notes: Optional[str] = None
    formats_planned: List[str]
    # Hooks
    script_hook: str
    carousel_hook: str
    newsletter_hook: str
    thumbnail_hook: str
    # CTAs
    script_cta: str
    carousel_cta: str
    newsletter_cta: str
    # Claims
    script_claims: List[str]
    carousel_claims: List[str]
    newsletter_claims: List[str]
    # Visual
    visual_style: VisualStyle
    visual_metaphor: str
