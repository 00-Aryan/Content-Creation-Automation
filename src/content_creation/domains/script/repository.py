"""Script domain repository."""

from pathlib import Path

from content_creation.models.script import Script
from content_creation.platform.storage.json_repository import JsonRepository


class ScriptRepository(JsonRepository[Script]):
    """Repository for Script persistence."""

    def __init__(self, directory: Path):
        super().__init__(model_class=Script, directory=directory, id_field="topic_id")
