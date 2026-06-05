from unittest.mock import MagicMock, patch

from content_creation.application import (
    ApplicationContext,
    PipelineRunResult,
    PipelineRunService,
)


def test_pipeline_run_service_success_orchestration(tmp_path):
    """Test that PipelineRunService runs all stages sequentially and compiles results upon success."""
    service = PipelineRunService()

    with patch("content_creation.workflow.workflow_action_executor.WorkflowActionExecutor") as mock_executor_cls:
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        call_order = []

        # Mock execute side effect for each action
        def mock_execute(ctx, action_id, target_artifact_type, target_artifact_id, payload, notes=None):
            call_order.append(action_id)
            if action_id == "collect":
                res = MagicMock(count=5)
                return MagicMock(success=True, raw_result=res)
            elif action_id == "score_topics":
                res = MagicMock(scored_count=3, rejected_count=1)
                return MagicMock(success=True, raw_result=res)
            elif action_id == "generate_briefs":
                res = MagicMock(generated_count=2, skipped_count=0, failures=[])
                return MagicMock(success=True, raw_result=res)
            elif action_id == "generate_ci":
                res = MagicMock(generated_count=2, skipped_count=0, failures=[])
                return MagicMock(success=True, raw_result=res)
            elif action_id == "generate_storyboards":
                res = MagicMock(generated_count=2, skipped_count=0, failures=[])
                return MagicMock(success=True, raw_result=res)
            elif action_id == "generate_assets":
                res = MagicMock(counts={"thumbnail": 1}, skipped_count=0, failed_count=0)
                return MagicMock(success=True, raw_result=res)
            elif action_id == "build_all_manifests":
                res = []
                return MagicMock(success=True, raw_result=res)
            elif action_id == "batch_approve":
                return MagicMock(success=True, raw_result=0)
            return MagicMock(success=False, blocking_reasons=["Unknown action"])

        mock_executor.execute.side_effect = mock_execute

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
        assert call_order == [
            "collect",
            "score_topics",
            "generate_briefs",
            "generate_ci",
            "generate_storyboards",
            "generate_assets",
            "build_all_manifests",
        ]


def test_pipeline_run_service_auto_approve(tmp_path):
    """Test that PipelineRunService runs batch_approve stage if auto_approve is True."""
    service = PipelineRunService()

    with patch("content_creation.workflow.workflow_action_executor.WorkflowActionExecutor") as mock_executor_cls:
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        call_order = []

        def mock_execute(ctx, action_id, target_artifact_type, target_artifact_id, payload, notes=None):
            call_order.append(action_id)
            if action_id == "collect":
                return MagicMock(success=True, raw_result=MagicMock(count=1))
            elif action_id == "score_topics":
                return MagicMock(success=True, raw_result=MagicMock(scored_count=1, rejected_count=0))
            elif action_id == "generate_briefs":
                return MagicMock(success=True, raw_result=MagicMock(generated_count=1, skipped_count=0, failures=[]))
            elif action_id == "generate_ci":
                return MagicMock(success=True, raw_result=MagicMock(generated_count=1, skipped_count=0, failures=[]))
            elif action_id == "generate_storyboards":
                return MagicMock(success=True, raw_result=MagicMock(generated_count=1, skipped_count=0, failures=[]))
            elif action_id == "generate_assets":
                return MagicMock(success=True, raw_result=MagicMock(counts={"thumbnail": 1}, skipped_count=0, failed_count=0))
            elif action_id == "build_all_manifests":
                return MagicMock(success=True, raw_result=[])
            elif action_id == "batch_approve":
                return MagicMock(success=True, raw_result=4)
            return MagicMock(success=False, blocking_reasons=["Unknown action"])

        mock_executor.execute.side_effect = mock_execute

        mock_storage = MagicMock()
        mock_storage.logs_dir = tmp_path / "logs"
        ctx = MagicMock(storage=mock_storage)

        # Run
        result = service.run(
            ctx, top_n=5, auto_approve=True, api_key="dummy_key"
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
            "batch-approve",
        ]
        assert result.stage_summaries["batch-approve"]["approved_count"] == 4
        assert call_order == [
            "collect",
            "score_topics",
            "generate_briefs",
            "generate_ci",
            "generate_storyboards",
            "generate_assets",
            "build_all_manifests",
            "batch_approve",
        ]


def test_pipeline_run_service_failure_halts_downstream(tmp_path):
    """Test that PipelineRunService halts downstream execution if a stage raises an exception."""
    service = PipelineRunService()

    with patch("content_creation.workflow.workflow_action_executor.WorkflowActionExecutor") as mock_executor_cls:
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        # First execution returns failure
        mock_executor.execute.return_value = MagicMock(success=False, blocking_reasons=["Collect failed!"])

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
