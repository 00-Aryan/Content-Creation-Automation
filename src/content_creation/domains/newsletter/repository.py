"""Newsletter domain repository."""

from pathlib import Path

from content_creation.models.newsletter import Newsletter
from content_creation.platform.storage.json_repository import JsonRepository


class NewsletterRepository(JsonRepository[Newsletter]):
    """Repository for Newsletter persistence."""

    def __init__(self, directory: Path):
        super().__init__(model_class=Newsletter, directory=directory, id_field="topic_id")
