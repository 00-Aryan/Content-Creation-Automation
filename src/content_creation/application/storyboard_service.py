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
    ) -> StoryboardGenerationResult:
        """Generates Storyboards for content intelligence items that don't have them yet."""
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError("GEMINI_API_KEY not set in environment or parameter")

        generator = StoryboardGenerator(resolved_key, ctx.prompt_registry)

        ci_list = ctx.storage.list_content_intelligence()
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
        candidates.sort(key=lambda x: x["priority_score"], reverse=True)
        candidates = candidates[:top_n]

        generated_items = []
        failures = []
        skipped_count = 0

        for candidate in candidates:
            ci = candidate["ci"]
            topic_id = ci.topic_id

            # 1. Skip if workflow stage is completed
            if ctx.workflow.stage_completed(topic_id, "storyboard"):
                skipped_count += 1
                continue

            # 2. Skip if file already exists in storage
            sb_file = ctx.storage.storyboards_dir / f"{topic_id}.json"
            if sb_file.exists():
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
