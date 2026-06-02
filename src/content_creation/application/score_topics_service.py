"""Service for orchestrating topic scoring and validation."""

from dataclasses import dataclass
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.models.topic import ScoredTopicItem
from content_creation.scoring.config import load_scoring_config
from content_creation.scoring.engine import ScoringEngine
from content_creation.scoring.validation import ValidationEngine


@dataclass(frozen=True)
class ScoreResult:
    """Result of the scoring process."""

    scored_count: int
    rejected_count: int
    items: List[ScoredTopicItem]


class ScoreTopicsService:
    """Service to orchestrate scoring and validation of staged topics."""

    def run(
        self, ctx: ApplicationContext, limit: Optional[int] = None
    ) -> ScoreResult:
        """Loads staging topics, scores and validates them, and persists the results."""
        config = load_scoring_config(ctx.scoring_config_path)

        items = ctx.storage.list_staged()
        if limit:
            items = items[:limit]

        if not items:
            return ScoreResult(scored_count=0, rejected_count=0, items=[])

        scorer = ScoringEngine(config)
        validator = ValidationEngine(config.validation)

        results = scorer.score_items(items)
        scored_items = results["scored"]
        rejected_items = results["rejected"]

        all_processed = []

        for item in scored_items:
            validated_item = validator.validate_item(item)
            ctx.storage.save_scored(validated_item)
            all_processed.append(validated_item)

        for item in rejected_items:
            ctx.storage.save_scored(item)
            all_processed.append(item)

        return ScoreResult(
            scored_count=len(scored_items),
            rejected_count=len(rejected_items),
            items=all_processed,
        )
