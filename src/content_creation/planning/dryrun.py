import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from content_creation.models.calendar import WeeklyCalendar
from content_creation.models.dryrun import AssetCheck, DryRunReport
from content_creation.storage.local import LocalStorage
from content_creation.utils.config import load_yaml_config

logger = logging.getLogger(__name__)


class DryRunValidator:
    def __init__(self, storage: LocalStorage, config_path: Path):
        self.storage = storage
        config = load_yaml_config(config_path)
        self.publishing_config = config
        logger.info("DryRunValidator initialized")

    def run(self, calendar: WeeklyCalendar) -> DryRunReport:
        checks: list[AssetCheck] = []
        warnings: list[str] = []
        ready_count = 0
        warning_count = 0
        blocked_count = 0

        has_draft = False
        has_needs_review = False
        has_rejected = False
        has_missing = False

        for post in calendar.posts:
            asset_path = self.storage.base_dir / post.asset_path

            if not asset_path.exists():
                check = AssetCheck(
                    topic_id=post.topic_id,
                    topic_title=post.topic_title,
                    format=post.format,
                    asset_path=post.asset_path,
                    review_status="missing",
                    is_ready=False,
                    warning=f"{post.format} for {post.topic_title} asset file not found at {post.asset_path}",
                )
                checks.append(check)
                blocked_count += 1
                has_missing = True
                warnings.append(f"⚠ {check.warning}")
                logger.warning(check.warning)
                continue

            try:
                with open(asset_path, "r") as f:
                    asset_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                check = AssetCheck(
                    topic_id=post.topic_id,
                    topic_title=post.topic_title,
                    format=post.format,
                    asset_path=post.asset_path,
                    review_status="error",
                    is_ready=False,
                    warning=f"Failed to load asset: {e}",
                )
                checks.append(check)
                blocked_count += 1
                logger.warning("Failed to load asset for %s: %s", post.topic_id, e)
                continue

            review_status = asset_data.get("review_status", "unknown")
            is_ready = review_status == "approved"

            warning = None
            if not is_ready:
                warning = f"{post.format} for {post.topic_title} is {review_status} — not approved for publishing"
                warnings.append(f"⚠ {warning}")
                logger.warning(warning)

            check = AssetCheck(
                topic_id=post.topic_id,
                topic_title=post.topic_title,
                format=post.format,
                asset_path=post.asset_path,
                review_status=review_status,
                is_ready=is_ready,
                warning=warning,
            )
            checks.append(check)

            if is_ready:
                ready_count += 1
            elif review_status == "missing":
                blocked_count += 1
            else:
                warning_count += 1

            if review_status == "draft":
                has_draft = True
            elif review_status == "needs_review":
                has_needs_review = True
            elif review_status == "rejected":
                has_rejected = True

        recommended_actions: list[str] = []
        if has_draft:
            recommended_actions.append("Run review-assets for topics with draft assets")
        if has_needs_review:
            recommended_actions.append("Review and approve needs_review assets before publishing")
        if has_rejected:
            recommended_actions.append("Regenerate rejected assets before scheduling")
        if has_missing:
            recommended_actions.append("Run generation commands for missing assets")
        if not has_draft and not has_needs_review and not has_rejected and not has_missing:
            recommended_actions.append("All assets ready — safe to publish")

        logger.info(
            "Dry run complete: %d ready, %d warnings, %d blocked",
            ready_count,
            warning_count,
            blocked_count,
        )

        return DryRunReport(
            week_start=calendar.week_start,
            week_end=calendar.week_end,
            total_scheduled=len(calendar.posts),
            ready_count=ready_count,
            warning_count=warning_count,
            blocked_count=blocked_count,
            checks=checks,
            warnings=warnings,
            recommended_actions=recommended_actions,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def export_markdown(self, report: DryRunReport, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        generated_at = report.generated_at[:19].replace("T", " ")

        md_content = f"""# Dry Run Report: {report.week_start} to {report.week_end}
Generated: {generated_at}

## Summary
- Total Scheduled: {report.total_scheduled}
- ✓ Ready: {report.ready_count}
- ⚠ Warnings: {report.warning_count}
- ✗ Blocked: {report.blocked_count}

## Asset Checklist
"""

        sorted_checks = sorted(report.checks, key=lambda c: (c.topic_id, c.format))

        for check in sorted_checks:
            ready_str = "✓ Yes" if check.is_ready else "✗ No"
            md_content += f"### {check.topic_title} — {check.format}\n"
            md_content += f"- Status: {check.review_status}\n"
            md_content += f"- Ready: {ready_str}\n"
            md_content += f"- Asset: {check.asset_path}\n"
            if check.warning:
                md_content += f"- Warning: {check.warning}\n"
            md_content += "\n"

        md_content += "## Warnings\n"
        if report.warnings:
            for w in report.warnings:
                md_content += f"{w}\n"
        else:
            md_content += "None\n"

        md_content += "\n## Recommended Actions\n"
        for i, action in enumerate(report.recommended_actions, 1):
            md_content += f"{i}. {action}\n"

        with open(output_path, "w") as f:
            f.write(md_content)