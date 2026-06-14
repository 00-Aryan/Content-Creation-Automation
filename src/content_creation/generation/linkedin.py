import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from content_creation.domains.storyboard.model import Storyboard
from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief
from content_creation.models.linkedin import LinkedInPost
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus

logger = logging.getLogger(__name__)


def _clean_markers(text: str) -> str:
    """Remove structural marker tokens (F), (K), and (C) while preserving normal parenthesis and readable spacing."""
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"\s*\((?:F|K|C)\)", "", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"^[ \t]+|[ \t]+$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[ \t]*\n[ \t]*", "\n", cleaned)
    return cleaned.strip()


class LinkedInPostGenerator:
    """Generate LinkedIn post content from a brief."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        prompt_dir: Optional[Union[Path, PromptRegistry]] = None,
    ):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = prompt_dir if isinstance(prompt_dir, PromptRegistry) else None
        self.prompt_dir = prompt_dir if isinstance(prompt_dir, Path) else None

    def generate(
        self,
        storyboard: Optional[Storyboard],
        brief: Brief,
    ) -> LinkedInPost:
        """Generate a LinkedIn post.

        If storyboard is provided, we can use its visual_metaphor to replace {{ brief.analogy }}.
        """
        if self._registry:
            template = self._registry.get("linkedin", "post")
        else:
            prompt_path = self.prompt_dir / "linkedin_post.md"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            with open(prompt_path, "r") as f:
                template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        if storyboard is not None:
            prompt = prompt.replace("{{ brief.analogy }}", storyboard.visual_metaphor)
        else:
            prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)

        summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])
        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)

        generated_at = datetime.now(timezone.utc).isoformat()

        result = self._manager.generate(
            prompt=prompt, task_type="linkedin_post_generation"
        )

        if result.success:
            try:
                data = json.loads(result.text)
                if "review_status" in data and data["review_status"]:
                    data["review_status"] = ReviewStatus(data["review_status"])
                else:
                    data["review_status"] = ReviewStatus.DRAFT

                # Ensure all required text fields exist in parsed data
                for field in [
                    "hook",
                    "post_body",
                    "takeaway",
                    "cta",
                    "source_reference",
                ]:
                    if field not in data:
                        data[field] = "needs_review"
                    elif isinstance(data[field], str):
                        data[field] = _clean_markers(data[field])

                if "hashtags" not in data:
                    data["hashtags"] = [
                        "#needs_review",
                        "#needs_review",
                        "#needs_review",
                    ]
                if "claims_used" not in data:
                    data["claims_used"] = ["needs_review"]

                data.pop("source_links", None)
                source_links = [brief.source_url]

                post = LinkedInPost(
                    topic_id=brief.topic_id,
                    source_links=source_links,
                    generated_at=generated_at,
                    **data,
                )
                return post
            except Exception as e:
                logger.warning(
                    "Failed to parse LinkedIn post for topic %s: %s",
                    brief.topic_id,
                    e,
                )
        else:
            logger.warning(
                "Inference failed for topic %s: %s",
                brief.topic_id,
                result.error,
            )

        # Fallback
        return LinkedInPost(
            topic_id=brief.topic_id,
            hook="needs_review",
            post_body="needs_review",
            takeaway="needs_review",
            cta="needs_review",
            hashtags=["#needs_review", "#needs_review", "#needs_review"],
            source_reference="needs_review",
            source_links=[brief.source_url],
            claims_used=["needs_review"],
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )
