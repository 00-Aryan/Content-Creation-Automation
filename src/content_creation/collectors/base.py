"""Base collector interface."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from content_creation.models.topic import TopicItem

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for all source collectors."""

    def __init__(self, source_config: Dict[str, Any]):
        self.config = source_config
        self.source_id = source_config.get("id")
        self.source_name = source_config.get("source")

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch raw data from the source."""
        pass

    @abstractmethod
    def parse(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Parse raw data into a list of record dictionaries."""
        pass

    @abstractmethod
    def normalize(self, record: Dict[str, Any]) -> TopicItem:
        """Normalize a single record into a TopicItem."""
        pass

    def collect(self) -> List[TopicItem]:
        """Orchestrate the collection process."""
        try:
            raw_data = self.fetch()
            records = self.parse(raw_data)
        except Exception as e:
            logger.error(f"Failed to fetch or parse data for {self.source_id}: {e}")
            return []

        items = []
        for record in records:
            try:
                item = self.normalize(record)
                items.append(item)
            except Exception as e:
                logger.warning(f"Error normalizing record in {self.source_id}: {e}")
        return items
