"""Generic JSON file repository for Pydantic models."""

import json
import logging
import os
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

    def __init__(self, model_class: Type[T], directory: Path, id_field: str = "topic_id") -> None:
        self._model_class = model_class
        self._directory = directory
        self._id_field = id_field

    def save(self, entity: T) -> Path:
        """Save entity as JSON atomically. Overwrites if exists."""
        entity_id = getattr(entity, self._id_field)
        self._directory.mkdir(parents=True, exist_ok=True)
        file_path = self._directory / f"{entity_id}.json"
        tmp_file = self._directory / f".{entity_id}.tmp"
        try:
            tmp_file.write_text(entity.model_dump_json(indent=2), encoding="utf-8")
            os.replace(tmp_file, file_path)
            return file_path
        except Exception as e:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass
            logger.error("Failed to save %s to %s: %s", self._model_class.__name__, file_path, e)
            raise

    def _load_file(self, file_path: Path) -> Optional[T]:
        """Load and validate an entity from a JSON file.

        Handles 0-byte files, UTF-8 decoding with cp1252 fallback,
        and invalid JSON gracefully with structured warnings.
        """
        try:
            if not file_path.exists():
                return None
            if file_path.stat().st_size == 0:
                logger.warning(
                    "Encountered 0-byte JSON file for %s at %s",
                    self._model_class.__name__,
                    file_path,
                )
                return None
        except OSError as e:
            logger.warning("Filesystem access error for %s: %s", file_path, e)
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "UTF-8 decoding failed for %s, falling back to cp1252", file_path
            )
            try:
                content = file_path.read_text(encoding="cp1252")
            except Exception as e:
                logger.warning("Failed to decode %s with cp1252: %s", file_path, e)
                return None
        except OSError as e:
            logger.warning("Failed to read %s: %s", file_path, e)
            return None

        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                logger.warning("JSON content in %s is not an object", file_path)
                return None
            return self._model_class(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                "Failed to parse %s at %s: %s",
                self._model_class.__name__,
                file_path.name,
                e,
            )
            return None

    def list_all(self) -> List[T]:
        """Load all entities from the directory, skipping 0-byte and corrupted files."""
        items: List[T] = []
        if not self._directory.exists():
            return items
        for file_path in self._directory.glob("*.json"):
            item = self._load_file(file_path)
            if item is not None:
                items.append(item)
        return items

    def get(self, entity_id: str) -> Optional[T]:
        """Get a single entity by ID. Returns None if not found or corrupted."""
        file_path = self._directory / f"{entity_id}.json"
        if not file_path.exists():
            return None
        return self._load_file(file_path)

    def exists(self, entity_id: str) -> bool:
        """Check if an entity file exists on disk."""
        return (self._directory / f"{entity_id}.json").exists()

