"""Content Creation Factory CLI - Main entry point."""

import argparse
import sys

from content_creation import __version__
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

    # Collect command stub
    collect_parser = subparsers.add_parser("collect", help="Ingest topics from sources")
    collect_parser.add_argument("--source", type=str, help="Specific source to collect (e.g., arxiv)")
    collect_parser.add_argument("--all", action="store_true", help="Collect from all sources")

    # Status command stub
    subparsers.add_parser("status", help="Check system and ingestion status")

    try:
        args = parser.parse_args()

        # Setup logging
        log_level = "DEBUG" if args.verbose else "INFO"
        setup_logging(level=log_level)

        if args.command == "collect":
            source = args.source if args.source else "all"
            print(f"STUB: Collecting from source: {source}")
            print("Feature implementation planned for Week 1 Task: Source Ingestion.")
            return 0

        elif args.command == "status":
            print("Content Creation Factory - Status: Setup Phase")
            print("Documentation: OK")
            print("Schemas: OK")
            print("Implementation: Awaiting Week 1 feature logic.")
            return 0

        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
