"""Content Creation Factory CLI - Main entry point."""

import argparse
import logging
import os
import sys
from datetime import timedelta, timezone
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

    # Build manifest command
    manifest_parser = subparsers.add_parser("build-manifest", help="Build a manifest for a single topic")
    manifest_parser.add_argument("--topic-id", type=str, required=True, help="Topic ID to build manifest for")

    # Build all manifests command
    subparsers.add_parser("build-all-manifests", help="Build manifests for all topics with briefs")

    # Plan week command
    plan_week_parser = subparsers.add_parser("plan-week", help="Plan content calendar for a week")
    plan_week_parser.add_argument(
        "--week-start",
        type=str,
        help="Week start date (YYYY-MM-DD format, defaults to next Monday)"
    )

    # Dry run command
    dry_run_parser = subparsers.add_parser("dry-run", help="Run dry-run validation for a week's content")
    dry_run_parser.add_argument(
        "--week-start",
        type=str,
        help="Week start date (YYYY-MM-DD format, defaults to next Monday)"
    )

    # Init analytics command
    init_analytics_parser = subparsers.add_parser("init-analytics", help="Initialize analytics records for a week's posts")
    init_analytics_parser.add_argument(
        "--week-start",
        type=str,
        help="Week start date (YYYY-MM-DD format, defaults to next Monday)"
    )

    # Update analytics command
    update_analytics_parser = subparsers.add_parser("update-analytics", help="Update analytics record for a post")
    update_analytics_parser.add_argument(
        "--post-id",
        type=str,
        required=True,
        help="Post ID to update (format: topic_id_format_weekstart)"
    )

    # Review assets command
    review_assets_parser = subparsers.add_parser("review-assets", help="Interactively review assets for a topic")
    review_assets_parser.add_argument("--topic-id", type=str, required=True, help="Topic ID to review assets for")

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
            
            import time
            
            for item in items_to_process:
                try:
                    brief = generate_brief(item, prompt_path, api_key)
                    storage.save_brief(brief)
                    generated_count += 1
                except Exception as e:
                    print(f"Error generating brief for {item.id}: {e}")
                    failed_count += 1
                
                # Mandatory delay to respect free-tier RPM limits
                time.sleep(5)
            
            print(f"Generated {generated_count} briefs, {failed_count} failed")
            return 0

        elif args.command == "build-manifest":
            storage = LocalStorage(base_dir)

            # Load the brief to get topic_title and source_url
            brief = storage.get_scored(args.topic_id)
            if not brief:
                # Try to get from briefs dir
                briefs = storage.list_briefs()
                matching = [b for b in briefs if b.topic_id == args.topic_id]
                if matching:
                    brief = matching[0]
                else:
                    print(f"Error: No brief found for topic_id '{args.topic_id}'")
                    return 1

            topic_title = getattr(brief, "why_it_matters", "unknown")
            source_url = brief.source_url

            from content_creation.manifest import ManifestBuilder

            builder = ManifestBuilder(storage)
            manifest = builder.build(
                topic_id=args.topic_id,
                topic_title=topic_title,
                source_url=source_url,
            )

            storage.save_manifest(manifest)

            # Print summary
            print(f"Topic ID: {manifest.topic_id}")
            print(f"Overall Status: {manifest.overall_status}")
            print(f"Ready for Planner: {manifest.ready_for_planner}")
            print("Assets:")
            for asset_type in ["brief", "script", "carousel", "newsletter", "thumbnail"]:
                status = manifest.assets.get(asset_type, {}).status if manifest.assets.get(asset_type) else "missing"
                print(f"  {asset_type:12} {status}")
            if manifest.blocking_reasons:
                print(f"Blocking: {', '.join(manifest.blocking_reasons)}")
            else:
                print("Blocking: none")

            return 0

        elif args.command == "build-all-manifests":
            from content_creation.manifest import ManifestBuilder

            storage = LocalStorage(base_dir)
            builder = ManifestBuilder(storage)
            manifests = builder.build_all()

            # Save each manifest
            for manifest in manifests:
                storage.save_manifest(manifest)

            complete = sum(1 for m in manifests if m.overall_status == "complete")
            partial = sum(1 for m in manifests if m.overall_status == "partial")
            blocked = sum(1 for m in manifests if m.overall_status == "blocked")

            print(f"Built and saved {len(manifests)} manifests")
            print(f"  Complete: {complete}")
            print(f"  Partial: {partial}")
            print(f"  Blocked: {blocked}")

            return 0

        elif args.command == "plan-week":
            from datetime import timedelta

            storage = LocalStorage(base_dir)
            publishing_config_path = base_dir / "config" / "publishing.yaml"

            # Parse week_start
            if args.week_start:
                try:
                    week_start_date = datetime.strptime(args.week_start, "%Y-%m-%d").date()
                except ValueError:
                    print(f"Error: Invalid date format '{args.week_start}'. Use YYYY-MM-DD format.")
                    return 1
            else:
                # Default to next Monday
                today = datetime.now().date()
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                week_start_date = today + timedelta(days=days_until_monday)

            from content_creation.planning.planner import PostingPlanner

            planner = PostingPlanner(storage, publishing_config_path)
            calendar = planner.plan_week(week_start_date)

            # Save JSON
            json_path = storage.save_calendar(calendar)

            # Generate markdown
            week_end = calendar.week_end
            generated_at = calendar.generated_at[:19].replace("T", " ")

            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

            md_content = f"""# Content Calendar: {calendar.week_start} to {week_end}
Generated: {generated_at}

## Week Summary
- Total Posts: {calendar.total_posts}
- Formats: {', '.join(f'{k}: {v}' for k, v in calendar.format_counts.items()) if calendar.format_counts else 'None'}
- Topics: {len(calendar.topics_used)}

## Daily Schedule
"""

            for day_offset in range(7):
                day_num = day_offset + 1
                day_date_obj = week_start_date + timedelta(days=day_offset)
                day_date = day_date_obj.isoformat()
                day_name = day_names[day_offset]

                posts_for_day = [p for p in calendar.posts if p.day == day_num]

                if posts_for_day:
                    md_content += f"### Day {day_num} — {day_date} ({day_name})\n"
                    for post in posts_for_day:
                        md_content += f"- {post.format}: {post.topic_title}\n"
                        md_content += f"  Asset: {post.asset_path}\n\n"
                else:
                    md_content += f"### Day {day_num} — {day_date} ({day_name})\n- No posts scheduled\n\n"

            # Save markdown
            md_path = storage.calendars_dir / f"{calendar.week_start}.md"
            with open(md_path, "w") as f:
                f.write(md_content)

            # Print summary
            print(f"Week planned: {calendar.week_start} to {week_end}")
            print(f"Total posts: {calendar.total_posts}")
            for fmt, count in calendar.format_counts.items():
                print(f"  {fmt}: {count} posts")
            print(f"Saved to: {json_path}")
            print(f"Markdown: {md_path}")

            return 0

        elif args.command == "dry-run":
            from datetime import timedelta

            storage = LocalStorage(base_dir)
            publishing_config_path = base_dir / "config" / "publishing.yaml"

            # Parse week_start
            if args.week_start:
                try:
                    week_start_date = datetime.strptime(args.week_start, "%Y-%m-%d").date()
                    week_start_str = args.week_start
                except ValueError:
                    print(f"Error: Invalid date format '{args.week_start}'. Use YYYY-MM-DD format.")
                    return 1
            else:
                # Default to next Monday
                today = datetime.now().date()
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                week_start_date = today + timedelta(days=days_until_monday)
                week_start_str = week_start_date.isoformat()

            # Try to find existing calendar
            calendars = storage.list_calendars()
            calendar = None
            for c in calendars:
                if c.week_start == week_start_str:
                    calendar = c
                    break

            # If not found, generate one
            if calendar is None:
                from content_creation.planning.planner import PostingPlanner
                planner = PostingPlanner(storage, publishing_config_path)
                calendar = planner.plan_week(week_start_date)
                storage.save_calendar(calendar)

            # Run dry-run validation
            from content_creation.planning.dryrun import DryRunValidator
            validator = DryRunValidator(storage, publishing_config_path)
            report = validator.run(calendar)

            # Save JSON
            json_path = storage.save_dryrun(report)

            # Export markdown
            md_path = storage.dryruns_dir / f"{week_start_str}.md"
            validator.export_markdown(report, md_path)

            # Print terminal summary
            week_end = report.week_end
            print(f"Dry Run: {week_start_str} to {week_end}")
            print("─" * 30)
            print(f"  ✓ Ready:    {report.ready_count}")
            print(f"  ⚠ Warning:  {report.warning_count}")
            print(f"  ✗ Blocked:  {report.blocked_count}")
            print("─" * 30)
            print(f"Saved: {json_path}")
            print(f"Report: {md_path}")

            if report.warning_count > 0 or report.blocked_count > 0:
                print("\nRecommended Actions:")
                for i, action in enumerate(report.recommended_actions, 1):
                    print(f"  {i}. {action}")

            return 0

        elif args.command == "init-analytics":
            from datetime import timedelta
            from content_creation.models.analytics import PostAnalytics, PerformanceSnapshot

            storage = LocalStorage(base_dir)

            # Parse week_start
            if args.week_start:
                try:
                    week_start_str = args.week_start
                except ValueError:
                    print(f"Error: Invalid date format '{args.week_start}'. Use YYYY-MM-DD format.")
                    return 1
            else:
                # Default to next Monday
                today = datetime.now().date()
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                week_start_date = today + timedelta(days=days_until_monday)
                week_start_str = week_start_date.isoformat()

            # Load calendar
            calendars = storage.list_calendars()
            calendar = None
            for c in calendars:
                if c.week_start == week_start_str:
                    calendar = c
                    break

            if calendar is None:
                print(f"Error: No calendar found for {week_start_str}. Run 'plan-week' first.")
                return 1

            # Initialize analytics for each post
            new_count = 0
            skipped_count = 0

            for post in calendar.posts:
                post_id = f"{post.topic_id}_{post.format}_{week_start_str}"

                # Check if already exists
                existing = storage.get_analytics(post_id)
                if existing is not None:
                    print(f"→ Skipping {post_id} (already exists)")
                    skipped_count += 1
                    continue

                # Create new analytics record
                analytics = PostAnalytics(
                    post_id=post_id,
                    topic_id=post.topic_id,
                    topic_title=post.topic_title,
                    format=post.format,
                    asset_path=post.asset_path,
                    source_url=post.source_url,
                    posted_at=None,
                    week_start=week_start_str,
                    performance=PerformanceSnapshot(),
                    last_updated=datetime.now(timezone.utc).isoformat(),
                    notes=None,
                )
                storage.save_analytics(analytics)
                print(f"✓ Initialized {post_id}")
                new_count += 1

            print(f"\nAnalytics initialized: {new_count} new records")
            print(f"Skipped: {skipped_count} existing records")
            print(f"Week: {week_start_str}")

            return 0

        elif args.command == "update-analytics":
            storage = LocalStorage(base_dir)

            # Load existing analytics
            analytics = storage.get_analytics(args.post_id)
            if analytics is None:
                print(f"Error: No analytics record found for '{args.post_id}'")
                return 1

            print(f"Updating: {args.post_id}")
            print("Press Enter to keep current value, or enter new value.")

            # Helper function to prompt for optional numeric field
            def prompt_numeric(field_name: str, current_value: Optional[int], is_required: bool = False) -> Optional[int]:
                while True:
                    prompt = f"{field_name} [{current_value if current_value is not None else 'None'}]: "
                    try:
                        user_input = input(prompt).strip()
                        if user_input == "":
                            return current_value
                        value = int(user_input)
                        if value < 0:
                            print("Error: Value must be non-negative")
                            continue
                        return value
                    except ValueError:
                        print("Error: Please enter a valid integer")

            # Helper function to prompt for optional float field
            def prompt_float(field_name: str, current_value: Optional[float], min_val: float = 0.0, max_val: float = 100.0) -> Optional[float]:
                while True:
                    prompt = f"{field_name} [{current_value if current_value is not None else 'None'}]: "
                    try:
                        user_input = input(prompt).strip()
                        if user_input == "":
                            return current_value
                        value = float(user_input)
                        if value < min_val or value > max_val:
                            print(f"Error: Value must be between {min_val} and {max_val}")
                            continue
                        return value
                    except ValueError:
                        print("Error: Please enter a valid number")

            # Helper function to prompt for optional string field
            def prompt_optional_string(field_name: str, current_value: Optional[str]) -> Optional[str]:
                prompt = f"{field_name} [{current_value if current_value else 'None'}]: "
                user_input = input(prompt).strip()
                if user_input == "":
                    return current_value
                return user_input

            try:
                # Prompt for performance fields
                analytics.performance.views_24h = prompt_numeric("Views (24h)", analytics.performance.views_24h)
                analytics.performance.views_7d = prompt_numeric("Views (7d)", analytics.performance.views_7d)
                analytics.performance.views_30d = prompt_numeric("Views (30d)", analytics.performance.views_30d)
                analytics.performance.reach_24h = prompt_numeric("Reach (24h)", analytics.performance.reach_24h)
                analytics.performance.reach_7d = prompt_numeric("Reach (7d)", analytics.performance.reach_7d)
                analytics.performance.saves = prompt_numeric("Saves", analytics.performance.saves)
                analytics.performance.comments = prompt_numeric("Comments", analytics.performance.comments)
                analytics.performance.cta_clicks = prompt_numeric("CTA Clicks", analytics.performance.cta_clicks)

                # Watch time (video only)
                if analytics.format == "short_video":
                    analytics.performance.watch_time_pct = prompt_float("Watch time %", analytics.performance.watch_time_pct)
                else:
                    print("Watch time %: (skipped - video only)")

                # Posted at - only update if user provides a value
                posted_input = input(f"Posted at (YYYY-MM-DDTHH:MM) [{analytics.posted_at or 'None'}]: ").strip()
                if posted_input != "":
                    try:
                        datetime.strptime(posted_input, "%Y-%m-%dT%H:%M")
                        analytics.posted_at = posted_input
                    except ValueError:
                        print("Error: Invalid date format. Use YYYY-MM-DDTHH:MM")
                        # Don't update posted_at if invalid format

                # Notes
                analytics.notes = prompt_optional_string("Notes", analytics.notes)

            except KeyboardInterrupt:
                print("\nUpdate cancelled.")
                return 130

            # Update last_updated
            analytics.last_updated = datetime.now(timezone.utc).isoformat()

            # Save
            storage.save_analytics(analytics)

            print(f"\nUpdated: {args.post_id}")
            print(f"Last updated: {analytics.last_updated}")

            return 0

        elif args.command == "review-assets":
            from content_creation.models.brief import ReviewStatus
            from content_creation.manifest import ManifestBuilder

            storage = LocalStorage(base_dir)

            # Load manifest
            manifest_path = storage.manifests_dir / f"{args.topic_id}.json"
            if not manifest_path.exists():
                print(f"Error: No manifest found for topic '{args.topic_id}'")
                print("Run 'build-manifest --topic-id {topic_id}' first to create the manifest.")
                return 1

            try:
                with open(manifest_path, "r") as f:
                    import json
                    manifest_data = json.load(f)
            except Exception as e:
                print(f"Error: Failed to load manifest: {e}")
                return 1

            # Print topic summary
            print("\n" + "=" * 50)
            print(f"Topic: {manifest_data.get('topic_title', 'Unknown')}")
            print(f"Source: {manifest_data.get('source_url', 'Unknown')}")
            print(f"Overall Status: {manifest_data.get('overall_status', 'unknown')}")
            print("=" * 50)

            # Asset order
            asset_order = ["brief", "script", "carousel", "newsletter", "thumbnail"]
            assets = manifest_data.get("assets", {})

            # Counters
            approved_count = 0
            rejected_count = 0
            skipped_count = 0

            try:
                for asset_type in asset_order:
                    asset_entry = assets.get(asset_type)
                    if not asset_entry:
                        continue

                    status = asset_entry.get("status", "missing")

                    # Skip skipped or missing
                    if status in ("skipped", "missing"):
                        continue

                    # Skip already approved
                    if status == "approved":
                        print(f"\n=== {asset_type.upper()} ===")
                        print(f"Status: {status} (ALREADY APPROVED)")
                        continue

                    # Show summary view
                    print(f"\n=== {asset_type.upper()} ===")
                    print(f"Status: {status}")

                    # Load and show asset-specific summary
                    asset_dirs = {
                        "brief": storage.briefs_dir,
                        "script": storage.scripts_dir,
                        "carousel": storage.carousels_dir,
                        "newsletter": storage.newsletters_dir,
                        "thumbnail": storage.thumbnails_dir,
                    }
                    asset_file = asset_dirs.get(asset_type, storage.briefs_dir) / f"{args.topic_id}.json"

                    summary_field = None
                    if asset_file.exists():
                        with open(asset_file, "r") as f:
                            asset_data = json.load(f)
                        if asset_type == "brief":
                            summary_field = asset_data.get("why_it_matters", "N/A")
                        elif asset_type == "script":
                            summary_field = asset_data.get("hook", "N/A")
                        elif asset_type == "carousel":
                            slides = asset_data.get("slides", [])
                            summary_field = slides[0].get("title", "N/A") if slides else "N/A"
                        elif asset_type == "newsletter":
                            summary_field = asset_data.get("subject_line", "N/A")
                        elif asset_type == "thumbnail":
                            summary_field = asset_data.get("title_text", "N/A")

                    if summary_field:
                        print(f"Summary: {summary_field[:100]}...")

                    # Prompt: Show full content?
                    while True:
                        show_full = input("Show full content? (y/n): ").strip().lower()
                        if show_full in ("y", "n"):
                            break
                        print("Invalid input. Please enter 'y' or 'n'.")

                    if show_full == "y":
                        print("\n--- Full Content ---")
                        print(json.dumps(asset_data, indent=2))
                        print("--- End ---\n")

                    # Prompt: Decision
                    while True:
                        decision = input("Decision (a=approve / r=reject / s=skip): ").strip().lower()
                        if decision in ("a", "r", "s"):
                            break
                        print("Invalid input. Please enter 'a', 'r', or 's'.")

                    if decision == "a":
                        storage.update_asset_status(asset_type, args.topic_id, ReviewStatus.APPROVED)
                        print("✓ Approved")
                        approved_count += 1
                    elif decision == "r":
                        reason = input("Reason (optional): ").strip()
                        if reason:
                            print(f"Rejection reason: {reason}")
                        storage.update_asset_status(asset_type, args.topic_id, ReviewStatus.REJECTED)
                        print("✗ Rejected")
                        rejected_count += 1
                    else:
                        print("→ Skipped")
                        skipped_count += 1

                # Rebuild manifest after all decisions
                scored_item = storage.get_scored(args.topic_id)
                topic_title = scored_item.title if scored_item else manifest_data.get("topic_title", "Unknown")
                source_url = manifest_data.get("source_url", "")

                builder = ManifestBuilder(storage)
                new_manifest = builder.build(
                    topic_id=args.topic_id,
                    topic_title=topic_title,
                    source_url=source_url,
                )
                storage.save_manifest(new_manifest)

                # Print updated summary
                print("\n" + "=" * 50)
                print("Review complete.")
                print(f"Approved: {approved_count}")
                print(f"Rejected: {rejected_count}")
                print(f"Skipped: {skipped_count}")
                print(f"Overall Status: {new_manifest.overall_status}")
                print(f"Ready for Planner: {new_manifest.ready_for_planner}")
                print("=" * 50)

                return 0

            except KeyboardInterrupt:
                print("\nReview interrupted.")
                return 130

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
