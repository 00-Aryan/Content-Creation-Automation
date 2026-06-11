import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from content_creation.models.manifest import TopicManifest, AssetEntry
from content_creation.storage.local import LocalStorage

logger = logging.getLogger(__name__)

FORMAT_TO_ASSET: Dict[str, str] = {
    "short_video": "script",
    "carousel": "carousel",
    "newsletter": "newsletter",
}

FREETEXT_TO_FORMAT: Dict[str, str] = {
    "lecture": "short_video",
    "video": "short_video",
    "short video": "short_video",
    "technical deep dive": "short_video",
    "case study": "carousel",
    "infographic": "carousel",
    "visual guide": "carousel",
    "email": "newsletter",
    "blog": "newsletter",
    "research project": "newsletter",
}

OPTIONAL_ASSET_TYPES = frozenset({"script", "carousel", "newsletter"})
ALWAYS_REQUIRED_ASSET_TYPES = frozenset({"brief", "thumbnail"})

ASSET_PATH_PREFIX: Dict[str, str] = {
    "brief": "data/briefs",
    "script": "data/scripts",
    "carousel": "data/carousels",
    "newsletter": "data/newsletters",
    "thumbnail": "data/thumbnails",
}


class ManifestBuilder:
    """Build topic manifests by checking asset file existence and review status."""

    def __init__(self, storage: LocalStorage):
        self.storage = storage

    def build(
        self, topic_id: str, topic_title: str, source_url: str
    ) -> TopicManifest:
        """Build a manifest for a single topic."""
        recommended_asset_types = self._recommended_asset_types(topic_id)
        assets: Dict[str, AssetEntry] = {}

        asset_dirs = {
            "brief": self.storage.briefs_dir,
            "script": self.storage.scripts_dir,
            "carousel": self.storage.carousels_dir,
            "newsletter": self.storage.newsletters_dir,
            "thumbnail": self.storage.thumbnails_dir,
        }

        for asset_type in ("brief", "script", "carousel", "newsletter", "thumbnail"):
            rel_path = f"{ASSET_PATH_PREFIX[asset_type]}/{topic_id}.json"
            asset_file = asset_dirs[asset_type] / f"{topic_id}.json"

            if asset_type in ALWAYS_REQUIRED_ASSET_TYPES:
                assets[asset_type] = self._check_asset(rel_path, asset_file)
            elif asset_type in recommended_asset_types:
                assets[asset_type] = self._check_asset(rel_path, asset_file)
            else:
                assets[asset_type] = AssetEntry(
                    path=rel_path,
                    status="skipped",
                    generated_at=None,
                )

        non_skipped_statuses = [
            asset.status for asset in assets.values() if asset.status != "skipped"
        ]

        if "missing" in non_skipped_statuses or "rejected" in non_skipped_statuses:
            overall_status = "blocked"
        elif all(s == "approved" for s in non_skipped_statuses):
            overall_status = "complete"
        else:
            overall_status = "partial"

        blocking_reasons = []
        for asset_type, asset in assets.items():
            if asset.status == "skipped":
                continue
            if asset.status != "approved":
                blocking_reasons.append(f"{asset_type}: {asset.status}")

        ready_for_planner = all(
            asset.status == "approved"
            for asset in assets.values()
            if asset.status != "skipped"
        )

        skipped_types = [
            asset_type
            for asset_type, asset in assets.items()
            if asset.status == "skipped"
        ]

        generated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Built manifest for %s: %s (skipped: %s)",
            topic_id,
            overall_status,
            skipped_types,
        )

        return TopicManifest(
            topic_id=topic_id,
            topic_title=topic_title,
            source_url=source_url,
            assets=assets,
            overall_status=overall_status,
            blocking_reasons=blocking_reasons,
            ready_for_planner=ready_for_planner,
            generated_at=generated_at,
        )

    def build_all(self) -> List[TopicManifest]:
        """Build manifests for all topics with briefs."""
        try:
            briefs = self.storage.list_briefs()
        except Exception as e:
            logger.warning(
                "No briefs found — manifest build_all() returning empty list: %s", e
            )
            return []

        if not briefs:
            logger.warning(
                "No briefs found — manifest build_all() returning empty list"
            )
            return []

        manifests = []

        for brief in briefs:
            try:
                scored_item = self.storage.get_scored(brief.topic_id)
                title = scored_item.title if scored_item else "Unknown Title"

                manifest = self.build(
                    topic_id=brief.topic_id,
                    topic_title=title,
                    source_url=brief.source_url,
                )
                manifests.append(manifest)
            except Exception as e:
                logger.warning(
                    "Skipping manifest for %s: %s", brief.topic_id, e
                )
                continue

        logger.info("Built %d manifests", len(manifests))
        return manifests

    def _recommended_asset_types(self, topic_id: str) -> Set[str]:
        """Map brief recommended_formats to asset types; all optional if no brief."""
        brief_file = self.storage.briefs_dir / f"{topic_id}.json"
        if not brief_file.exists():
            return set(OPTIONAL_ASSET_TYPES)

        data = self._load_json(brief_file)
        formats = data.get("recommended_formats", [])

        mapped_formats: Set[str] = set()
        for fmt in formats:
            if fmt in FORMAT_TO_ASSET:
                mapped_formats.add(fmt)
            else:
                mapped = FREETEXT_TO_FORMAT.get(fmt.lower())
                if mapped:
                    logger.info("Mapped format '%s' → '%s' for topic %s", fmt, mapped, topic_id)
                    mapped_formats.add(mapped)
                else:
                    logger.warning("Unknown format '%s' for topic %s, defaulting to short_video", fmt, topic_id)
                    mapped_formats.add("short_video")

        if not mapped_formats:
            mapped_formats = {"short_video"}

        return {
            FORMAT_TO_ASSET[fmt]
            for fmt in mapped_formats
            if fmt in FORMAT_TO_ASSET
        }

    def _check_asset(self, rel_path: str, asset_file: Path) -> AssetEntry:
        if asset_file.exists():
            data = self._load_json(asset_file)
            return AssetEntry(
                path=rel_path,
                status=data.get("review_status", "unknown"),
                generated_at=data.get("generated_at"),
            )
        return AssetEntry(
            path=rel_path,
            status="missing",
            generated_at=None,
        )

    def _load_json(self, file_path: Path) -> dict:
        """Load and parse a JSON file safely."""
        import json

        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load or parse JSON from %s: %s", file_path, e)
            return {}
