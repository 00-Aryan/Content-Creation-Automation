"""Tests for analytics models and storage."""

import json
import tempfile
from pathlib import Path

import pytest

from content_creation.models.analytics import PostAnalytics, PerformanceSnapshot
from content_creation.storage.local import LocalStorage


class TestPostAnalyticsModel:
    """Test PostAnalytics model validates with all None performance fields."""

    def test_postanalytics_validates_with_none_performance(self):
        """Test PostAnalytics accepts model with all None performance fields."""
        analytics = PostAnalytics(
            post_id="topic-1_short_video_2026-05-18",
            topic_id="topic-1",
            topic_title="Test Topic",
            format="short_video",
            asset_path="data/scripts/topic-1.json",
            source_url="https://example.com",
            posted_at=None,
            week_start="2026-05-18",
            performance=PerformanceSnapshot(),
            last_updated="2026-05-16T12:00:00Z",
            notes=None,
        )

        assert analytics.post_id == "topic-1_short_video_2026-05-18"
        assert analytics.performance.views_24h is None
        assert analytics.performance.views_7d is None


class TestPostAnalyticsPostId:
    """Test PostAnalytics post_id format is correct."""

    def test_post_id_format(self):
        """Test post_id follows {topic_id}_{format}_{week_start} format."""
        analytics = PostAnalytics(
            post_id="my-topic_carousel_2026-05-25",
            topic_id="my-topic",
            topic_title="My Topic",
            format="carousel",
            asset_path="data/carousels/my-topic.json",
            source_url="https://example.com",
            week_start="2026-05-25",
            last_updated="2026-05-16T12:00:00Z",
        )

        assert "my-topic" in analytics.post_id
        assert "carousel" in analytics.post_id
        assert "2026-05-25" in analytics.post_id


class TestPerformanceSnapshotDefaults:
    """Test PerformanceSnapshot defaults all fields to None."""

    def test_performance_snapshot_defaults(self):
        """Test PerformanceSnapshot has all fields default to None."""
        perf = PerformanceSnapshot()

        assert perf.views_24h is None
        assert perf.views_7d is None
        assert perf.views_30d is None
        assert perf.reach_24h is None
        assert perf.reach_7d is None
        assert perf.saves is None
        assert perf.comments is None
        assert perf.cta_clicks is None
        assert perf.watch_time_pct is None


class TestWatchTimePct:
    """Test watch_time_pct accepts 0.0 and 100.0 as valid."""

    def test_watch_time_pct_accepts_0_and_100(self):
        """Test watch_time_pct accepts 0.0 and 100.0 as valid values."""
        perf = PerformanceSnapshot(watch_time_pct=0.0)
        assert perf.watch_time_pct == 0.0

        perf = PerformanceSnapshot(watch_time_pct=100.0)
        assert perf.watch_time_pct == 100.0

        perf = PerformanceSnapshot(watch_time_pct=50.5)
        assert perf.watch_time_pct == 50.5


class TestSaveAnalytics:
    """Test save_analytics saves to correct path."""

    def test_save_analytics_to_correct_path(self):
        """Test save_analytics saves to data/analytics/{post_id}.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            analytics = PostAnalytics(
                post_id="topic-1_short_video_2026-05-18",
                topic_id="topic-1",
                topic_title="Test Topic",
                format="short_video",
                asset_path="data/scripts/topic-1.json",
                source_url="https://example.com",
                week_start="2026-05-18",
                last_updated="2026-05-16T12:00:00Z",
            )

            path = storage.save_analytics(analytics)

            assert path.name == "topic-1_short_video_2026-05-18.json"
            assert path.parent.name == "analytics"
            assert path.exists()


class TestGetAnalyticsMissing:
    """Test get_analytics returns None for missing post_id."""

    def test_get_analytics_returns_none_for_missing(self):
        """Test get_analytics returns None when post_id doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            result = storage.get_analytics("nonexistent-id")

            assert result is None


class TestGetAnalyticsExists:
    """Test get_analytics returns correct record when exists."""

    def test_get_analytics_returns_correct_record(self):
        """Test get_analytics returns the saved analytics record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            analytics = PostAnalytics(
                post_id="topic-1_short_video_2026-05-18",
                topic_id="topic-1",
                topic_title="Test Topic",
                format="short_video",
                asset_path="data/scripts/topic-1.json",
                source_url="https://example.com",
                week_start="2026-05-18",
                last_updated="2026-05-16T12:00:00Z",
            )

            storage.save_analytics(analytics)

            result = storage.get_analytics("topic-1_short_video_2026-05-18")

            assert result is not None
            assert result.post_id == "topic-1_short_video_2026-05-18"
            assert result.topic_title == "Test Topic"


class TestListAnalytics:
    """Test list_analytics returns all saved records."""

    def test_list_analytics_returns_all(self):
        """Test list_analytics returns all saved analytics records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            analytics1 = PostAnalytics(
                post_id="topic-1_short_video_2026-05-18",
                topic_id="topic-1",
                topic_title="Topic 1",
                format="short_video",
                asset_path="data/scripts/topic-1.json",
                source_url="https://example.com/1",
                week_start="2026-05-18",
                last_updated="2026-05-16T12:00:00Z",
            )

            analytics2 = PostAnalytics(
                post_id="topic-2_carousel_2026-05-18",
                topic_id="topic-2",
                topic_title="Topic 2",
                format="carousel",
                asset_path="data/carousels/topic-2.json",
                source_url="https://example.com/2",
                week_start="2026-05-18",
                last_updated="2026-05-16T12:00:00Z",
            )

            storage.save_analytics(analytics1)
            storage.save_analytics(analytics2)

            results = storage.list_analytics()

            assert len(results) == 2
            post_ids = {r.post_id for r in results}
            assert "topic-1_short_video_2026-05-18" in post_ids
            assert "topic-2_carousel_2026-05-18" in post_ids


class TestInitAnalyticsSkipsExisting:
    """Test init-analytics skips existing records correctly."""

    def test_skip_existing_records(self):
        """Test that existing analytics records are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            # Create existing analytics
            existing = PostAnalytics(
                post_id="topic-1_short_video_2026-05-18",
                topic_id="topic-1",
                topic_title="Existing Topic",
                format="short_video",
                asset_path="data/scripts/topic-1.json",
                source_url="https://example.com",
                week_start="2026-05-18",
                last_updated="2026-05-16T12:00:00Z",
            )
            storage.save_analytics(existing)

            # Check that get_analytics returns existing
            result = storage.get_analytics("topic-1_short_video_2026-05-18")
            assert result is not None
            assert result.topic_title == "Existing Topic"


class TestPostAnalyticsLastUpdated:
    """Test PostAnalytics last_updated changes on update."""

    def test_last_updated_changes_on_update(self):
        """Test that last_updated can be changed when updating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            original_time = "2026-05-16T12:00:00Z"
            new_time = "2026-05-17T14:30:00Z"

            analytics = PostAnalytics(
                post_id="topic-1_short_video_2026-05-18",
                topic_id="topic-1",
                topic_title="Test Topic",
                format="short_video",
                asset_path="data/scripts/topic-1.json",
                source_url="https://example.com",
                week_start="2026-05-18",
                last_updated=original_time,
            )
            storage.save_analytics(analytics)

            # Retrieve and update
            updated = storage.get_analytics("topic-1_short_video_2026-05-18")
            assert updated is not None
            assert updated.last_updated == original_time

            updated.last_updated = new_time
            storage.save_analytics(updated)

            # Verify update
            final = storage.get_analytics("topic-1_short_video_2026-05-18")
            assert final is not None
            assert final.last_updated == new_time