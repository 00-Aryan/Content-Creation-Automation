"""Local file system storage for raw and staged data."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from content_creation.models.topic import ScoredTopicItem, TopicItem

logger = logging.getLogger(__name__)


class LocalStorage:
    """Handles persistence of raw and staged data to the local file system."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.raw_dir = base_dir / "data" / "raw"
        self.staged_dir = base_dir / "data" / "staged"
        self.scored_dir = base_dir / "data" / "scored"
        
        self._verify_writeable()
        self._ensure_dirs()

    def _verify_writeable(self):
        """Perform a robust writeability check using EAFP."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        test_file = self.base_dir / f".write_test_{datetime.now().timestamp()}"
        try:
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()
        except (OSError, IOError) as e:
            raise OSError(f"Storage base directory {self.base_dir} is not writeable: {e}")

    def _ensure_dirs(self):
        """Ensure that storage directories exist."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.staged_dir.mkdir(parents=True, exist_ok=True)
        self.scored_dir.mkdir(parents=True, exist_ok=True)

    def save_raw(self, source_id: str, data: Any):
        """Save raw payload to data/raw/."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.raw_dir / f"{source_id}_{timestamp}.json"
        
        try:
            with open(file_path, "w") as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, indent=2)
                else:
                    f.write(str(data))
        except Exception as e:
            logger.error(f"Failed to save raw data to {file_path}: {e}")

    def save_staged(self, item: TopicItem):
        """Save a normalized TopicItem to data/staged/.
        
        Uses mode 'x' for atomic creation to prevent race conditions during concurrent ingestion.
        Note: Atomic deduplication is guaranteed for writes on the same local filesystem target;
        other storage backends may require a different locking strategy.
        """
        file_path = self.staged_dir / f"{item.id}.json"
        try:
            with open(file_path, "x") as f:
                f.write(item.model_dump_json(indent=2))
        except FileExistsError:
            # Re-raise so ingestion engine can handle it as a duplicate
            raise
        except Exception as e:
            logger.error(f"Failed to save staged item to {file_path}: {e}")

    def save_scored(self, item: ScoredTopicItem):
        """Save a scored TopicItem to data/scored/."""
        file_path = self.scored_dir / f"{item.id}.json"
        try:
            with open(file_path, "w") as f:
                f.write(item.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save scored item to {file_path}: {e}")

    def list_staged(self) -> List[TopicItem]:
        """List all staged items."""
        items = []
        for file_path in self.staged_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(TopicItem(**data))
            except Exception as e:
                logger.warning(f"Failed to load staged item {file_path}: {e}")
        return items

    def list_scored(self) -> List[ScoredTopicItem]:
        """List all scored items."""
        items = []
        for file_path in self.scored_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(ScoredTopicItem(**data))
            except Exception as e:
                logger.warning(f"Failed to load scored item {file_path}: {e}")
        return items

    def get_staged(self, item_id: str) -> Optional[TopicItem]:
        """Get a specific staged item by ID."""
        file_path = self.staged_dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return TopicItem(**data)
        except Exception as e:
            logger.error(f"Failed to load staged item {file_path}: {e}")
            return None

    def get_scored(self, item_id: str) -> Optional[ScoredTopicItem]:
        """Get a specific scored item by ID."""
        file_path = self.scored_dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return ScoredTopicItem(**data)
        except Exception as e:
            logger.error(f"Failed to load scored item {file_path}: {e}")
            return None

    def exists(self, item_id: str) -> bool:
        """Check if an item already exists in staged storage."""
        return (self.staged_dir / f"{item_id}.json").exists()

    def scored_exists(self, item_id: str) -> bool:
        """Check if a scored item already exists in scored storage."""
        return (self.scored_dir / f"{item_id}.json").exists()
