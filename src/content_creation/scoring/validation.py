"""Scoring validation rules and quality checks."""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from content_creation.models.topic import ScoredTopicItem
from content_creation.scoring.config import ValidationConfig

logger = logging.getLogger(__name__)


class ValidationRule(ABC):
    """Abstract base class for scoring validation rules."""

    def __init__(self, config: ValidationConfig):
        """Initialize with validation configuration."""
        self.config = config

    @abstractmethod
    def validate(self, item: ScoredTopicItem) -> Optional[str]:
        """Validate a scored item.

        Returns:
            A warning message if validation fails, otherwise None.
        """
        pass


class ScoreConsistencyRule(ValidationRule):
    """Ensures priority_score matches the sum of individual rule scores."""

    def validate(self, item: ScoredTopicItem) -> Optional[str]:
        if not self.config.check_consistency:
            return None

        # Calculate sum of individual scores
        # Note: We round to 2 decimal places to avoid floating point issues
        sum_scores = round(
            item.student_usefulness_score + 
            item.novelty_score + 
            item.credibility_score + 
            item.explainability_score +
            item.hook_potential_score, 
            2
        )
        
        if abs(sum_scores - item.priority_score) > 0.01:
            return f"Score inconsistency: priority_score ({item.priority_score}) != sum of components ({sum_scores})"
        
        return None


class SuspiciousScoreRule(ValidationRule):
    """Flags items with extreme scores based on configuration."""

    def validate(self, item: ScoredTopicItem) -> Optional[str]:
        if item.priority_score >= self.config.suspiciously_high_score:
            return f"Suspiciously high score: {item.priority_score}"
        
        if item.priority_score <= self.config.suspiciously_low_score:
            return f"Suspiciously low score: {item.priority_score}"
        
        return None


class MetadataCompletenessRule(ValidationRule):
    """Flags high-scoring items missing critical metadata."""

    def validate(self, item: ScoredTopicItem) -> Optional[str]:
        # Only check completeness for items that scored reasonably well
        if item.priority_score < 50.0:
            return None

        flags = []
        if self.config.require_published_at and item.published_at == "unknown":
            flags.append("missing published_at")
        
        if self.config.require_author and item.author == "unknown":
            flags.append("missing author")
        
        if item.excerpt == "unknown" or len(item.excerpt) < 20:
            flags.append("missing or short excerpt")

        if flags:
            return f"High score but missing metadata: {', '.join(flags)}"
        
        return None


class ValidationEngine:
    """Orchestrates all validation rules for scored items."""

    def __init__(self, config: ValidationConfig):
        """Initialize with validation configuration."""
        self.config = config
        self.rules: List[ValidationRule] = [
            ScoreConsistencyRule(config),
            SuspiciousScoreRule(config),
            MetadataCompletenessRule(config),
        ]

    def validate_item(self, item: ScoredTopicItem) -> ScoredTopicItem:
        """Apply all validation rules to an item and update its flags."""
        new_flags = []
        for rule in self.rules:
            warning = rule.validate(item)
            if warning:
                new_flags.append(warning)
        
        # Merge with existing flags and ensure uniqueness
        item.validation_flags = list(set(item.validation_flags + new_flags))
        
        if new_flags:
            logger.info(f"Item {item.id} flagged with {len(new_flags)} warnings: {new_flags}")
            
        return item

    def validate_items(self, items: List[ScoredTopicItem]) -> List[ScoredTopicItem]:
        """Apply validation to a list of items."""
        return [self.validate_item(item) for item in items]
