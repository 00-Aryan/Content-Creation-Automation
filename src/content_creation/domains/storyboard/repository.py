"""Storyboard repository."""

from pathlib import Path

from content_creation.platform.storage import JsonRepository

from .model import Storyboard


class StoryboardRepository(JsonRepository[Storyboard]):
    def __init__(self, directory: Path):
        super().__init__(model_class=Storyboard, directory=directory, id_field="topic_id")
        self._directory.mkdir(parents=True, exist_ok=True)
