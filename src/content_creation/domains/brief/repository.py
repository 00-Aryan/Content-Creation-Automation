"""Brief domain repository."""

from pathlib import Path

from content_creation.models.brief import Brief
from content_creation.platform.storage.json_repository import JsonRepository


class BriefRepository(JsonRepository[Brief]):
    """Repository for Brief persistence."""

    def __init__(self, directory: Path):
        super().__init__(model_class=Brief, directory=directory, id_field="topic_id")
