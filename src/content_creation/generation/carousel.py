import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief
from content_creation.domains.storyboard.model import Storyboard
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus
from content_creation.models.carousel import Carousel, CarouselSlide

logger = logging.getLogger(__name__)


class CarouselGenerator:
    """Generate carousel content from a brief."""

    def __init__(self, api_key: Optional[str] = None, prompt_dir: Optional[Union[Path, PromptRegistry]] = None):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = prompt_dir if isinstance(prompt_dir, PromptRegistry) else None
        self.prompt_dir = prompt_dir if isinstance(prompt_dir, Path) else None

    def generate(
        self,
        storyboard: Optional[Storyboard],
        brief: Brief,
    ) -> Carousel:
        """Generate a carousel.

        Storyboard is the primary layout planner, and Brief is the auxiliary content.
        If storyboard is None, fallback to legacy/brief-only mode is executed.
        """
        if self._registry:
            template = self._registry.get("carousel", "carousel")
        else:
            prompt_path = self.prompt_dir / "carousel.md"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            with open(prompt_path, "r") as f:
                template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        if storyboard is not None:
            summary_bullets = "\n".join([f"- {s}" for s in storyboard.carousel_claims])
            prompt = prompt.replace("{{ brief.analogy }}", storyboard.visual_metaphor)
        else:
            summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])
            prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)

        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
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
                carousel = Carousel(
                    topic_id=brief.topic_id,
                    slides=slides,
                    source_links=source_links,
                    generated_at=generated_at,
                    **data,
                )

                if storyboard is not None:
                    # Storyboard override: authoritative values for owned fields
                    updated_slides = list(carousel.slides)
                    if updated_slides:
                        updated_slides[0] = updated_slides[0].model_copy(update={
                            "title": storyboard.carousel_hook
                        })
                    carousel = carousel.model_copy(update={
                        "slides": updated_slides,
                        "cta_slide": storyboard.carousel_cta,
                        "claims_used": storyboard.carousel_claims,
                    })

                return carousel
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

        if storyboard is not None:
            return Carousel(
                topic_id=brief.topic_id,
                slides=[
                    CarouselSlide(
                        slide_number=1,
                        title=storyboard.carousel_hook,
                        body="needs_review",
                        visual_note=storyboard.visual_metaphor,
                    )
                ],
                cta_slide=storyboard.carousel_cta,
                claims_used=storyboard.carousel_claims,
                source_links=[brief.source_url],
                review_status=ReviewStatus.NEEDS_REVIEW,
                generated_at=generated_at,
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
