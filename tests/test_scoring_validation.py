"""Tests for scoring validation rules and quality checks."""

import pytest
from content_creation.models.topic import ScoredTopicItem, TopicCategory
from content_creation.scoring.config import ValidationConfig
from content_creation.scoring.validation import (
    ScoreConsistencyRule,
    SuspiciousScoreRule,
    MetadataCompletenessRule,
    ValidationEngine
)


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
        raw_text="Some raw text for testing.",
        excerpt="This is a test excerpt that is long enough.",
        category=TopicCategory.NEWS,
        total_score=50.0,
        recency_score=10.0,
        source_quality_score=20.0,
        keyword_score=10.0,
        quality_score=10.0,
        validation_flags=[]
    )


def test_score_consistency_rule_valid(validation_config, base_scored_item):
    """Test that consistent scores pass."""
    rule = ScoreConsistencyRule(validation_config)
    assert rule.validate(base_scored_item) is None


def test_score_consistency_rule_invalid(validation_config, base_scored_item):
    """Test that inconsistent scores are flagged."""
    base_scored_item.total_score = 100.0  # Sum is 50.0
    rule = ScoreConsistencyRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "Score inconsistency" in warning


def test_suspicious_score_rule_high(validation_config, base_scored_item):
    """Test flagging of suspiciously high scores."""
    base_scored_item.total_score = 95.0
    rule = SuspiciousScoreRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "Suspiciously high" in warning


def test_suspicious_score_rule_low(validation_config, base_scored_item):
    """Test flagging of suspiciously low scores."""
    base_scored_item.total_score = 5.0
    rule = SuspiciousScoreRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "Suspiciously low" in warning


def test_metadata_completeness_rule_missing_fields(validation_config, base_scored_item):
    """Test flagging of missing metadata for high-scoring items."""
    base_scored_item.total_score = 80.0
    base_scored_item.author = "unknown"
    base_scored_item.published_at = "unknown"
    
    rule = MetadataCompletenessRule(validation_config)
    warning = rule.validate(base_scored_item)
    assert warning is not None
    assert "missing published_at" in warning
    assert "missing author" in warning


def test_metadata_completeness_rule_ignored_for_low_scores(validation_config, base_scored_item):
    """Test that low-scoring items don't trigger completeness flags."""
    base_scored_item.total_score = 30.0
    base_scored_item.author = "unknown"
    
    rule = MetadataCompletenessRule(validation_config)
    assert rule.validate(base_scored_item) is None


def test_validation_engine_integration(validation_config, base_scored_item):
    """Test that ValidationEngine applies multiple rules."""
    base_scored_item.total_score = 95.0  # High score
    base_scored_item.author = "unknown"   # Missing metadata
    # Sum is 50.0, total is 95.0 -> Inconsistent
    
    engine = ValidationEngine(validation_config)
    validated_item = engine.validate_item(base_scored_item)
    
    assert len(validated_item.validation_flags) >= 3
    flags_str = " ".join(validated_item.validation_flags)
    assert "Suspiciously high" in flags_str
    assert "missing author" in flags_str
    assert "Score inconsistency" in flags_str
