"""Application dependency container for resource and configuration initialization."""

from dataclasses import dataclass
from pathlib import Path

from content_creation.prompts import PromptRegistry
from content_creation.storage.local import LocalStorage
from content_creation.workflow import WorkflowStateManager


@dataclass(frozen=True)
class ApplicationContext:
    """Application dependency injection container."""

    base_dir: Path
    storage: LocalStorage
    workflow: WorkflowStateManager
    prompt_registry: PromptRegistry
    feeds_config_path: Path
    scoring_config_path: Path

    @classmethod
    def create(cls, base_dir: Path) -> "ApplicationContext":
        """Factory method to bootstrap dependencies relative to base_dir."""
        storage = LocalStorage(base_dir)
        workflow = WorkflowStateManager(base_dir / "data" / "workflow_state")
        prompt_registry = PromptRegistry(base_dir)
        feeds_config_path = base_dir / "config" / "feeds.yaml"
        scoring_config_path = base_dir / "config" / "scoring.yaml"

        return cls(
            base_dir=base_dir,
            storage=storage,
            workflow=workflow,
            prompt_registry=prompt_registry,
            feeds_config_path=feeds_config_path,
            scoring_config_path=scoring_config_path,
        )

    @property
    def content_intelligence_dir(self) -> Path:
        """Directory path for content intelligence files."""
        return self.storage.content_intelligence_dir

    @property
    def storyboards_dir(self) -> Path:
        """Directory path for storyboard files."""
        return self.storage.storyboards_dir
