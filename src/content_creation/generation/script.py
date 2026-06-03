import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief
from content_creation.domains.storyboard.model import Storyboard
from content_creation.models.script import Script
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus

logger = logging.getLogger(__name__)

_VALID_FORMATS = frozenset({"short_video", "carousel", "newsletter"})


class ScriptGenerator:
    """Generate scripts from a brief using per-format prompt templates."""

    def __init__(self, api_key: str, prompt_dir: Union[Path, PromptRegistry]):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = prompt_dir if isinstance(prompt_dir, PromptRegistry) else None
        self.prompt_dir = prompt_dir if isinstance(prompt_dir, Path) else None

    def generate(
        self,
        storyboard: Optional[Storyboard],
        brief: Brief,
        format: str,
    ) -> Script:
        """Generate a script for ``brief`` using the prompt for ``format``."""
        if format not in _VALID_FORMATS:
            raise ValueError(
                f"Invalid format {format!r}. Must be one of: "
                f"{', '.join(sorted(_VALID_FORMATS))}"
            )

        if self._registry:
            template = self._registry.get("script", format)
        else:
            prompt_path = self.prompt_dir / f"{format}.md"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            with open(prompt_path, "r") as f:
                template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        if storyboard is not None:
            prompt = prompt.replace("{{ brief.analogy }}", storyboard.visual_metaphor)
            if format == "short_video":
                claims = storyboard.script_claims
            elif format == "carousel":
                claims = storyboard.carousel_claims
            else:  # newsletter
                claims = storyboard.newsletter_claims
            summary_bullets = "\n".join([f"- {s}" for s in claims])
        else:
            prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)
            summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])

        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)

        generated_at = datetime.now(timezone.utc).isoformat()

        result = self._manager.generate(prompt=prompt, task_type="script_generation")

        if result.success:
            try:
                data = json.loads(result.text)
                if "review_status" in data:
                    data["review_status"] = ReviewStatus(data["review_status"])
                data.pop("source_links", None)
                source_links = [brief.source_url]
                script = Script(
                    topic_id=brief.topic_id,
                    format=format,
                    source_links=source_links,
                    generated_at=generated_at,
                    **data,
                )

                if storyboard is not None:
                    if format == "short_video":
                        hook_val = storyboard.script_hook
                        cta_val = storyboard.script_cta
                        claims_val = storyboard.script_claims
                    elif format == "carousel":
                        hook_val = storyboard.carousel_hook
                        cta_val = storyboard.carousel_cta
                        claims_val = storyboard.carousel_claims
                    else:  # newsletter
                        hook_val = storyboard.newsletter_hook
                        cta_val = storyboard.newsletter_cta
                        claims_val = storyboard.newsletter_claims

                    script = script.model_copy(update={
                        "hook": hook_val,
                        "cta": cta_val,
                        "claims_used": claims_val,
                    })

                return script
            except Exception as e:
                logger.warning(
                    "Failed to parse script for topic %s: %s",
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
            if format == "short_video":
                hook_val = storyboard.script_hook
                cta_val = storyboard.script_cta
                claims_val = storyboard.script_claims
            elif format == "carousel":
                hook_val = storyboard.carousel_hook
                cta_val = storyboard.carousel_cta
                claims_val = storyboard.carousel_claims
            else:  # newsletter
                hook_val = storyboard.newsletter_hook
                cta_val = storyboard.newsletter_cta
                claims_val = storyboard.newsletter_claims

            return Script(
                topic_id=brief.topic_id,
                format=format,
                hook=hook_val,
                script_sections=[
                    "needs_review",
                    "needs_review",
                    "needs_review",
                    "needs_review",
                ],
                cta=cta_val,
                claims_used=claims_val,
                source_links=[brief.source_url],
                review_status=ReviewStatus.NEEDS_REVIEW,
                generated_at=generated_at,
            )

        return Script(
            topic_id=brief.topic_id,
            format=format,
            hook="needs_review",
            script_sections=[
                "needs_review",
                "needs_review",
                "needs_review",
                "needs_review",
            ],
            cta="needs_review",
            claims_used=["needs_review"],
            source_links=[brief.source_url],
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )
