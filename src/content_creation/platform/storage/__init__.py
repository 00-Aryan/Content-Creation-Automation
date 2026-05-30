"""Platform storage infrastructure."""

from content_creation.platform.storage.local_backend import LocalBackend
from content_creation.platform.storage.json_repository import JsonRepository

__all__ = ["LocalBackend", "JsonRepository"]
