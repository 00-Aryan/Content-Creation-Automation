from unittest.mock import MagicMock, patch

from content_creation.application import ApplicationContext, ScoreResult, ScoreTopicsService
from content_creation.models.topic import ScoredTopicItem, TopicItem


def test_score_topics_service_orchestration(tmp_path):
    """Test that ScoreTopicsService properly orchestrates config loading, list/save, and engine execution."""
    staged_item = TopicItem(
        id="test-id-1",
        title="Ingested Topic Title",
        url="https://example.com/topic-1",
        source="arxiv",
        published_at="2026-06-02T12:00:00Z",
        author="John Doe",
        raw_text="Canonical topic content representation.",
        status="staged",
    )

    scored_item = ScoredTopicItem(
        id="test-id-1",
        title="Ingested Topic Title",
        url="https://example.com/topic-1",
        source="arxiv",
        published_at="2026-06-02T12:00:00Z",
        author="John Doe",
        raw_text="Canonical topic content representation.",
        status="scored",
        priority_score=8.5,
        scoring_details={"relevance": 8.0, "novelty": 9.0},
        validation_flags=[],
    )

    service = ScoreTopicsService()

    with patch(
        "content_creation.application.score_topics_service.load_scoring_config"
    ) as mock_load_config, patch(
        "content_creation.application.score_topics_service.ScoringEngine"
    ) as mock_scoring_engine_cls, patch(
        "content_creation.application.score_topics_service.ValidationEngine"
    ) as mock_val_engine_cls:

        mock_config = MagicMock()
        mock_config.validation = MagicMock()
        mock_load_config.return_value = mock_config

        # Setup mock storage
        mock_storage = MagicMock()
        mock_storage.list_staged.return_value = [staged_item]

        # Construct application context mock container
        ctx = MagicMock(
            storage=mock_storage,
            scoring_config_path=tmp_path / "config" / "scoring.yaml",
        )

        mock_scorer = MagicMock()
        mock_scorer.score_items.return_value = {
            "scored": [scored_item],
            "rejected": [],
        }
        mock_scoring_engine_cls.return_value = mock_scorer

        mock_validator = MagicMock()
        mock_validator.validate_item.return_value = scored_item
        mock_val_engine_cls.return_value = mock_validator

        result = service.run(ctx, limit=5)

        assert isinstance(result, ScoreResult)
        assert result.scored_count == 1
        assert result.rejected_count == 0
        assert result.items == [scored_item]

        # Verify calls and boundaries
        mock_load_config.assert_called_once_with(ctx.scoring_config_path)
        mock_storage.list_staged.assert_called_once()
        mock_scoring_engine_cls.assert_called_once_with(mock_config)
        mock_scorer.score_items.assert_called_once_with([staged_item])
        mock_val_engine_cls.assert_called_once_with(mock_config.validation)
        mock_validator.validate_item.assert_called_once_with(scored_item)
        mock_storage.save_scored.assert_called_once_with(scored_item)
