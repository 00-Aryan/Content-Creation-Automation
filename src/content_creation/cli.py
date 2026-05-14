"""Content Creation Factory CLI - Main entry point."""

import argparse
import logging
import os
import sys
from pathlib import Path

from content_creation import __version__
from content_creation.generation.brief import generate_brief
from content_creation.ingestion import IngestionEngine
from content_creation.scoring.config import load_scoring_config
from content_creation.scoring.engine import ScoringEngine
from content_creation.scoring.validation import ValidationEngine
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
    list_parser.add_argument("--status", type=str, help="Filter by status (raw, staged, scored, approved, rejected, review)")

    # Validate items command
    subparsers.add_parser("validate-items", help="Validate all staged items against schema")

    # Score topics command
    score_parser = subparsers.add_parser("score-topics", help="Score staged topics and run validation")
    score_parser.add_argument("--limit", type=int, help="Limit number of items to score")

    # Review scores command
    review_parser = subparsers.add_parser("review-scores", help="Review scored topics and flags")
    review_parser.add_argument("--flagged-only", action="store_true", help="Only show items with validation flags")
    review_parser.add_argument("--min-score", type=float, help="Minimum total score to show")
    review_parser.add_argument("--limit", type=int, default=10, help="Maximum number of topics to list")

    # Scoring dashboard command
    subparsers.add_parser("scoring-dashboard", help="Show aggregate scoring metrics and flag breakdown")

    # Generate briefs command
    generate_parser = subparsers.add_parser("generate-briefs", help="Generate educational briefs using Gemini")
    generate_parser.add_argument("--top", type=int, default=5, help="Number of top scored topics to process")

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
            
            if args.status:
                from content_creation.models.topic import TopicStatus
                try:
                    # Validate status
                    status_enum = TopicStatus(args.status)
                    items = [item for item in items if item.status == status_enum]
                except ValueError:
                    valid_statuses = ", ".join([s.value for s in TopicStatus])
                    print(f"Error: Invalid status '{args.status}'. Valid values: {valid_statuses}")
                    return 1
            
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

        elif args.command == "score-topics":
            storage = LocalStorage(base_dir)
            scoring_config_path = base_dir / "config" / "scoring.yaml"
            config = load_scoring_config(scoring_config_path)
            
            items = storage.list_staged()
            if args.limit:
                items = items[:args.limit]
            
            if not items:
                print("No staged items found to score.")
                return 0
            
            print(f"Scoring {len(items)} items...")
            scorer = ScoringEngine(config)
            validator = ValidationEngine(config.validation)
            
            results = scorer.score_items(items)
            scored_items = results["scored"]
            rejected_items = results["rejected"]
            
            for item in scored_items:
                validated_item = validator.validate_item(item)
                storage.save_scored(validated_item)
            
            for item in rejected_items:
                storage.save_scored(item)
            
            print(f"Successfully scored {len(scored_items)} items.")
            if rejected_items:
                print(f"Rejected {len(rejected_items)} items (check logs for reasons).")
            return 0

        elif args.command == "review-scores":
            storage = LocalStorage(base_dir)
            items = storage.list_scored()
            
            if args.flagged_only:
                items = [item for item in items if item.validation_flags]
            
            if args.min_score:
                items = [item for item in items if item.priority_score >= args.min_score]
            
            items.sort(key=lambda x: x.priority_score, reverse=True)
            
            print(f"\nScored Topics Review (showing {min(len(items), args.limit)} of {len(items)}):")
            for item in items[:args.limit]:
                flag_indicator = "[!]" if item.validation_flags else "[ ]"
                print(f"{flag_indicator} {item.priority_score:5.1f} | {item.title[:60]}... ({item.source})")
                if item.validation_flags:
                    for flag in item.validation_flags:
                        print(f"    - {flag}")
            return 0

        elif args.command == "scoring-dashboard":
            storage = LocalStorage(base_dir)
            items = storage.list_scored()
            
            if not items:
                print("No scored items found. Run 'score-topics' first.")
                return 0
            
            avg_score = sum(item.priority_score for item in items) / len(items)
            flagged_items = [item for item in items if item.validation_flags]
            
            all_flags = []
            for item in items:
                all_flags.extend(item.validation_flags)
            
            flag_counts = {}
            for flag in all_flags:
                # Group by flag type (first part of message)
                flag_type = flag.split(":")[0]
                flag_counts[flag_type] = flag_counts.get(flag_type, 0) + 1
            
            print("\n=== Scoring Dashboard ===")
            print(f"Total Scored Items:  {len(items)}")
            print(f"Average Priority Score: {avg_score:.2f}")
            print(f"Flagged Items:       {len(flagged_items)} ({len(flagged_items)/len(items)*100:.1f}%)")
            
            if flag_counts:
                print("\nFlag Breakdown:")
                for ftype, count in sorted(flag_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {ftype}: {count}")
            
            items.sort(key=lambda x: x.priority_score, reverse=True)
            print("\nTop 5 Scored Items:")
            for item in items[:5]:
                print(f"  {item.priority_score:5.1f} | {item.title[:50]}...")
                
            return 0

        elif args.command == "generate-briefs":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("Error: GEMINI_API_KEY not set in environment")
                return 1
            
            storage = LocalStorage(base_dir)
            scored_items = storage.list_scored()
            
            # Filter and sort
            from content_creation.models.topic import TopicStatus
            items_to_process = [item for item in scored_items if item.status == TopicStatus.SCORED]
            items_to_process.sort(key=lambda x: x.priority_score, reverse=True)
            items_to_process = items_to_process[:args.top]
            
            if not items_to_process:
                print("No scored topics found to process.")
                return 0
            
            print(f"Generating briefs for top {len(items_to_process)} topics...")
            
            prompt_path = base_dir / "prompts" / "summarize.md"
            generated_count = 0
            failed_count = 0
            
            from content_creation.models.brief import ReviewStatus
            import time
            
            for item in items_to_process:
                try:
                    brief = generate_brief(item, prompt_path, api_key)
                    storage.save_brief(brief)
                    if brief.review_status == ReviewStatus.NEEDS_REVIEW:
                        failed_count += 1
                    else:
                        generated_count += 1
                except Exception as e:
                    print(f"Error generating brief for {item.id}: {e}")
                    failed_count += 1
                
                # Mandatory delay to respect free-tier RPM limits
                time.sleep(5)
            
            print(f"Generated {generated_count} briefs, {failed_count} failed")
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
