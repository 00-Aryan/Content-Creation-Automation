from unittest.mock import MagicMock, patch

from content_creation.application import (
    ApplicationContext,
    BriefFailure,
    BriefGenerationResult,
    BriefGenerationService,
)
from content_creation.models.brief import Brief
from content_creation.models.topic import ScoredTopicItem


def test_brief_generation_service_orchestration(tmp_path):
    """Test that BriefGenerationService handles limits, filters, sorting, skipping, and exceptions."""
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

    mock_brief = Brief(
        topic_id="test-id-1",
        why_it_matters="Matters because test",
        plain_english_summary=["Summary 1", "Summary 2", "Summary 3"],
        student_takeaway="Takeaway",
        analogy="Analogy",
        limitation="Limit",
        audience_fit="Fit",
        recommended_formats=["short_video"],
        source_url="https://example.com/topic-1",
        review_status="draft",
        generated_at="2026-06-02T12:00:00Z",
    )

    service = BriefGenerationService()

    with patch(
        "content_creation.application.brief_generation_service.generate_brief"
    ) as mock_gen:
        mock_gen.return_value = mock_brief

        # Setup mock storage
        mock_storage = MagicMock()
        mock_storage.list_scored.return_value = [scored_item]
        # briefs_dir mock pointing to tmp_path so exists() check works correctly
        mock_storage.briefs_dir = tmp_path

        # Construct application context mock container
        mock_prompt_registry = MagicMock()
        ctx = MagicMock(
            storage=mock_storage,
            prompt_registry=mock_prompt_registry,
        )

        # Run service (rate_limit_delay = 0 to speed up test execution)
        result = service.run(
            ctx, top_n=5, api_key="dummy_api_key", rate_limit_delay=0.0
        )

        assert isinstance(result, BriefGenerationResult)
        assert result.generated_count == 1
        assert result.skipped_count == 0
        assert result.failures == []
        assert result.briefs == [mock_brief]

        # Verify orchestration calls
        mock_storage.list_scored.assert_called_once()
        mock_gen.assert_called_once_with(
            scored_item, mock_prompt_registry, "dummy_api_key"
        )
        mock_storage.save_brief.assert_called_once_with(mock_brief)
