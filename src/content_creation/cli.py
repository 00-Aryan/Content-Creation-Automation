"""Content Creation Factory CLI - Main entry point."""

import argparse
from typing import Optional
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

    # Event timeline command
    event_timeline_parser = subparsers.add_parser("event-timeline", help="View recent events from the event store")
    event_timeline_parser.add_argument("--category", type=str, help="Filter by category (workflow, review, job, lock, recovery, pipeline)")
    event_timeline_parser.add_argument("--limit", type=int, default=20, help="Maximum number of events to show")
    event_timeline_parser.add_argument("--entity-type", type=str, help="Filter by entity type")
    event_timeline_parser.add_argument("--entity-id", type=str, help="Filter by entity ID")
    event_timeline_parser.add_argument("--correlation-id", type=str, help="Filter by correlation ID")

    # Event stats command
    subparsers.add_parser("event-stats", help="Show event store statistics")

    # Event replay command
    event_replay_parser = subparsers.add_parser("event-replay", help="Replay events from the event store")
    event_replay_parser.add_argument("--category", type=str, help="Replay events from a specific category")
    event_replay_parser.add_argument("--correlation-id", type=str, help="Replay events by correlation ID")
    event_replay_parser.add_argument("--entity-type", type=str, help="Replay events by entity type")
    event_replay_parser.add_argument("--entity-id", type=str, help="Replay events by entity ID")
    event_replay_parser.add_argument("--dry-run", action="store_true", help="Inspect events without re-emitting")
    event_replay_parser.add_argument("--limit", type=int, default=100, help="Maximum number of events to replay")

    # Event cleanup command
    event_cleanup_parser = subparsers.add_parser("event-cleanup", help="Run event store retention cleanup")
    event_cleanup_parser.add_argument("--category", type=str, help="Cleanup events from a specific category")
    event_cleanup_parser.add_argument("--dry-run", action="store_true", help="Preview cleanup without deleting")

    # Metrics commands
    metrics_kpi_parser = subparsers.add_parser("metrics-kpi", help="Show KPI metrics from the metrics store")
    metrics_kpi_parser.add_argument("--days", type=int, default=30, help="Lookback period in days")

    metrics_summary_parser = subparsers.add_parser("metrics-summary", help="Show telemetry summary")
    metrics_summary_parser.add_argument("--days", type=int, default=30, help="Lookback period in days")

    metrics_query_parser = subparsers.add_parser("metrics-query", help="Query metrics from the store")
    metrics_query_parser.add_argument("--name", type=str, help="Filter by metric name")
    metrics_query_parser.add_argument("--type", type=str, choices=["counter", "gauge", "histogram", "timer"], help="Filter by metric type")
    metrics_query_parser.add_argument("--limit", type=int, default=20, help="Maximum number of results")

    metrics_cleanup_parser = subparsers.add_parser("metrics-cleanup", help="Run metrics store retention cleanup")
    metrics_cleanup_parser.add_argument("--dry-run", action="store_true", help="Preview cleanup without deleting")

    metrics_rebuild_parser = subparsers.add_parser("metrics-rebuild", help="Rebuild metrics from event store")
    metrics_rebuild_parser.add_argument("--dry-run", action="store_true", help="Preview rebuild without writing")

    # Audit commands
    audit_query_parser = subparsers.add_parser("audit-query", help="Query audit trail records")
    audit_query_parser.add_argument("--limit", type=int, default=20, help="Maximum number of results")
    audit_query_parser.add_argument("--entity-type", type=str, help="Filter by entity type")
    audit_query_parser.add_argument("--action", type=str, help="Filter by action type")
    audit_query_parser.add_argument("--actor-id", type=str, help="Filter by actor ID")
    audit_query_parser.add_argument("--event-type", type=str, help="Filter by event type")
    audit_query_parser.add_argument("--severity", type=str, choices=["INFO", "WARNING", "ERROR", "CRITICAL"], help="Filter by severity")
    audit_query_parser.add_argument("--source", type=str, choices=["workflow", "review", "job", "lock", "recovery", "pipeline", "system"], help="Filter by source")
    audit_query_parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    audit_query_parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")

    audit_entity_parser = subparsers.add_parser("audit-entity", help="Search audit trail by entity")
    audit_entity_parser.add_argument("--entity-type", type=str, required=True, help="Entity type (brief, job, asset, etc.)")
    audit_entity_parser.add_argument("--entity-id", type=str, help="Specific entity ID")
    audit_entity_parser.add_argument("--limit", type=int, default=20, help="Maximum number of results")

    audit_actor_parser = subparsers.add_parser("audit-actor", help="Search audit trail by actor")
    audit_actor_parser.add_argument("--actor-id", type=str, required=True, help="Actor ID to search for")
    audit_actor_parser.add_argument("--limit", type=int, default=20, help="Maximum number of results")

    audit_report_parser = subparsers.add_parser("audit-report", help="Generate compliance reports from audit trail")
    audit_report_parser.add_argument("--type", type=str, choices=["operator", "decision", "job", "incident", "summary"], required=True, help="Report type")

    audit_rebuild_parser = subparsers.add_parser("audit-rebuild", help="Rebuild audit trail from event store")
    audit_rebuild_parser.add_argument("--dry-run", action="store_true", help="Preview rebuild without writing")

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
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()
            source = args.source if args.source else None
            res = executor.execute(ctx, "collect", "topic", "all", {"source": source})
            if res.success:
                print(f"\nIngestion complete. Added {res.affected_artifacts.get('collected_count', '0')} new items.")
                return 0
            else:
                print(f"Error during collection: {res.blocking_reasons}")
                return 1

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
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()
            
            print("Scoring topics...")
            res = executor.execute(ctx, "score_topics", "topic", "all", {"limit": args.limit})
            if res.success:
                print(f"Successfully scored {res.affected_artifacts.get('scored_count', '0')} items.")
                rejected = int(res.affected_artifacts.get('rejected_count', '0'))
                if rejected > 0:
                    print(f"Rejected {rejected} items (check logs for reasons).")
                return 0
            else:
                print(f"Error during scoring: {res.blocking_reasons}")
                return 1

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
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()
            
            print("Generating briefs...")
            res = executor.execute(ctx, "generate_briefs", "brief", "all", {"top_n": args.top, "api_key": api_key})
            if res.success:
                print(f"Generated {res.affected_artifacts.get('generated_count', '0')} briefs, {res.affected_artifacts.get('failures', '0')} failed")
                return 0
            else:
                print(f"Error during brief generation: {res.blocking_reasons}")
                return 1

        elif args.command == "generate-assets":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("Error: GEMINI_API_KEY not set in environment")
                return 1

            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            print("Generating assets...")
            res = executor.execute(ctx, "generate_assets", "assets", "all", {"top_n": args.top, "api_key": api_key})
            if res.success:
                print(f"\nGenerated: {res.affected_artifacts.get('counts')}")
                print(f"Failures: {res.affected_artifacts.get('failed_count', '0')}")
                return 0
            else:
                print(f"Error during asset generation: {res.blocking_reasons}")
                return 1

        elif args.command == "batch-approve":
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            res = executor.execute(
                ctx,
                "batch_approve",
                "assets",
                "all",
                {
                    "asset_type": args.asset_type,
                    "exclude_incomplete": args.exclude_incomplete,
                }
            )

            if res.success:
                print(f"Approved: {res.affected_artifacts.get('approved_count', '0')} assets")
                print(f"Manifests rebuilt: {res.affected_artifacts.get('manifests_rebuilt', '0')}")
                return 0
            else:
                print(f"Error executing batch approval: {res.blocking_reasons}")
                return 1

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
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()
            
            res = executor.execute(
                ctx,
                "run_pipeline",
                "manifest",
                "all",
                {
                    "top_n": args.top,
                    "source": args.source if args.source else None,
                    "auto_approve": args.auto_approve,
                    "api_key": api_key,
                }
            )
            
            if not res.success:
                print(f"Pipeline execution failed: {res.blocking_reasons}")
                return 1
                
            run_result = res.raw_result

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
                # Stage 7: Plan week
                with pl.stage("plan-week") as s_ctx:
                    try:
                        today = datetime.now(timezone.utc).date()
                        days_until_monday = (7 - today.weekday()) % 7
                        if days_until_monday == 0:
                            days_until_monday = 7
                        week_start_date = today + timedelta(days=days_until_monday)
                        week_start_str = week_start_date.isoformat()
                        res_plan = executor.execute(
                            ctx,
                            "plan_week",
                            "weekly_calendar",
                            week_start_str,
                            {"week_start_date": week_start_date}
                        )
                        if not res_plan.success:
                            raise RuntimeError(f"Plan week failed: {res_plan.blocking_reasons}")
                        calendar = res_plan.raw_result
                        s_ctx["items"] = calendar.total_posts
                        print(f"[plan-week] {calendar.total_posts} posts scheduled")
                    except Exception as e:
                        s_ctx["status"] = "error"
                        s_ctx["error"] = str(e)
                        print(f"[plan-week] ERROR: {e}")

                # Stage 8: Dry run
                with pl.stage("dry-run") as s_ctx:
                    try:
                        today = datetime.now(timezone.utc).date()
                        days_until_monday = (7 - today.weekday()) % 7
                        if days_until_monday == 0:
                            days_until_monday = 7
                        week_start_date = today + timedelta(days=days_until_monday)
                        week_start_str = week_start_date.isoformat()
                        res_val = executor.execute(
                            ctx,
                            "dry_run",
                            "weekly_calendar",
                            week_start_str,
                            {"week_start": week_start_str}
                        )
                        if not res_val.success:
                            raise RuntimeError(f"Dry run failed: {res_val.blocking_reasons}")
                        report = res_val.raw_result
                        s_ctx["items"] = report.ready_count
                        print(f"[dry-run] ✓ {report.ready_count} ready, ⚠ {report.warning_count} warnings, ✗ {report.blocked_count} blocked")
                    except Exception as e:
                        s_ctx["status"] = "error"
                        s_ctx["error"] = str(e)
                        print(f"[dry-run] ERROR: {e}")

                # Stage 9: Init analytics
                with pl.stage("init-analytics") as s_ctx:
                    try:
                        today = datetime.now(timezone.utc).date()
                        days_until_monday = (7 - today.weekday()) % 7
                        if days_until_monday == 0:
                            days_until_monday = 7
                        week_start_date = today + timedelta(days=days_until_monday)
                        week_start_str = week_start_date.isoformat()
                        res_analytics = executor.execute(
                            ctx,
                            "init_analytics",
                            "weekly_calendar",
                            week_start_str,
                            {"week_start": week_start_str}
                        )
                        if not res_analytics.success:
                            raise RuntimeError(f"Init analytics failed: {res_analytics.blocking_reasons}")
                        count = int(res_analytics.affected_artifacts.get("initialized_count", "0"))
                        s_ctx["items"] = count
                        print(f"[init-analytics] {count} records created")
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
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            res = executor.execute(ctx, "build_manifest", "manifest", args.topic_id, {})
            if res.success:
                manifest = res.raw_result
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
            else:
                print(f"Error building manifest: {res.blocking_reasons}")
                return 1

        elif args.command == "build-all-manifests":
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            res = executor.execute(ctx, "build_all_manifests", "manifest", "all", {})
            if res.success:
                manifests = res.raw_result
                complete = sum(1 for m in manifests if m.overall_status == "complete")
                partial = sum(1 for m in manifests if m.overall_status == "partial")
                blocked = sum(1 for m in manifests if m.overall_status == "blocked")

                print(f"Built and saved {len(manifests)} manifests")
                print(f"  Complete: {complete}")
                print(f"  Partial: {partial}")
                print(f"  Blocked: {blocked}")
                return 0
            else:
                print(f"Error building manifests: {res.blocking_reasons}")
                return 1

        elif args.command == "plan-week":
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            # Parse week_start
            if args.week_start:
                try:
                    week_start_date = datetime.strptime(args.week_start, "%Y-%m-%d").date()
                except ValueError:
                    print(f"Error: Invalid date format '{args.week_start}'. Use YYYY-MM-DD format.")
                    return 1
            else:
                # Default to next Monday
                today = datetime.now(timezone.utc).date()
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                week_start_date = today + timedelta(days=days_until_monday)

            res = executor.execute(
                ctx,
                "plan_week",
                "weekly_calendar",
                week_start_date.isoformat(),
                {"week_start_date": week_start_date}
            )

            if not res.success:
                print(f"Error planning week: {res.blocking_reasons}")
                return 1

            calendar = res.raw_result
            json_path = ctx.storage.save_calendar(calendar)

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
            md_path = ctx.storage.calendars_dir / f"{calendar.week_start}.md"
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
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

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
                today = datetime.now(timezone.utc).date()
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                week_start_date = today + timedelta(days=days_until_monday)
                week_start_str = week_start_date.isoformat()

            # Try to find existing calendar
            calendars = ctx.storage.list_calendars()
            calendar = None
            for c in calendars:
                if c.week_start == week_start_str:
                    calendar = c
                    break

            # If not found, generate one via executor
            if calendar is None:
                res_plan = executor.execute(
                    ctx,
                    "plan_week",
                    "weekly_calendar",
                    week_start_str,
                    {"week_start_date": week_start_date}
                )
                if not res_plan.success:
                    print(f"Error planning week for dry-run: {res_plan.blocking_reasons}")
                    return 1
                calendar = res_plan.raw_result

            # Run dry-run validation
            res_val = executor.execute(
                ctx,
                "dry_run",
                "weekly_calendar",
                week_start_str,
                {"week_start": week_start_str}
            )

            if not res_val.success:
                print(f"Error running dry-run validation: {res_val.blocking_reasons}")
                return 1

            report = res_val.raw_result
            json_path = ctx.storage.save_dryrun(report)

            # Export markdown
            from content_creation.planning.dryrun import DryRunValidator
            publishing_config_path = base_dir / "config" / "publishing.yaml"
            validator = DryRunValidator(ctx.storage, publishing_config_path)
            md_path = ctx.storage.dryruns_dir / f"{week_start_str}.md"
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
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            # Parse week_start
            if args.week_start:
                try:
                    week_start_str = args.week_start
                except ValueError:
                    print(f"Error: Invalid date format '{args.week_start}'. Use YYYY-MM-DD format.")
                    return 1
            else:
                # Default to next Monday
                today = datetime.now(timezone.utc).date()
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                week_start_date = today + timedelta(days=days_until_monday)
                week_start_str = week_start_date.isoformat()

            res = executor.execute(
                ctx,
                "init_analytics",
                "weekly_calendar",
                week_start_str,
                {"week_start": week_start_str}
            )

            if res.success:
                print(f"\nAnalytics initialized: {res.affected_artifacts.get('initialized_count', '0')} new records")
                print(f"Week: {week_start_str}")
                return 0
            else:
                print(f"Error executing init-analytics: {res.blocking_reasons}")
                return 1

        elif args.command == "update-analytics":
            ctx = ApplicationContext.create(base_dir)
            from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
            executor = WorkflowActionExecutor()

            # Load existing analytics
            analytics = ctx.storage.get_analytics(args.post_id)
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
                metrics = {}
                # Prompt for performance fields
                metrics["views_24h"] = prompt_numeric("Views (24h)", analytics.performance.views_24h)
                metrics["views_7d"] = prompt_numeric("Views (7d)", analytics.performance.views_7d)
                metrics["views_30d"] = prompt_numeric("Views (30d)", analytics.performance.views_30d)
                metrics["reach_24h"] = prompt_numeric("Reach (24h)", analytics.performance.reach_24h)
                metrics["reach_7d"] = prompt_numeric("Reach (7d)", analytics.performance.reach_7d)
                metrics["saves"] = prompt_numeric("Saves", analytics.performance.saves)
                metrics["comments"] = prompt_numeric("Comments", analytics.performance.comments)
                metrics["cta_clicks"] = prompt_numeric("CTA Clicks", analytics.performance.cta_clicks)

                # Watch time (video only)
                if analytics.format == "short_video":
                    metrics["watch_time_pct"] = prompt_float("Watch time %", analytics.performance.watch_time_pct)
                else:
                    print("Watch time %: (skipped - video only)")

                # Posted at - only update if user provides a value
                posted_at = analytics.posted_at
                posted_input = input(f"Posted at (YYYY-MM-DDTHH:MM) [{analytics.posted_at or 'None'}]: ").strip()
                if posted_input != "":
                    try:
                        datetime.strptime(posted_input, "%Y-%m-%dT%H:%M")
                        posted_at = posted_input
                    except ValueError:
                        print("Error: Invalid date format. Use YYYY-MM-DDTHH:MM")

                # Notes
                notes_val = prompt_optional_string("Notes", analytics.notes)

            except KeyboardInterrupt:
                print("\nUpdate cancelled.")
                return 130

            res = executor.execute(
                ctx,
                "update_analytics",
                "weekly_calendar",
                args.post_id,
                {
                    "post_id": args.post_id,
                    "posted_at": posted_at,
                    "notes": notes_val,
                    "metrics": metrics,
                }
            )

            if res.success:
                updated_analytics = res.raw_result
                print(f"\nUpdated: {args.post_id}")
                print(f"Last updated: {updated_analytics.last_updated}")
                return 0
            else:
                print(f"Error updating analytics: {res.blocking_reasons}")
                return 1

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

                # Apply decisions and rebuild manifest using the executor
                from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                executor = WorkflowActionExecutor()
                last_manifest = None
                
                for decision in decisions:
                    action_id = "approve_asset" if decision.status.value == "approved" else "reject_asset"
                    res = executor.execute(
                        ctx,
                        action_id,
                        "assets",
                        args.topic_id,
                        {"asset_type": decision.asset_type},
                        notes=decision.rejection_reason
                    )
                    if not res.success:
                        raise RuntimeError(f"Asset review decision failed: {res.blocking_reasons}")
                    last_manifest = res.raw_result.manifest

                # Print updated summary
                print("\n" + "=" * 50)
                print("Review complete.")
                print(f"Approved: {approved_count}")
                print(f"Rejected: {rejected_count}")
                print(f"Skipped: {skipped_count}")
                if last_manifest:
                    print(f"Overall Status: {last_manifest.overall_status}")
                    print(f"Ready for Planner: {last_manifest.ready_for_planner}")
                else:
                    # If all assets were already approved or no decisions were made, load the manifest
                    manifest_data_status = manifest_data.get('overall_status', 'unknown')
                    manifest_data_ready = manifest_data.get('ready_for_planner', False)
                    print(f"Overall Status: {manifest_data_status}")
                    print(f"Ready for Planner: {manifest_data_ready}")
                print("=" * 50)

                return 0

            except KeyboardInterrupt:
                print("\nReview interrupted.")
                return 130

        elif args.command == "event-timeline":
            from content_creation.events.store import (
                SQLiteEventRepository,
                EventTimelineService,
            )

            db_path = base_dir / "data" / "events.db"
            if not db_path.exists():
                print("No event store found. Events will appear after running pipeline actions.")
                return 0

            repo = SQLiteEventRepository(str(db_path))
            try:
                service = EventTimelineService(repository=repo)

                if args.correlation_id:
                    events = service.timeline_for_correlation(args.correlation_id)
                elif args.entity_type and args.entity_id:
                    events = service.entity_history(args.entity_type, args.entity_id, limit=args.limit)
                elif args.entity_type:
                    events = service.entity_history(args.entity_type, "__all__", limit=args.limit)
                else:
                    page = service.recent_events(
                        page_size=args.limit,
                        category=args.category,
                    )
                    events = page.events

                if not events:
                    print("No events found.")
                    return 0

                print(f"\n{'Timestamp':<20} {'Event':<25} {'Category':<12} {'Source':<20} {'Entity':<15}")
                print("-" * 92)
                for e in events:
                    ts = e.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    entity = f"{e.entity_type}:{e.entity_id[:12]}" if e.entity_type else "-"
                    print(f"{ts:<20} {e.event_name:<25} {e.category:<12} {e.source:<20} {entity:<15}")

                print(f"\nTotal: {len(events)} events")
                return 0
            finally:
                repo.close()

        elif args.command == "event-stats":
            from content_creation.events.store import (
                SQLiteEventRepository,
                EventMaintenanceService,
            )

            db_path = base_dir / "data" / "events.db"
            if not db_path.exists():
                print("No event store found.")
                return 0

            repo = SQLiteEventRepository(str(db_path))
            try:
                service = EventMaintenanceService(repository=repo)
                stats = service.storage_stats()

                print("\n=== Event Store Statistics ===")
                for category, count in sorted(stats.items()):
                    print(f"  {category:<15} {count:>6} events")
                print("-" * 25)
                print(f"  {'TOTAL':<15} {stats.get('total', 0):>6} events")
                return 0
            finally:
                repo.close()

        elif args.command == "event-replay":
            from content_creation.events.store import (
                SQLiteEventRepository,
                EventReplayEngine,
            )
            from content_creation.events.bus import InMemoryEventBus

            db_path = base_dir / "data" / "events.db"
            if not db_path.exists():
                print("No event store found.")
                return 0

            repo = SQLiteEventRepository(str(db_path))
            try:
                bus = InMemoryEventBus()
                engine = EventReplayEngine(repository=repo, bus=bus)

                dry_run_label = " (dry-run)" if args.dry_run else ""

                if args.correlation_id:
                    events = engine.replay_by_correlation(args.correlation_id, dry_run=args.dry_run)
                    print(f"Replayed {len(events)} events for correlation {args.correlation_id}{dry_run_label}")
                elif args.entity_type and args.entity_id:
                    events = engine.replay_by_entity(args.entity_type, args.entity_id, dry_run=args.dry_run)
                    print(f"Replayed {len(events)} events for {args.entity_type}:{args.entity_id}{dry_run_label}")
                elif args.category:
                    events = engine.replay_by_category(args.category, limit=args.limit, dry_run=args.dry_run)
                    print(f"Replayed {len(events)} events from category '{args.category}'{dry_run_label}")
                else:
                    events = engine.replay_all(limit=args.limit, dry_run=args.dry_run)
                    print(f"Replayed {len(events)} events{dry_run_label}")

                if events and args.dry_run:
                    print(f"\n{'Timestamp':<20} {'Event':<25} {'Entity':<15}")
                    print("-" * 60)
                    for e in events[:20]:
                        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        entity = f"{e.entity_type}:{e.entity_id[:12]}" if e.entity_type else "-"
                        print(f"{ts:<20} {e.event_type.value:<25} {entity:<15}")
                    if len(events) > 20:
                        print(f"  ... and {len(events) - 20} more")

                return 0
            finally:
                repo.close()

        elif args.command == "event-cleanup":
            from content_creation.events.store import (
                SQLiteEventRepository,
                EventMaintenanceService,
            )

            db_path = base_dir / "data" / "events.db"
            if not db_path.exists():
                print("No event store found.")
                return 0

            repo = SQLiteEventRepository(str(db_path))
            try:
                service = EventMaintenanceService(repository=repo)

                if args.dry_run:
                    stats = service.storage_stats()
                    print("Dry-run mode — no events will be deleted.")
                    print(f"\nCurrent event counts:")
                    for cat, count in sorted(stats.items()):
                        print(f"  {cat:<15} {count:>6}")
                else:
                    if args.category:
                        deleted = service.cleanup_expired(category=args.category)
                        print(f"Deleted {deleted} expired events from category '{args.category}'")
                    else:
                        summary = service.enforce_retention()
                        total = sum(summary.values())
                        print(f"Retention enforcement complete: {total} events deleted")
                        if summary:
                            for cat, count in summary.items():
                                print(f"  {cat}: {count} deleted")

                return 0
            finally:
                repo.close()

        elif args.command == "metrics-kpi":
            from content_creation.metrics import (
                SQLiteMetricRepository,
                KPICatalog,
            )

            db_path = base_dir / "data" / "metrics.db"
            if not db_path.exists():
                print("No metrics store found. Run pipeline actions first to generate metrics.")
                return 0

            repo = SQLiteMetricRepository(str(db_path))
            try:
                from datetime import timedelta
                end = datetime.now(timezone.utc)
                start = end - timedelta(days=args.days)

                catalog = KPICatalog(repo)
                kpis = catalog.calculate_all(start=start, end=end)

                print(f"\n=== KPI Report (last {args.days} days) ===\n")

                print("Workflow KPIs:")
                for name in ["briefs_generated", "storyboards_generated", "assets_generated", "approval_rate", "rejection_rate"]:
                    kpi = kpis[name]
                    print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

                print("\nJob KPIs:")
                for name in ["jobs_started", "jobs_completed", "jobs_failed", "job_success_rate", "job_retries", "average_job_runtime"]:
                    kpi = kpis[name]
                    print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

                print("\nSystem KPIs:")
                for name in ["lock_contentions", "zombie_recoveries", "stale_lock_expirations"]:
                    kpi = kpis[name]
                    print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

                print("\nPipeline KPIs:")
                for name in ["pipelines_completed", "pipelines_failed", "pipeline_success_rate"]:
                    kpi = kpis[name]
                    print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

                return 0
            finally:
                repo.close()

        elif args.command == "metrics-summary":
            from content_creation.metrics import (
                SQLiteMetricRepository,
                TelemetryService,
            )
            from content_creation.events.store import SQLiteEventRepository

            metrics_db = base_dir / "data" / "metrics.db"
            events_db = base_dir / "data" / "events.db"

            metrics_repo = None
            event_repo = None
            try:
                if metrics_db.exists():
                    metrics_repo = SQLiteMetricRepository(str(metrics_db))
                if events_db.exists():
                    event_repo = SQLiteEventRepository(str(events_db))

                if metrics_repo is None:
                    print("No metrics store found.")
                    return 0

                from datetime import timedelta
                end = datetime.now(timezone.utc)
                start = end - timedelta(days=args.days)

                service = TelemetryService(
                    metrics_repository=metrics_repo,
                    event_repository=event_repo,
                )
                summary = service.full_summary(start=start, end=end)

                print(f"\n=== Telemetry Summary (last {args.days} days) ===\n")

                sys = summary["system"]
                print("System:")
                print(f"  Events stored:    {sys.total_events_stored}")
                print(f"  Metrics stored:   {sys.total_metrics_stored}")

                wf = summary["workflow"]
                print("\nWorkflow:")
                print(f"  Briefs generated:     {wf.briefs_generated}")
                print(f"  Storyboards:          {wf.storyboards_generated}")
                print(f"  Assets generated:     {wf.assets_generated}")
                print(f"  Approval rate:        {wf.approval_rate:.1f}%")

                jobs = summary["jobs"]
                print("\nJobs:")
                print(f"  Started:          {jobs.jobs_started}")
                print(f"  Completed:        {jobs.jobs_completed}")
                print(f"  Failed:           {jobs.jobs_failed}")
                print(f"  Success rate:     {jobs.success_rate:.1f}%")
                print(f"  Avg runtime:      {jobs.average_runtime_seconds:.1f}s")

                rel = summary["reliability"]
                print("\nReliability:")
                print(f"  Lock contentions:     {rel.lock_contentions}")
                print(f"  Zombie recoveries:    {rel.zombie_recoveries}")
                print(f"  Pipeline success:     {rel.pipeline_success_rate:.1f}%")

                return 0
            finally:
                if metrics_repo:
                    metrics_repo.close()
                if event_repo:
                    event_repo.close()

        elif args.command == "metrics-query":
            from content_creation.metrics import (
                SQLiteMetricRepository,
                MetricType,
            )

            db_path = base_dir / "data" / "metrics.db"
            if not db_path.exists():
                print("No metrics store found.")
                return 0

            repo = SQLiteMetricRepository(str(db_path))
            try:
                metric_type = None
                if args.type:
                    metric_type = MetricType(args.type)

                results = repo.query_metrics(
                    metric_name=args.name,
                    metric_type=metric_type,
                    limit=args.limit,
                )

                if not results:
                    print("No metrics found.")
                    return 0

                print(f"\n{'Timestamp':<20} {'Metric':<30} {'Type':<10} {'Value':>10}")
                print("-" * 70)
                for r in results:
                    ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"{ts:<20} {r.metric_name:<30} {r.metric_type.value:<10} {r.value:>10.2f}")

                print(f"\nTotal: {len(results)} metrics")
                return 0
            finally:
                repo.close()

        elif args.command == "metrics-cleanup":
            from content_creation.metrics import (
                SQLiteMetricRepository,
                MetricsMaintenanceService,
            )

            db_path = base_dir / "data" / "metrics.db"
            if not db_path.exists():
                print("No metrics store found.")
                return 0

            repo = SQLiteMetricRepository(str(db_path))
            try:
                service = MetricsMaintenanceService(repository=repo)

                if args.dry_run:
                    stats = service.storage_stats()
                    print("Dry-run mode — no metrics will be deleted.")
                    print(f"\nCurrent metrics: {stats['total_metrics']}")
                    print(f"Retention: {stats['retention_days']} days")
                else:
                    result = service.enforce_retention()
                    print(f"Deleted {result['deleted']} expired metrics")

                return 0
            finally:
                repo.close()

        elif args.command == "metrics-rebuild":
            from content_creation.metrics import (
                SQLiteMetricRepository,
                MetricsSubscriber,
            )
            from content_creation.events.store import (
                SQLiteEventRepository,
                EventReplayEngine,
            )
            from content_creation.events.bus import InMemoryEventBus

            metrics_db = base_dir / "data" / "metrics.db"
            events_db = base_dir / "data" / "events.db"

            if not events_db.exists():
                print("No event store found. Cannot rebuild metrics.")
                return 0

            event_repo = SQLiteEventRepository(str(events_db))
            metric_repo = SQLiteMetricRepository(str(metrics_db))
            try:
                if args.dry_run:
                    event_count = event_repo.count_events()
                    metric_count = metric_repo.count_metrics()
                    print("Dry-run mode — no metrics will be written.")
                    print(f"Events in store: {event_count}")
                    print(f"Current metrics: {metric_count}")
                    print(f"\nReplay would process {event_count} events.")
                else:
                    # Clear existing metrics
                    from datetime import timedelta
                    deleted = metric_repo.delete_expired(
                        datetime.now(timezone.utc) + timedelta(days=365)
                    )
                    print(f"Cleared {deleted} existing metrics.")

                    # Replay events to rebuild
                    replay_bus = InMemoryEventBus()
                    MetricsSubscriber(repository=metric_repo, bus=replay_bus)
                    engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
                    replayed = engine.replay_all()

                    print(f"Replayed {len(replayed)} events.")
                    print(f"Metrics store now has {metric_repo.count_metrics()} metrics.")

                return 0
            finally:
                event_repo.close()
                metric_repo.close()

        elif args.command == "audit-query":
            from content_creation.audit import (
                SQLiteAuditRepository,
                AuditQueryService,
            )

            db_path = base_dir / "data" / "audit.db"
            if not db_path.exists():
                print("No audit store found. Run pipeline actions first to generate audit records.")
                return 0

            repo = SQLiteAuditRepository(str(db_path))
            try:
                service = AuditQueryService(repository=repo)

                start_dt = None
                end_dt = None
                if args.start:
                    start_dt = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if args.end:
                    end_dt = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

                from content_creation.audit.models import AuditSeverity as AS, AuditSource
                severity = AS(args.severity) if args.severity else None
                source = AuditSource(args.source) if args.source else None

                records = service.search_records(
                    query=args.action or args.event_type,
                    entity_type=args.entity_type,
                    actor_id=args.actor_id,
                )

                # Apply additional filters
                if args.severity:
                    records = [r for r in records if r.severity == severity]
                if args.source:
                    records = [r for r in records if r.source == source]
                if start_dt:
                    records = [r for r in records if r.timestamp >= start_dt]
                if end_dt:
                    records = [r for r in records if r.timestamp <= end_dt]

                records = records[:args.limit]

                if not records:
                    print("No audit records found.")
                    return 0

                print(f"\n{'Timestamp':<20} {'Action':<20} {'Entity':<20} {'Actor':<15} {'Severity':<10}")
                print("-" * 85)
                for r in records:
                    ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    entity = f"{r.entity_type}:{r.entity_id[:12]}" if r.entity_type else "-"
                    print(f"{ts:<20} {r.action_type:<20} {entity:<20} {r.actor_id[:15]:<15} {r.severity.value:<10}")

                print(f"\nTotal: {len(records)} audit records")
                return 0
            finally:
                repo.close()

        elif args.command == "audit-entity":
            from content_creation.audit import (
                SQLiteAuditRepository,
                AuditQueryService,
            )

            db_path = base_dir / "data" / "audit.db"
            if not db_path.exists():
                print("No audit store found.")
                return 0

            repo = SQLiteAuditRepository(str(db_path))
            try:
                service = AuditQueryService(repository=repo)
                records = service.search_by_entity(args.entity_type, args.entity_id)
                records = records[:args.limit]

                if not records:
                    print(f"No audit records found for {args.entity_type}" + (f":{args.entity_id}" if args.entity_id else ""))
                    return 0

                print(f"\nAudit Trail for {args.entity_type}" + (f":{args.entity_id}" if args.entity_id else "") + ":")
                print(f"{'Timestamp':<20} {'Action':<20} {'Actor':<15} {'Severity':<10}")
                print("-" * 65)
                for r in records:
                    ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"{ts:<20} {r.action_type:<20} {r.actor_id[:15]:<15} {r.severity.value:<10}")

                print(f"\nTotal: {len(records)} records")
                return 0
            finally:
                repo.close()

        elif args.command == "audit-actor":
            from content_creation.audit import (
                SQLiteAuditRepository,
                AuditQueryService,
            )

            db_path = base_dir / "data" / "audit.db"
            if not db_path.exists():
                print("No audit store found.")
                return 0

            repo = SQLiteAuditRepository(str(db_path))
            try:
                service = AuditQueryService(repository=repo)
                records = service.search_by_actor(args.actor_id)
                records = records[:args.limit]

                if not records:
                    print(f"No audit records found for actor '{args.actor_id}'")
                    return 0

                print(f"\nAudit Trail for Actor: {args.actor_id}")
                print(f"{'Timestamp':<20} {'Action':<20} {'Entity':<20} {'Severity':<10}")
                print("-" * 70)
                for r in records:
                    ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    entity = f"{r.entity_type}:{r.entity_id[:12]}" if r.entity_type else "-"
                    print(f"{ts:<20} {r.action_type:<20} {entity:<20} {r.severity.value:<10}")

                print(f"\nTotal: {len(records)} records")
                return 0
            finally:
                repo.close()

        elif args.command == "audit-report":
            from content_creation.audit import (
                SQLiteAuditRepository,
                ComplianceReportService,
            )

            db_path = base_dir / "data" / "audit.db"
            if not db_path.exists():
                print("No audit store found.")
                return 0

            repo = SQLiteAuditRepository(str(db_path))
            try:
                service = ComplianceReportService(repository=repo)

                if args.type == "summary":
                    s = service.compliance_summary()
                    print("\n=== Compliance Summary ===")
                    print(f"  Total audit records:     {s.total_audit_records}")
                    print(f"  Active actors:           {s.actors_active}")
                    print(f"  Unique entities:         {s.unique_entities}")
                    print(f"  Critical events:         {s.critical_events}")
                    print(f"  Retention period:        {s.retention_period_days} days")

                elif args.type == "operator":
                    reports = service.operator_activity_report()
                    if not reports:
                        print("No operator activity found.")
                        return 0
                    print("\n=== Operator Activity Report ===")
                    print(f"{'Actor ID':<15} {'Actions':>8} {'First Seen':<20} {'Last Seen':<20}")
                    print("-" * 65)
                    for r in reports:
                        first = r.first_action.strftime("%Y-%m-%d %H:%M") if r.first_action else "-"
                        last = r.last_action.strftime("%Y-%m-%d %H:%M") if r.last_action else "-"
                        print(f"{r.actor_id[:15]:<15} {r.total_actions:>8} {first:<20} {last:<20}")

                elif args.type == "decision":
                    report = service.workflow_decision_report()
                    print("\n=== Workflow Decision Report ===")
                    print(f"  Total decisions:    {report.total_decisions}")
                    print(f"  Approvals:          {report.approvals}")
                    print(f"  Rejections:         {report.rejections}")
                    print(f"  Approval rate:      {report.approval_rate:.1f}%")

                elif args.type == "job":
                    report = service.job_execution_report()
                    print("\n=== Job Execution Report ===")
                    print(f"  Total jobs:         {report.total_jobs}")
                    print(f"  Completed:          {report.completed}")
                    print(f"  Failed:             {report.failed}")
                    print(f"  Success rate:       {report.success_rate:.1f}%")

                elif args.type == "incident":
                    timeline = service.incident_timeline()
                    print("\n=== Incident Timeline ===")
                    print(f"  Critical events:    {timeline.total_critical}")
                    print(f"  Warning events:     {timeline.total_warning}")
                    if timeline.events:
                        print(f"\n{'Timestamp':<20} {'Action':<20} {'Severity':<10} {'Entity':<20}")
                        print("-" * 70)
                        for r in timeline.events[:20]:
                            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                            entity = f"{r.entity_type}:{r.entity_id[:12]}" if r.entity_type else "-"
                            print(f"{ts:<20} {r.action_type:<20} {r.severity.value:<10} {entity:<20}")

                return 0
            finally:
                repo.close()

        elif args.command == "audit-rebuild":
            from content_creation.audit import (
                SQLiteAuditRepository,
                AuditSubscriber,
            )
            from content_creation.events.store import (
                SQLiteEventRepository,
                EventReplayEngine,
            )
            from content_creation.events.bus import InMemoryEventBus

            events_db = base_dir / "data" / "events.db"
            audit_db = base_dir / "data" / "audit.db"

            if not events_db.exists():
                print("No event store found. Cannot rebuild audit trail.")
                return 0

            event_repo = SQLiteEventRepository(str(events_db))
            audit_repo = SQLiteAuditRepository(str(audit_db))
            try:
                if args.dry_run:
                    event_count = event_repo.count_events()
                    audit_count = audit_repo.count_records()
                    print("Dry-run mode — no audit records will be written.")
                    print(f"Events in store: {event_count}")
                    print(f"Current audit records: {audit_count}")
                    print(f"\nReplay would process {event_count} events.")
                else:
                    # Clear existing audit records
                    from datetime import timedelta
                    deleted = audit_repo.delete_expired(
                        datetime.now(timezone.utc) + timedelta(days=365)
                    )
                    print(f"Cleared {deleted} existing audit records.")

                    # Replay events to rebuild audit trail
                    replay_bus = InMemoryEventBus()
                    AuditSubscriber(repository=audit_repo, bus=replay_bus)
                    engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
                    replayed = engine.replay_all()

                    print(f"Replayed {len(replayed)} events.")
                    print(f"Audit store now has {audit_repo.count_records()} records.")

                return 0
            finally:
                event_repo.close()
                audit_repo.close()

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
