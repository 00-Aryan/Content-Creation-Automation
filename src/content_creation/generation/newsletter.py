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
from content_creation.models.newsletter import Newsletter, NewsletterSection

logger = logging.getLogger(__name__)


class NewsletterGenerator:
    """Generate newsletter content from a brief."""

    def __init__(self, api_key: str, prompt_dir: Union[Path, PromptRegistry]):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = prompt_dir if isinstance(prompt_dir, PromptRegistry) else None
        self.prompt_dir = prompt_dir if isinstance(prompt_dir, Path) else None

    def generate(
        self,
        storyboard: Optional[Storyboard],
        brief: Brief,
    ) -> Newsletter:
        """Generate a newsletter.

        Storyboard is the primary layout planner, and Brief is the auxiliary content.
        If storyboard is None, fallback to legacy/brief-only mode is executed.
        """
        if self._registry:
            template = self._registry.get("newsletter", "newsletter")
        else:
            prompt_path = self.prompt_dir / "newsletter.md"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            with open(prompt_path, "r") as f:
                template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        if storyboard is not None:
            summary_bullets = "\n".join([f"- {s}" for s in storyboard.newsletter_claims])
            prompt = prompt.replace("{{ brief.analogy }}", storyboard.visual_metaphor)
        else:
            summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])
            prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)

        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)

        formats_list = "\n".join([f"- {fmt}" for fmt in brief.recommended_formats])
        prompt = prompt.replace("{{ brief.recommended_formats }}", formats_list)

        generated_at = datetime.now(timezone.utc).isoformat()

        result = self._manager.generate(prompt=prompt, task_type="newsletter_generation")

        if result.success:
            try:
                data = json.loads(result.text)
                if "review_status" in data:
                    data["review_status"] = ReviewStatus(data["review_status"])
                data.pop("source_links", None)
                sections_data = data.pop("sections", [])
                sections = [NewsletterSection(**section) for section in sections_data]
                source_links = [brief.source_url]
                newsletter = Newsletter(
                    topic_id=brief.topic_id,
                    sections=sections,
                    source_links=source_links,
                    generated_at=generated_at,
                    **data,
                )

                if storyboard is not None:
                    # Storyboard override: authoritative values for owned fields
                    newsletter = newsletter.model_copy(update={
                        "subject_line": storyboard.newsletter_hook,
                        "cta": storyboard.newsletter_cta,
                        "claims_used": storyboard.newsletter_claims,
                    })

                return newsletter
            except Exception as e:
                logger.warning(
                    "Failed to parse newsletter for topic %s: %s",
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
            return Newsletter(
                topic_id=brief.topic_id,
                subject_line=storyboard.newsletter_hook,
                sections=[
                    NewsletterSection(section_name="what_happened", content="needs_review"),
                    NewsletterSection(section_name="why_it_matters", content="needs_review"),
                    NewsletterSection(
                        section_name="student_takeaway", content="needs_review"
                    ),
                ],
                cta=storyboard.newsletter_cta,
                claims_used=storyboard.newsletter_claims,
                source_links=[brief.source_url],
                review_status=ReviewStatus.NEEDS_REVIEW,
                generated_at=generated_at,
            )

        return Newsletter(
            topic_id=brief.topic_id,
            subject_line="needs_review",
            sections=[
                NewsletterSection(section_name="what_happened", content="needs_review"),
                NewsletterSection(section_name="why_it_matters", content="needs_review"),
                NewsletterSection(
                    section_name="student_takeaway", content="needs_review"
                ),
            ],
            cta="needs_review",
            claims_used=["needs_review"],
            source_links=[brief.source_url],
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )
