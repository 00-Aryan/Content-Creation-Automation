"""Tests for individual scoring rules."""

import pytest
from content_creation.models.topic import TopicItem, TopicCategory
from content_creation.scoring.rules import KeywordRule, RecencyRule
from content_creation.scoring.engine import ScoringEngine
from content_creation.scoring.config import ScoringConfig


@pytest.fixture
def base_item():
    """A base TopicItem for testing."""
    return TopicItem(
        id="test-id",
        title="Deep Learning in AI",
        url="https://example.com/test",
        source="test_source",
        published_at="2023-10-27T10:00:00Z",
        author="Test Author",
        raw_text="Some raw text for testing.",
        excerpt="This is a test excerpt about deep learning.",
        category=TopicCategory.NEWS,
        topic_tags=["AI", "ML"]
    )


def test_keyword_rule_exact_match(base_item):
    """Test KeywordRule with exact word matches."""
    config = {
        "topic_areas": {
            "ml": ["deep", "learning"]
        }
    }
    rule = KeywordRule(config)
    # "deep" and "learning" are in title/excerpt
    score = rule.score(base_item)
    assert score > 0
    assert score == 100.0  # 2 out of 2 keywords matched


def test_keyword_rule_no_substring_match(base_item):
    """Test KeywordRule avoids substring matches."""
    # Title has "AI", we'll search for "Ais"
    config = {
        "topic_areas": {
            "test": ["Ais", "deeply"]
        }
    }
    rule = KeywordRule(config)
    score = rule.score(base_item)
    assert score == 0.0  # "Ais" should not match "AI", "deeply" should not match "Deep"


def test_keyword_rule_case_insensitivity(base_item):
    """Test KeywordRule is case-insensitive."""
    config = {
        "topic_areas": {
            "ml": ["DEEP", "learning"]
        }
    }
    rule = KeywordRule(config)
    score = rule.score(base_item)
    assert score == 100.0


def test_keyword_rule_punctuation_boundaries():
    """Test KeywordRule handles punctuation boundaries."""
    item = TopicItem(
        id="test-id",
        title="AI/ML: The Future",
        url="https://example.com/test",
        source="test_source",
        published_at="2023-10-27T10:00:00Z",
        raw_text="...",
        excerpt="...",
        topic_tags=[]
    )
    config = {
        "topic_areas": {
            "test": ["AI", "ML"]
        }
    }
    rule = KeywordRule(config)
    score = rule.score(item)
    assert score == 100.0  # Should match AI and ML even with / and :


def test_scorer_config_weight_validation(base_item):
    """Test that ScoringConfig prevents weights summing to > 1.0."""
    # Create a config where weights sum > 1.0
    config_dict = {
    "student_usefulness": {"weight": 1.0},
    "novelty": {"weight": 1.0},
    "credibility": {"weight": 1.0},
    "explainability": {"weight": 1.0},
    "hook_potential": {"weight": 1.0}
}
    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(**config_dict)
