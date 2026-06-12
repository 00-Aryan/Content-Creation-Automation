"""Scoring engine orchestrator for topic prioritization."""

import logging
from typing import Any, Dict, List, Optional

from datetime import datetime, timezone
from content_creation.models.topic import ScoredTopicItem, TopicCategory, TopicItem, TopicStatus
from content_creation.scoring.base import Scorer, ScoringRule
from content_creation.scoring.config import ScoringConfig

logger = logging.getLogger(__name__)


class StudentUsefulnessRule(ScoringRule):
    """Rule to score usefulness for students based on AI/ML keywords, category and tags."""

    def score(self, item: TopicItem) -> float:
        override = item.metadata.get("student_usefulness_score")
        if override is not None:
            return float(override)

        search_text = f"{item.title} {item.excerpt or ''} {item.raw_text or ''}".lower()
        keywords = ["ai", "ml", "machine learning", "deep learning", "neural", "transformer", 
                    "model", "agent", "llm", "benchmark", "dataset", "evaluation", "framework", 
                    "training", "prompt", "fine-tuning", "rag", "rlhf", "optimiz"]
        matches = sum(1 for kw in keywords if kw in search_text)
        kw_score = min(matches * 10.0, 50.0)
        
        category_score = 0.0
        if item.category in (TopicCategory.PAPER, TopicCategory.REPO, TopicCategory.TOOL):
            category_score = 30.0
        elif item.category == TopicCategory.CONCEPT:
            category_score = 20.0
        elif item.category in (TopicCategory.NEWS, TopicCategory.RELEASE):
            category_score = 10.0
            
        tag_score = 0.0
        if any(tag.lower().startswith("cs.") or "ai" in tag.lower() or "ml" in tag.lower() for tag in item.topic_tags):
            tag_score = 20.0
        elif item.topic_tags:
            tag_score = 10.0
            
        score = 20.0 + kw_score + category_score + tag_score
        return float(round(max(0.0, min(100.0, score)), 2))

    def get_rule_name(self) -> str:
        return "student_usefulness"


class NoveltyRule(ScoringRule):
    """Rule to score novelty based on publication age decay."""

    def score(self, item: TopicItem) -> float:
        override = item.metadata.get("novelty_score")
        if override is not None:
            return float(override)

        recency = 50.0
        if item.published_at and item.published_at != "unknown":
            try:
                published_date = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
                if published_date.tzinfo is None:
                    published_date = published_date.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                age_days = (now - published_date).days
                if age_days < 0:
                    recency = 100.0
                else:
                    # Decay with half life of 30 days
                    recency = 100.0 * (0.5 ** (age_days / 30.0))
            except Exception:
                recency = 50.0
                
        recency_val = max(20.0, min(100.0, recency))
        
        is_paper_or_release = item.category in (TopicCategory.PAPER, TopicCategory.RELEASE)
        
        search_text = f"{item.title} {item.excerpt or ''}".lower()
        novel_terms = ["novel", "state-of-the-art", "sota", "new", "recent", "introduce", "present", "proposed", "breakthrough"]
        has_novel_terms = any(term in search_text for term in novel_terms)
        
        score = 0.8 * recency_val
        if is_paper_or_release:
            score += 10.0
        if has_novel_terms:
            score += 10.0
            
        return float(round(max(0.0, min(100.0, score)), 2))

    def get_rule_name(self) -> str:
        return "novelty"


class CredibilityRule(ScoringRule):
    """Rule to score credibility based on source type and author metadata."""

    def score(self, item: TopicItem) -> float:
        override = item.metadata.get("credibility_score")
        if override is not None:
            return float(override)

        source_scores = {
            "arxiv": 90.0,
            "openai": 95.0,
            "huggingface": 90.0,
            "github": 85.0,
            "nature": 95.0,
            "science": 95.0,
        }
        base_source_score = source_scores.get(item.source.lower(), 70.0)
        
        author_bonus = 0.0
        if item.author and item.author != "unknown" and len(item.author) > 3:
            author_bonus = 10.0
            
        url_bonus = 5.0 if item.url and item.url.startswith("https://") else 0.0
        
        text_bonus = 5.0 if item.raw_text and len(item.raw_text) >= 500 else 0.0
        
        score = base_source_score + author_bonus + url_bonus + text_bonus
        return float(round(max(0.0, min(100.0, score)), 2))

    def get_rule_name(self) -> str:
        return "credibility"


class ExplainabilityRule(ScoringRule):
    """Rule to score explainability based on structured content and description presence."""

    def score(self, item: TopicItem) -> float:
        override = item.metadata.get("explainability_score")
        if override is not None:
            return float(override)

        excerpt_points = 0.0
        if item.excerpt and item.excerpt != "unknown":
            if len(item.excerpt) > 100:
                excerpt_points = 30.0
            elif len(item.excerpt) > 50:
                excerpt_points = 15.0
                
        has_structure = False
        if item.raw_text:
            if "\n-" in item.raw_text or "\n*" in item.raw_text or "\n1." in item.raw_text or "##" in item.raw_text:
                has_structure = True
        structure_points = 20.0 if has_structure else 0.0
        
        search_text = f"{item.title} {item.excerpt or ''} {item.raw_text or ''}".lower()
        edu_keywords = ["explain", "overview", "introduction", "tutorial", "how to", "example", "simple", "concept", "illustrate"]
        has_edu = any(kw in search_text for kw in edu_keywords)
        edu_points = 20.0 if has_edu else 0.0
        
        text_len_points = 0.0
        if item.raw_text:
            if len(item.raw_text) >= 1000:
                text_len_points = 30.0
            elif len(item.raw_text) >= 500:
                text_len_points = 15.0
                
        score = 20.0 + excerpt_points + structure_points + edu_points + text_len_points
        return float(round(max(0.0, min(100.0, score)), 2))

    def get_rule_name(self) -> str:
        return "explainability"


class HookPotentialRule(ScoringRule):
    """Rule to score hook potential based on title properties and engaging keywords."""

    def score(self, item: TopicItem) -> float:
        override = item.metadata.get("hook_potential_score")
        if override is not None:
            return float(override)

        title_len = len(item.title) if item.title else 0
        title_points = 30.0 if 20 <= title_len <= 80 else 10.0
        
        search_text = f"{item.title} {item.excerpt or ''}".lower()
        hook_keywords = ["breakthrough", "revolution", "state-of-the-art", "sota", "insane", 
                         "amazing", "game-changer", "game changer", "fast", "tiny", "giant", 
                         "massive", "easy", "powerful", "next-gen", "future"]
        has_hook = any(kw in search_text for kw in hook_keywords)
        hook_points = 30.0 if has_hook else 0.0
        
        category_points = 0.0
        if item.category in (TopicCategory.REPO, TopicCategory.TOOL, TopicCategory.RELEASE):
            category_points = 30.0
        elif item.category == TopicCategory.NEWS:
            category_points = 15.0
            
        excerpt_points = 10.0 if item.excerpt and item.excerpt != "unknown" else 0.0
        
        score = title_points + hook_points + category_points + excerpt_points
        return float(round(max(0.0, min(100.0, score)), 2))

    def get_rule_name(self) -> str:
        return "hook_potential"


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
        rule_map = {
            "student_usefulness": StudentUsefulnessRule,
            "novelty": NoveltyRule,
            "credibility": CredibilityRule,
            "explainability": ExplainabilityRule,
            "hook_potential": HookPotentialRule,
        }
        
        for name, rule_class in rule_map.items():
            rule_config = getattr(self.config, name)
            if rule_config.enabled:
                self.rules.append(rule_class(rule_config.model_dump()))
                logger.info(f"Enabled {name} rule (weight={rule_config.weight})")

        if not self.rules:
            logger.warning("No scoring rules enabled")

    def score_item(self, item: TopicItem) -> ScoredTopicItem:
        """Score a single TopicItem and set quality_score equal to priority_score."""
        scored_item = super().score_item(item)
        scored_item.quality_score = scored_item.priority_score
        return scored_item

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
