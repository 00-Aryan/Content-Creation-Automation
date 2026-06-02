from pathlib import Path

from content_creation.application.context import ApplicationContext
from content_creation.prompts import PromptRegistry
from content_creation.storage.local import LocalStorage
from content_creation.workflow import WorkflowStateManager


def test_application_context_creation(tmp_path):
    """Test that ApplicationContext builds dependencies correctly relative to tmp_path."""
    ctx = ApplicationContext.create(tmp_path)

    assert ctx.base_dir == tmp_path
    assert isinstance(ctx.storage, LocalStorage)
    assert isinstance(ctx.workflow, WorkflowStateManager)
    assert isinstance(ctx.prompt_registry, PromptRegistry)
    assert ctx.feeds_config_path == tmp_path / "config" / "feeds.yaml"
    assert ctx.scoring_config_path == tmp_path / "config" / "scoring.yaml"
