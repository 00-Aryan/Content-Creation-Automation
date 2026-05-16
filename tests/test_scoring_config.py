"""Tests for scoring configuration."""

from pathlib import Path

import pytest

from content_creation.scoring.config import RuleConfig, ScoringConfig, load_scoring_config


def _rule(weight: float, enabled: bool = True) -> RuleConfig:
    return RuleConfig(weight=weight, enabled=enabled)


def test_scoring_config_total_weight_validation():
    """Test that ScoringConfig validates total weight of enabled rules."""

    config_path = Path("config/scoring.yaml")
    config = load_scoring_config(config_path)
    assert config.get_total_weight() == 1.0

    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(
            student_usefulness=_rule(0.2),
            novelty=_rule(0.2),
            credibility=_rule(0.2),
            explainability=_rule(0.1),
            hook_potential=_rule(0.1),
        )

    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(
            student_usefulness=_rule(0.3),
            novelty=_rule(0.3),
            credibility=_rule(0.3),
            explainability=_rule(0.15),
            hook_potential=_rule(0.15),
        )


def test_scoring_config_partial_enabled_validation():
    """Test validation when some rules are disabled."""

    config = ScoringConfig(
        student_usefulness=_rule(0.6, enabled=True),
        novelty=_rule(0.4, enabled=True),
        credibility=_rule(0.2, enabled=False),
        explainability=_rule(0.15, enabled=False),
        hook_potential=_rule(0.1, enabled=False),
    )
    assert config.get_total_weight() == 1.0

    with pytest.raises(ValueError, match="Total enabled weights must sum to 1.0"):
        ScoringConfig(
            student_usefulness=_rule(0.5, enabled=True),
            novelty=_rule(0.25, enabled=False),
            credibility=_rule(0.25, enabled=False),
            explainability=_rule(0.15, enabled=False),
            hook_potential=_rule(0.1, enabled=False),
        )
