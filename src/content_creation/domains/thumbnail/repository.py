"""Thumbnail domain repository."""

from pathlib import Path

from content_creation.models.thumbnail import ThumbnailPrompt
from content_creation.platform.storage.json_repository import JsonRepository


class ThumbnailRepository(JsonRepository[ThumbnailPrompt]):
    """Repository for ThumbnailPrompt persistence."""

    def __init__(self, directory: Path):
        super().__init__(model_class=ThumbnailPrompt, directory=directory, id_field="topic_id")
