from pydantic import BaseModel
from typing import List, Literal

from content_creation.shared.enums import ReviewStatus
from content_creation.shared.types import TopicId


class ThumbnailPrompt(BaseModel):
    topic_id: TopicId
    title_text: str
    supporting_text: str
    visual_metaphor: str
    style: Literal[
        "clean_minimal",
        "bold_typographic",
        "diagram_overlay",
        "metaphor_illustration",
    ]
    negative_prompt: List[str]
    readability_notes: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    generated_at: str
