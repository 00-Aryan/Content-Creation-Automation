"""Pipeline generation commands: collection, scoring, briefs, CI, storyboards, assets, and end-to-end execution."""

import json as json_mod
import os
from typing import Any, Optional, cast

import typer

from content_creation.application.pipeline_run_service import PipelineRunResult
from content_creation.cli.common import get_context, get_next_monday
from content_creation.utils.logging import PipelineLogger
from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor


def collect(
    source: Optional[str] = typer.Option(
        None, "--source", help="Specific source ID or type to collect (e.g., arxiv)"
    ),
    all: bool = typer.Option(
        False, "--all", help="Collect from all enabled sources"
    ),
) -> int:
    """Ingest topics from sources."""
    if not source and not all:
        print("Error: Please specify --source <id> or --all")
        return 1

    ctx = get_context()
    executor = WorkflowActionExecutor()
    src = source if source else None
    res = executor.execute(ctx, "collect", "topic", "all", {"source": src})
    if res.success:
        print(
            f"\nIngestion complete. Added {res.affected_artifacts.get('collected_count', '0')} new items."
        )
        return 0
    else:
        print(f"Error during collection: {res.blocking_reasons}")
        return 1


def score_topics(
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Limit number of items to score"
    ),
) -> int:
    """Score staged topics and run validation."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    print("Scoring topics...")
    res = executor.execute(ctx, "score_topics", "topic", "all", {"limit": limit})
    if res.success:
        print(f"Successfully scored {res.affected_artifacts.get('scored_count', '0')} items.")
        rejected = int(res.affected_artifacts.get("rejected_count", "0"))
        if rejected > 0:
            print(f"Rejected {rejected} items (check logs for reasons).")
        return 0
    else:
        print(f"Error during scoring: {res.blocking_reasons}")
        return 1


def generate_briefs(
    top: int = typer.Option(5, "--top", help="Number of top scored topics to process"),
) -> int:
    """Generate educational briefs using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set in environment")
        return 1

    ctx = get_context()
    executor = WorkflowActionExecutor()

    print("Generating briefs...")
    res = executor.execute(
        ctx,
        "generate_briefs",
        "brief",
        "all",
        {"top_n": top, "api_key": api_key},
    )
    if res.success:
        print(
            f"Generated {res.affected_artifacts.get('generated_count', '0')} briefs, {res.affected_artifacts.get('failures', '0')} failed"
        )
        return 0
    else:
        print(f"Error during brief generation: {res.blocking_reasons}")
        return 1


def generate_ci(
    top: int = typer.Option(5, "--top", help="Number of top scored topics to process"),
    topic_id: Optional[str] = typer.Option(
        None, "--topic-id", help="Specific topic ID to process"
    ),
) -> int:
    """Generate content intelligence (key insights)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    ctx = get_context()
    executor = WorkflowActionExecutor()

    target_id = topic_id if topic_id else "all"
    print("Generating content intelligence...")
    res = executor.execute(
        ctx,
        "generate_ci",
        "content_intelligence",
        target_id,
        {"top_n": top, "api_key": api_key},
    )
    if res.success:
        print(
            f"Generated {res.affected_artifacts.get('generated_count', '0')} content intelligence items, {res.affected_artifacts.get('failures', '0')} failed"
        )
        return 0
    else:
        print(f"Error during content intelligence generation: {res.blocking_reasons}")
        return 1


def generate_storyboards(
    top: int = typer.Option(5, "--top", help="Number of top scored topics to process"),
    topic_id: Optional[str] = typer.Option(
        None, "--topic-id", help="Specific topic ID to process"
    ),
) -> int:
    """Generate storyboards (visual narratives)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    ctx = get_context()
    executor = WorkflowActionExecutor()

    target_id = topic_id if topic_id else "all"
    print("Generating storyboards...")
    res = executor.execute(
        ctx,
        "generate_storyboards",
        "storyboard",
        target_id,
        {"top_n": top, "api_key": api_key},
    )
    if res.success:
        print(
            f"Generated {res.affected_artifacts.get('generated_count', '0')} storyboards, {res.affected_artifacts.get('failures', '0')} failed"
        )
        return 0
    else:
        print(f"Error during storyboard generation: {res.blocking_reasons}")
        return 1


def generate_assets(
    top: int = typer.Option(5, "--top", help="Number of briefs to process"),
) -> int:
    """Generate missing assets (thumbnails, scripts, carousels, newsletters)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set in environment")
        return 1

    ctx = get_context()
    executor = WorkflowActionExecutor()

    print("Generating assets...")
    res = executor.execute(
        ctx,
        "generate_assets",
        "assets",
        "all",
        {"top_n": top, "api_key": api_key},
    )
    if res.success:
        print(f"\nGenerated: {res.affected_artifacts.get('counts')}")
        print(f"Failures: {res.affected_artifacts.get('failed_count', '0')}")
        return 0
    else:
        print(f"Error during asset generation: {res.blocking_reasons}")
        return 1


def run_pipeline(
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve",
        help="Auto-approve all assets (skips human review)",
    ),
    top: int = typer.Option(
        5, "--top", help="Number of topics to process through generation"
    ),
    source: Optional[str] = typer.Option(
        None, "--source", help="Specific source to collect from"
    ),
) -> int:
    """Run the full pipeline end-to-end."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set in environment")
        return 1

    if auto_approve:
        print(
            "⚠ Auto-approve enabled — assets will be marked approved without human inspection."
        )

    ctx = get_context()
    executor = WorkflowActionExecutor()

    res = executor.execute(
        ctx,
        "run_pipeline",
        "manifest",
        "all",
        {
            "top_n": top,
            "source": source if source else None,
            "auto_approve": auto_approve,
            "api_key": api_key,
        },
    )

    if not res.success:
        print(f"Pipeline execution failed: {res.blocking_reasons}")
        return 1

    run_result = cast(PipelineRunResult, res.raw_result)
    if run_result is None:
        print("Pipeline execution failed: missing run result")
        return 1

    print(f"Pipeline log: {run_result.log_path}\n")

    # Print outputs for stages 1 to 6 based on service results
    collect_summary = run_result.stage_summaries.get("collect")
    if collect_summary:
        if collect_summary.get("success"):
            print(f"[collect] {collect_summary.get('count', 0)} new items")
        else:
            print(f"[collect] ERROR: {collect_summary.get('error')}")

    score_summary = run_result.stage_summaries.get("score")
    if score_summary:
        if score_summary.get("success"):
            print(
                f"[score] {score_summary.get('scored_count', 0)} scored, {score_summary.get('rejected_count', 0)} rejected"
            )
        else:
            print(f"[score] ERROR: {score_summary.get('error')}")

    briefs_summary = run_result.stage_summaries.get("generate-briefs")
    if briefs_summary:
        if briefs_summary.get("success"):
            print(f"[generate-briefs] {briefs_summary.get('generated_count', 0)} generated")
        else:
            print(f"[generate-briefs] ERROR: {briefs_summary.get('error')}")

    assets_summary = run_result.stage_summaries.get("generate-assets")
    if assets_summary:
        if assets_summary.get("success"):
            counts = cast(dict[str, int], assets_summary.get("counts", {}))
            asset_count = sum(counts.values())
            print(f"[generate-assets] {asset_count} generated")
        else:
            print(f"[generate-assets] ERROR: {assets_summary.get('error')}")

    manifests_summary = run_result.stage_summaries.get("build-manifests")
    if manifests_summary:
        if manifests_summary.get("success"):
            print(f"[build-manifests] {manifests_summary.get('count', 0)} built")
        else:
            print(f"[build-manifests] ERROR: {manifests_summary.get('error')}")

    if auto_approve:
        approve_summary = run_result.stage_summaries.get("batch-approve")
        if approve_summary:
            if approve_summary.get("success"):
                print(
                    f"[batch-approve] {approve_summary.get('approved_count', 0)} approved"
                )
            else:
                print(f"[batch-approve] ERROR: {approve_summary.get('error')}")

    pl = PipelineLogger(run_result.log_path)
    if run_result.log_path.exists():
        with open(run_result.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    pl.entries.append(json_mod.loads(line))

    # Run Stages 7, 8, 9 only if the service run succeeded
    if run_result.success:
        week_start_date = get_next_monday()
        week_start_str = week_start_date.isoformat()

        # Stage 7: Plan week
        with pl.stage("plan-week") as s_ctx:
            try:
                res_plan = executor.execute(
                    ctx,
                    "plan_week",
                    "weekly_calendar",
                    week_start_str,
                    {"week_start_date": week_start_date},
                )
                if not res_plan.success:
                    raise RuntimeError(f"Plan week failed: {res_plan.blocking_reasons}")
                calendar: Any = res_plan.raw_result
                s_ctx["items"] = calendar.total_posts
                print(f"[plan-week] {calendar.total_posts} posts scheduled")
            except Exception as e:
                s_ctx["status"] = "error"
                s_ctx["error"] = str(e)
                print(f"[plan-week] ERROR: {e}")

        # Stage 8: Dry run
        with pl.stage("dry-run") as s_ctx:
            try:
                res_val = executor.execute(
                    ctx,
                    "dry_run",
                    "weekly_calendar",
                    week_start_str,
                    {"week_start": week_start_str},
                )
                if not res_val.success:
                    raise RuntimeError(f"Dry run failed: {res_val.blocking_reasons}")
                report: Any = res_val.raw_result
                s_ctx["items"] = report.ready_count
                print(
                    f"[dry-run] ✓ {report.ready_count} ready, ⚠ {report.warning_count} warnings, ✗ {report.blocked_count} blocked"
                )
            except Exception as e:
                s_ctx["status"] = "error"
                s_ctx["error"] = str(e)
                print(f"[dry-run] ERROR: {e}")

        # Stage 9: Init analytics
        with pl.stage("init-analytics") as s_ctx:
            try:
                res_analytics = executor.execute(
                    ctx,
                    "init_analytics",
                    "weekly_calendar",
                    week_start_str,
                    {"week_start": week_start_str},
                )
                if not res_analytics.success:
                    raise RuntimeError(
                        f"Init analytics failed: {res_analytics.blocking_reasons}"
                    )
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
        st = info["status"]
        dur = f"{info['duration_s']:.1f}s" if info["duration_s"] else "-"
        items_val = info["details"].get("items", "-")
        print(f"{stage_name:<20} {st:<10} {dur:<10} {items_val}")
    print("=" * 50)
    print(f"Log saved: {run_result.log_path}")
    return 0


def register_pipeline_commands(app: typer.Typer) -> None:
    """Register pipeline subcommands to the Typer application."""
    app.command("collect", help="Ingest topics from sources")(collect)
    app.command("score-topics", help="Score staged topics and run validation")(
        score_topics
    )
    app.command(
        "generate-briefs", help="Generate educational briefs using Gemini"
    )(generate_briefs)
    app.command(
        "generate-ci", help="Generate content intelligence (key insights)"
    )(generate_ci)
    app.command(
        "generate-storyboards", help="Generate storyboards (visual narratives)"
    )(generate_storyboards)
    app.command(
        "generate-assets",
        help="Generate missing assets (thumbnails, scripts, carousels, newsletters)",
    )(generate_assets)
    app.command("run-pipeline", help="Run the full pipeline end-to-end")(run_pipeline)
