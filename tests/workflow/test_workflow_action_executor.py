import pytest
from unittest.mock import MagicMock, patch

from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.states import ArtifactLifecycleState
from content_creation.workflow.workflow_action_executor import (
    WorkflowActionExecutor,
    ActionExecutionResult,
    ActionExecutionStatus,
)


@pytest.fixture
def mock_ctx():
    """Mock ApplicationContext with a mocked storage engine."""
    ctx = MagicMock()
    ctx.storage = MagicMock()
    ctx.base_dir = MagicMock()
    return ctx


@pytest.fixture
def mock_availability_engine():
    return MagicMock()


@pytest.fixture
def mock_transition_engine():
    return MagicMock()


def test_allowed_execution(mock_ctx, mock_availability_engine, mock_transition_engine):
    """Test that a valid action passes all checks and executes the underlying service."""
    mock_availability_engine.is_action_available.return_value = True
    
    # Mocking review transition engine for an approval step
    mock_val_result = MagicMock()
    mock_val_result.valid = True
    mock_transition_engine.validate_transition.return_value = mock_val_result

    executor = WorkflowActionExecutor(
        availability_engine=mock_availability_engine,
        transition_engine=mock_transition_engine,
    )

    # Mock the resolve methods to return desired mock state values
    executor._resolve_lifecycle_state = MagicMock(return_value=ArtifactLifecycleState.DRAFT)
    executor._resolve_dependencies = MagicMock(return_value={})
    
    # Mock dispatch to return a mock result
    mock_service_result = MagicMock()
    executor._dispatch_to_service = MagicMock(return_value=({"brief": "data/briefs/123.json"}, mock_service_result))

    result = executor.execute(
        ctx=mock_ctx,
        action_id="approve_brief",
        target_artifact_type="brief",
        target_artifact_id="topic_123",
        payload={},
        notes="All looks great!",
    )

    # Verifications
    assert result.success is True
    assert result.execution_status == ActionExecutionStatus.SUCCESS
    assert result.affected_artifacts == {"brief": "data/briefs/123.json"}
    assert result.raw_result == mock_service_result
    assert len(result.blocking_reasons) == 0
    assert result.execution_time > 0.0

    executor._dispatch_to_service.assert_called_once_with(
        mock_ctx, "approve_brief", "brief", "topic_123", {}, "All looks great!"
    )


def test_blocked_execution(mock_ctx, mock_availability_engine, mock_transition_engine):
    """Test that when availability engine blocks the action, it aborts without running the service."""
    mock_availability_engine.is_action_available.return_value = False
    mock_availability_engine.get_blocking_reasons.return_value = [
        MagicMock(blocking_message="Brief is not approved.")
    ]

    executor = WorkflowActionExecutor(
        availability_engine=mock_availability_engine,
        transition_engine=mock_transition_engine,
    )

    executor._resolve_lifecycle_state = MagicMock(return_value=ArtifactLifecycleState.MISSING)
    executor._resolve_dependencies = MagicMock(return_value={})
    executor._dispatch_to_service = MagicMock()

    result = executor.execute(
        ctx=mock_ctx,
        action_id="generate_storyboards",
        target_artifact_type="storyboard",
        target_artifact_id="topic_123",
        payload={},
    )

    # Verifications
    assert result.success is False
    assert result.execution_status == ActionExecutionStatus.BLOCKED
    assert "Brief is not approved." in result.blocking_reasons
    # The service was never called
    executor._dispatch_to_service.assert_not_called()


def test_transition_failures(mock_ctx, mock_availability_engine, mock_transition_engine):
    """Test that when transition graph validation fails, the action is blocked."""
    mock_availability_engine.is_action_available.return_value = True

    # Transition validation returns False
    mock_val_result = MagicMock()
    mock_val_result.valid = False
    mock_val_result.reason = "Cannot transition from APPROVED to REJECTED."
    mock_transition_engine.validate_transition.return_value = mock_val_result

    executor = WorkflowActionExecutor(
        availability_engine=mock_availability_engine,
        transition_engine=mock_transition_engine,
    )

    executor._resolve_lifecycle_state = MagicMock(return_value=ArtifactLifecycleState.APPROVED)
    executor._resolve_dependencies = MagicMock(return_value={})
    executor._dispatch_to_service = MagicMock()

    result = executor.execute(
        ctx=mock_ctx,
        action_id="reject_brief",
        target_artifact_type="brief",
        target_artifact_id="topic_123",
        payload={},
    )

    # Verifications
    assert result.success is False
    assert result.execution_status == ActionExecutionStatus.BLOCKED
    assert "Cannot transition from APPROVED to REJECTED." in result.blocking_reasons
    # The service was never called
    executor._dispatch_to_service.assert_not_called()


def test_dependency_failures(mock_ctx, mock_availability_engine, mock_transition_engine):
    """Test that a dependency check failure correctly blocks execution and details the reason."""
    mock_availability_engine.is_action_available.return_value = False
    mock_availability_engine.get_blocking_reasons.return_value = [
        MagicMock(blocking_message="Upstream storyboard must be APPROVED.")
    ]

    executor = WorkflowActionExecutor(
        availability_engine=mock_availability_engine,
        transition_engine=mock_transition_engine,
    )

    # We simulate storyboard missing/draft dependency
    executor._resolve_lifecycle_state = MagicMock(return_value=ArtifactLifecycleState.MISSING)
    executor._resolve_dependencies = MagicMock(return_value={"storyboard": ArtifactLifecycleState.DRAFT})
    executor._dispatch_to_service = MagicMock()

    result = executor.execute(
        ctx=mock_ctx,
        action_id="generate_assets",
        target_artifact_type="assets",
        target_artifact_id="topic_123",
        payload={},
    )

    # Verifications
    assert result.success is False
    assert result.execution_status == ActionExecutionStatus.BLOCKED
    assert "Upstream storyboard must be APPROVED." in result.blocking_reasons
    executor._dispatch_to_service.assert_not_called()


def test_result_generation_fields():
    """Verify that ActionExecutionResult captures all necessary architecture model fields."""
    result = ActionExecutionResult(
        action_id="collect",
        success=True,
        execution_status=ActionExecutionStatus.SUCCESS,
        affected_artifacts={"staged": "data/staging/1.json"},
        warnings=["Rate limit delay applied"],
        blocking_reasons=[],
        execution_time=1.25,
        emitted_events=["event_123"],
        raw_result="MockRaw"
    )

    assert result.action_id == "collect"
    assert result.success is True
    assert result.execution_status == ActionExecutionStatus.SUCCESS
    assert result.affected_artifacts == {"staged": "data/staging/1.json"}
    assert result.warnings == ["Rate limit delay applied"]
    assert result.blocking_reasons == []
    assert result.execution_time == 1.25
    assert result.emitted_events == ["event_123"]
    assert result.raw_result == "MockRaw"

    d = result.to_dict()
    assert d["success"] is True
    assert d["execution_status"] == "success"


def test_run_pipeline_execution(mock_ctx, mock_availability_engine, mock_transition_engine):
    """Test that run_pipeline action dispatches to PipelineRunService."""
    mock_availability_engine.is_action_available.return_value = True

    executor = WorkflowActionExecutor(
        availability_engine=mock_availability_engine,
        transition_engine=mock_transition_engine,
    )

    executor._resolve_lifecycle_state = MagicMock(return_value=ArtifactLifecycleState.DRAFT)
    executor._resolve_dependencies = MagicMock(return_value={})

    mock_run_result = MagicMock()
    mock_run_result.log_path = MagicMock()

    with patch("content_creation.application.pipeline_run_service.PipelineRunService") as mock_pipeline_cls:
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.run.return_value = mock_run_result
        mock_pipeline_cls.return_value = mock_pipeline_instance

        result = executor.execute(
            ctx=mock_ctx,
            action_id="run_pipeline",
            target_artifact_type="manifest",
            target_artifact_id="all",
            payload={"top_n": 5, "source": "test_src", "auto_approve": True, "api_key": "test_key"},
        )

        assert result.success is True
        assert result.execution_status == ActionExecutionStatus.SUCCESS
        assert result.raw_result == mock_run_result
        mock_pipeline_cls.assert_called_once()
        mock_pipeline_instance.run.assert_called_once_with(
            mock_ctx,
            top_n=5,
            source_filter="test_src",
            auto_approve=True,
            api_key="test_key",
        )
