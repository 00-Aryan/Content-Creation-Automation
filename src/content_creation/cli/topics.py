"""Topic inspection, listing, scoring dashboard, and schema validation commands."""

from typing import Optional

import typer

from content_creation import __version__
from content_creation.cli.common import get_context
from content_creation.models.topic import ScoredTopicItem, TopicItem, TopicStatus


def status() -> int:
    """Check system and ingestion status."""
    ctx = get_context()
    staged_items: list[TopicItem] = ctx.storage.list_staged()

    print("Content Creation Factory - Status: Operational")
    print(f"Version: {__version__}")
    print(f"Storage: {ctx.base_dir / 'data'}")
    print(f"Staged Items: {len(staged_items)}")

    if staged_items:
        sources: dict[str, int] = {}
        for item in staged_items:
            sources[item.source] = sources.get(item.source, 0) + 1
        print("Items by Source:")
        for src, count in sources.items():
            print(f"  - {src}: {count}")
    return 0


def list_topics(
    limit: int = typer.Option(10, "--limit", help="Maximum number of topics to list"),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status (raw, staged, scored, approved, rejected, review)",
    ),
) -> int:
    """List staged topics."""
    ctx = get_context()
    items: list[TopicItem] = ctx.storage.list_staged()

    if status:
        try:
            status_enum = TopicStatus(status)
            items = [item for item in items if item.status == status_enum]
        except ValueError:
            valid_statuses = ", ".join([s.value for s in TopicStatus])
            print(f"Error: Invalid status '{status}'. Valid values: {valid_statuses}")
            return 1

    items.sort(key=lambda x: x.published_at, reverse=True)

    print(f"\nLast {min(len(items), limit)} Staged Topics:")
    for item in items[:limit]:
        print(f"[{item.published_at[:10]}] {item.title[:60]}... ({item.source})")
    return 0


def validate_items() -> int:
    """Validate all staged items against schema."""
    ctx = get_context()
    items: list[TopicItem] = ctx.storage.list_staged()
    print(f"Validating {len(items)} items...")
    # Pydantic already validated them on load in list_staged()
    print("All items valid against TopicItem schema.")
    return 0


def review_scores(
    flagged_only: bool = typer.Option(
        False, "--flagged-only", help="Only show items with validation flags"
    ),
    min_score: Optional[float] = typer.Option(
        None, "--min-score", help="Minimum total score to show"
    ),
    limit: int = typer.Option(10, "--limit", help="Maximum number of topics to list"),
) -> int:
    """Review scored topics and flags."""
    ctx = get_context()
    items: list[ScoredTopicItem] = ctx.storage.list_scored()

    if flagged_only:
        items = [item for item in items if item.validation_flags]

    if min_score is not None:
        items = [item for item in items if item.priority_score >= min_score]

    items.sort(key=lambda x: x.priority_score, reverse=True)

    print(f"\nScored Topics Review (showing {min(len(items), limit)} of {len(items)}):")
    for item in items[:limit]:
        flag_indicator = "[!]" if item.validation_flags else "[ ]"
        print(
            f"{flag_indicator} {item.priority_score:5.1f} | {item.title[:60]}... ({item.source})"
        )
        if item.validation_flags:
            for flag in item.validation_flags:
                print(f"    - {flag}")
    return 0


def scoring_dashboard() -> int:
    """Show aggregate scoring metrics and flag breakdown."""
    ctx = get_context()
    items: list[ScoredTopicItem] = ctx.storage.list_scored()

    if not items:
        print("No scored items found. Run 'score-topics' first.")
        return 0

    avg_score = sum(item.priority_score for item in items) / len(items)
    flagged_items = [item for item in items if item.validation_flags]

    all_flags: list[str] = []
    for item in items:
        all_flags.extend(item.validation_flags)

    flag_counts: dict[str, int] = {}
    for flag in all_flags:
        flag_type = flag.split(":")[0]
        flag_counts[flag_type] = flag_counts.get(flag_type, 0) + 1

    print("\n=== Scoring Dashboard ===")
    print(f"Total Scored Items:  {len(items)}")
    print(f"Average Priority Score: {avg_score:.2f}")
    print(
        f"Flagged Items:       {len(flagged_items)} ({len(flagged_items)/len(items)*100:.1f}%)"
    )

    if flag_counts:
        print("\nFlag Breakdown:")
        for ftype, count in sorted(flag_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {ftype}: {count}")

    items.sort(key=lambda x: x.priority_score, reverse=True)
    print("\nTop 5 Scored Items:")
    for item in items[:5]:
        print(f"  {item.priority_score:5.1f} | {item.title[:50]}...")

    return 0


def register_topics_commands(app: typer.Typer) -> None:
    """Register topic subcommands to the Typer application."""
    app.command("status", help="Check system and ingestion status")(status)
    app.command("list-topics", help="List staged topics")(list_topics)
    app.command("validate-items", help="Validate all staged items against schema")(
        validate_items
    )
    app.command("review-scores", help="Review scored topics and flags")(review_scores)
    app.command(
        "scoring-dashboard",
        help="Show aggregate scoring metrics and flag breakdown",
    )(scoring_dashboard)
