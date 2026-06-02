"""Service for orchestrating feed ingestion and topic collection."""

from dataclasses import dataclass
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.ingestion import IngestionEngine
from content_creation.models.topic import TopicItem
from content_creation.utils.config import load_yaml_config


@dataclass(frozen=True)
class CollectResult:
    """Result of the collection process."""

    new_items: List[TopicItem]
    count: int


class CollectTopicsService:
    """Service to orchestrate topic collection and ingestion from feeds."""

    def run(
        self, ctx: ApplicationContext, source_filter: Optional[str] = None
    ) -> CollectResult:
        """Runs the ingestion pipeline for enabled sources, matching the optional filter."""
        config = load_yaml_config(ctx.feeds_config_path)
        engine = IngestionEngine(config, ctx.storage)
        new_items = engine.run(source_filter=source_filter)

        return CollectResult(new_items=new_items, count=len(new_items))
