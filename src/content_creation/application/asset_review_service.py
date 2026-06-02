"""Service for orchestrating human-in-the-loop asset review processes."""

from dataclasses import dataclass
import json
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.manifest import ManifestBuilder
from content_creation.models.manifest import TopicManifest
from content_creation.shared.enums import ReviewStatus


@dataclass(frozen=True)
class AssetReviewItem:
    """Represents a reviewable asset metadata package."""

    asset_type: str
    status: str
    summary_text: Optional[str]
    content: Optional[dict]


@dataclass(frozen=True)
class AssetDecision:
    """Input payload for making a review decision on an asset."""

    asset_type: str
    status: ReviewStatus
    rejection_reason: Optional[str] = None


@dataclass(frozen=True)
class ReviewResult:
    """Outcome of applying asset review decisions."""

    approved_count: int
    rejected_count: int
    manifest: TopicManifest


class AssetReviewService:
    """Service to coordinate asset reviews, status updates, and manifest compilations."""

    def get_review_queue(
        self, ctx: ApplicationContext, topic_id: str
    ) -> List[AssetReviewItem]:
        """Loads and filters all reviewable assets for a given topic."""
        manifest_path = ctx.storage.manifests_dir / f"{topic_id}.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest found for topic '{topic_id}'")

        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        assets = manifest_data.get("assets", {})
        asset_order = ["brief", "script", "carousel", "newsletter", "thumbnail"]
        review_queue = []

        asset_dirs = {
            "brief": ctx.storage.briefs_dir,
            "script": ctx.storage.scripts_dir,
            "carousel": ctx.storage.carousels_dir,
            "newsletter": ctx.storage.newsletters_dir,
            "thumbnail": ctx.storage.thumbnails_dir,
        }

        for asset_type in asset_order:
            asset_entry = assets.get(asset_type)
            if not asset_entry:
                continue

            status = asset_entry.get("status", "missing")
            if status in ("skipped", "missing"):
                continue

            asset_file = asset_dirs.get(asset_type) / f"{topic_id}.json"
            summary_field = None
            asset_data = None

            if asset_file.exists():
                with open(asset_file, "r") as f:
                    asset_data = json.load(f)
                if asset_type == "brief":
                    summary_field = asset_data.get("why_it_matters", "N/A")
                elif asset_type == "script":
                    summary_field = asset_data.get("hook", "N/A")
                elif asset_type == "carousel":
                    slides = asset_data.get("slides", [])
                    summary_field = (
                        slides[0].get("title", "N/A") if slides else "N/A"
                    )
                elif asset_type == "newsletter":
                    summary_field = asset_data.get("subject_line", "N/A")
                elif asset_type == "thumbnail":
                    summary_field = asset_data.get("title_text", "N/A")

            review_queue.append(
                AssetReviewItem(
                    asset_type=asset_type,
                    status=status,
                    summary_text=summary_field,
                    content=asset_data,
                )
            )

        return review_queue

    def apply_decisions(
        self, ctx: ApplicationContext, topic_id: str, decisions: List[AssetDecision]
    ) -> ReviewResult:
        """Updates asset review statuses and recompiles the overall topic manifest."""
        manifest_path = ctx.storage.manifests_dir / f"{topic_id}.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest found for topic '{topic_id}'")

        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        approved = 0
        rejected = 0

        for decision in decisions:
            success = ctx.storage.update_asset_status(
                decision.asset_type, topic_id, decision.status
            )
            if success:
                if decision.status == ReviewStatus.APPROVED:
                    approved += 1
                elif decision.status == ReviewStatus.REJECTED:
                    rejected += 1

        scored_item = ctx.storage.get_scored(topic_id)
        topic_title = (
            scored_item.title
            if scored_item
            else manifest_data.get("topic_title", "Unknown")
        )
        source_url = manifest_data.get("source_url", "")

        builder = ManifestBuilder(ctx.storage)
        new_manifest = builder.build(
            topic_id=topic_id,
            topic_title=topic_title,
            source_url=source_url,
        )
        ctx.storage.save_manifest(new_manifest)

        return ReviewResult(
            approved_count=approved,
            rejected_count=rejected,
            manifest=new_manifest,
        )
