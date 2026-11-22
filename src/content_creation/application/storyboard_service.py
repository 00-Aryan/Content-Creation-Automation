"""Service for orchestrating Storyboard generation."""

from dataclasses import dataclass
import logging
import os
import time
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.domains.storyboard import Storyboard, StoryboardGenerator
from content_creation.models.brief import Brief
from content_creation.models.topic import TopicCategory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoryboardFailure:
    """Represents a failure during storyboard generation for a topic."""

    topic_id: str
    error: str


@dataclass(frozen=True)
class StoryboardGenerationResult:
    """Result of the storyboard generation process."""

    generated_count: int
    skipped_count: int
    failures: List[StoryboardFailure]
    storyboards: List[Storyboard]


class StoryboardService:
    """Service to orchestrate Storyboard generation for topics."""

    def run(
        self,
        ctx: ApplicationContext,
        top_n: int = 5,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 5.0,
        topic_id: Optional[str] = None,
    ) -> StoryboardGenerationResult:
        """Generates Storyboards for content intelligence items that don't have them yet."""
        generator = StoryboardGenerator(api_key, ctx.prompt_registry)

        ci_list = ctx.storage.list_content_intelligence()
        if topic_id:
            target_ci = next((ci for ci in ci_list if ci.topic_id == topic_id), None)
            ci_list = [target_ci] if target_ci else []

        if not ci_list:
            return StoryboardGenerationResult(
                generated_count=0,
                skipped_count=0,
                failures=[],
                storyboards=[],
            )

        # Pair content intelligence with priority metadata
        candidates = []
        for ci in ci_list:
            scored_item = ctx.storage.get_scored(ci.topic_id)
            if scored_item is None:
                scored_item = ctx.storage.get_staged(ci.topic_id)

            priority_score = (
                scored_item.priority_score
                if hasattr(scored_item, "priority_score")
                else 0.0
            )

            candidates.append(
                {
                    "ci": ci,
                    "priority_score": priority_score,
                }
            )

        # Sort candidates descending by priority score and slice to top_n
        if not topic_id:
            candidates.sort(key=lambda x: x["priority_score"], reverse=True)
            candidates = candidates[:top_n]

        generated_items = []
        failures = []
        skipped_count = 0

        for candidate in candidates:
            ci = candidate["ci"]
            topic_id = ci.topic_id

            sb_file = ctx.storage.storyboards_dir / f"{topic_id}.json"
            sb_completed = ctx.workflow.stage_completed(topic_id, "storyboard")

            if sb_completed and sb_file.exists():
                skipped_count += 1
                continue

            if sb_completed and not sb_file.exists():
                logger.warning(
                    f"Divergence detected: stage storyboard completed but artifact {sb_file} is missing. Regenerating."
                )

            if not sb_completed and sb_file.exists():
                skipped_count += 1
                continue

            # 3. Load matched Brief object
            brief = ctx.storage.get_brief(topic_id)
            if not brief:
                error_msg = f"Missing Brief dependency for topic {topic_id}"
                logger.error(error_msg)
                failures.append(StoryboardFailure(topic_id=topic_id, error=error_msg))
                ctx.workflow.mark_failed(topic_id, "storyboard")
                continue

            try:
                # 4. Generate storyboard
                sb = generator.generate(brief=brief, ci=ci)

                # Ensure manual topics always include short_video in formats_planned
                topic_item = ctx.storage.get_scored(topic_id) or ctx.storage.get_staged(topic_id)
                is_manual = False
                if topic_item:
                    is_manual = (
                        getattr(topic_item, "source", None) == "manual"
                        or "manual" in getattr(topic_item, "topic_tags", [])
                        or (hasattr(topic_item, "metadata") and topic_item.metadata and getattr(topic_item.metadata, "source_type", None) == "manual")
                    )
                if is_manual or "script" in getattr(brief, "recommended_formats", []):
                    if "short_video" not in sb.formats_planned:
                        sb.formats_planned.append("short_video")
                
                # 5. Save storyboard
                ctx.storage.save_storyboard(sb)

                # 6. Update workflow state
                ctx.workflow.mark_completed(
                    topic_id=topic_id,
                    stage="storyboard",
                    artifact_path=str(sb_file),
                )
                
                generated_items.append(sb)
            except Exception as e:
                ctx.workflow.mark_failed(topic_id, "storyboard")
                logger.error(f"Error generating Storyboard for {topic_id}: {e}")
                failures.append(StoryboardFailure(topic_id=topic_id, error=str(e)))

            # Respect rate limit delay
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)

        return StoryboardGenerationResult(
            generated_count=len(generated_items),
            skipped_count=skipped_count,
            failures=failures,
            storyboards=generated_items,
        )
