"""Content Creation Factory CLI - Main entry point."""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from content_creation import __version__
from content_creation.storage.local import LocalStorage
from content_creation.utils.logging import setup_logging
from content_creation.application import (
    ApplicationContext,
    CollectTopicsService,
    ScoreTopicsService,
    BriefGenerationService,
    AssetGenerationService,
    AssetReviewService,
    PipelineRunService,
    AssetDecision,
)
from dotenv import load_dotenv
load_dotenv()



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

    # Generate assets command
    gen_assets_parser = subparsers.add_parser("generate-assets", help="Generate missing assets (thumbnails, scripts, carousels, newsletters)")
    gen_assets_parser.add_argument("--top", type=int, default=5, help="Number of briefs to process")

    # Batch approve command
    batch_approve_parser = subparsers.add_parser("batch-approve", help="Batch approve assets across all topics")
    batch_approve_parser.add_argument("--asset-type", type=str, default="all", help="Asset type to approve (brief/script/carousel/newsletter/thumbnail/all)")
    batch_approve_parser.add_argument("--all", action="store_true", required=True, help="Confirm approving all matching assets")
    batch_approve_parser.add_argument("--exclude-incomplete", action="store_true", help="Skip assets where any field is 'needs_review'")

    # Run pipeline command
    run_pipeline_parser = subparsers.add_parser("run-pipeline", help="Run the full pipeline end-to-end")
    run_pipeline_parser.add_argument("--auto-approve", action="store_true", help="Auto-approve all assets (skips human review)")
    run_pipeline_parser.add_argument("--top", type=int, default=5, help="Number of topics to process through generation")
    run_pipeline_parser.add_argument("--source", type=str, help="Specific source to collect from")

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
            
            ctx = ApplicationContext.create(base_dir)
            service = CollectTopicsService()
            source = args.source if args.source else None
            result = service.run(ctx, source_filter=source)
            print(f"\nIngestion complete. Added {result.count} new items.")
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
            ctx = ApplicationContext.create(base_dir)
            items = ctx.storage.list_staged()
            if args.limit:
                items = items[:args.limit]
            
            if not items:
                print("No staged items found to score.")
                return 0
            
            print(f"Scoring {len(items)} items...")
            service = ScoreTopicsService()
            result = service.run(ctx, limit=args.limit)
            
            print(f"Successfully scored {result.scored_count} items.")
            if result.rejected_count > 0:
                print(f"Rejected {result.rejected_count} items (check logs for reasons).")
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
            
            ctx = ApplicationContext.create(base_dir)
            scored_items = ctx.storage.list_scored()
            from content_creation.models.topic import TopicStatus
            items_to_process = [item for item in scored_items if item.status == TopicStatus.SCORED]
            items_to_process.sort(key=lambda x: x.priority_score, reverse=True)
            items_to_process = items_to_process[:args.top]
            
            if not items_to_process:
                print("No scored topics found to process.")
                return 0
            
            print(f"Generating briefs for top {len(items_to_process)} topics...")
            service = BriefGenerationService()
            result = service.run(ctx, top_n=args.top, api_key=api_key)
            print(f"Generated {result.generated_count} briefs, {len(result.failures)} failed")
            return 0

        elif args.command == "generate-assets":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("Error: GEMINI_API_KEY not set in environment")
                return 1

            ctx = ApplicationContext.create(base_dir)
            briefs = ctx.storage.list_briefs()
            briefs.sort(key=lambda b: b.generated_at, reverse=True)
            briefs = briefs[:args.top]

            if not briefs:
                print("No briefs found. Run 'generate-briefs' first.")
                return 0

            print(f"Generating assets for {len(briefs)} briefs...")
            service = AssetGenerationService()
            result = service.run(ctx, top_n=args.top, api_key=api_key)
            
            print(f"\nGenerated: {result.counts}")
            if result.skipped_count > 0:
                print(f"Skipped (already completed): {result.skipped_count}")
            print(f"Failures: {result.failed_count}")
            return 0

        elif args.command == "batch-approve":
            from content_creation.shared.enums import ReviewStatus
            from content_creation.manifest import ManifestBuilder

            storage = LocalStorage(base_dir)

            asset_types = ["brief", "script", "carousel", "newsletter", "thumbnail"]
            if args.asset_type != "all":
                if args.asset_type not in asset_types:
                    print(f"Error: Invalid asset type '{args.asset_type}'. Valid: {asset_types + ['all']}")
                    return 1
                asset_types = [args.asset_type]

            asset_dirs = {
                "brief": storage.briefs_dir,
                "script": storage.scripts_dir,
                "carousel": storage.carousels_dir,
                "newsletter": storage.newsletters_dir,
                "thumbnail": storage.thumbnails_dir,
            }

            import json as json_mod
            approved_count = 0
            skipped_count = 0

            for asset_type in asset_types:
                dir_path = asset_dirs[asset_type]
                for file_path in dir_path.glob("*.json"):
                    try:
                        with open(file_path, "r") as f:
                            data = json_mod.load(f)
                    except Exception:
                        continue

                    status = data.get("review_status")
                    if status in ("approved", "rejected"):
                        continue

                    if args.exclude_incomplete:
                        has_incomplete = any(
                            v == "needs_review"
                            for k, v in data.items()
                            if k != "review_status" and isinstance(v, str)
                        )
                        if has_incomplete:
                            skipped_count += 1
                            continue

                    topic_id = file_path.stem
                    storage.update_asset_status(asset_type, topic_id, ReviewStatus.APPROVED)
                    approved_count += 1

            # Rebuild manifests
            builder = ManifestBuilder(storage)
            manifests = builder.build_all()
            for m in manifests:
                storage.save_manifest(m)

            print(f"Approved: {approved_count} assets")
            if skipped_count:
                print(f"Skipped (incomplete): {skipped_count}")
            complete = sum(1 for m in manifests if m.overall_status == "complete")
            print(f"Manifests rebuilt: {len(manifests)} ({complete} complete)")
            return 0

        elif args.command == "run-pipeline":
            import json as json_mod
            from content_creation.utils.logging import PipelineLogger

            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("Error: GEMINI_API_KEY not set in environment")
                return 1

            if args.auto_approve:
                print("⚠ Auto-approve enabled — assets will be marked approved without human inspection.")

            ctx = ApplicationContext.create(base_dir)
            run_result = PipelineRunService().run(
                ctx=ctx,
                top_n=args.top,
                source_filter=args.source if args.source else None,
                auto_approve=args.auto_approve,
                api_key=api_key,
            )

            print(f"Pipeline log: {run_result.log_path}\n")

            # Print outputs for stages 1 to 6 based on service results
            # Stage 1: collect
            collect_summary = run_result.stage_summaries.get("collect")
            if collect_summary:
                if collect_summary.get("success"):
                    print(f"[collect] {collect_summary['count']} new items")
                else:
                    print(f"[collect] ERROR: {collect_summary.get('error')}")

            # Stage 2: score
            score_summary = run_result.stage_summaries.get("score")
            if score_summary:
                if score_summary.get("success"):
                    print(f"[score] {score_summary['scored_count']} scored, {score_summary['rejected_count']} rejected")
                else:
                    print(f"[score] ERROR: {score_summary.get('error')}")

            # Stage 3: generate-briefs
            briefs_summary = run_result.stage_summaries.get("generate-briefs")
            if briefs_summary:
                if briefs_summary.get("success"):
                    print(f"[generate-briefs] {briefs_summary['generated_count']} generated")
                else:
                    print(f"[generate-briefs] ERROR: {briefs_summary.get('error')}")

            # Stage 4: generate-assets
            assets_summary = run_result.stage_summaries.get("generate-assets")
            if assets_summary:
                if assets_summary.get("success"):
                    asset_count = sum(assets_summary["counts"].values())
                    print(f"[generate-assets] {asset_count} generated")
                else:
                    print(f"[generate-assets] ERROR: {assets_summary.get('error')}")

            # Stage 5: build-manifests
            manifests_summary = run_result.stage_summaries.get("build-manifests")
            if manifests_summary:
                if manifests_summary.get("success"):
                    print(f"[build-manifests] {manifests_summary['count']} built")
                else:
                    print(f"[build-manifests] ERROR: {manifests_summary.get('error')}")

            # Stage 6: batch-approve
            if args.auto_approve:
                approve_summary = run_result.stage_summaries.get("batch-approve")
                if approve_summary:
                    if approve_summary.get("success"):
                        print(f"[batch-approve] {approve_summary['approved_count']} approved")
                    else:
                        print(f"[batch-approve] ERROR: {approve_summary.get('error')}")

            # Instantiate PipelineLogger and load historical entries
            pl = PipelineLogger(run_result.log_path)
            if run_result.log_path.exists():
                with open(run_result.log_path, "r") as f:
                    for line in f:
                        if line.strip():
                            pl.entries.append(json_mod.loads(line))

            # Run Stages 7, 8, 9 only if the service run succeeded
            if run_result.success:
                storage = ctx.storage
                
                # Stage 7: Plan week
                with pl.stage("plan-week") as s_ctx:
                    try:
                        from content_creation.planning.planner import PostingPlanner
                        publishing_config_path = base_dir / "config" / "publishing.yaml"
                        today = datetime.now().date()
                        days_until_monday = (7 - today.weekday()) % 7
                        if days_until_monday == 0:
                            days_until_monday = 7
                        week_start_date = today + timedelta(days=days_until_monday)
                        planner = PostingPlanner(storage, publishing_config_path)
                        calendar = planner.plan_week(week_start_date)
                        storage.save_calendar(calendar)
                        s_ctx["items"] = calendar.total_posts
                        print(f"[plan-week] {calendar.total_posts} posts scheduled")
                    except Exception as e:
                        s_ctx["status"] = "error"
                        s_ctx["error"] = str(e)
                        print(f"[plan-week] ERROR: {e}")

                # Stage 8: Dry run
                with pl.stage("dry-run") as s_ctx:
                    try:
                        from content_creation.planning.dryrun import DryRunValidator
                        publishing_config_path = base_dir / "config" / "publishing.yaml"
                        calendars = storage.list_calendars()
                        if calendars:
                            latest_cal = max(calendars, key=lambda c: c.week_start)
                            validator = DryRunValidator(storage, publishing_config_path)
                            report = validator.run(latest_cal)
                            storage.save_dryrun(report)
                            s_ctx["items"] = report.ready_count
                            print(f"[dry-run] ✓ {report.ready_count} ready, ⚠ {report.warning_count} warnings, ✗ {report.blocked_count} blocked")
                        else:
                            s_ctx["items"] = 0
                            print("[dry-run] No calendar found")
                    except Exception as e:
                        s_ctx["status"] = "error"
                        s_ctx["error"] = str(e)
                        print(f"[dry-run] ERROR: {e}")

                # Stage 9: Init analytics
                with pl.stage("init-analytics") as s_ctx:
                    try:
                        from content_creation.models.analytics import PostAnalytics, PerformanceSnapshot
                        calendars = storage.list_calendars()
                        if calendars:
                            latest_cal = max(calendars, key=lambda c: c.week_start)
                            count = 0
                            for post in latest_cal.posts:
                                post_id = f"{post.topic_id}_{post.format}_{latest_cal.week_start}"
                                if storage.get_analytics(post_id) is not None:
                                    continue
                                analytics = PostAnalytics(
                                    post_id=post_id,
                                    topic_id=post.topic_id,
                                    topic_title=post.topic_title,
                                    format=post.format,
                                    asset_path=post.asset_path,
                                    source_url=post.source_url,
                                    week_start=latest_cal.week_start,
                                    last_updated=datetime.now(timezone.utc).isoformat(),
                                )
                                storage.save_analytics(analytics)
                                count += 1
                            s_ctx["items"] = count
                            print(f"[init-analytics] {count} records created")
                        else:
                            s_ctx["items"] = 0
                            print("[init-analytics] No calendar found")
                    except Exception as e:
                        s_ctx["status"] = "error"
                        s_ctx["error"] = str(e)
                        print(f"[init-analytics] ERROR: {e}")

            # Summary
            print("\n" + "=" * 50)
            print(f"{'Stage':<20} {'Status':<10} {'Duration':<10} {'Items'}")
            print("-" * 50)
            for stage_name, info in pl.summary().items():
                status = info["status"]
                dur = f"{info['duration_s']:.1f}s" if info["duration_s"] else "-"
                items = info["details"].get("items", "-")
                print(f"{stage_name:<20} {status:<10} {dur:<10} {items}")
            print("=" * 50)
            print(f"Log saved: {run_result.log_path}")
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
            from content_creation.shared.enums import ReviewStatus
            import json

            ctx = ApplicationContext.create(base_dir)
            service = AssetReviewService()

            # Load and display review queue items
            try:
                queue = service.get_review_queue(ctx, args.topic_id)
            except FileNotFoundError as e:
                print(f"Error: {e}")
                print("Run 'build-manifest --topic-id {topic_id}' first to create the manifest.")
                return 1
            except Exception as e:
                print(f"Error: Failed to load manifest: {e}")
                return 1

            # Fetch manifest data for presentation header
            manifest_path = ctx.storage.manifests_dir / f"{args.topic_id}.json"
            try:
                with open(manifest_path, "r") as f:
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

            # Counters
            approved_count = 0
            rejected_count = 0
            skipped_count = 0
            
            decisions = []

            try:
                for item in queue:
                    asset_type = item.asset_type
                    status = item.status

                    # Skip already approved
                    if status == "approved":
                        print(f"\n=== {asset_type.upper()} ===")
                        print(f"Status: {status} (ALREADY APPROVED)")
                        continue

                    # Show summary view
                    print(f"\n=== {asset_type.upper()} ===")
                    print(f"Status: {status}")

                    if item.summary_text:
                        print(f"Summary: {item.summary_text[:100]}...")

                    # Prompt: Show full content?
                    while True:
                        show_full = input("Show full content? (y/n): ").strip().lower()
                        if show_full in ("y", "n"):
                            break
                        print("Invalid input. Please enter 'y' or 'n'.")

                    if show_full == "y":
                        print("\n--- Full Content ---")
                        print(json.dumps(item.content, indent=2))
                        print("--- End ---\n")

                    # Prompt: Decision
                    while True:
                        decision = input("Decision (a=approve / r=reject / s=skip): ").strip().lower()
                        if decision in ("a", "r", "s"):
                            break
                        print("Invalid input. Please enter 'a', 'r', or 's'.")

                    if decision == "a":
                        decisions.append(AssetDecision(asset_type=asset_type, status=ReviewStatus.APPROVED))
                        print("✓ Approved")
                        approved_count += 1
                    elif decision == "r":
                        reason = input("Reason (optional): ").strip()
                        if reason:
                            print(f"Rejection reason: {reason}")
                        decisions.append(AssetDecision(asset_type=asset_type, status=ReviewStatus.REJECTED, rejection_reason=reason))
                        print("✗ Rejected")
                        rejected_count += 1
                    else:
                        print("→ Skipped")
                        skipped_count += 1

                # Apply decisions and rebuild manifest using the service
                result = service.apply_decisions(ctx, args.topic_id, decisions)

                # Print updated summary
                print("\n" + "=" * 50)
                print("Review complete.")
                print(f"Approved: {approved_count}")
                print(f"Rejected: {rejected_count}")
                print(f"Skipped: {skipped_count}")
                print(f"Overall Status: {result.manifest.overall_status}")
                print(f"Ready for Planner: {result.manifest.ready_for_planner}")
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
