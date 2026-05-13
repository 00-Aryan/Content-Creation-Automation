"""Individual scoring rules for topic prioritization."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from content_creation.models.topic import TopicItem
from content_creation.scoring.base import ScoringRule

logger = logging.getLogger(__name__)


class RecencyRule(ScoringRule):
    """Scores items based on publication recency using exponential decay."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.half_life_days = config.get("half_life_days", 30)
        self.max_age_days = config.get("max_age_days", 365)

    def get_rule_name(self) -> str:
        return "recency"

    def score(self, item: TopicItem) -> float:
        """Calculate recency score using exponential decay.

        Args:
            item: The TopicItem to score.

        Returns:
            A score between 0 and 100.
        """
        if item.published_at == "unknown":
            logger.debug(f"Item {item.id} has unknown published_at, using minimum recency score")
            return 0.0

        try:
            published_date = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
            if published_date.tzinfo is None:
                published_date = published_date.replace(tzinfo=timezone.utc)
                
            now = datetime.now(timezone.utc)
            age_days = (now - published_date).days

            if age_days < 0:
                logger.debug(f"Item {item.id} has future date, using maximum score")
                return 100.0

            if age_days >= self.max_age_days:
                return 0.0

            # Exponential decay: score = 100 * (0.5)^(age / half_life)
            decay_factor = 0.5 ** (age_days / self.half_life_days)
            score = 100.0 * decay_factor
            return round(score, 2)

        except Exception as e:
            logger.warning(f"Failed to parse date for item {item.id}: {e}")
            return 0.0


class SourceQualityRule(ScoringRule):
    """Scores items based on source quality weights."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.sources = config.get("sources", {})
        self.default = config.get("default", 50.0)

    def get_rule_name(self) -> str:
        return "source_quality"

    def score(self, item: TopicItem) -> float:
        """Calculate source quality score.

        Args:
            item: The TopicItem to score.

        Returns:
            A score between 0 and 100.
        """
        source_score = self.sources.get(item.source, self.default)
        return round(source_score, 2)


class KeywordRule(ScoringRule):
    """Scores items based on keyword relevance to topic areas."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.topic_areas = config.get("topic_areas", {})

    def get_rule_name(self) -> str:
        return "keyword"

    def score(self, item: TopicItem) -> float:
        """Calculate keyword relevance score.

        Args:
            item: The TopicItem to score.

        Returns:
            A score between 0 and 100.
        """
        if not self.topic_areas:
            return 0.0

        # Collect all keywords from all topic areas
        all_keywords = set()
        for keywords in self.topic_areas.values():
            all_keywords.update(k.lower() for k in keywords)

        if not all_keywords:
            return 0.0

        # Search in title, excerpt, and tags
        searchable_text = (
            f"{item.title} {item.excerpt} "
            f"{' '.join(tag for tag in item.topic_tags)}"
        )

        matches = 0
        matched_keywords = []

        for keyword in all_keywords:
            # Case-insensitive word-boundary matching
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, searchable_text, re.IGNORECASE):
                matches += 1
                matched_keywords.append(keyword)

        if matches == 0:
            return 0.0

        # Score based on percentage of keywords matched
        score = (matches / len(all_keywords)) * 100.0
        logger.debug(f"Item {item.id} matched {matches} keywords: {matched_keywords}")
        return round(score, 2)


class QualityRule(ScoringRule):
    """Scores items based on quality heuristics."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_title_length = config.get("min_title_length", 10)
        self.max_title_length = config.get("max_title_length", 200)
        self.has_description_bonus = config.get("has_description_bonus", 10.0)
        self.has_tags_bonus = config.get("has_tags_bonus", 5.0)

    def get_rule_name(self) -> str:
        return "quality"

    def score(self, item: TopicItem) -> float:
        """Calculate quality score based on heuristics.

        Args:
            item: The TopicItem to score.

        Returns:
            A score between 0 and 100.
        """
        score = 0.0

        # Title length check
        title_len = len(item.title)
        if self.min_title_length <= title_len <= self.max_title_length:
            score += 50.0
        elif title_len > 0:
            # Partial credit for non-empty title
            score += 25.0

        # Has description/excerpt
        if item.excerpt and item.excerpt != "unknown" and len(item.excerpt) > 10:
            score += self.has_description_bonus

        # Has tags
        if item.topic_tags:
            score += self.has_tags_bonus

        # Cap at 100
        return round(min(score, 100.0), 2)
