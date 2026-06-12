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
from content_creation.models.thumbnail import ThumbnailPrompt

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Generate thumbnail prompts from a brief."""

    def __init__(self, api_key: Optional[str] = None, prompt_dir: Optional[Union[Path, PromptRegistry]] = None):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = prompt_dir if isinstance(prompt_dir, PromptRegistry) else None
        self.prompt_dir = prompt_dir if isinstance(prompt_dir, Path) else None

    def generate(
        self,
        storyboard: Optional[Storyboard],
        brief: Brief,
    ) -> ThumbnailPrompt:
        """Generate a thumbnail prompt.

        Storyboard is the primary layout planner, and Brief is the auxiliary content.
        If storyboard is None, fallback to legacy/brief-only mode is executed.
        """
        if self._registry:
            template = self._registry.get("thumbnail", "thumbnail")
        else:
            prompt_path = self.prompt_dir / "thumbnail.md"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            with open(prompt_path, "r") as f:
                template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])
        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)

        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)

        # Map analogy to storyboard's visual metaphor under new flow
        if storyboard is not None:
            prompt = prompt.replace("{{ brief.analogy }}", storyboard.visual_metaphor)
        else:
            prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)

        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)

        generated_at = datetime.now(timezone.utc).isoformat()

        result = self._manager.generate(prompt=prompt, task_type="thumbnail_generation")

        if result.success:
            try:
                data = json.loads(result.text)
                if "review_status" in data:
                    data["review_status"] = ReviewStatus(data["review_status"])

                thumb = ThumbnailPrompt(
                    topic_id=brief.topic_id,
                    generated_at=generated_at,
                    **data,
                )

                # Storyboard override: authoritative values for owned fields
                if storyboard is not None:
                    thumb = thumb.model_copy(update={
                        "title_text": storyboard.thumbnail_hook,
                        "style": storyboard.visual_style,
                        "visual_metaphor": storyboard.visual_metaphor,
                    })

                return thumb
            except Exception as e:
                logger.warning(
                    "Failed to parse thumbnail for topic %s: %s",
                    brief.topic_id,
                    e,
                )
        else:
            logger.warning(
                "Inference failed for topic %s: %s",
                brief.topic_id,
                result.error,
            )

        # Fallback — use Storyboard values if available, else defaults
        if storyboard is not None:
            return ThumbnailPrompt(
                topic_id=brief.topic_id,
                title_text=storyboard.thumbnail_hook,
                supporting_text=storyboard.carousel_hook or "Pending supporting text review",
                visual_metaphor=storyboard.visual_metaphor,
                style=storyboard.visual_style,
                negative_prompt=["low quality", "blurry", "cluttered background", "unreadable text"],
                readability_notes="Fallback generated due to inference failure. Review design style and text contrast.",
                review_status=ReviewStatus.NEEDS_REVIEW,
                generated_at=generated_at,
            )

        return ThumbnailPrompt(
            topic_id=brief.topic_id,
            title_text="Pending title review",
            supporting_text="Pending supporting text review",
            visual_metaphor="Pending visual metaphor review",
            style="clean_minimal",
            negative_prompt=["low quality", "blurry", "cluttered background", "unreadable text"],
            readability_notes="Fallback generated due to inference failure. Review design style and text contrast.",
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )
