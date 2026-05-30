"""Carousel domain repository."""

from pathlib import Path

from content_creation.models.carousel import Carousel
from content_creation.platform.storage.json_repository import JsonRepository


class CarouselRepository(JsonRepository[Carousel]):
    """Repository for Carousel persistence."""

    def __init__(self, directory: Path):
        super().__init__(model_class=Carousel, directory=directory, id_field="topic_id")
