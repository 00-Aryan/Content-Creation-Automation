"""Helper script to clear old generated/staged RSS artifacts under data/ while preserving directory structure."""

import os
from pathlib import Path
import shutil


TARGET_DIRS = [
    "staged",
    "scored",
    "briefs",
    "content_intelligence",
    "storyboards",
    "scripts",
    "carousels",
    "newsletters",
    "thumbnails",
    "manifests",
    "workflow_state",
    "review_history",
]

TARGET_FILES = [
    "content_factory.db",
    "content_factory.db-wal",
    "content_factory.db-shm",
    "jobs.db",
    "events.db",
    "locks.db",
    "metrics.db",
    "notifications.db",
    "audit.db",
]


def clean_data_dir(data_dir: Path) -> None:
    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist. Nothing to clean.")
        return

    total_files_removed = 0

    # Clean target directories
    for dir_name in TARGET_DIRS:
        folder = data_dir / dir_name
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            # Add .gitkeep if missing
            gitkeep = folder / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()
            continue

        for item in folder.iterdir():
            if item.name == ".gitkeep":
                continue
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    total_files_removed += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    total_files_removed += 1
            except Exception as e:
                print(f"Warning: Failed to remove {item}: {e}")

        # Ensure .gitkeep is preserved/created
        gitkeep = folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    # Clean target database files
    for file_name in TARGET_FILES:
        target_file = data_dir / file_name
        if target_file.exists():
            try:
                target_file.unlink()
                total_files_removed += 1
                print(f"Removed database file: {file_name}")
            except Exception as e:
                print(f"Warning: Failed to remove database {file_name}: {e}")

    print(f"Clean complete! Removed {total_files_removed} items across data directories.")


def main() -> None:
    root_env = os.environ.get("CONTENT_FACTORY_ROOT")
    if root_env:
        base_dir = Path(root_env)
    else:
        base_dir = Path(__file__).resolve().parent.parent

    data_dir = base_dir / "data"
    print(f"Cleaning data directory at: {data_dir}")
    clean_data_dir(data_dir)


if __name__ == "__main__":
    main()
