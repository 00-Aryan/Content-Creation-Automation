"""Local filesystem storage backend — pure infrastructure, no domain models."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

logger = logging.getLogger(__name__)


class LocalBackend:
    """Filesystem operations for the local storage backend.

    This class owns infrastructure concerns only:
    - directory management
    - writeability verification
    - raw payload persistence
    - file existence checks

    It has zero domain model knowledge.
    """

    def __init__(self, base_dir: Path, directories: List[Path]):
        self.base_dir = base_dir
        self._directories = directories
        self._verify_writeable()
        self._ensure_dirs()

    def _verify_writeable(self):
        """Perform a robust writeability check using EAFP."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        test_file = self.base_dir / f".write_test_{datetime.now(timezone.utc).timestamp()}"
        try:
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()
        except (OSError, IOError) as e:
            raise OSError(f"Storage base directory {self.base_dir} is not writeable: {e}")

    def _ensure_dirs(self):
        """Ensure that all storage directories exist."""
        for directory in self._directories:
            directory.mkdir(parents=True, exist_ok=True)

    def save_raw(self, raw_dir: Path, source_id: str, data: Any):
        """Save raw payload with timestamp-based naming."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = raw_dir / f"{source_id}_{timestamp}.json"

        try:
            with open(file_path, "w") as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, indent=2)
                else:
                    f.write(str(data))
        except Exception as e:
            logger.error(f"Failed to save raw data to {file_path}: {e}")

    def exists(self, directory: Path, item_id: str) -> bool:
        """Check if a JSON file exists in the given directory."""
        return (directory / f"{item_id}.json").exists()
