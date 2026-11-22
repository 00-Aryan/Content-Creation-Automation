"""Service for orchestrating Gemini-based brief generation."""

from dataclasses import dataclass
import logging
import os
import time
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.generation.brief import generate_brief
from content_creation.inference.models import ErrorCategory, ProviderError
from content_creation.models.brief import Brief
from content_creation.models.topic import TopicStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BriefFailure:
    """Represents a failure during brief generation for a topic."""

    topic_id: str
    error: str


@dataclass(frozen=True)
class BriefGenerationResult:
    """Result of the brief generation process."""

    generated_count: int
    skipped_count: int
    failures: List[BriefFailure]
    briefs: List[Brief]


class BriefGenerationService:
    """Service to orchestrate educational brief generation for top-scored topics."""

    def run(
        self,
        ctx: ApplicationContext,
        top_n: int = 5,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 5.0,
        topic_id: Optional[str] = None,
    ) -> BriefGenerationResult:
        """Generates briefs for top scored topics that don't have them yet."""
        scored_items = ctx.storage.list_scored()

        # Filter and sort
        if topic_id:
            items_to_process = [item for item in scored_items if item.id == topic_id]
            if not items_to_process:
                target = ctx.storage.get_scored(topic_id) or ctx.storage.get_staged(topic_id)
                if target:
                    items_to_process = [target]
        else:
            items_to_process = [
                item for item in scored_items if item.status == TopicStatus.SCORED
            ]
            items_to_process.sort(key=lambda x: x.priority_score, reverse=True)
            items_to_process = items_to_process[:top_n]

        if not items_to_process:
            return BriefGenerationResult(
                generated_count=0, skipped_count=0, failures=[], briefs=[]
            )

        generated_briefs = []
        failures = []
        skipped_count = 0

        for item in items_to_process:
            # Skip if brief already exists in storage or on disk
            try:
                existing_brief = ctx.storage.get_brief(item.id)
                if existing_brief is not None and isinstance(existing_brief, Brief):
                    skipped_count += 1
                    continue
            except Exception as e:
                logger.warning(f"Error checking storage for existing brief {item.id}: {e}")

            brief_file = ctx.storage.briefs_dir / f"{item.id}.json"
            if brief_file.exists():
                skipped_count += 1
                continue

            try:
                brief = generate_brief(item, ctx.prompt_registry, api_key)

                # Ensure manual topics always include script in recommended_formats
                is_manual = (
                    getattr(item, "source", None) == "manual"
                    or "manual" in getattr(item, "topic_tags", [])
                    or (hasattr(item, "metadata") and item.metadata and getattr(item.metadata, "source_type", None) == "manual")
                )
                if is_manual:
                    has_script = any(fmt in {"script", "short_video", "video"} for fmt in brief.recommended_formats)
                    if not has_script:
                        brief.recommended_formats.append("script")

                # Check topic_id mismatch
                if brief.topic_id != item.id:
                    failures.append(
                        BriefFailure(
                            topic_id=item.id,
                            error=f"Generated brief topic_id mismatch: expected {item.id}, got {brief.topic_id}",
                        )
                    )
                    continue

                try:
                    ctx.storage.save_brief(brief)
                    generated_briefs.append(brief)
                except Exception as e:
                    if "Target asset file is already populated" in str(e):
                        existing_brief = ctx.storage.get_brief(item.id)
                        if existing_brief is not None:
                            skipped_count += 1
                            continue
                    logger.error(f"Error saving brief for {item.id}: {e}")
                    failures.append(BriefFailure(topic_id=item.id, error=str(e)))
            except Exception as e:
                logger.error(f"Error generating brief for {item.id}: {e}")
                failures.append(BriefFailure(topic_id=item.id, error=str(e)))
                prov_err = getattr(e, "provider_error", None)
                nested_err = getattr(e, "error", None)
                is_auth_error = (
                    getattr(e, "category", None) == ErrorCategory.AUTH
                    or (isinstance(prov_err, ProviderError) and prov_err.category == ErrorCategory.AUTH)
                    or (isinstance(nested_err, ProviderError) and nested_err.category == ErrorCategory.AUTH)
                    or "API_KEY_INVALID" in str(e).upper()
                    or "API key not found" in str(e)
                    or getattr(e, "code", None) in (401, 403)
                )
                if is_auth_error:
                    logger.warning(
                        f"Non-retryable authentication failure encountered for {item.id}; "
                        "aborting remaining brief generation batch."
                    )
                    break

            # Respect free-tier limits if there are more items to process
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)

        return BriefGenerationResult(
            generated_count=len(generated_briefs),
            skipped_count=skipped_count,
            failures=failures,
            briefs=generated_briefs,
        )
