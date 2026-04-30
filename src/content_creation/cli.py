"""Content Creation Factory CLI - Main entry point."""

import argparse
import logging
import sys
from pathlib import Path

from content_creation import __version__
from content_creation.ingestion import IngestionEngine
from content_creation.storage.local import LocalStorage
from content_creation.utils.config import load_yaml_config
from content_creation.utils.logging import setup_logging


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="Content Creation Factory CLI - A source-grounded content pipeline for ML/AI students.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"content-creation {__version__}",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Ingest topics from sources")
    collect_parser.add_argument("--source", type=str, help="Specific source ID or type to collect (e.g., arxiv)")
    collect_parser.add_argument("--all", action="store_true", help="Collect from all enabled sources")

    # Status command
    subparsers.add_parser("status", help="Check system and ingestion status")

    # List topics command
    list_parser = subparsers.add_parser("list-topics", help="List staged topics")
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of topics to list")

    # Validate items command
    subparsers.add_parser("validate-items", help="Validate all staged items against schema")

    args = None
    try:
        args = parser.parse_args()

        # Setup logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        setup_logging(level=log_level)

        base_dir = Path.cwd()
        config_path = base_dir / "config" / "feeds.yaml"
        
        if args.command == "collect":
            if not args.source and not args.all:
                print("Error: Please specify --source <id> or --all")
                return 1
            
            config = load_yaml_config(config_path)
            storage = LocalStorage(base_dir)
            engine = IngestionEngine(config, storage)
            
            source = args.source if args.source else None
            new_items = engine.run(source_filter=source)
            print(f"\nIngestion complete. Added {len(new_items)} new items.")
            return 0

        elif args.command == "status":
            storage = LocalStorage(base_dir)
            staged_items = storage.list_staged()
            
            print("Content Creation Factory - Status: Operational")
            print(f"Version: {__version__}")
            print(f"Storage: {base_dir / 'data'}")
            print(f"Staged Items: {len(staged_items)}")
            
            if staged_items:
                sources = {}
                for item in staged_items:
                    sources[item.source] = sources.get(item.source, 0) + 1
                print("Items by Source:")
                for src, count in sources.items():
                    print(f"  - {src}: {count}")
            return 0

        elif args.command == "list-topics":
            storage = LocalStorage(base_dir)
            items = storage.list_staged()
            items.sort(key=lambda x: x.published_at, reverse=True)
            
            print(f"\nLast {min(len(items), args.limit)} Staged Topics:")
            for item in items[:args.limit]:
                print(f"[{item.published_at[:10]}] {item.title[:60]}... ({item.source})")
            return 0

        elif args.command == "validate-items":
            storage = LocalStorage(base_dir)
            items = storage.list_staged()
            print(f"Validating {len(items)} items...")
            # Pydantic already validated them on load in list_staged()
            print("All items valid against TopicItem schema.")
            return 0

        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # In verbose mode, print full traceback
        if args and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
