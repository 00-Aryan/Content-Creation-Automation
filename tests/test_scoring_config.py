"""Tests for scoring configuration."""

import pytest
from pydantic import ValidationError
from content_creation.scoring.config import ScoringConfig, RecencyConfig, SourceQualityConfig, KeywordConfig, QualityConfig


def test_scoring_config_total_weight_validation():
    """Test that ScoringConfig validates total weight of enabled rules."""
    
    # Valid weights (sum to 1.0)
    config = ScoringConfig(
        recency=RecencyConfig(weight=0.3, enabled=True),
        source_quality=SourceQualityConfig(weight=0.25, enabled=True),
        keywords=KeywordConfig(weight=0.25, enabled=True),
        quality=QualityConfig(weight=0.2, enabled=True)
    )
    assert config.get_total_weight() == 1.0
    
    # Invalid weights (sum to 0.8)
    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(
            recency=RecencyConfig(weight=0.3, enabled=True),
            source_quality=SourceQualityConfig(weight=0.2, enabled=True),
            keywords=KeywordConfig(weight=0.1, enabled=True),
            quality=QualityConfig(weight=0.2, enabled=True)
        )

    # Invalid weights (sum to 1.2)
    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(
            recency=RecencyConfig(weight=0.5, enabled=True),
            source_quality=SourceQualityConfig(weight=0.3, enabled=True),
            keywords=KeywordConfig(weight=0.2, enabled=True),
            quality=QualityConfig(weight=0.2, enabled=True)
        )

def test_scoring_config_partial_enabled_validation():
    """Test validation when some rules are disabled."""
    
    # Enabled sum to 1.0, one disabled
    config = ScoringConfig(
        recency=RecencyConfig(weight=0.5, enabled=True),
        source_quality=SourceQualityConfig(weight=0.5, enabled=True),
        keywords=KeywordConfig(weight=0.25, enabled=False),
        quality=QualityConfig(weight=0.2, enabled=False)
    )
    assert config.get_total_weight() == 1.0
    
    # Enabled sum to 0.5, others disabled
    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(
            recency=RecencyConfig(weight=0.5, enabled=True),
            source_quality=SourceQualityConfig(weight=0.25, enabled=False),
            keywords=KeywordConfig(weight=0.25, enabled=False),
            quality=QualityConfig(weight=0.2, enabled=False)
        )
