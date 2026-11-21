"""Shared CLI helpers, context management, date utilities, and export helpers."""

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from content_creation.application.context import ApplicationContext
from content_creation.storage.local import LocalStorage

logger = logging.getLogger(__name__)


def get_context(base_dir: Optional[Path] = None) -> ApplicationContext:
    """Create ApplicationContext for CLI operations.

    Delegates storage instantiation through content_creation.cli to allow
    test mocking while preserving layer isolation.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Import LocalStorage via content_creation.cli to respect test mocks
    import content_creation.cli

    storage = content_creation.cli.LocalStorage(base_dir)

    from content_creation.prompts import PromptRegistry
    from content_creation.workflow import WorkflowStateManager

    workflow = WorkflowStateManager(base_dir / "data" / "workflow_state")
    prompt_registry = PromptRegistry(base_dir)
    feeds_config_path = base_dir / "config" / "feeds.yaml"
    scoring_config_path = base_dir / "config" / "scoring.yaml"

    return ApplicationContext(
        base_dir=base_dir,
        storage=storage,
        workflow=workflow,
        prompt_registry=prompt_registry,
        feeds_config_path=feeds_config_path,
        scoring_config_path=scoring_config_path,
    )


def get_next_monday(start_date: Optional[date] = None) -> date:
    """Calculate the next Monday relative to start_date or today.

    Eliminates duplicated timedelta math across plan-week, dry-run,
    and init-analytics commands.
    """
    if start_date is None:
        today = datetime.now(timezone.utc).date()
    else:
        today = start_date

    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return today + timedelta(days=days_until_monday)


def write_text_utf8(path: Path, content: str) -> None:
    """Safely write text to file enforcing UTF-8 encoding.

    Ensures Windows CP1252 default encoding never corrupts Unicode characters
    or em-dashes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
