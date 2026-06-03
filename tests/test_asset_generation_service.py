from unittest.mock import MagicMock, patch

from content_creation.application import (
    ApplicationContext,
    AssetGenerationResult,
    AssetGenerationService,
)
from content_creation.models.brief import Brief


def test_asset_generation_service_orchestration(tmp_path):
    """Test that AssetGenerationService routes formats, maps formats, interacts with workflow, and saves assets."""
    ctx = ApplicationContext.create(tmp_path)

    mock_brief = Brief(
        topic_id="test-id-1",
        why_it_matters="Matters because test",
        plain_english_summary=["Summary 1", "Summary 2", "Summary 3"],
        student_takeaway="Takeaway",
        analogy="Analogy",
        limitation="Limit",
        audience_fit="Fit",
        recommended_formats=["short_video", "carousel"],
        source_url="https://example.com/topic-1",
        review_status="draft",
        generated_at="2026-06-02T12:00:00Z",
    )

    service = AssetGenerationService()

    with patch(
        "content_creation.application.asset_generation_service.ThumbnailGenerator"
    ) as mock_thumb_cls, patch(
        "content_creation.application.asset_generation_service.ScriptGenerator"
    ) as mock_script_cls, patch(
        "content_creation.application.asset_generation_service.CarouselGenerator"
    ) as mock_carousel_cls, patch(
        "content_creation.application.asset_generation_service.NewsletterGenerator"
    ) as mock_news_cls:

        # Mock generator instances
        mock_thumb = MagicMock()
        mock_thumb_cls.return_value = mock_thumb
        mock_script = MagicMock()
        mock_script_cls.return_value = mock_script
        mock_carousel = MagicMock()
        mock_carousel_cls.return_value = mock_carousel
        mock_news = MagicMock()
        mock_news_cls.return_value = mock_news

        # Mock storage and directories
        mock_storage = MagicMock()
        mock_storage.list_briefs.return_value = [mock_brief]
        mock_storage.thumbnails_dir = tmp_path / "thumbnails"
        mock_storage.scripts_dir = tmp_path / "scripts"
        mock_storage.carousels_dir = tmp_path / "carousels"

        # Initialize folders to bypass path existence logic
        mock_storage.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        mock_storage.scripts_dir.mkdir(parents=True, exist_ok=True)
        mock_storage.carousels_dir.mkdir(parents=True, exist_ok=True)

        mock_workflow = MagicMock()
        # Mock initial run: no stages are completed
        mock_workflow.stage_completed.return_value = False

        # Construct application context mock container
        mock_prompt_registry = MagicMock()
        ctx = MagicMock(
            storage=mock_storage,
            workflow=mock_workflow,
            prompt_registry=mock_prompt_registry,
        )

        # Run service (rate_limit_delay = 0 to speed up test execution)
        result = service.run(
            ctx, top_n=5, api_key="dummy_api_key", rate_limit_delay=0.0
        )

        assert isinstance(result, AssetGenerationResult)
        assert result.counts["thumbnail"] == 1
        assert result.counts["script"] == 1
        assert result.counts["carousel"] == 1
        assert result.skipped_count == 0
        assert result.failed_count == 0

        # Verify generator instantiation
        mock_thumb_cls.assert_called_once_with("dummy_api_key", mock_prompt_registry)
        mock_script_cls.assert_called_once_with("dummy_api_key", mock_prompt_registry)
        mock_carousel_cls.assert_called_once_with("dummy_api_key", mock_prompt_registry)

        # Verify generation dispatch
        mock_thumb.generate.assert_called_once_with(mock_storage.get_storyboard.return_value, mock_brief)
        mock_script.generate.assert_called_once_with(mock_storage.get_storyboard.return_value, mock_brief, "short_video")
        mock_carousel.generate.assert_called_once_with(mock_storage.get_storyboard.return_value, mock_brief)
        mock_storage.get_storyboard.assert_called_once_with(mock_brief.topic_id)

        # Verify storage saves
        mock_storage.save_thumbnail.assert_called_once()
        mock_storage.save_script.assert_called_once()
        mock_storage.save_carousel.assert_called_once()

        # Verify workflow status updates
        mock_workflow.mark_completed.assert_any_call(
            "test-id-1",
            "thumbnail",
            artifact_path=str(mock_storage.thumbnails_dir / "test-id-1.json"),
        )
        mock_workflow.mark_completed.assert_any_call(
            "test-id-1",
            "script",
            artifact_path=str(mock_storage.scripts_dir / "test-id-1.json"),
        )
        mock_workflow.mark_completed.assert_any_call(
            "test-id-1",
            "carousel",
            artifact_path=str(mock_storage.carousels_dir / "test-id-1.json"),
        )
