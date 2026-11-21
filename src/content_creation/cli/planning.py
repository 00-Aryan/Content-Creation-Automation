"""Planning and review commands: assets review, batch approval, manifests, calendar, dry-run, and analytics."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, cast

import typer

from content_creation.application import AssetDecision, AssetReviewService
from content_creation.cli.common import get_context, get_next_monday, write_text_utf8
from content_creation.planning.dryrun import DryRunValidator
from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor


def review_assets(
    topic_id: str = typer.Option(
        ..., "--topic-id", help="Topic ID to review assets for"
    ),
) -> int:
    """Interactively review assets for a topic."""
    ctx = get_context()
    service = AssetReviewService()

    # Load and display review queue items
    try:
        queue = service.get_review_queue(ctx, topic_id)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Run 'build-manifest --topic-id {topic_id}' first to create the manifest.")
        return 1
    except Exception as e:
        print(f"Error: Failed to load manifest: {e}")
        return 1

    manifest_path = ctx.storage.manifests_dir / f"{topic_id}.json"
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data: dict[str, Any] = json.load(f)
    except Exception as e:
        print(f"Error: Failed to load manifest: {e}")
        return 1

    print("\n" + "=" * 50)
    print(f"Topic: {manifest_data.get('topic_title', 'Unknown')}")
    print(f"Source: {manifest_data.get('source_url', 'Unknown')}")
    print(f"Overall Status: {manifest_data.get('overall_status', 'unknown')}")
    print("=" * 50)

    approved_count = 0
    rejected_count = 0
    skipped_count = 0
    decisions: list[AssetDecision] = []

    try:
        for item in queue:
            asset_type = item.asset_type
            status = item.status

            if status == "approved":
                print(f"\n=== {asset_type.upper()} ===")
                print(f"Status: {status} (ALREADY APPROVED)")
                continue

            print(f"\n=== {asset_type.upper()} ===")
            print(f"Status: {status}")

            if item.summary_text:
                print(f"Summary: {item.summary_text[:100]}...")

            while True:
                show_full = input("Show full content? (y/n): ").strip().lower()
                if show_full in ("y", "n"):
                    break
                print("Invalid input. Please enter 'y' or 'n'.")

            if show_full == "y":
                print("\n--- Full Content ---")
                print(json.dumps(item.content, indent=2))
                print("--- End ---\n")

            while True:
                decision = (
                    input("Decision (a=approve / r=reject / s=skip): ").strip().lower()
                )
                if decision in ("a", "r", "s"):
                    break
                print("Invalid input. Please enter 'a', 'r', or 's'.")

            if decision == "a":
                decisions.append(
                    AssetDecision(asset_type=asset_type, status=ReviewStatus.APPROVED)
                )
                print("✓ Approved")
                approved_count += 1
            elif decision == "r":
                reason = input("Reason (optional): ").strip()
                if reason:
                    print(f"Rejection reason: {reason}")
                decisions.append(
                    AssetDecision(
                        asset_type=asset_type,
                        status=ReviewStatus.REJECTED,
                        rejection_reason=reason,
                    )
                )
                print("✗ Rejected")
                rejected_count += 1
            else:
                print("→ Skipped")
                skipped_count += 1

        executor = WorkflowActionExecutor()
        last_manifest: Any = None

        for dec in decisions:
            action_id = (
                "approve_asset"
                if dec.status.value == "approved"
                else "reject_asset"
            )
            res = executor.execute(
                ctx,
                action_id,
                "assets",
                topic_id,
                {"asset_type": dec.asset_type},
                notes=dec.rejection_reason,
            )
            if not res.success:
                raise RuntimeError(
                    f"Asset review decision failed: {res.blocking_reasons}"
                )
            res_result: Any = res.raw_result
            last_manifest = getattr(res_result, "manifest", None)

        print("\n" + "=" * 50)
        print("Review complete.")
        print(f"Approved: {approved_count}")
        print(f"Rejected: {rejected_count}")
        print(f"Skipped: {skipped_count}")
        if last_manifest:
            print(f"Overall Status: {last_manifest.overall_status}")
            print(f"Ready for Planner: {last_manifest.ready_for_planner}")
        else:
            manifest_data_status = manifest_data.get("overall_status", "unknown")
            manifest_data_ready = manifest_data.get("ready_for_planner", False)
            print(f"Overall Status: {manifest_data_status}")
            print(f"Ready for Planner: {manifest_data_ready}")
        print("=" * 50)
        return 0

    except KeyboardInterrupt:
        print("\nReview interrupted.")
        return 130


def batch_approve(
    asset_type: str = typer.Option(
        "all",
        "--asset-type",
        help="Asset type to approve (brief/script/carousel/newsletter/thumbnail/all)",
    ),
    all: bool = typer.Option(
        False, "--all", help="Confirm approving all matching assets"
    ),
    exclude_incomplete: bool = typer.Option(
        False,
        "--exclude-incomplete",
        help="Skip assets where any field is 'needs_review'",
    ),
) -> int:
    """Batch approve assets across all topics."""
    if not all:
        print("Error: Please specify --all to confirm batch approval")
        return 1

    ctx = get_context()
    executor = WorkflowActionExecutor()

    res = executor.execute(
        ctx,
        "batch_approve",
        "assets",
        "all",
        {
            "asset_type": asset_type,
            "exclude_incomplete": exclude_incomplete,
        },
    )

    if res.success:
        print(f"Approved: {res.affected_artifacts.get('approved_count', '0')} assets")
        print(
            f"Manifests rebuilt: {res.affected_artifacts.get('manifests_rebuilt', '0')}"
        )
        return 0
    else:
        print(f"Error executing batch approval: {res.blocking_reasons}")
        return 1


def build_manifest(
    topic_id: str = typer.Option(
        ..., "--topic-id", help="Topic ID to build manifest for"
    ),
) -> int:
    """Build a manifest for a single topic."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    res = executor.execute(ctx, "build_manifest", "manifest", topic_id, {})
    if res.success:
        manifest: Any = res.raw_result
        print(f"Topic ID: {manifest.topic_id}")
        print(f"Overall Status: {manifest.overall_status}")
        print(f"Ready for Planner: {manifest.ready_for_planner}")
        print("Assets:")
        for atype in ["brief", "script", "carousel", "newsletter", "thumbnail"]:
            asset_entry = manifest.assets.get(atype) if manifest.assets else None
            status_str = asset_entry.status if asset_entry else "missing"
            print(f"  {atype:12} {status_str}")
        if manifest.blocking_reasons:
            print(f"Blocking: {', '.join(manifest.blocking_reasons)}")
        else:
            print("Blocking: none")
        return 0
    else:
        print(f"Error building manifest: {res.blocking_reasons}")
        return 1


def build_all_manifests() -> int:
    """Build manifests for all topics with briefs."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    res = executor.execute(ctx, "build_all_manifests", "manifest", "all", {})
    if res.success:
        manifests = cast(list[Any], res.raw_result)
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


def plan_week(
    week_start: Optional[str] = typer.Option(
        None,
        "--week-start",
        help="Week start date (YYYY-MM-DD format, defaults to next Monday)",
    ),
) -> int:
    """Plan content calendar for a week."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    if week_start:
        try:
            week_start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{week_start}'. Use YYYY-MM-DD format.")
            return 1
    else:
        week_start_date = get_next_monday()

    res = executor.execute(
        ctx,
        "plan_week",
        "weekly_calendar",
        week_start_date.isoformat(),
        {"week_start_date": week_start_date},
    )

    if not res.success:
        print(f"Error planning week: {res.blocking_reasons}")
        return 1

    calendar: Any = res.raw_result
    json_path = ctx.storage.save_calendar(calendar)

    week_end = calendar.week_end
    generated_at = calendar.generated_at[:19].replace("T", " ")
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

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

    # Save markdown with strict UTF-8 encoding
    md_path = ctx.storage.calendars_dir / f"{calendar.week_start}.md"
    write_text_utf8(md_path, md_content)

    print(f"Week planned: {calendar.week_start} to {week_end}")
    print(f"Total posts: {calendar.total_posts}")
    for fmt, count in calendar.format_counts.items():
        print(f"  {fmt}: {count} posts")
    print(f"Saved to: {json_path}")
    print(f"Markdown: {md_path}")
    return 0


def dry_run(
    week_start: Optional[str] = typer.Option(
        None,
        "--week-start",
        help="Week start date (YYYY-MM-DD format, defaults to next Monday)",
    ),
) -> int:
    """Run dry-run validation for a week's content."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    if week_start:
        try:
            week_start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
            week_start_str = week_start
        except ValueError:
            print(f"Error: Invalid date format '{week_start}'. Use YYYY-MM-DD format.")
            return 1
    else:
        week_start_date = get_next_monday()
        week_start_str = week_start_date.isoformat()

    calendars = ctx.storage.list_calendars()
    calendar: Any = None
    for c in calendars:
        if c.week_start == week_start_str:
            calendar = c
            break

    if calendar is None:
        res_plan = executor.execute(
            ctx,
            "plan_week",
            "weekly_calendar",
            week_start_str,
            {"week_start_date": week_start_date},
        )
        if not res_plan.success:
            print(f"Error planning week for dry-run: {res_plan.blocking_reasons}")
            return 1
        calendar = res_plan.raw_result

    res_val = executor.execute(
        ctx,
        "dry_run",
        "weekly_calendar",
        week_start_str,
        {"week_start": week_start_str},
    )

    if not res_val.success:
        print(f"Error running dry-run validation: {res_val.blocking_reasons}")
        return 1

    report: Any = res_val.raw_result
    json_path = ctx.storage.save_dryrun(report)

    publishing_config_path = ctx.base_dir / "config" / "publishing.yaml"
    validator = DryRunValidator(ctx.storage, publishing_config_path)
    md_path = ctx.storage.dryruns_dir / f"{week_start_str}.md"
    validator.export_markdown(report, md_path)

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


def init_analytics(
    week_start: Optional[str] = typer.Option(
        None,
        "--week-start",
        help="Week start date (YYYY-MM-DD format, defaults to next Monday)",
    ),
) -> int:
    """Initialize analytics records for a week's posts."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    if week_start:
        week_start_str = week_start
    else:
        week_start_str = get_next_monday().isoformat()

    res = executor.execute(
        ctx,
        "init_analytics",
        "weekly_calendar",
        week_start_str,
        {"week_start": week_start_str},
    )

    if res.success:
        print(
            f"\nAnalytics initialized: {res.affected_artifacts.get('initialized_count', '0')} new records"
        )
        print(f"Week: {week_start_str}")
        return 0
    else:
        print(f"Error executing init-analytics: {res.blocking_reasons}")
        return 1


def update_analytics(
    post_id: str = typer.Option(
        ..., "--post-id", help="Post ID to update (format: topic_id_format_weekstart)"
    ),
) -> int:
    """Update analytics record for a post."""
    ctx = get_context()
    executor = WorkflowActionExecutor()

    analytics = ctx.storage.get_analytics(post_id)
    if analytics is None:
        print(f"Error: No analytics record found for '{post_id}'")
        return 1

    print(f"Updating: {post_id}")
    print("Press Enter to keep current value, or enter new value.")

    def prompt_numeric(
        field_name: str, current_value: Optional[int]
    ) -> Optional[int]:
        while True:
            prompt_str = f"{field_name} [{current_value if current_value is not None else 'None'}]: "
            try:
                user_input = input(prompt_str).strip()
                if user_input == "":
                    return current_value
                value = int(user_input)
                if value < 0:
                    print("Error: Value must be non-negative")
                    continue
                return value
            except ValueError:
                print("Error: Please enter a valid integer")

    def prompt_float(
        field_name: str,
        current_value: Optional[float],
        min_val: float = 0.0,
        max_val: float = 100.0,
    ) -> Optional[float]:
        while True:
            prompt_str = f"{field_name} [{current_value if current_value is not None else 'None'}]: "
            try:
                user_input = input(prompt_str).strip()
                if user_input == "":
                    return current_value
                value = float(user_input)
                if value < min_val or value > max_val:
                    print(f"Error: Value must be between {min_val} and {max_val}")
                    continue
                return value
            except ValueError:
                print("Error: Please enter a valid number")

    def prompt_optional_string(
        field_name: str, current_value: Optional[str]
    ) -> Optional[str]:
        prompt_str = f"{field_name} [{current_value if current_value else 'None'}]: "
        user_input = input(prompt_str).strip()
        if user_input == "":
            return current_value
        return user_input

    try:
        metrics: dict[str, Any] = {}
        metrics["views_24h"] = prompt_numeric("Views (24h)", analytics.performance.views_24h)
        metrics["views_7d"] = prompt_numeric("Views (7d)", analytics.performance.views_7d)
        metrics["views_30d"] = prompt_numeric("Views (30d)", analytics.performance.views_30d)
        metrics["reach_24h"] = prompt_numeric("Reach (24h)", analytics.performance.reach_24h)
        metrics["reach_7d"] = prompt_numeric("Reach (7d)", analytics.performance.reach_7d)
        metrics["saves"] = prompt_numeric("Saves", analytics.performance.saves)
        metrics["comments"] = prompt_numeric("Comments", analytics.performance.comments)
        metrics["cta_clicks"] = prompt_numeric("CTA Clicks", analytics.performance.cta_clicks)

        if analytics.format == "short_video":
            metrics["watch_time_pct"] = prompt_float(
                "Watch time %", analytics.performance.watch_time_pct
            )
        else:
            print("Watch time %: (skipped - video only)")

        posted_at = analytics.posted_at
        posted_input = input(
            f"Posted at (YYYY-MM-DDTHH:MM) [{analytics.posted_at or 'None'}]: "
        ).strip()
        if posted_input != "":
            try:
                datetime.strptime(posted_input, "%Y-%m-%dT%H:%M")
                posted_at = posted_input
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DDTHH:MM")

        notes_val = prompt_optional_string("Notes", analytics.notes)

    except KeyboardInterrupt:
        print("\nUpdate cancelled.")
        return 130

    res = executor.execute(
        ctx,
        "update_analytics",
        "weekly_calendar",
        post_id,
        {
            "post_id": post_id,
            "posted_at": posted_at,
            "notes": notes_val,
            "metrics": metrics,
        },
    )

    if res.success:
        updated_analytics: Any = res.raw_result
        print(f"\nUpdated: {post_id}")
        print(f"Last updated: {updated_analytics.last_updated}")
        return 0
    else:
        print(f"Error updating analytics: {res.blocking_reasons}")
        return 1


def register_planning_commands(app: typer.Typer) -> None:
    """Register planning and review subcommands to the Typer application."""
    app.command("review-assets", help="Interactively review assets for a topic")(
        review_assets
    )
    app.command("batch-approve", help="Batch approve assets across all topics")(
        batch_approve
    )
    app.command("build-manifest", help="Build a manifest for a single topic")(
        build_manifest
    )
    app.command(
        "build-all-manifests", help="Build manifests for all topics with briefs"
    )(build_all_manifests)
    app.command("plan-week", help="Plan content calendar for a week")(plan_week)
    app.command("dry-run", help="Run dry-run validation for a week's content")(dry_run)
    app.command(
        "init-analytics",
        help="Initialize analytics records for a week's posts",
    )(init_analytics)
    app.command("update-analytics", help="Update analytics record for a post")(
        update_analytics
    )
