"""Storyboard v1 generator."""

import json
import logging
from datetime import datetime, timezone
from typing import List

from content_creation.domains.content_intelligence.model import ContentIntelligence, TopicType
from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus

from .model import Storyboard

logger = logging.getLogger(__name__)

# Deterministic: topic_type → visual_style
_STYLE_MAP = {
    TopicType.PAPER: "diagram_overlay",
    TopicType.REPO: "bold_typographic",
    TopicType.RELEASE: "bold_typographic",
    TopicType.CONCEPT: "metaphor_illustration",
    TopicType.NEWS: "bold_typographic",
    TopicType.TOOL: "bold_typographic",
    TopicType.UNKNOWN: "clean_minimal",
}

# Normalize free-text formats to canonical names
_FORMAT_NORMALIZE = {
    "lecture": "short_video",
    "video": "short_video",
    "short video": "short_video",
    "technical deep dive": "short_video",
    "technical presentation": "short_video",
    "research paper summary": "short_video",
    "research seminar": "short_video",
    "theoretical lecture": "short_video",
    "concept deep dive": "short_video",
    "case study": "carousel",
    "infographic": "carousel",
    "visual guide": "carousel",
    "dataset walkthrough and tutorial": "carousel",
    "interactive simulation demo": "carousel",
    "workshop on compositional vlm evaluation": "carousel",
    "system design discussion": "carousel",
    "research paper discussion": "short_video",
    "journal club": "newsletter",
    "email": "newsletter",
    "blog": "newsletter",
}

_VALID_FORMATS = {"short_video", "carousel", "newsletter"}


def _normalize_formats(raw_formats: List[str]) -> List[str]:
    """Normalize Brief.recommended_formats to canonical format names."""
    result = set()
    for fmt in raw_formats:
        lower = fmt.lower().strip()
        if lower in _VALID_FORMATS:
            result.add(lower)
        elif lower in _FORMAT_NORMALIZE:
            result.add(_FORMAT_NORMALIZE[lower])
        elif lower != "needs_review":
            result.add("short_video")  # fallback
    return sorted(result) if result else ["short_video"]


def _resolve_visual_metaphor(brief: Brief, ci: ContentIntelligence) -> str:
    """Pick visual metaphor from Brief.analogy or CI.contrast_pair."""
    if brief.analogy and brief.analogy != "needs_review":
        return brief.analogy
    return f"{ci.contrast_pair.before} → {ci.contrast_pair.after}"


class StoryboardGenerator:
    """Generate Storyboard from Brief + ContentIntelligence."""

    def __init__(self, api_key: str, registry: PromptRegistry):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = registry

    def generate(self, brief: Brief, ci: ContentIntelligence) -> Storyboard:
        """Produce a Storyboard. Deterministic fields computed in code, rest via LLM."""
        generated_at = datetime.now(timezone.utc).isoformat()

        # Deterministic fields
        visual_style = _STYLE_MAP.get(ci.topic_type, "clean_minimal")
        visual_metaphor = _resolve_visual_metaphor(brief, ci)
        formats_planned = _normalize_formats(brief.recommended_formats)

        # Pass-through hooks
        script_hook = ci.primary_hook.hook_text
        carousel_hook = ci.secondary_hook.hook_text
        newsletter_hook = ci.curiosity_gap

        # LLM call for: thumbnail_hook, 3 CTAs, claim allocation
        template = self._registry.get("storyboard", "generate")
        prompt = template.replace("{{ ci.primary_hook }}", ci.primary_hook.hook_text)
        prompt = prompt.replace("{{ ci.story_angle }}", ci.story_angle)
        prompt = prompt.replace("{{ formats_planned }}", ", ".join(formats_planned))
        claims = "\n".join(f"- {s}" for s in brief.plain_english_summary)
        prompt = prompt.replace("{{ brief.claims }}", claims)

        result = self._manager.generate(prompt=prompt, task_type="storyboard")

        if result.success:
            try:
                data = json.loads(result.text)
                return Storyboard(
                    topic_id=brief.topic_id,
                    generated_at=generated_at,
                    review_status=ReviewStatus.DRAFT,
                    formats_planned=formats_planned,
                    script_hook=script_hook,
                    carousel_hook=carousel_hook,
                    newsletter_hook=newsletter_hook,
                    thumbnail_hook=data["thumbnail_hook"],
                    script_cta=data["script_cta"],
                    carousel_cta=data["carousel_cta"],
                    newsletter_cta=data["newsletter_cta"],
                    script_claims=data["script_claims"],
                    carousel_claims=data["carousel_claims"],
                    newsletter_claims=data["newsletter_claims"],
                    visual_style=visual_style,
                    visual_metaphor=visual_metaphor,
                )
            except Exception as e:
                logger.warning("Failed to parse Storyboard for %s: %s", brief.topic_id, e)
        else:
            logger.warning("Storyboard inference failed for %s: %s", brief.topic_id, result.error)

        # Fallback
        all_claims = brief.plain_english_summary
        return Storyboard(
            topic_id=brief.topic_id,
            generated_at=generated_at,
            review_status=ReviewStatus.NEEDS_REVIEW,
            formats_planned=formats_planned,
            script_hook=script_hook,
            carousel_hook=carousel_hook,
            newsletter_hook=newsletter_hook,
            thumbnail_hook="needs_review",
            script_cta="needs_review",
            carousel_cta="needs_review",
            newsletter_cta="needs_review",
            script_claims=all_claims,
            carousel_claims=all_claims,
            newsletter_claims=all_claims,
            visual_style=visual_style,
            visual_metaphor=visual_metaphor,
        )
