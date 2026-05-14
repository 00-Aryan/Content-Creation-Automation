"""Scoring engine orchestrator for topic prioritization."""

import logging
from typing import Any, Dict, List, Optional

from content_creation.models.topic import ScoredTopicItem, TopicItem, TopicStatus
from content_creation.scoring.base import Scorer, ScoringRule
from content_creation.scoring.config import ScoringConfig

logger = logging.getLogger(__name__)


class SimpleRule(ScoringRule):
    """Generic rule for weighted categories."""
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(config)
        self.name = name

    def score(self, item: TopicItem) -> float:
        # Placeholder logic: return a default score or use metadata if it exists
        return item.metadata.get(f"{self.name}_score", 50.0)

    def get_rule_name(self) -> str:
        return self.name


class ScoringEngine(Scorer):
    """Main scoring engine that orchestrates all scoring rules and hard filters."""

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
        rule_names = [
            "student_usefulness",
            "novelty",
            "credibility",
            "explainability",
            "hook_potential",
        ]
        
        for name in rule_names:
            rule_config = getattr(self.config, name)
            if rule_config.enabled:
                self.rules.append(SimpleRule(name, rule_config.model_dump()))
                logger.info(f"Enabled {name} rule (weight={rule_config.weight})")

        if not self.rules:
            logger.warning("No scoring rules enabled")

    def score_items(self, items: List[TopicItem]) -> Dict[str, List[ScoredTopicItem]]:
        """Score multiple TopicItems and apply hard rejection filters.
        
        Returns:
            A dictionary with 'scored' and 'rejected' lists of ScoredTopicItem.
        """
        scored_items = []
        rejected_items = []
        seen_titles = set()

        logger.info(f"Processing {len(items)} items through scoring and filters...")

        for item in items:
            # 1. raw_text length < 100 characters
            if len(item.raw_text) < 100:
                rejected_items.append(self._reject(item, "insufficient_text"))
                continue

            # 3. source field is missing or empty
            if not item.source or item.source == "unknown":
                rejected_items.append(self._reject(item, "missing_source"))
                continue

            # 4. title is duplicate of already scored item in this batch
            title_norm = item.title.lower().strip()
            if title_norm in seen_titles:
                rejected_items.append(self._reject(item, "duplicate_title"))
                continue

            # If passed hard filters, score it
            scored_item = self.score_item(item)

            # 2. priority_score < 0.2 → reject
            if scored_item.priority_score < 0.2:
                rejected_items.append(self._reject(item, "low_score"))
                continue

            scored_items.append(scored_item)
            seen_titles.add(title_norm)

        logger.info(f"Completed: {len(scored_items)} scored, {len(rejected_items)} rejected")
        return {"scored": scored_items, "rejected": rejected_items}

    def _reject(self, item: TopicItem, reason: str) -> ScoredTopicItem:
        """Helper to create a rejected ScoredTopicItem and log it."""
        logger.warning(f"REJECTED topic {item.id} ({item.title}): {reason}")

        item_data = item.model_dump()
        item_data["status"] = TopicStatus.REJECTED  # override before unpacking
        
        # Create ScoredTopicItem with rejected status
        rejected_item = ScoredTopicItem(
            **item_data,
            priority_score=0.0,
            validation_flags=[f"rejection_reason: {reason}"]
        )
        return rejected_item

    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule names."""
        return [rule.get_rule_name() for rule in self.rules]

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the scoring configuration."""
        summary = {
            "total_weight": self.config.get_total_weight(),
            "enabled_rules": self.get_enabled_rules(),
        }
        for name in ["student_usefulness", "novelty", "credibility", "explainability", "hook_potential"]:
            rule_config = getattr(self.config, name)
            summary[name] = {
                "enabled": rule_config.enabled,
                "weight": rule_config.weight,
            }
        return summary
