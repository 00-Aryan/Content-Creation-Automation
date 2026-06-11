"""Service for orchestrating Content Intelligence generation."""

from dataclasses import dataclass
import logging
import os
import time
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.domains.content_intelligence import (
    ContentIntelligence,
    ContentIntelligenceGenerator,
)
from content_creation.models.brief import Brief
from content_creation.models.topic import TopicCategory, TopicStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContentIntelligenceFailure:
    """Represents a failure during content intelligence generation for a topic."""

    topic_id: str
    error: str


@dataclass(frozen=True)
class ContentIntelligenceGenerationResult:
    """Result of the content intelligence generation process."""

    generated_count: int
    skipped_count: int
    failures: List[ContentIntelligenceFailure]
    content_intelligences: List[ContentIntelligence]


class ContentIntelligenceService:
    """Service to orchestrate Content Intelligence generation for briefs."""

    def run(
        self,
        ctx: ApplicationContext,
        top_n: int = 5,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 5.0,
    ) -> ContentIntelligenceGenerationResult:
        """Generates Content Intelligence for briefs that don't have them yet."""
        generator = ContentIntelligenceGenerator(api_key, ctx.prompt_registry)

        briefs = ctx.storage.list_briefs()
        if not briefs:
            return ContentIntelligenceGenerationResult(
                generated_count=0,
                skipped_count=0,
                failures=[],
                content_intelligences=[],
            )

        # Pair briefs with original scored/staged topic priority metadata
        candidates = []
        for brief in briefs:
            if brief is None:
                candidates.append(
                    {
                        "brief": None,
                        "topic_id": "unknown",
                        "priority_score": 0.0,
                        "topic_category": TopicCategory.UNKNOWN,
                        "published_at": "unknown",
                    }
                )
                continue

            topic_id = getattr(brief, "topic_id", None)
            if not topic_id:
                candidates.append(
                    {
                        "brief": brief,
                        "topic_id": "unknown",
                        "priority_score": 0.0,
                        "topic_category": TopicCategory.UNKNOWN,
                        "published_at": "unknown",
                    }
                )
                continue

            scored_item = ctx.storage.get_scored(topic_id)
            if scored_item is None:
                # Fallback to staged if scored item not found
                scored_item = ctx.storage.get_staged(topic_id)

            priority_score = (
                scored_item.priority_score
                if hasattr(scored_item, "priority_score")
                else 0.0
            )
            topic_category = (
                scored_item.category
                if hasattr(scored_item, "category")
                else TopicCategory.UNKNOWN
            )
            published_at = (
                scored_item.published_at
                if (hasattr(scored_item, "published_at") and scored_item.published_at)
                else "unknown"
            )

            candidates.append(
                {
                    "brief": brief,
                    "topic_id": topic_id,
                    "priority_score": priority_score,
                    "topic_category": topic_category,
                    "published_at": published_at,
                }
            )

        # Sort candidates descending by priority score and slice to top_n
        candidates.sort(key=lambda x: x["priority_score"], reverse=True)
        candidates = candidates[:top_n]

        generated_items = []
        failures = []
        skipped_count = 0

        for candidate in candidates:
            brief = candidate.get("brief")
            topic_id = candidate.get("topic_id") or (brief.topic_id if brief else None)

            if not topic_id or topic_id == "unknown":
                failures.append(ContentIntelligenceFailure(topic_id="unknown", error="Brief is missing."))
                continue

            if brief is None:
                failures.append(ContentIntelligenceFailure(topic_id=topic_id, error="Brief is missing."))
                continue

            # Validate required brief content fields
            is_invalid = False
            missing_fields = []
            for field in ["why_it_matters", "student_takeaway", "analogy", "limitation", "audience_fit"]:
                val = getattr(brief, field, None)
                if not val or (isinstance(val, str) and not val.strip()):
                    missing_fields.append(field)
                    is_invalid = True
            
            # Check plain_english_summary
            summary = getattr(brief, "plain_english_summary", None)
            if not summary or not isinstance(summary, list) or len(summary) != 3 or any(not s.strip() for s in summary):
                missing_fields.append("plain_english_summary")
                is_invalid = True

            if is_invalid:
                failures.append(ContentIntelligenceFailure(
                    topic_id=topic_id,
                    error=f"Required brief content fields are empty or invalid: {missing_fields}"
                ))
                continue

            ci_file = ctx.storage.content_intelligence_dir / f"{topic_id}.json"
            ci_completed = ctx.workflow.stage_completed(topic_id, "content_intelligence")

            if ci_completed and ci_file.exists():
                skipped_count += 1
                continue

            if ci_completed and not ci_file.exists():
                logger.warning(
                    f"Divergence detected: stage content_intelligence completed but artifact {ci_file} is missing. Regenerating."
                )

            if not ci_completed and ci_file.exists():
                skipped_count += 1
                continue

            try:
                # 3. Generate CI artifact
                ci = generator.generate(
                    brief=brief,
                    topic_category=candidate["topic_category"],
                    published_at=candidate["published_at"],
                )
                
                # 4. Save CI artifact to disk
                ctx.storage.save_content_intelligence(ci)

                # 5. Update workflow state to completed
                ctx.workflow.mark_completed(
                    topic_id=topic_id,
                    stage="content_intelligence",
                    artifact_path=str(ci_file),
                )
                
                generated_items.append(ci)
            except Exception as e:
                # 6. Update workflow state to failed
                ctx.workflow.mark_failed(topic_id, "content_intelligence")
                logger.error(f"Error generating Content Intelligence for {topic_id}: {e}")
                failures.append(ContentIntelligenceFailure(topic_id=topic_id, error=str(e)))

            # Respect rate limit delay
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)

        return ContentIntelligenceGenerationResult(
            generated_count=len(generated_items),
            skipped_count=skipped_count,
            failures=failures,
            content_intelligences=generated_items,
        )
