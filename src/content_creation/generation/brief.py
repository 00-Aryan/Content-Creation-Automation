import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief, ReviewStatus
from content_creation.models.topic import ScoredTopicItem

logger = logging.getLogger(__name__)


def generate_brief(item: ScoredTopicItem, prompt_path: Path, api_key: str) -> Brief:
    """Generate a brief for a scored topic using the inference manager."""

    if not item.raw_text or len(item.raw_text) < 100:
        raise ValueError(
            f"Raw text is too short ({len(item.raw_text) if item.raw_text else 0} chars). Minimum 100 required."
        )

    # Truncate input to respect token limits
    truncated_text = item.raw_text[:15000]

    # Read prompt template
    with open(prompt_path, "r") as f:
        template = f.read()

    # Replace placeholders
    prompt = template.replace("{{ topic.title }}", item.title)
    prompt = prompt.replace("{{ topic.source }}", item.source)
    prompt = prompt.replace("{{ topic.url }}", item.url)
    prompt = prompt.replace("{{ topic.raw_text }}", truncated_text)

    generated_at = datetime.now(timezone.utc).isoformat()

    # Use inference manager instead of direct SDK call
    manager = InferenceManager(api_key=api_key)
    result = manager.generate(prompt=prompt, task_type="brief_generation")

    if result.success:
        try:
            data = json.loads(result.text)
            if "review_status" in data:
                data["review_status"] = ReviewStatus(data["review_status"])
            return Brief(
                topic_id=item.id,
                source_url=item.url,
                generated_at=generated_at,
                **data,
            )
        except Exception as e:
            logger.warning(f"Failed to parse brief for topic {item.id}: {e}")
    else:
        logger.warning(f"Inference failed for topic {item.id}: {result.error}")

    # Fallback for failures
    return Brief(
        topic_id=item.id,
        why_it_matters="needs_review",
        plain_english_summary=["needs_review", "needs_review", "needs_review"],
        student_takeaway="needs_review",
        analogy="needs_review",
        limitation="needs_review",
        audience_fit="needs_review",
        recommended_formats=["needs_review"],
        source_url=item.url,
        review_status=ReviewStatus.NEEDS_REVIEW,
        generated_at=generated_at,
    )
