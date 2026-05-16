"""Tests for posting planner and calendar models."""

import json
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from content_creation.models.calendar import ScheduledPost, WeeklyCalendar
from content_creation.models.manifest import TopicManifest, AssetEntry
from content_creation.planning.planner import PostingPlanner
from content_creation.storage.local import LocalStorage


class TestWeeklyCalendarModel:
    """Test WeeklyCalendar model validates correctly."""

    def test_weekly_calendar_validates_correctly(self):
        """Test WeeklyCalendar accepts valid data."""
        calendar = WeeklyCalendar(
            week_start="2026-05-18",
            week_end="2026-05-24",
            posts=[
                ScheduledPost(
                    day=1,
                    date="2026-05-18",
                    topic_id="topic-1",
                    topic_title="Test Topic",
                    format="short_video",
                    asset_path="data/scripts/topic-1.json",
                    source_url="https://example.com",
                    scheduled_at="2026-05-16T12:00:00Z"
                )
            ],
            total_posts=1,
            format_counts={"short_video": 1},
            topics_used=["topic-1"],
            generated_at="2026-05-16T12:00:00Z",
            config_snapshot={"weekly_targets": {"short_video": 3}}
        )

        assert calendar.week_start == "2026-05-18"
        assert calendar.total_posts == 1
        assert "short_video" in calendar.format_counts


class TestScheduledPostModel:
    """Test ScheduledPost model validates correctly."""

    def test_scheduled_post_validates_all_formats(self):
        """Test ScheduledPost accepts all valid format values."""
        formats = ["short_video", "carousel", "newsletter", "thumbnail"]

        for fmt in formats:
            post = ScheduledPost(
                day=1,
                date="2026-05-18",
                topic_id="topic-1",
                topic_title="Test",
                format=fmt,
                asset_path=f"data/{fmt}s/topic-1.json",
                source_url="https://example.com",
                scheduled_at="2026-05-16T12:00:00Z"
            )
            assert post.format == fmt


class TestPlanWeekEmptyCalendar:
    """Test plan_week() returns empty calendar when no approved manifests exist."""

    def test_plan_week_returns_empty_when_no_manifests(self):
        """Test plan_week returns empty calendar when no manifests exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""
weekly_targets:
  short_video: 3
  carousel: 2

scheduling_rules:
  max_same_topic_per_week: 2
  min_days_between_same_topic: 2

diversity_rules:
  never_same_format_consecutive_days: true
  never_same_topic_consecutive_days: true
""")

            planner = PostingPlanner(storage, config_path)
            calendar = planner.plan_week(date(2026, 5, 18))

            assert calendar.total_posts == 0
            assert calendar.posts == []
            assert calendar.format_counts == {}


class TestPlanWeekNoConsecutiveTopics:
    """Test plan_week() never schedules same topic on consecutive days."""

    def test_no_consecutive_same_topic(self):
        """Test same topic is never scheduled on consecutive days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""
weekly_targets:
  short_video: 3

scheduling_rules:
  max_same_topic_per_week: 2
  min_days_between_same_topic: 2
  prioritize_freshness: true

diversity_rules:
  never_same_format_consecutive_days: false
  never_same_topic_consecutive_days: true
""")

            # Create manifests with same topic appearing in multiple approved assets
            manifest_data = {
                "topic_id": "topic-1",
                "topic_title": "Test Topic",
                "source_url": "https://example.com",
                "assets": {
                    "brief": {"path": "data/briefs/topic-1.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                    "script": {"path": "data/scripts/topic-1.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                    "thumbnail": {"path": "data/thumbnails/topic-1.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                },
                "overall_status": "complete",
                "blocking_reasons": [],
                "ready_for_planner": True,
                "generated_at": "2026-05-16T00:00:00Z"
            }

            # Create manifest files
            storage.manifests_dir.mkdir(parents=True, exist_ok=True)
            (storage.manifests_dir / "topic-1.json").write_text(json.dumps(manifest_data))

            # Create asset files
            (storage.scripts_dir / "topic-1.json").write_text(json.dumps({
                "topic_id": "topic-1",
                "hook": "Test",
                "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }))

            planner = PostingPlanner(storage, config_path)
            calendar = planner.plan_week(date(2026, 5, 18))

            days_with_topic = [p.day for p in calendar.posts if p.topic_id == "topic-1"]
            for i in range(len(days_with_topic) - 1):
                assert days_with_topic[i + 1] - days_with_topic[i] > 1


class TestPlanWeekNoConsecutiveFormats:
    """Test plan_week() never schedules same format on consecutive days."""

    def test_no_consecutive_same_format(self):
        """Test same format is never scheduled on consecutive days when rule is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""
weekly_targets:
  short_video: 3
  carousel: 2

scheduling_rules:
  max_same_topic_per_week: 2
  min_days_between_same_topic: 2

diversity_rules:
  never_same_format_consecutive_days: true
  never_same_topic_consecutive_days: false
""")

            # Create multiple topics with approved scripts
            for i in range(5):
                manifest_data = {
                    "topic_id": f"topic-{i}",
                    "topic_title": f"Topic {i}",
                    "source_url": f"https://example.com/{i}",
                    "assets": {
                        "brief": {"path": f"data/briefs/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                        "script": {"path": f"data/scripts/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                        "thumbnail": {"path": f"data/thumbnails/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                    },
                    "overall_status": "complete",
                    "blocking_reasons": [],
                    "ready_for_planner": True,
                    "generated_at": "2026-05-16T00:00:00Z"
                }
                (storage.manifests_dir / f"topic-{i}.json").write_text(json.dumps(manifest_data))
                (storage.scripts_dir / f"topic-{i}.json").write_text(json.dumps({
                    "topic_id": f"topic-{i}",
                    "hook": f"Test {i}",
                    "review_status": "approved",
                    "generated_at": "2026-05-16T00:00:00Z"
                }))

            planner = PostingPlanner(storage, config_path)
            calendar = planner.plan_week(date(2026, 5, 18))

            sorted_posts = sorted(calendar.posts, key=lambda p: p.day)
            for i in range(len(sorted_posts) - 1):
                if sorted_posts[i].day + 1 == sorted_posts[i + 1].day:
                    assert sorted_posts[i].format != sorted_posts[i + 1].format


class TestPlanWeekMaxTopicPerWeek:
    """Test plan_week() respects max_same_topic_per_week=2."""

    def test_respects_max_topic_per_week(self):
        """Test max_same_topic_per_week=2 is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""
weekly_targets:
  short_video: 3

scheduling_rules:
  max_same_topic_per_week: 2
  min_days_between_same_topic: 0

diversity_rules:
  never_same_format_consecutive_days: false
  never_same_topic_consecutive_days: false
""")

            # Create manifest with 3 approved assets for same topic
            manifest_data = {
                "topic_id": "topic-1",
                "topic_title": "Test Topic",
                "source_url": "https://example.com",
                "assets": {
                    "brief": {"path": "data/briefs/topic-1.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                    "script": {"path": "data/scripts/topic-1.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                    "thumbnail": {"path": "data/thumbnails/topic-1.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                },
                "overall_status": "complete",
                "blocking_reasons": [],
                "ready_for_planner": True,
                "generated_at": "2026-05-16T00:00:00Z"
            }

            storage.manifests_dir.mkdir(parents=True, exist_ok=True)
            (storage.manifests_dir / "topic-1.json").write_text(json.dumps(manifest_data))
            (storage.scripts_dir / "topic-1.json").write_text(json.dumps({
                "topic_id": "topic-1",
                "hook": "Test",
                "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }))

            planner = PostingPlanner(storage, config_path)
            calendar = planner.plan_week(date(2026, 5, 18))

            topic_appearances = sum(1 for p in calendar.posts if p.topic_id == "topic-1")
            assert topic_appearances <= 2


class TestPlanWeekSortsByFreshness:
    """Test plan_week() sorts topics by freshness (newer brief scheduled first)."""

    def test_newer_topics_scheduled_first(self):
        """Test topics with newer generated_at are prioritized when prioritize_freshness is true."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""
weekly_targets:
  short_video: 3

scheduling_rules:
  max_same_topic_per_week: 1
  min_days_between_same_topic: 1
  prioritize_freshness: true

diversity_rules:
  never_same_format_consecutive_days: false
  never_same_topic_consecutive_days: false
""")

            # Create two topics with different generated_at timestamps
            older_manifest = {
                "topic_id": "topic-old",
                "topic_title": "Older Topic",
                "source_url": "https://example.com/old",
                "assets": {
                    "brief": {"path": "data/briefs/topic-old.json", "status": "approved", "generated_at": "2026-05-10T00:00:00Z"},
                    "script": {"path": "data/scripts/topic-old.json", "status": "approved", "generated_at": "2026-05-10T00:00:00Z"},
                },
                "overall_status": "complete",
                "blocking_reasons": [],
                "ready_for_planner": True,
                "generated_at": "2026-05-10T00:00:00Z"
            }

            newer_manifest = {
                "topic_id": "topic-new",
                "topic_title": "Newer Topic",
                "source_url": "https://example.com/new",
                "assets": {
                    "brief": {"path": "data/briefs/topic-new.json", "status": "approved", "generated_at": "2026-05-15T00:00:00Z"},
                    "script": {"path": "data/scripts/topic-new.json", "status": "approved", "generated_at": "2026-05-15T00:00:00Z"},
                },
                "overall_status": "complete",
                "blocking_reasons": [],
                "ready_for_planner": True,
                "generated_at": "2026-05-15T00:00:00Z"
            }

            storage.manifests_dir.mkdir(parents=True, exist_ok=True)
            (storage.manifests_dir / "topic-old.json").write_text(json.dumps(older_manifest))
            (storage.manifests_dir / "topic-new.json").write_text(json.dumps(newer_manifest))

            (storage.scripts_dir / "topic-old.json").write_text(json.dumps({
                "topic_id": "topic-old", "hook": "Old", "review_status": "approved", "generated_at": "2026-05-10T00:00:00Z"
            }))
            (storage.scripts_dir / "topic-new.json").write_text(json.dumps({
                "topic_id": "topic-new", "hook": "New", "review_status": "approved", "generated_at": "2026-05-15T00:00:00Z"
            }))

            planner = PostingPlanner(storage, config_path)
            calendar = planner.plan_week(date(2026, 5, 18))

            if calendar.posts:
                first_post = sorted(calendar.posts, key=lambda p: p.day)[0]
                assert first_post.topic_id == "topic-new"


class TestPlanWeekRespectsWeeklyTargets:
    """Test plan_week() respects weekly_targets counts."""

    def test_respects_weekly_targets(self):
        """Test weekly_targets counts are respected when enough topics are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""
weekly_targets:
  short_video: 2
  carousel: 1

scheduling_rules:
  max_same_topic_per_week: 1
  min_days_between_same_topic: 1

diversity_rules:
  never_same_format_consecutive_days: true
  never_same_topic_consecutive_days: true
""")

            # Create 3 topics with both script and carousel approved
            for i in range(3):
                manifest = {
                    "topic_id": f"topic-{i}",
                    "topic_title": f"Topic {i}",
                    "source_url": f"https://example.com/{i}",
                    "assets": {
                        "brief": {"path": f"data/briefs/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                        "script": {"path": f"data/scripts/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                        "carousel": {"path": f"data/carousels/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                        "thumbnail": {"path": f"data/thumbnails/topic-{i}.json", "status": "approved", "generated_at": "2026-05-16T00:00:00Z"},
                    },
                    "overall_status": "complete",
                    "blocking_reasons": [],
                    "ready_for_planner": True,
                    "generated_at": "2026-05-16T00:00:00Z"
                }
                (storage.manifests_dir / f"topic-{i}.json").write_text(json.dumps(manifest))
                (storage.scripts_dir / f"topic-{i}.json").write_text(json.dumps({
                    "topic_id": f"topic-{i}", "hook": f"Hook {i}", "review_status": "approved", "generated_at": "2026-05-16T00:00:00Z"
                }))
                (storage.carousels_dir / f"topic-{i}.json").write_text(json.dumps({
                    "topic_id": f"topic-{i}", "slides": [{"title": "Slide", "content": "Content"}], "review_status": "approved", "generated_at": "2026-05-16T00:00:00Z"
                }))

            planner = PostingPlanner(storage, config_path)
            calendar = planner.plan_week(date(2026, 5, 18))

            assert calendar.format_counts.get("short_video", 0) <= 2
            assert calendar.format_counts.get("carousel", 0) <= 1


class TestSaveCalendar:
    """Test save_calendar() saves to correct path."""

    def test_save_calendar_to_correct_path(self):
        """Test save_calendar saves to data/calendars/{week_start}.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            calendar = WeeklyCalendar(
                week_start="2026-05-18",
                week_end="2026-05-24",
                posts=[],
                total_posts=0,
                format_counts={},
                topics_used=[],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={}
            )

            path = storage.save_calendar(calendar)

            assert path.name == "2026-05-18.json"
            assert path.parent.name == "calendars"
            assert path.exists()


class TestListCalendars:
    """Test list_calendars() loads all saved calendars."""

    def test_list_calendars_loads_all(self):
        """Test list_calendars returns all saved calendars."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            calendar1 = WeeklyCalendar(
                week_start="2026-05-18",
                week_end="2026-05-24",
                posts=[],
                total_posts=0,
                format_counts={},
                topics_used=[],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={}
            )

            calendar2 = WeeklyCalendar(
                week_start="2026-05-25",
                week_end="2026-05-31",
                posts=[],
                total_posts=0,
                format_counts={},
                topics_used=[],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={}
            )

            storage.save_calendar(calendar1)
            storage.save_calendar(calendar2)

            calendars = storage.list_calendars()

            assert len(calendars) == 2
            week_starts = {c.week_start for c in calendars}
            assert week_starts == {"2026-05-18", "2026-05-25"}