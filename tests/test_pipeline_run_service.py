from unittest.mock import MagicMock, patch

from content_creation.application import (
    ApplicationContext,
    PipelineRunResult,
    PipelineRunService,
)


def test_pipeline_run_service_success_orchestration(tmp_path):
    """Test that PipelineRunService runs all stages sequentially and compiles results upon success."""
    service = PipelineRunService()

    # Mock all inner service calls
    with patch(
        "content_creation.application.pipeline_run_service.CollectTopicsService"
    ) as mock_collect_cls, patch(
        "content_creation.application.pipeline_run_service.ScoreTopicsService"
    ) as mock_score_cls, patch(
        "content_creation.application.pipeline_run_service.BriefGenerationService"
    ) as mock_brief_cls, patch(
        "content_creation.application.pipeline_run_service.ContentIntelligenceService"
    ) as mock_ci_cls, patch(
        "content_creation.application.pipeline_run_service.StoryboardService"
    ) as mock_storyboard_cls, patch(
        "content_creation.application.pipeline_run_service.AssetGenerationService"
    ) as mock_asset_cls, patch(
        "content_creation.application.pipeline_run_service.ManifestBuilder"
    ) as mock_manifest_builder_cls:

        call_order = []

        # Mock results
        mock_collect = MagicMock()
        mock_collect.run.side_effect = lambda *args, **kwargs: (
            call_order.append("collect") or MagicMock(count=5)
        )
        mock_collect_cls.return_value = mock_collect

        mock_score = MagicMock()
        mock_score.run.side_effect = lambda *args, **kwargs: (
            call_order.append("score")
            or MagicMock(scored_count=3, rejected_count=1)
        )
        mock_score_cls.return_value = mock_score

        mock_brief = MagicMock()
        mock_brief.run.side_effect = lambda *args, **kwargs: (
            call_order.append("brief")
            or MagicMock(generated_count=2, skipped_count=0, failures=[])
        )
        mock_brief_cls.return_value = mock_brief

        mock_ci = MagicMock()
        mock_ci.run.side_effect = lambda *args, **kwargs: (
            call_order.append("content_intelligence")
            or MagicMock(generated_count=2, skipped_count=0, failures=[])
        )
        mock_ci_cls.return_value = mock_ci

        mock_storyboard = MagicMock()
        mock_storyboard.run.side_effect = lambda *args, **kwargs: (
            call_order.append("storyboard")
            or MagicMock(generated_count=2, skipped_count=0, failures=[])
        )
        mock_storyboard_cls.return_value = mock_storyboard

        mock_asset = MagicMock()
        mock_asset.run.side_effect = lambda *args, **kwargs: (
            call_order.append("assets")
            or MagicMock(counts={"thumbnail": 1}, skipped_count=0, failed_count=0)
        )
        mock_asset_cls.return_value = mock_asset

        mock_manifest_builder = MagicMock()
        mock_manifest_builder.build_all.return_value = []
        mock_manifest_builder_cls.return_value = mock_manifest_builder

        # Mock storage paths inside context
        mock_storage = MagicMock()
        mock_storage.logs_dir = tmp_path / "logs"
        ctx = MagicMock(storage=mock_storage)

        # Run
        result = service.run(
            ctx, top_n=5, auto_approve=False, api_key="dummy_key"
        )

        assert isinstance(result, PipelineRunResult)
        assert result.success is True
        assert result.stages == [
            "collect",
            "score",
            "generate-briefs",
            "generate-content-intelligence",
            "generate-storyboards",
            "generate-assets",
            "build-manifests",
        ]

        # Verify the sequence of calls
        mock_collect.run.assert_called_once_with(ctx, source_filter=None)
        mock_score.run.assert_called_once_with(ctx)
        mock_brief.run.assert_called_once_with(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=5.0
        )
        mock_ci.run.assert_called_once_with(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=5.0
        )
        mock_storyboard.run.assert_called_once_with(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=5.0
        )
        mock_asset.run.assert_called_once_with(
            ctx, top_n=5, api_key="dummy_key", rate_limit_delay=5.0
        )
        mock_manifest_builder.build_all.assert_called_once()

        assert call_order == [
            "collect",
            "score",
            "brief",
            "content_intelligence",
            "storyboard",
            "assets",
        ]


def test_pipeline_run_service_failure_halts_downstream(tmp_path):
    """Test that PipelineRunService halts downstream execution if a stage raises an exception."""
    service = PipelineRunService()

    with patch(
        "content_creation.application.pipeline_run_service.CollectTopicsService"
    ) as mock_collect_cls, patch(
        "content_creation.application.pipeline_run_service.ScoreTopicsService"
    ) as mock_score_cls:

        # Stage 1 (Collect) throws exception
        mock_collect = MagicMock()
        mock_collect.run.side_effect = RuntimeError("Collect failed!")
        mock_collect_cls.return_value = mock_collect

        mock_score = MagicMock()
        mock_score_cls.return_value = mock_score

        mock_storage = MagicMock()
        mock_storage.logs_dir = tmp_path / "logs"
        ctx = MagicMock(storage=mock_storage)

        result = service.run(
            ctx, top_n=5, auto_approve=False, api_key="dummy_key"
        )

        assert isinstance(result, PipelineRunResult)
        assert result.success is False
        assert result.stages == ["collect"]  # Halts after collect stage
        assert result.stage_summaries["collect"]["success"] is False
        assert "Collect failed!" in result.stage_summaries["collect"]["error"]

        # Ensure score stage was never executed
        mock_score.run.assert_not_called()
