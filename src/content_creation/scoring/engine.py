"""Scoring engine orchestrator for topic prioritization."""

import logging
from typing import Any, Dict, List

from content_creation.models.topic import ScoredTopicItem, TopicItem
from content_creation.scoring.base import Scorer
from content_creation.scoring.config import ScoringConfig
from content_creation.scoring.rules import KeywordRule, QualityRule, RecencyRule, SourceQualityRule

logger = logging.getLogger(__name__)


class ScoringEngine(Scorer):
    """Main scoring engine that orchestrates all scoring rules."""

    def __init__(self, config: ScoringConfig):
        """Initialize with scoring configuration.

        Args:
            config: ScoringConfig instance with rule configurations.
        """
        self.config = config
        self.rules: List[Any] = []
        self._initialize_rules()

    def _initialize_rules(self):
        """Initialize scoring rules based on configuration."""
        # Recency rule
        if self.config.recency.enabled:
            self.rules.append(
                RecencyRule(self.config.recency.model_dump())
            )
            logger.info(f"Enabled recency rule (weight={self.config.recency.weight})")

        # Source quality rule
        if self.config.source_quality.enabled:
            self.rules.append(
                SourceQualityRule(self.config.source_quality.model_dump())
            )
            logger.info(f"Enabled source_quality rule (weight={self.config.source_quality.weight})")

        # Keyword rule
        if self.config.keywords.enabled:
            self.rules.append(
                KeywordRule(self.config.keywords.model_dump())
            )
            logger.info(f"Enabled keyword rule (weight={self.config.keywords.weight})")

        # Quality rule
        if self.config.quality.enabled:
            self.rules.append(
                QualityRule(self.config.quality.model_dump())
            )
            logger.info(f"Enabled quality rule (weight={self.config.quality.weight})")

        if not self.rules:
            logger.warning("No scoring rules enabled")

    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule names."""
        return [rule.get_rule_name() for rule in self.rules]

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the scoring configuration."""
        return {
            "total_weight": self.config.get_total_weight(),
            "enabled_rules": self.get_enabled_rules(),
            "recency": {
                "enabled": self.config.recency.enabled,
                "weight": self.config.recency.weight,
                "half_life_days": self.config.recency.half_life_days,
            },
            "source_quality": {
                "enabled": self.config.source_quality.enabled,
                "weight": self.config.source_quality.weight,
                "sources": self.config.source_quality.sources,
            },
            "keywords": {
                "enabled": self.config.keywords.enabled,
                "weight": self.config.keywords.weight,
                "topic_areas": list(self.config.keywords.topic_areas.keys()),
            },
            "quality": {
                "enabled": self.config.quality.enabled,
                "weight": self.config.quality.weight,
            },
        }
