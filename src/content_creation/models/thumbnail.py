from pydantic import BaseModel
from typing import List, Literal

from .brief import ReviewStatus


class ThumbnailPrompt(BaseModel):
    topic_id: str
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
