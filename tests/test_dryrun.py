"""Tests for dry-run validation and report models."""

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from content_creation.models.calendar import WeeklyCalendar, ScheduledPost
from content_creation.models.dryrun import AssetCheck, DryRunReport
from content_creation.planning.dryrun import DryRunValidator
from content_creation.storage.local import LocalStorage


class TestDryRunReportModel:
    """Test DryRunReport model validates correctly."""

    def test_dryrun_report_validates_correctly(self):
        """Test DryRunReport accepts valid data."""
        report = DryRunReport(
            week_start="2026-05-18",
            week_end="2026-05-24",
            total_scheduled=3,
            ready_count=2,
            warning_count=1,
            blocked_count=0,
            checks=[
                AssetCheck(
                    topic_id="topic-1",
                    topic_title="Test Topic",
                    format="short_video",
                    asset_path="data/scripts/topic-1.json",
                    review_status="approved",
                    is_ready=True,
                    warning=None,
                )
            ],
            warnings=["⚠ Warning message"],
            recommended_actions=["Action 1"],
            generated_at="2026-05-16T12:00:00Z",
        )

        assert report.week_start == "2026-05-18"
        assert report.total_scheduled == 3
        assert report.ready_count == 2


class TestAssetCheckReady:
    """Test AssetCheck is_ready is True only for approved status."""

    def test_is_ready_true_for_approved(self):
        """Test is_ready is True when review_status is approved."""
        check = AssetCheck(
            topic_id="topic-1",
            topic_title="Test Topic",
            format="short_video",
            asset_path="data/scripts/topic-1.json",
            review_status="approved",
            is_ready=True,
            warning=None,
        )
        assert check.is_ready is True

    def test_is_ready_false_for_draft(self):
        """Test is_ready is False when review_status is draft."""
        check = AssetCheck(
            topic_id="topic-1",
            topic_title="Test Topic",
            format="short_video",
            asset_path="data/scripts/topic-1.json",
            review_status="draft",
            is_ready=False,
            warning="short_video for Test Topic is draft — not approved for publishing",
        )
        assert check.is_ready is False

    def test_is_ready_false_for_needs_review(self):
        """Test is_ready is False when review_status is needs_review."""
        check = AssetCheck(
            topic_id="topic-1",
            topic_title="Test Topic",
            format="short_video",
            asset_path="data/scripts/topic-1.json",
            review_status="needs_review",
            is_ready=False,
            warning="short_video for Test Topic is needs_review — not approved for publishing",
        )
        assert check.is_ready is False


class TestDryRunValidatorWarnings:
    """Test DryRunValidator.run() builds correct warning messages."""

    def test_warning_message_for_non_approved(self):
        """Test warning message is built correctly for non-approved assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("weekly_targets: {}")

            # Create calendar with a draft asset
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
                        scheduled_at="2026-05-16T12:00:00Z",
                    )
                ],
                total_posts=1,
                format_counts={"short_video": 1},
                topics_used=["topic-1"],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={},
            )

            # Create draft asset file
            (storage.scripts_dir / "topic-1.json").write_text(json.dumps({
                "topic_id": "topic-1",
                "hook": "Test",
                "review_status": "draft",
                "generated_at": "2026-05-16T00:00:00Z"
            }))

            validator = DryRunValidator(storage, config_path)
            report = validator.run(calendar)

            assert len(report.checks) == 1
            assert report.checks[0].warning is not None
            assert "draft" in report.checks[0].warning
            assert "Test Topic" in report.checks[0].warning


class TestDryRunValidatorBlockedCount:
    """Test DryRunValidator.run() sets blocked_count correctly for missing files."""

    def test_blocked_count_for_missing_files(self):
        """Test blocked_count is set correctly when asset file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("weekly_targets: {}")

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
                        scheduled_at="2026-05-16T12:00:00Z",
                    )
                ],
                total_posts=1,
                format_counts={"short_video": 1},
                topics_used=["topic-1"],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={},
            )

            # Don't create asset file - it will be missing

            validator = DryRunValidator(storage, config_path)
            report = validator.run(calendar)

            assert report.blocked_count == 1
            assert "not found" in report.checks[0].warning


class TestDryRunValidatorAllReady:
    """Test DryRunValidator.run() returns 'All assets ready' action when all approved."""

    def test_all_assets_ready_action(self):
        """Test recommended_actions contains 'All assets ready' when all approved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("weekly_targets: {}")

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
                        scheduled_at="2026-05-16T12:00:00Z",
                    )
                ],
                total_posts=1,
                format_counts={"short_video": 1},
                topics_used=["topic-1"],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={},
            )

            # Create approved asset file
            (storage.scripts_dir / "topic-1.json").write_text(json.dumps({
                "topic_id": "topic-1",
                "hook": "Test",
                "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }))

            validator = DryRunValidator(storage, config_path)
            report = validator.run(calendar)

            assert "All assets ready — safe to publish" in report.recommended_actions


class TestDryRunValidatorAllActions:
    """Test DryRunValidator.run() includes all 4 recommended actions when all problem types present."""

    def test_all_recommended_actions_present(self):
        """Test all 4 recommended action types appear when problems exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("weekly_targets: {}")

            # Calendar with 4 posts that will have different issues
            calendar = WeeklyCalendar(
                week_start="2026-05-18",
                week_end="2026-05-24",
                posts=[
                    ScheduledPost(day=1, date="2026-05-18", topic_id="topic-1",
                        topic_title="Draft Topic", format="short_video",
                        asset_path="data/scripts/topic-1.json", source_url="https://example.com",
                        scheduled_at="2026-05-16T12:00:00Z"),
                    ScheduledPost(day=2, date="2026-05-19", topic_id="topic-2",
                        topic_title="Needs Review Topic", format="carousel",
                        asset_path="data/carousels/topic-2.json", source_url="https://example.com",
                        scheduled_at="2026-05-16T12:00:00Z"),
                    ScheduledPost(day=3, date="2026-05-20", topic_id="topic-3",
                        topic_title="Rejected Topic", format="newsletter",
                        asset_path="data/newsletters/topic-3.json", source_url="https://example.com",
                        scheduled_at="2026-05-16T12:00:00Z"),
                    ScheduledPost(day=4, date="2026-05-21", topic_id="topic-4",
                        topic_title="Missing Topic", format="thumbnail",
                        asset_path="data/thumbnails/topic-4.json", source_url="https://example.com",
                        scheduled_at="2026-05-16T12:00:00Z"),
                ],
                total_posts=4,
                format_counts={"short_video": 1, "carousel": 1, "newsletter": 1, "thumbnail": 1},
                topics_used=["topic-1", "topic-2", "topic-3", "topic-4"],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={},
            )

            # Create files with different statuses
            (storage.scripts_dir / "topic-1.json").write_text(json.dumps({
                "topic_id": "topic-1", "hook": "Test", "review_status": "draft",
                "generated_at": "2026-05-16T00:00:00Z"
            }))
            (storage.carousels_dir / "topic-2.json").write_text(json.dumps({
                "topic_id": "topic-2", "slides": [], "review_status": "needs_review",
                "generated_at": "2026-05-16T00:00:00Z"
            }))
            (storage.newsletters_dir / "topic-3.json").write_text(json.dumps({
                "topic_id": "topic-3", "subject_line": "Test", "review_status": "rejected",
                "generated_at": "2026-05-16T00:00:00Z"
            }))
            # topic-4 has no file - it's missing

            validator = DryRunValidator(storage, config_path)
            report = validator.run(calendar)

            assert any("draft" in action for action in report.recommended_actions)
            assert any("needs_review" in action for action in report.recommended_actions)
            assert any("rejected" in action for action in report.recommended_actions)
            assert any("missing" in action for action in report.recommended_actions)


class TestExportMarkdown:
    """Test export_markdown() creates file at correct path."""

    def test_export_markdown_creates_file(self):
        """Test export_markdown writes file to correct path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("weekly_targets: {}")

            report = DryRunReport(
                week_start="2026-05-18",
                week_end="2026-05-24",
                total_scheduled=1,
                ready_count=1,
                warning_count=0,
                blocked_count=0,
                checks=[
                    AssetCheck(
                        topic_id="topic-1",
                        topic_title="Test Topic",
                        format="short_video",
                        asset_path="data/scripts/topic-1.json",
                        review_status="approved",
                        is_ready=True,
                        warning=None,
                    )
                ],
                warnings=[],
                recommended_actions=["All assets ready — safe to publish"],
                generated_at="2026-05-16T12:00:00Z",
            )

            output_path = Path(tmpdir) / "data" / "dryruns" / "2026-05-18.md"

            validator = DryRunValidator(storage, config_path)
            validator.export_markdown(report, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "Dry Run Report" in content
            assert "2026-05-18" in content


class TestReadyCountMatchesApproved:
    """Test ready_count matches number of approved assets."""

    def test_ready_count_matches_approved(self):
        """Test ready_count equals number of approved assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            config_path = Path(tmpdir) / "config" / "publishing.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("weekly_targets: {}")

            calendar = WeeklyCalendar(
                week_start="2026-05-18",
                week_end="2026-05-24",
                posts=[
                    ScheduledPost(day=1, date="2026-05-18", topic_id="topic-1",
                        topic_title="Approved Topic", format="short_video",
                        asset_path="data/scripts/topic-1.json", source_url="https://example.com",
                        scheduled_at="2026-05-16T12:00:00Z"),
                    ScheduledPost(day=2, date="2026-05-19", topic_id="topic-2",
                        topic_title="Draft Topic", format="carousel",
                        asset_path="data/carousels/topic-2.json", source_url="https://example.com",
                        scheduled_at="2026-05-16T12:00:00Z"),
                ],
                total_posts=2,
                format_counts={"short_video": 1, "carousel": 1},
                topics_used=["topic-1", "topic-2"],
                generated_at="2026-05-16T12:00:00Z",
                config_snapshot={},
            )

            # Create one approved, one draft
            (storage.scripts_dir / "topic-1.json").write_text(json.dumps({
                "topic_id": "topic-1", "hook": "Test", "review_status": "approved",
                "generated_at": "2026-05-16T00:00:00Z"
            }))
            (storage.carousels_dir / "topic-2.json").write_text(json.dumps({
                "topic_id": "topic-2", "slides": [], "review_status": "draft",
                "generated_at": "2026-05-16T00:00:00Z"
            }))

            validator = DryRunValidator(storage, config_path)
            report = validator.run(calendar)

            assert report.ready_count == 1
            assert report.warning_count == 1