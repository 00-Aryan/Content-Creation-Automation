"""Base scorer interface and scoring rule abstraction."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from content_creation.models.topic import ScoredTopicItem, TopicItem

logger = logging.getLogger(__name__)


class ScoringRule(ABC):
    """Abstract base class for scoring rules."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with rule-specific configuration.

        Args:
            config: Configuration dictionary for this rule.
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.weight = config.get("weight", 0.0)

    @abstractmethod
    def score(self, item: TopicItem) -> float:
        """Calculate a score for the given item.

        Args:
            item: The TopicItem to score.

        Returns:
            A score between 0 and 100.
        """
        pass

    @abstractmethod
    def get_rule_name(self) -> str:
        """Return the name of this scoring rule."""
        pass

    def apply(self, item: TopicItem) -> Optional[float]:
        """Apply this rule to an item if enabled.

        Args:
            item: The TopicItem to score.

        Returns:
            The weighted score contribution, or None if rule is disabled.
        """
        if not self.enabled:
            return None

        try:
            raw_score = self.score(item)
            weighted_score = raw_score * self.weight
            logger.debug(f"{self.get_rule_name()}: raw={raw_score:.2f}, weighted={weighted_score:.2f}")
            return weighted_score
        except Exception as e:
            logger.warning(f"Failed to apply {self.get_rule_name()} to {item.id}: {e}")
            return None


class Scorer(ABC):
    """Abstract base class for scoring engines."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with scoring configuration.

        Args:
            config: Full scoring configuration dictionary.
        """
        self.config = config
        self.rules: List[ScoringRule] = []
        self._initialize_rules()

    @abstractmethod
    def _initialize_rules(self):
        """Initialize scoring rules based on configuration."""
        pass

    def score_item(self, item: TopicItem) -> ScoredTopicItem:
        """Score a single TopicItem.

        Args:
            item: The TopicItem to score.

        Returns:
            A ScoredTopicItem with scoring metadata.
        """
        from datetime import datetime

        total_score = 0.0
        scores: Dict[str, float] = {}
        rules_fired: List[str] = []

        for rule in self.rules:
            weighted_score = rule.apply(item)
            if weighted_score is not None:
                rule_name = rule.get_rule_name()
                scores[rule_name] = weighted_score
                total_score += weighted_score
                rules_fired.append(rule_name)

        # Create ScoredTopicItem
        scored_item = ScoredTopicItem(
            **item.model_dump(),
            priority_score=round(min(total_score, 100.0), 2),
            scoring_timestamp=datetime.now().isoformat(),
            scoring_rules_fired=rules_fired,
        )

        # Set individual scores
        for rule_name, score in scores.items():
            setattr(scored_item, f"{rule_name}_score", round(score, 2))

        logger.info(f"Scored item {item.id}: total={total_score:.2f}, rules={rules_fired}")
        return scored_item

    def score_items(self, items: List[TopicItem]) -> Dict[str, List[ScoredTopicItem]]:
        """Score multiple TopicItems.

        Args:
            items: List of TopicItems to score.

        Returns:
            Dictionary with ``scored`` and ``rejected`` lists of ``ScoredTopicItem``.
        """
        logger.info(f"Scoring {len(items)} items...")
        scored_items = [self.score_item(item) for item in items]
        logger.info(f"Completed scoring {len(scored_items)} items")
        return {"scored": scored_items, "rejected": []}
