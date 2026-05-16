"""Tests for review and approval state machine."""

import json
import tempfile
from pathlib import Path

import pytest

from content_creation.models.brief import ReviewStatus
from content_creation.manifest import ManifestBuilder
from content_creation.storage.local import LocalStorage


class TestReviewStatusEnum:
    """Test that ReviewStatus enum has all 5 values."""

    def test_review_status_has_all_values(self):
        """Test ReviewStatus enum contains all expected values."""
        expected = {"draft", "needs_review", "reviewed", "approved", "rejected"}
        actual = {status.value for status in ReviewStatus}
        assert actual == expected

    def test_review_status_values_are_strings(self):
        """Test that ReviewStatus values are strings."""
        for status in ReviewStatus:
            assert isinstance(status.value, str)


class TestManifestBuilderComplete:
    """Test ManifestBuilder.build() returns 'complete' only when all non-skipped assets are 'approved'."""

    def test_complete_when_all_approved(self):
        """Test overall_status is 'complete' when all assets are approved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            # Create approved brief
            brief_data = {
                "topic_id": "test-topic",
                "why_it_matters": "Test",
                "plain_english_summary": ["a", "b", "c"],
                "student_takeaway": "test",
                "analogy": "test",
                "limitation": "test",
                "audience_fit": "test",
                "recommended_formats": ["carousel"],
                "source_url": "https://example.com",
                "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.briefs_dir / "test-topic.json").write_text(json.dumps(brief_data))

            # Create approved carousel
            carousel_data = {
                "topic_id": "test-topic",
                "slides": [{"title": "Test", "content": "Test"}],
                "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.carousels_dir / "test-topic.json").write_text(json.dumps(carousel_data))

            # Create approved thumbnail
            thumbnail_data = {
                "topic_id": "test-topic",
                "title_text": "Test",
                "visual_elements": "test",
                "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.thumbnails_dir / "test-topic.json").write_text(json.dumps(thumbnail_data))

            builder = ManifestBuilder(storage)
            manifest = builder.build(
                topic_id="test-topic",
                topic_title="Test Topic",
                source_url="https://example.com"
            )

            assert manifest.overall_status == "complete"


class TestManifestBuilderBlocked:
    """Test ManifestBuilder.build() returns 'blocked' when any asset is 'rejected'."""

    def test_blocked_when_rejected(self):
        """Test overall_status is 'blocked' when any asset is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            # Create rejected brief
            brief_data = {
                "topic_id": "test-topic",
                "why_it_matters": "Test",
                "plain_english_summary": ["a", "b", "c"],
                "student_takeaway": "test",
                "analogy": "test",
                "limitation": "test",
                "audience_fit": "test",
                "recommended_formats": ["carousel"],
                "source_url": "https://example.com",
                "review_status": "rejected",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.briefs_dir / "test-topic.json").write_text(json.dumps(brief_data))

            builder = ManifestBuilder(storage)
            manifest = builder.build(
                topic_id="test-topic",
                topic_title="Test Topic",
                source_url="https://example.com"
            )

            assert manifest.overall_status == "blocked"


class TestManifestBuilderBlockingReasons:
    """Test ManifestBuilder.build() blocking_reasons includes rejected assets."""

    def test_blocking_reasons_includes_rejected(self):
        """Test blocking_reasons contains rejected asset reasons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            # Create rejected brief
            brief_data = {
                "topic_id": "test-topic",
                "why_it_matters": "Test",
                "plain_english_summary": ["a", "b", "c"],
                "student_takeaway": "test",
                "analogy": "test",
                "limitation": "test",
                "audience_fit": "test",
                "recommended_formats": [],
                "source_url": "https://example.com",
                "review_status": "rejected",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.briefs_dir / "test-topic.json").write_text(json.dumps(brief_data))

            builder = ManifestBuilder(storage)
            manifest = builder.build(
                topic_id="test-topic",
                topic_title="Test Topic",
                source_url="https://example.com"
            )

            assert "brief: rejected" in manifest.blocking_reasons


class TestReadyForPlanner:
    """Test ready_for_planner is False when any asset is 'reviewed' but not 'approved'."""

    def test_ready_for_planner_false_when_reviewed(self):
        """Test ready_for_planner is False when asset is reviewed but not approved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            # Create reviewed (not approved) brief
            brief_data = {
                "topic_id": "test-topic",
                "why_it_matters": "Test",
                "plain_english_summary": ["a", "b", "c"],
                "student_takeaway": "test",
                "analogy": "test",
                "limitation": "test",
                "audience_fit": "test",
                "recommended_formats": [],
                "source_url": "https://example.com",
                "review_status": "reviewed",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.briefs_dir / "test-topic.json").write_text(json.dumps(brief_data))

            builder = ManifestBuilder(storage)
            manifest = builder.build(
                topic_id="test-topic",
                topic_title="Test Topic",
                source_url="https://example.com"
            )

            assert manifest.ready_for_planner is False


class TestStorageUpdateAssetStatus:
    """Test storage.update_asset_status() correctly updates review_status in file."""

    def test_update_asset_status_success(self):
        """Test update_asset_status correctly updates review_status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            # Create a brief file
            brief_data = {
                "topic_id": "test-topic",
                "why_it_matters": "Test",
                "plain_english_summary": ["a", "b", "c"],
                "student_takeaway": "test",
                "analogy": "test",
                "limitation": "test",
                "audience_fit": "test",
                "recommended_formats": [],
                "source_url": "https://example.com",
                "review_status": "draft",
                "generated_at": "2026-05-16T00:00:00Z"
            }
            (storage.briefs_dir / "test-topic.json").write_text(json.dumps(brief_data))

            result = storage.update_asset_status("brief", "test-topic", ReviewStatus.APPROVED)

            assert result is True
            # Verify the file was updated
            updated_data = json.loads((storage.briefs_dir / "test-topic.json").read_text())
            assert updated_data["review_status"] == "approved"

    def test_update_asset_status_returns_false_for_missing_file(self):
        """Test update_asset_status returns False when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            result = storage.update_asset_status("brief", "nonexistent", ReviewStatus.APPROVED)

            assert result is False

    def test_update_asset_status_raises_value_error_for_unknown_type(self):
        """Test update_asset_status raises ValueError for unknown asset_type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))

            with pytest.raises(ValueError) as exc_info:
                storage.update_asset_status("unknown_type", "test-topic", ReviewStatus.APPROVED)

            assert "unknown_type" in str(exc_info.value)