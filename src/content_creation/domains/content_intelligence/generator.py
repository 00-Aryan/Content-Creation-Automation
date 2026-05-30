"""Content Intelligence generator."""

import json
import logging
from datetime import datetime, timezone

from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief
from content_creation.models.topic import TopicCategory
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus

from .model import (
    ContentIntelligence,
    ContrastPair,
    EmotionalRegister,
    Hook,
    TopicType,
)
from .quality import QualityStatus, evaluate_brief_quality

logger = logging.getLogger(__name__)

# Deterministic mapping from TopicCategory to TopicType
_CATEGORY_TO_TYPE = {
    TopicCategory.PAPER: TopicType.PAPER,
    TopicCategory.REPO: TopicType.REPO,
    TopicCategory.RELEASE: TopicType.RELEASE,
    TopicCategory.CONCEPT: TopicType.CONCEPT,
    TopicCategory.NEWS: TopicType.NEWS,
    TopicCategory.TOOL: TopicType.TOOL,
    TopicCategory.UNKNOWN: TopicType.UNKNOWN,
}


def _compute_timeliness(published_at: str) -> str:
    """Return timeliness hook if published within 7 days, else empty."""
    if not published_at or published_at == "unknown":
        return ""
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if (now - pub).days <= 7:
            return "Published this week"
    except (ValueError, TypeError):
        pass
    return ""


class ContentIntelligenceGenerator:
    """Generate Content Intelligence from a Brief."""

    def __init__(self, api_key: str, registry: PromptRegistry):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = registry

    def generate(
        self,
        brief: Brief,
        topic_category: TopicCategory = TopicCategory.UNKNOWN,
        published_at: str = "unknown",
    ) -> ContentIntelligence:
        """Generate CI for a Brief. Deterministic fields computed in code."""
        topic_type = _CATEGORY_TO_TYPE.get(topic_category, TopicType.UNKNOWN)
        timeliness_hook = _compute_timeliness(published_at)
        generated_at = datetime.now(timezone.utc).isoformat()

        quality_status = evaluate_brief_quality(brief)

        # Block generation if Brief is too degraded
        if quality_status == QualityStatus.BLOCKED:
            logger.warning("CI blocked for %s: insufficient Brief quality", brief.topic_id)
            return ContentIntelligence(
                topic_id=brief.topic_id,
                generated_at=generated_at,
                review_status=ReviewStatus.NEEDS_REVIEW,
                quality_status=quality_status,
                topic_type=topic_type,
                timeliness_hook=timeliness_hook,
                primary_hook=Hook(hook_text="needs_review", hook_type="bold_claim", source_field="unknown"),
                secondary_hook=Hook(hook_text="needs_review", hook_type="question", source_field="unknown"),
                story_angle="needs_review",
                curiosity_gap="needs_review",
                contrast_pair=ContrastPair(before="needs_review", after="needs_review"),
                emotional_register=EmotionalRegister.CLARITY,
            )

        template = self._registry.get("content_intelligence", "generate")

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)
        summary = "\n".join(f"- {s}" for s in brief.plain_english_summary)
        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary)
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)

        result = self._manager.generate(
            prompt=prompt, task_type="content_intelligence"
        )

        if result.success:
            try:
                data = json.loads(result.text)
                return ContentIntelligence(
                    topic_id=brief.topic_id,
                    generated_at=generated_at,
                    review_status=ReviewStatus.DRAFT,
                    quality_status=quality_status,
                    topic_type=topic_type,
                    timeliness_hook=timeliness_hook,
                    primary_hook=Hook(**data["primary_hook"]),
                    secondary_hook=Hook(**data["secondary_hook"]),
                    story_angle=data["story_angle"],
                    curiosity_gap=data["curiosity_gap"],
                    contrast_pair=ContrastPair(**data["contrast_pair"]),
                    emotional_register=EmotionalRegister(data["emotional_register"]),
                )
            except Exception as e:
                logger.warning("Failed to parse CI for %s: %s", brief.topic_id, e)
        else:
            logger.warning("CI inference failed for %s: %s", brief.topic_id, result.error)

        # Fallback
        return ContentIntelligence(
            topic_id=brief.topic_id,
            generated_at=generated_at,
            review_status=ReviewStatus.NEEDS_REVIEW,
            quality_status=quality_status,
            topic_type=topic_type,
            timeliness_hook=timeliness_hook,
            primary_hook=Hook(hook_text="needs_review", hook_type="bold_claim", source_field="unknown"),
            secondary_hook=Hook(hook_text="needs_review", hook_type="question", source_field="unknown"),
            story_angle="needs_review",
            curiosity_gap="needs_review",
            contrast_pair=ContrastPair(before="needs_review", after="needs_review"),
            emotional_register=EmotionalRegister.CLARITY,
        )
