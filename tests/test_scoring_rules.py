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


def test_scoring_engine_differentiation():
    """Test that two clearly different topic inputs produce different, bounded, and robust scores."""
    from content_creation.scoring.config import load_scoring_config
    from pathlib import Path
    
    config = load_scoring_config(Path("config/scoring.yaml"))
    engine = ScoringEngine(config)
    
    # 1. A highly valuable, new AI paper with author, tags, and good text length
    strong_item = TopicItem(
        id="strong-topic",
        title="MobiBench: Multi-Branch, Modular Benchmark for Mobile GUI Agents",
        url="https://arxiv.org/abs/2512.12634",
        source="arxiv",
        published_at="2026-05-14T04:00:00Z",
        author="Youngmin Im et al.",
        raw_text="arXiv:2512.12634v3 Abstract: Mobile GUI Agents, AI agents capable of interacting with mobile applications on behalf of users, have the potential to transform human computer interaction. However, current evaluation practices for GUI agents face two fundamental limitations. First, they either rely on single path offline benchmarks or online live benchmarks. Offline benchmarks using static, single path annotated datasets unfairly penalize valid alternative actions, while online benchmarks suffer from poor scalability and reproducibility due to the dynamic and unpredictable nature of live evaluation.",
        excerpt="Mobile GUI Agents, AI agents capable of interacting with mobile applications on behalf of users, have the potential to transform human computer interaction.",
        category=TopicCategory.PAPER,
        topic_tags=["cs.AI", "cs.LG"]
    )
    
    # 2. A weak/generic concept topic with minimal details, unknown author, older date
    weak_item = TopicItem(
        id="weak-topic",
        title="Some Generic Topic Title That Is Short",
        url="https://example.com/generic",
        source="unknown_blog",
        published_at="2020-01-01T00:00:00Z",
        author="unknown",
        raw_text="This is a simple text that does not have any AI/ML keywords and is just general commentary. It has some extra padding to exceed the 100 character threshold for the hard filters.",
        excerpt="unknown",
        category=TopicCategory.CONCEPT,
        topic_tags=[]
    )
    
    # Score items
    res = engine.score_items([strong_item, weak_item])
    
    assert len(res["scored"]) == 2
    strong_scored = next(i for i in res["scored"] if i.id == "strong-topic")
    weak_scored = next(i for i in res["scored"] if i.id == "weak-topic")
    
    # Verify scores are different
    assert strong_scored.priority_score != weak_scored.priority_score
    # Strong should be significantly higher than weak
    assert strong_scored.priority_score > weak_scored.priority_score
    
    # Verify bounds (0.0 to 100.0)
    assert 0.0 <= strong_scored.priority_score <= 100.0
    assert 0.0 <= weak_scored.priority_score <= 100.0
    
    # Verify quality_score is set
    assert strong_scored.quality_score == strong_scored.priority_score
    assert weak_scored.quality_score == weak_scored.priority_score
    
    # Verify missing optional fields do not crash scoring
    minimal_item = TopicItem(
        id="minimal-topic",
        title="Another AI/ML Topic with minimal fields to test crashes",
        url="https://example.com/minimal",
        source="arxiv",
        published_at="2026-06-01T00:00:00Z",
        author=None,
        raw_text="This is a simple text that has AI/ML keywords and is just general commentary. It has some extra padding to exceed the 100 character threshold for the hard filters.",
        excerpt=None,
        category=TopicCategory.PAPER,
        topic_tags=[]
    )
    res_min = engine.score_items([minimal_item])
    assert len(res_min["scored"]) == 1

