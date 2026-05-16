import json
import logging
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from content_creation.models.calendar import ScheduledPost, WeeklyCalendar
from content_creation.models.manifest import TopicManifest
from content_creation.storage.local import LocalStorage
from content_creation.utils.config import load_yaml_config

logger = logging.getLogger(__name__)

FORMAT_TO_DIR: Dict[str, str] = {
    "short_video": "data/scripts",
    "carousel": "data/carousels",
    "newsletter": "data/newsletters",
    "thumbnail": "data/thumbnails",
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class PostingPlanner:
    def __init__(
        self,
        storage: LocalStorage,
        config_path: Path
    ):
        self.storage = storage
        config = load_yaml_config(config_path)

        self.weekly_targets: Dict[str, int] = config.get("weekly_targets", {})
        self.scheduling_rules: Dict = config.get("scheduling_rules", {})
        self.diversity_rules: Dict = config.get("diversity_rules", {})

        self.config_snapshot = deepcopy(config)

        logger.info(
            "PostingPlanner initialized with targets: %s",
            self.weekly_targets
        )

    def plan_week(self, week_start: date) -> WeeklyCalendar:
        manifests = self.storage.list_manifests()
        approved_manifests = [
            m for m in manifests
            if m.ready_for_planner
        ]

        if not approved_manifests:
            logger.warning("No approved manifests found for planning")
            week_end = week_start + timedelta(days=6)
            return WeeklyCalendar(
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat(),
                posts=[],
                total_posts=0,
                format_counts={},
                topics_used=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
                config_snapshot=self.config_snapshot,
            )

        approved_manifests.sort(
            key=lambda m: m.generated_at,
            reverse=True
        )

        posts: List[ScheduledPost] = []
        topic_appearances: Dict[str, int] = {}
        last_topic_day: Dict[str, int] = {}
        last_format_day: Dict[str, int] = {}
        used_topics_for_format: Dict[str, List[str]] = {}

        max_same_topic = self.scheduling_rules.get("max_same_topic_per_week", 2)
        min_days_gap = self.scheduling_rules.get("min_days_between_same_topic", 2)

        scheduled_count = 0

        for format_name, target_count in self.weekly_targets.items():
            if scheduled_count >= 7:
                break

            if format_name not in used_topics_for_format:
                used_topics_for_format[format_name] = []

            for _ in range(target_count):
                if scheduled_count >= 7:
                    break

                best_topic = None
                best_day = None

                for day_offset in range(7):
                    day_num = day_offset + 1
                    day_date = week_start + timedelta(days=day_offset)

                    for manifest in approved_manifests:
                        topic_id = manifest.topic_id

                        if topic_appearances.get(topic_id, 0) >= max_same_topic:
                            continue

                        if topic_id in used_topics_for_format[format_name]:
                            continue

                        if last_topic_day.get(topic_id, -100) >= day_num - min_days_gap:
                            continue

                        if format_name in last_format_day:
                            if last_format_day[format_name] == day_num - 1:
                                continue

                        asset_path = self._select_asset_path(topic_id, format_name)
                        if asset_path is None:
                            continue

                        best_topic = manifest
                        best_day = day_num
                        break

                    if best_topic is not None:
                        break

                if best_topic is not None and best_day is not None:
                    day_date = week_start + timedelta(days=best_day - 1)
                    asset_path = self._select_asset_path(best_topic.topic_id, format_name)

                    post = ScheduledPost(
                        day=best_day,
                        date=day_date.isoformat(),
                        topic_id=best_topic.topic_id,
                        topic_title=best_topic.topic_title,
                        format=format_name,
                        asset_path=asset_path,
                        source_url=best_topic.source_url,
                        scheduled_at=datetime.now(timezone.utc).isoformat(),
                    )
                    posts.append(post)

                    topic_appearances[best_topic.topic_id] = topic_appearances.get(best_topic.topic_id, 0) + 1
                    last_topic_day[best_topic.topic_id] = best_day
                    last_format_day[format_name] = best_day

                    used_topics_for_format[format_name].append(best_topic.topic_id)

                    scheduled_count += 1
                else:
                    logger.warning(
                        "Could not schedule %s for week of %s — no available topics that satisfy constraints",
                        format_name,
                        week_start
                    )

        posts.sort(key=lambda p: p.day)

        week_end = week_start + timedelta(days=6)
        format_counts: Dict[str, int] = {}
        topics_used: List[str] = []

        for post in posts:
            format_counts[post.format] = format_counts.get(post.format, 0) + 1
            if post.topic_id not in topics_used:
                topics_used.append(post.topic_id)

        logger.info(
            "Planned %d posts for week of %s",
            len(posts),
            week_start
        )

        return WeeklyCalendar(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            posts=posts,
            total_posts=len(posts),
            format_counts=format_counts,
            topics_used=topics_used,
            generated_at=datetime.now(timezone.utc).isoformat(),
            config_snapshot=self.config_snapshot,
        )

    def _select_asset_path(
        self,
        topic_id: str,
        format: str
    ) -> Optional[str]:
        dir_path = FORMAT_TO_DIR.get(format)
        if dir_path is None:
            return None

        asset_path = f"{dir_path}/{topic_id}.json"
        full_path = self.storage.base_dir / asset_path

        if full_path.exists():
            return asset_path

        return None