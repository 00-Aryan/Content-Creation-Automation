"""Local file system storage for raw and staged data."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from content_creation.models.brief import Brief
from content_creation.models.script import Script
from content_creation.models.carousel import Carousel
from content_creation.models.newsletter import Newsletter
from content_creation.models.thumbnail import ThumbnailPrompt
from content_creation.models.manifest import TopicManifest
from content_creation.models.calendar import WeeklyCalendar
from content_creation.models.dryrun import DryRunReport
from content_creation.models.analytics import PostAnalytics
from content_creation.models.topic import ScoredTopicItem, TopicItem
from content_creation.platform.storage.local_backend import LocalBackend
from content_creation.domains.brief.repository import BriefRepository
from content_creation.domains.script.repository import ScriptRepository
from content_creation.domains.carousel.repository import CarouselRepository
from content_creation.domains.newsletter.repository import NewsletterRepository
from content_creation.domains.thumbnail.repository import ThumbnailRepository
from content_creation.domains.content_intelligence import ContentIntelligence, ContentIntelligenceRepository
from content_creation.domains.storyboard import Storyboard, StoryboardRepository

logger = logging.getLogger(__name__)


class LocalStorage:
    """Handles persistence of raw and staged data to the local file system."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.raw_dir = base_dir / "data" / "raw"
        self.staged_dir = base_dir / "data" / "staged"
        self.scored_dir = base_dir / "data" / "scored"
        self.briefs_dir = base_dir / "data" / "briefs"
        self.scripts_dir = base_dir / "data" / "scripts"
        self.carousels_dir = base_dir / "data" / "carousels"
        self.newsletters_dir = base_dir / "data" / "newsletters"
        self.thumbnails_dir = base_dir / "data" / "thumbnails"
        self.manifests_dir = base_dir / "data" / "manifests"
        self.calendars_dir = base_dir / "data" / "calendars"
        self.dryruns_dir = base_dir / "data" / "dryruns"
        self.analytics_dir = base_dir / "data" / "analytics"
        self.content_intelligence_dir = base_dir / "data" / "content_intelligence"
        self.storyboards_dir = base_dir / "data" / "storyboards"
        self.logs_dir = base_dir / "data" / "logs"

        self._backend = LocalBackend(
            base_dir=base_dir,
            directories=[
                self.raw_dir, self.staged_dir, self.scored_dir,
                self.briefs_dir, self.scripts_dir, self.carousels_dir,
                self.newsletters_dir, self.thumbnails_dir, self.manifests_dir,
                self.calendars_dir, self.dryruns_dir, self.analytics_dir,
                self.content_intelligence_dir, self.storyboards_dir,
                self.logs_dir,
            ],
        )

        self._brief_repo = BriefRepository(directory=self.briefs_dir)
        self._script_repo = ScriptRepository(directory=self.scripts_dir)
        self._carousel_repo = CarouselRepository(directory=self.carousels_dir)
        self._newsletter_repo = NewsletterRepository(directory=self.newsletters_dir)
        self._thumbnail_repo = ThumbnailRepository(directory=self.thumbnails_dir)
        self._content_intelligence_repo = ContentIntelligenceRepository(directory=self.content_intelligence_dir)
        self._storyboard_repo = StoryboardRepository(directory=self.storyboards_dir)

    def save_raw(self, source_id: str, data: Any):
        """Save raw payload to data/raw/."""
        self._backend.save_raw(self.raw_dir, source_id, data)

    def exists(self, item_id: str) -> bool:
        """Check if an item already exists in staged storage."""
        return self._backend.exists(self.staged_dir, item_id)

    def scored_exists(self, item_id: str) -> bool:
        """Check if a scored item already exists in scored storage."""
        return self._backend.exists(self.scored_dir, item_id)

    def save_staged(self, item: TopicItem):
        """Save a normalized TopicItem to data/staged/.
        
        Uses mode 'x' for atomic creation to prevent race conditions during concurrent ingestion.
        Note: Atomic deduplication is guaranteed for writes on the same local filesystem target;
        other storage backends may require a different locking strategy.
        """
        file_path = self.staged_dir / f"{item.id}.json"
        try:
            with open(file_path, "x") as f:
                f.write(item.model_dump_json(indent=2))
        except FileExistsError:
            # Re-raise so ingestion engine can handle it as a duplicate
            raise
        except Exception as e:
            logger.error(f"Failed to save staged item to {file_path}: {e}")

    def save_scored(self, item: ScoredTopicItem):
        """Save a scored TopicItem to data/scored/."""
        file_path = self.scored_dir / f"{item.id}.json"
        try:
            with open(file_path, "w") as f:
                f.write(item.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save scored item to {file_path}: {e}")

    def save_brief(self, brief: Brief) -> Path:
        """Save brief JSON to data/briefs/{topic_id}.json"""
        return self._brief_repo.save(brief)

    def list_staged(self) -> List[TopicItem]:
        """List all staged items."""
        items = []
        for file_path in self.staged_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(TopicItem(**data))
            except Exception as e:
                logger.warning(f"Failed to load staged item {file_path}: {e}")
        return items

    def list_scored(self) -> List[ScoredTopicItem]:
        """List all scored items."""
        items = []
        for file_path in self.scored_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(ScoredTopicItem(**data))
            except Exception as e:
                logger.warning(f"Failed to load scored item {file_path}: {e}")
        return items

    def list_briefs(self) -> List[Brief]:
        """Load all briefs from data/briefs/"""
        return self._brief_repo.list_all()

    def get_brief(self, topic_id: str) -> Optional[Brief]:
        """Get a specific brief by topic ID."""
        return self._brief_repo.get(topic_id)

    def save_content_intelligence(self, ci: ContentIntelligence) -> Path:
        """Save content intelligence JSON to data/content_intelligence/{topic_id}.json"""
        return self._content_intelligence_repo.save(ci)

    def list_content_intelligence(self) -> List[ContentIntelligence]:
        """Load all content intelligence artifacts from data/content_intelligence/"""
        return self._content_intelligence_repo.list_all()

    def save_storyboard(self, storyboard: Storyboard) -> Path:
        """Save storyboard JSON to data/storyboards/{topic_id}.json"""
        return self._storyboard_repo.save(storyboard)

    def get_storyboard(self, topic_id: str) -> Optional[Storyboard]:
        """Get a specific storyboard by topic ID."""
        return self._storyboard_repo.get(topic_id)

    def list_storyboards(self) -> List[Storyboard]:
        """Load all storyboards from data/storyboards/"""
        return self._storyboard_repo.list_all()

    def save_script(self, script: Script) -> Path:
        """Save script JSON to data/scripts/{topic_id}.json"""
        return self._script_repo.save(script)

    def list_scripts(self) -> List[Script]:
        """Load all scripts from data/scripts/"""
        return self._script_repo.list_all()

    def save_carousel(self, carousel: Carousel) -> Path:
        """Save carousel JSON to data/carousels/{topic_id}.json"""
        return self._carousel_repo.save(carousel)

    def list_carousels(self) -> List[Carousel]:
        """Load all carousels from data/carousels/"""
        return self._carousel_repo.list_all()

    def save_newsletter(self, newsletter: Newsletter) -> Path:
        """Save newsletter JSON to data/newsletters/{topic_id}.json"""
        return self._newsletter_repo.save(newsletter)

    def list_newsletters(self) -> List[Newsletter]:
        """Load all newsletters from data/newsletters/"""
        return self._newsletter_repo.list_all()

    def save_thumbnail(self, thumbnail: ThumbnailPrompt) -> Path:
        """Save thumbnail JSON to data/thumbnails/{topic_id}.json"""
        return self._thumbnail_repo.save(thumbnail)

    def list_thumbnails(self) -> List[ThumbnailPrompt]:
        """Load all thumbnails from data/thumbnails/"""
        return self._thumbnail_repo.list_all()

    def save_manifest(self, manifest: TopicManifest) -> Path:
        """Save manifest JSON to data/manifests/{topic_id}.json"""
        file_path = self.manifests_dir / f"{manifest.topic_id}.json"
        try:
            with open(file_path, "w") as f:
                f.write(manifest.model_dump_json(indent=2))
            return file_path
        except Exception as e:
            logger.error(f"Failed to save manifest to {file_path}: {e}")
            raise

    def list_manifests(self) -> List[TopicManifest]:
        """Load all manifests from data/manifests/"""
        items = []
        for file_path in self.manifests_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(TopicManifest(**data))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning("Failed to load manifest %s: %s", file_path.name, e)
        return items

    def save_calendar(self, calendar: WeeklyCalendar) -> Path:
        """Save calendar JSON to data/calendars/{week_start}.json"""
        file_path = self.calendars_dir / f"{calendar.week_start}.json"
        try:
            with open(file_path, "w") as f:
                f.write(calendar.model_dump_json(indent=2))
            return file_path
        except Exception as e:
            logger.error(f"Failed to save calendar to {file_path}: {e}")
            raise

    def list_calendars(self) -> List[WeeklyCalendar]:
        """Load all calendars from data/calendars/"""
        items = []
        for file_path in self.calendars_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(WeeklyCalendar(**data))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning("Failed to load calendar %s: %s", file_path.name, e)
        return items

    def save_dryrun(self, report: DryRunReport) -> Path:
        """Save dryrun JSON to data/dryruns/{week_start}.json"""
        file_path = self.dryruns_dir / f"{report.week_start}.json"
        try:
            with open(file_path, "w") as f:
                f.write(report.model_dump_json(indent=2))
            return file_path
        except Exception as e:
            logger.error(f"Failed to save dryrun to {file_path}: {e}")
            raise

    def list_dryruns(self) -> List[DryRunReport]:
        """Load all dryruns from data/dryruns/"""
        items = []
        for file_path in self.dryruns_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(DryRunReport(**data))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning("Failed to load dryrun %s: %s", file_path.name, e)
        return items

    def save_analytics(self, analytics: PostAnalytics) -> Path:
        """Save analytics JSON to data/analytics/{post_id}.json"""
        file_path = self.analytics_dir / f"{analytics.post_id}.json"
        try:
            with open(file_path, "w") as f:
                f.write(analytics.model_dump_json(indent=2))
            return file_path
        except Exception as e:
            logger.error(f"Failed to save analytics to {file_path}: {e}")
            raise

    def list_analytics(self) -> List[PostAnalytics]:
        """Load all analytics from data/analytics/"""
        items = []
        for file_path in self.analytics_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    items.append(PostAnalytics(**data))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning("Failed to load analytics %s: %s", file_path.name, e)
        return items

    def get_analytics(self, post_id: str) -> Optional[PostAnalytics]:
        """Get a specific analytics record by post_id."""
        file_path = self.analytics_dir / f"{post_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return PostAnalytics(**data)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error("Failed to load analytics %s: %s", post_id, e)
            return None

    def get_staged(self, item_id: str) -> Optional[TopicItem]:
        """Get a specific staged item by ID."""
        file_path = self.staged_dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return TopicItem(**data)
        except Exception as e:
            logger.error(f"Failed to load staged item {file_path}: {e}")
            return None

    def get_scored(self, item_id: str) -> Optional[ScoredTopicItem]:
        """Get a specific scored item by ID."""
        file_path = self.scored_dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return ScoredTopicItem(**data)
        except Exception as e:
            logger.error(f"Failed to load scored item {file_path}: {e}")
            return None

    def update_asset_status(
        self,
        asset_type: str,
        topic_id: str,
        new_status: "ReviewStatus"
    ) -> bool:
        """Update review_status for an asset.

        Args:
            asset_type: One of brief, script, carousel, newsletter, thumbnail
            topic_id: The topic identifier
            new_status: The new ReviewStatus to set

        Returns:
            True on success, False if file not found

        Raises:
            ValueError: If asset_type is not recognized
        """
        from content_creation.shared.enums import ReviewStatus

        asset_dirs = {
            "brief": self.briefs_dir,
            "script": self.scripts_dir,
            "carousel": self.carousels_dir,
            "newsletter": self.newsletters_dir,
            "thumbnail": self.thumbnails_dir,
        }

        if asset_type not in asset_dirs:
            raise ValueError(f"Unknown asset_type: {asset_type}. Must be one of: {list(asset_dirs.keys())}")

        file_path = asset_dirs[asset_type] / f"{topic_id}.json"

        if not file_path.exists():
            logger.warning(f"Asset file not found: {file_path}")
            return False

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            data["review_status"] = new_status.value

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Updated {asset_type} {topic_id} status to {new_status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update asset status for {file_path}: {e}")
            return False
