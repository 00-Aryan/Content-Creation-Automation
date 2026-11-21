"""Regression tests for scoring validation rules and float rounding tolerance."""

from content_creation.models.topic import ScoredTopicItem, TopicCategory
from content_creation.scoring.config import ValidationConfig
from content_creation.scoring.validation import ScoreConsistencyRule


def test_score_consistency_rule_tolerates_float_rounding_drift():
    """Covers ERR-007: priority_score floating-point sum tolerance within 0.05."""
    config = ValidationConfig(check_consistency=True)
    rule = ScoreConsistencyRule(config)

    # Component scores sum to 65.76, priority_score is 65.75 (diff = 0.01)
    item = ScoredTopicItem(
        id="t1",
        title="Test Topic",
        url="https://example.com/item",
        source="arxiv",
        published_at="2026-04-30T12:00:00Z",
        raw_text="Machine learning research summary " * 5,
        category=TopicCategory.PAPER,
        priority_score=65.75,
        student_usefulness_score=13.15,
        novelty_score=13.15,
        credibility_score=13.15,
        explainability_score=13.15,
        hook_potential_score=13.16,
    )
    # Diff is 0.01 (within 0.05 tolerance) -> no false positive warning
    assert rule.validate(item) is None

    # Genuine score inconsistency (> 0.05) must still be flagged
    item.priority_score = 70.0
    warning = rule.validate(item)
    assert warning is not None
    assert "Score inconsistency" in warning
