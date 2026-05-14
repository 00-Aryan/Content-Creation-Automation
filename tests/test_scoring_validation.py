"""Tests for scoring validation rules and quality checks."""

import pytest
from pathlib import Path
from content_creation.models.topic import ScoredTopicItem, TopicCategory, TopicStatus, TopicItem
from content_creation.scoring.config import ValidationConfig, load_scoring_config
from content_creation.scoring.validation import (
    ScoreConsistencyRule,
    SuspiciousScoreRule,
    MetadataCompletenessRule,
    ValidationEngine
)
from content_creation.scoring.engine import ScoringEngine


@pytest.fixture
def validation_config():
    """Default validation configuration for tests."""
    return ValidationConfig(
        suspiciously_high_score=90.0,
        suspiciously_low_score=10.0,
        require_published_at=True,
        require_author=True,
        check_consistency=True
    )


@pytest.fixture
def base_scored_item():
    """A base ScoredTopicItem for testing."""
    return ScoredTopicItem(
        id="test-id",
        title="Test Topic Title",
        url="https://example.com/test",
        source="test_source",
        published_at="2023-10-27T10:00:00Z",
        author="Test Author",
        raw_text="Some raw text for testing that is definitely longer than one hundred characters so that it does not get rejected by the hard filters we just implemented.",
        excerpt="This is a test excerpt that is long enough.",
        category=TopicCategory.NEWS,
        priority_score=50.0,
        student_usefulness_score=10.0,
        novelty_score=10.0,
        credibility_score=10.0,
        explainability_score=10.0,
        hook_potential_score=10.0,
        validation_flags=[]
    )


def test_score_consistency_rule_valid(validation_config, base_scored_item):
    """Test that consistent scores pass."""
    rule = ScoreConsistencyRule(validation_config)
    assert rule.validate(base_scored_item) is None


def test_score_consistency_rule_invalid(validation_config, base_scored_item):
    """Test that inconsistent scores are flagged."""
    base_scored_item.priority_score = 100.0  # Sum is 50.0
    rule = ScoreConsistencyRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "Score inconsistency" in warning


def test_suspicious_score_rule_high(validation_config, base_scored_item):
    """Test flagging of suspiciously high scores."""
    base_scored_item.priority_score = 95.0
    rule = SuspiciousScoreRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "Suspiciously high" in warning


def test_suspicious_score_rule_low(validation_config, base_scored_item):
    """Test flagging of suspiciously low scores."""
    base_scored_item.priority_score = 5.0
    rule = SuspiciousScoreRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "Suspiciously low" in warning


def test_metadata_completeness_rule_missing_fields(validation_config, base_scored_item):
    """Test flagging of missing metadata for high-scoring items."""
    base_scored_item.priority_score = 80.0
    base_scored_item.author = "unknown"
    base_scored_item.published_at = "unknown"
    
    rule = MetadataCompletenessRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "missing published_at" in warning
    assert "missing author" in warning


def test_metadata_completeness_rule_ignored_for_low_scores(validation_config, base_scored_item):
    """Test that low-scoring items don't trigger completeness flags."""
    base_scored_item.priority_score = 30.0
    base_scored_item.author = "unknown"
    
    rule = MetadataCompletenessRule(validation_config)
    assert rule.validate(base_scored_item) is None


def test_validation_engine_integration(validation_config, base_scored_item):
    """Test that ValidationEngine applies multiple rules."""
    base_scored_item.priority_score = 95.0  # High score
    base_scored_item.author = "unknown"   # Missing metadata
    # Sum is 50.0, priority is 95.0 -> Inconsistent
    
    engine = ValidationEngine(validation_config)
    validated_item = engine.validate_item(base_scored_item)
    
    assert len(validated_item.validation_flags) >= 3
    flags_str = " ".join(validated_item.validation_flags)
    assert "Suspiciously high" in flags_str
    assert "missing author" in flags_str
    assert "Score inconsistency" in flags_str


# New Week 2 tests

def test_rejection_insufficient_text(validation_config):
    """Test: topics with raw_text < 100 chars are rejected."""
    scoring_config = load_scoring_config(Path("config/scoring.yaml"))
    engine = ScoringEngine(scoring_config)
    
    item = TopicItem(
        id="short-text",
        title="Short",
        url="http://short.com",
        source="test",
        published_at="2023-10-27T10:00:00Z",
        raw_text="Too short."
    )
    
    results = engine.score_items([item])
    assert len(results["rejected"]) == 1
    assert "insufficient_text" in results["rejected"][0].validation_flags[0]
    assert results["rejected"][0].status == TopicStatus.REJECTED


def test_rejection_low_score(validation_config):
    """Test: topics with priority_score < 0.2 are rejected."""
    # We'll mock metadata to get a low score
    scoring_config = load_scoring_config(Path("config/scoring.yaml"))
    engine = ScoringEngine(scoring_config)
    
    item = TopicItem(
        id="low-score",
        title="Boring Topic",
        url="http://boring.com",
        source="test",
        published_at="2023-10-27T10:00:00Z",
        raw_text="This is a long enough text but it will have a very low score because we will force it. Extra padding here.",
        metadata={
            "student_usefulness_score": 0.1,
            "novelty_score": 0.1,
            "credibility_score": 0.1,
            "explainability_score": 0.1,
            "hook_potential_score": 0.1
        }
    )
    
    results = engine.score_items([item])
    assert len(results["rejected"]) == 1
    assert "low_score" in results["rejected"][0].validation_flags[0]
    assert results["rejected"][0].status == TopicStatus.REJECTED


def test_rejection_missing_source():
    """Test: topics with missing source are rejected."""
    scoring_config = load_scoring_config(Path("config/scoring.yaml"))
    engine = ScoringEngine(scoring_config)
    
    item = TopicItem(
        id="no-source",
        title="No Source",
        url="http://nosource.com",
        source="unknown",
        published_at="2023-10-27T10:00:00Z",
       raw_text="Long enough text here as well to pass the first filter. Adding more text here to exceed the one hundred character minimum threshold."
               )
    
    results = engine.score_items([item])
    assert len(results["rejected"]) == 1
    assert "missing_source" in results["rejected"][0].validation_flags[0]
    assert results["rejected"][0].status == TopicStatus.REJECTED


def test_scoring_yaml_loads_correctly():
    """Test: config/scoring.yaml loads correctly with all 5 fields."""
    config = load_scoring_config(Path("config/scoring.yaml"))
    assert config.student_usefulness.weight == 0.30
    assert config.novelty.weight == 0.25
    assert config.credibility.weight == 0.20
    assert config.explainability.weight == 0.15
    assert config.hook_potential.weight == 0.10


def test_review_status_exists():
    """Test: TopicStatus.REVIEW exists and equals 'review'."""
    assert TopicStatus.REVIEW == "review"
    assert "review" in [s.value for s in TopicStatus]
