"""Generic JSON file repository for Pydantic models."""

import json
import logging
from pathlib import Path
from typing import Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class JsonRepository(Generic[T]):
    """Generic repository for persisting Pydantic models as JSON files.

    Parameterized by:
        model_class: The Pydantic model to serialize/deserialize.
        directory: Filesystem directory for storage.
        id_field: Attribute name used as the file key.
    """

    def __init__(self, model_class: Type[T], directory: Path, id_field: str = "topic_id"):
        self._model_class = model_class
        self._directory = directory
        self._id_field = id_field

    def save(self, entity: T) -> Path:
        """Save entity as JSON. Overwrites if exists."""
        entity_id = getattr(entity, self._id_field)
        file_path = self._directory / f"{entity_id}.json"
        try:
            with open(file_path, "w") as f:
                f.write(entity.model_dump_json(indent=2))
            return file_path
        except Exception as e:
            logger.error(f"Failed to save {self._model_class.__name__} to {file_path}: {e}")
            raise

    def list_all(self) -> List[T]:
        """Load all entities from the directory."""
        items: List[T] = []
        for file_path in self._directory.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                items.append(self._model_class(**data))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning("Failed to load %s %s: %s", self._model_class.__name__, file_path.name, e)
        return items

    def get(self, entity_id: str) -> Optional[T]:
        """Get a single entity by ID. Returns None if not found."""
        file_path = self._directory / f"{entity_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return self._model_class(**data)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error("Failed to load %s %s: %s", self._model_class.__name__, entity_id, e)
            return None

    def exists(self, entity_id: str) -> bool:
        """Check if an entity exists."""
        return (self._directory / f"{entity_id}.json").exists()
