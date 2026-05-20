import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief, ReviewStatus
from content_creation.models.carousel import Carousel, CarouselSlide

logger = logging.getLogger(__name__)


class CarouselGenerator:
    """Generate carousel content from a brief."""

    def __init__(self, api_key: str, prompt_dir: Path):
        self._manager = InferenceManager(api_key=api_key)
        self.prompt_dir = prompt_dir
        self.prompt_path = prompt_dir / "carousel.md"
        if not self.prompt_path.exists():
            logger.warning(
                "Prompt template not found: %s",
                self.prompt_path,
            )

    def generate(self, brief: Brief) -> Carousel:
        """Generate a carousel for ``brief``."""
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_path}")

        with open(self.prompt_path, "r") as f:
            template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])
        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)

        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)

        generated_at = datetime.now(timezone.utc).isoformat()

        result = self._manager.generate(prompt=prompt, task_type="carousel_generation")

        if result.success:
            try:
                data = json.loads(result.text)
                if "review_status" in data:
                    data["review_status"] = ReviewStatus(data["review_status"])
                data.pop("source_links", None)
                slides_data = data.pop("slides", [])
                slides = [CarouselSlide(**slide) for slide in slides_data]
                source_links = [brief.source_url]
                return Carousel(
                    topic_id=brief.topic_id,
                    slides=slides,
                    source_links=source_links,
                    generated_at=generated_at,
                    **data,
                )
            except Exception as e:
                logger.warning(
                    "Failed to parse carousel for topic %s: %s",
                    brief.topic_id,
                    e,
                )
        else:
            logger.warning(
                "Inference failed for topic %s: %s",
                brief.topic_id,
                result.error,
            )

        return Carousel(
            topic_id=brief.topic_id,
            slides=[
                CarouselSlide(
                    slide_number=1,
                    title="needs_review",
                    body="needs_review",
                    visual_note="needs_review",
                )
            ],
            cta_slide="needs_review",
            claims_used=["needs_review"],
            source_links=[brief.source_url],
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )
