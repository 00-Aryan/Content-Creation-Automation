"""Application dependency container for resource and configuration initialization."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
    db_path: Path = Path("data") / "content_factory.db"

    def __post_init__(self) -> None:
        if self.db_path == Path("data") / "content_factory.db":
            object.__setattr__(self, "db_path", self.base_dir / "data" / "content_factory.db")

    @classmethod
    def create(cls, base_dir: Path, source_dir: Optional[Path] = None) -> "ApplicationContext":
        """Factory method to bootstrap dependencies relative to base_dir.

        Args:
            base_dir: Root directory for data storage (workflow state, artifacts).
                      On Render, this points to the persistent disk mount.
            source_dir: Root directory for source code (config files, prompt templates).
                        Defaults to base_dir for backward compatibility.
                        On Render, this points to the immutable code directory.
        """
        if source_dir is None:
            source_dir = base_dir

        storage = LocalStorage(base_dir)
        workflow = WorkflowStateManager(base_dir / "data" / "workflow_state")
        prompt_registry = PromptRegistry(source_dir)
        feeds_config_path = source_dir / "config" / "feeds.yaml"
        scoring_config_path = source_dir / "config" / "scoring.yaml"
        db_path = base_dir / "data" / "content_factory.db"

        return cls(
            base_dir=base_dir,
            storage=storage,
            workflow=workflow,
            prompt_registry=prompt_registry,
            feeds_config_path=feeds_config_path,
            scoring_config_path=scoring_config_path,
            db_path=db_path,
        )

    def get_db_connection(
        self, timeout: float = 10.0, check_same_thread: bool = False
    ) -> sqlite3.Connection:
        """Create a SQLite connection to content_factory.db with WAL pragmas."""
        from content_creation.platform.storage.database import create_connection

        return create_connection(self.db_path, timeout=timeout, check_same_thread=check_same_thread)

    def __getattr__(self, name: str) -> Path:
        if name == "content_intelligence_dir":
            return self.storage.content_intelligence_dir
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    @property
    def storyboards_dir(self) -> Path:
        """Directory path for storyboard files."""
        return self.storage.storyboards_dir
