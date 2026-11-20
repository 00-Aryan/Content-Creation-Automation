"""Tests for manifest models and builder."""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_creation.models.manifest import AssetEntry, TopicManifest
from content_creation.shared.enums import ReviewStatus


class TestAssetEntry:
    def test_asset_entry_missing(self):
        """Test AssetEntry with status 'missing' and None generated_at."""
        entry = AssetEntry(
            path="data/briefs/test123.json",
            status="missing",
            generated_at=None,
        )
        assert entry.status == "missing"
        assert entry.generated_at is None
        assert entry.path == "data/briefs/test123.json"


class TestTopicManifest:
    def test_overall_status_complete(self):
        """Test overall_status 'complete' when all 5 assets are draft."""
        assets = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="draft", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="draft", generated_at="2026-05-14T10:01:00Z"),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="draft", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }

        manifest = TopicManifest(
            topic_id="t1",
            topic_title="Test Topic",
            source_url="https://example.com",
            assets=assets,
            overall_status="complete",
            blocking_reasons=[],
            ready_for_planner=True,
            generated_at="2026-05-14T10:00:00Z",
        )

        assert manifest.overall_status == "complete"
        assert manifest.ready_for_planner is True

    def test_overall_status_blocked(self):
        """Test overall_status 'blocked' when any asset is missing."""
        assets = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="draft", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="missing", generated_at=None),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="draft", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }

        manifest = TopicManifest(
            topic_id="t1",
            topic_title="Test Topic",
            source_url="https://example.com",
            assets=assets,
            overall_status="blocked",
            blocking_reasons=["script: missing"],
            ready_for_planner=False,
            generated_at="2026-05-14T10:00:00Z",
        )

        assert manifest.overall_status == "blocked"
        assert manifest.ready_for_planner is False

    def test_overall_status_partial(self):
        """Test overall_status 'partial' when mix of draft and needs_review."""
        assets = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="draft", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="draft", generated_at="2026-05-14T10:01:00Z"),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="needs_review", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }

        manifest = TopicManifest(
            topic_id="t1",
            topic_title="Test Topic",
            source_url="https://example.com",
            assets=assets,
            overall_status="partial",
            blocking_reasons=["carousel: needs_review"],
            ready_for_planner=False,
            generated_at="2026-05-14T10:00:00Z",
        )

        assert manifest.overall_status == "partial"
        assert manifest.ready_for_planner is False

    def test_blocking_reasons_empty_when_complete(self):
        """Test blocking_reasons is empty when complete."""
        assets = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="draft", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="draft", generated_at="2026-05-14T10:01:00Z"),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="draft", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }

        manifest = TopicManifest(
            topic_id="t1",
            topic_title="Test Topic",
            source_url="https://example.com",
            assets=assets,
            overall_status="complete",
            blocking_reasons=[],
            ready_for_planner=True,
            generated_at="2026-05-14T10:00:00Z",
        )

        assert manifest.blocking_reasons == []

    def test_blocking_reasons_contains_correct_entries_when_blocked(self):
        """Test blocking_reasons contains correct entries when blocked."""
        assets = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="needs_review", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="missing", generated_at=None),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="draft", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }

        manifest = TopicManifest(
            topic_id="t1",
            topic_title="Test Topic",
            source_url="https://example.com",
            assets=assets,
            overall_status="blocked",
            blocking_reasons=["brief: needs_review", "script: missing"],
            ready_for_planner=False,
            generated_at="2026-05-14T10:00:00Z",
        )

        assert "brief: needs_review" in manifest.blocking_reasons
        assert "script: missing" in manifest.blocking_reasons
        assert len(manifest.blocking_reasons) == 2

    def test_ready_for_planner_only_when_complete(self):
        """Test ready_for_planner is True only when complete."""
        # Complete - True
        assets_complete = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="draft", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="draft", generated_at="2026-05-14T10:01:00Z"),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="draft", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }
        manifest_complete = TopicManifest(
            topic_id="t1",
            topic_title="Test",
            source_url="https://x.com",
            assets=assets_complete,
            overall_status="complete",
            blocking_reasons=[],
            ready_for_planner=True,
            generated_at="2026-05-14T10:00:00Z",
        )
        assert manifest_complete.ready_for_planner is True

        # Partial - False
        assets_partial = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="draft", generated_at="2026-05-14T10:00:00Z"),
            "script": AssetEntry(path="data/scripts/t1.json", status="draft", generated_at="2026-05-14T10:01:00Z"),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="needs_review", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }
        manifest_partial = TopicManifest(
            topic_id="t1",
            topic_title="Test",
            source_url="https://x.com",
            assets=assets_partial,
            overall_status="partial",
            blocking_reasons=["carousel: needs_review"],
            ready_for_planner=False,
            generated_at="2026-05-14T10:00:00Z",
        )
        assert manifest_partial.ready_for_planner is False

        # Blocked - False
        assets_blocked = {
            "brief": AssetEntry(path="data/briefs/t1.json", status="missing", generated_at=None),
            "script": AssetEntry(path="data/scripts/t1.json", status="draft", generated_at="2026-05-14T10:01:00Z"),
            "carousel": AssetEntry(path="data/carousels/t1.json", status="draft", generated_at="2026-05-14T10:02:00Z"),
            "newsletter": AssetEntry(path="data/newsletters/t1.json", status="draft", generated_at="2026-05-14T10:03:00Z"),
            "thumbnail": AssetEntry(path="data/thumbnails/t1.json", status="draft", generated_at="2026-05-14T10:04:00Z"),
        }
        manifest_blocked = TopicManifest(
            topic_id="t1",
            topic_title="Test",
            source_url="https://x.com",
            assets=assets_blocked,
            overall_status="blocked",
            blocking_reasons=["brief: missing"],
            ready_for_planner=False,
            generated_at="2026-05-14T10:00:00Z",
        )
        assert manifest_blocked.ready_for_planner is False


class TestManifestBuilder:
    def test_build_detects_missing_files(self, tmp_path):
        """Test ManifestBuilder.build() correctly detects missing files."""
        from content_creation.storage.local import LocalStorage

        storage = LocalStorage(tmp_path)
        from content_creation.manifest import ManifestBuilder

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="test123",
            topic_title="Test Topic",
            source_url="https://example.com",
        )

        # All assets should be missing
        assert manifest.assets["brief"].status == "missing"
        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "missing"
        assert manifest.assets["newsletter"].status == "missing"
        assert manifest.assets["thumbnail"].status == "missing"

    def test_build_reads_status_from_existing_files(self, tmp_path):
        """Test ManifestBuilder.build() correctly reads status from existing asset JSON files."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)

        # Create a brief file with draft status
        brief_data = {
            "topic_id": "test123",
            "why_it_matters": "Test topic",
            "plain_english_summary": ["summary one", "summary two", "summary three"],
            "student_takeaway": "takeaway",
            "analogy": "analogy",
            "limitation": "limitation",
            "audience_fit": "audience",
            "recommended_formats": ["short_video"],
            "source_url": "https://example.com",
            "review_status": "draft",
            "generated_at": "2026-05-14T10:00:00Z",
        }

        with open(tmp_path / "data" / "briefs" / "test123.json", "w") as f:
            json.dump(brief_data, f)

        # Create a script file with needs_review status
        script_data = {
            "topic_id": "test123",
            "format": "short_video",
            "hook": "hook",
            "script_sections": ["section"],
            "cta": "cta",
            "claims_used": ["claim"],
            "source_links": ["https://example.com"],
            "review_status": "needs_review",
            "generated_at": "2026-05-14T10:01:00Z",
        }

        with open(tmp_path / "data" / "scripts" / "test123.json", "w") as f:
            json.dump(script_data, f)

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="test123",
            topic_title="Test Topic",
            source_url="https://example.com",
        )

        # Check status was read correctly
        assert manifest.assets["brief"].status == "draft"
        assert manifest.assets["script"].status == "needs_review"

    def test_build_all_returns_one_manifest_per_brief(self, tmp_path):
        """Test ManifestBuilder.build_all() returns one manifest per brief."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)

        # Create two briefs
        for topic_id in ["test1", "test2"]:
            brief_data = {
                "topic_id": topic_id,
                "why_it_matters": f"Topic {topic_id}",
                "plain_english_summary": ["summary one", "summary two", "summary three"],
                "student_takeaway": "takeaway",
                "analogy": "analogy",
                "limitation": "limitation",
                "audience_fit": "audience",
                "recommended_formats": ["short_video"],
                "source_url": f"https://example.com/{topic_id}",
                "review_status": "draft",
                "generated_at": "2026-05-14T10:00:00Z",
            }

            with open(tmp_path / "data" / "briefs" / f"{topic_id}.json", "w") as f:
                json.dump(brief_data, f)

        builder = ManifestBuilder(storage)
        manifests = builder.build_all()

        assert len(manifests) == 2
        topic_ids = [m.topic_id for m in manifests]
        assert "test1" in topic_ids
        assert "test2" in topic_ids

    def _write_brief(self, tmp_path, topic_id, recommended_formats=None, status="draft"):
        brief_data = {
            "topic_id": topic_id,
            "why_it_matters": "Test topic",
            "plain_english_summary": ["one", "two", "three"],
            "student_takeaway": "takeaway",
            "analogy": "analogy",
            "limitation": "limitation",
            "audience_fit": "audience",
            "recommended_formats": recommended_formats or ["short_video"],
            "source_url": "https://example.com",
            "review_status": status,
            "generated_at": "2026-05-14T10:00:00Z",
        }
        with open(tmp_path / "data" / "briefs" / f"{topic_id}.json", "w") as f:
            json.dump(brief_data, f)

    def _write_asset(self, tmp_path, asset_type, topic_id, status="draft"):
        dirs = {
            "script": "scripts",
            "carousel": "carousels",
            "newsletter": "newsletters",
            "thumbnail": "thumbnails",
        }
        payloads = {
            "script": {
                "topic_id": topic_id,
                "format": "short_video",
                "hook": "hook",
                "script_sections": ["section"],
                "cta": "cta",
                "claims_used": ["claim"],
                "source_links": ["https://example.com"],
                "review_status": status,
                "generated_at": "2026-05-14T10:01:00Z",
            },
            "carousel": {
                "topic_id": topic_id,
                "slides": [{"headline": "h", "body": "b", "visual_note": "v"}],
                "cta": "cta",
                "claims_used": ["claim"],
                "source_links": ["https://example.com"],
                "review_status": status,
                "generated_at": "2026-05-14T10:02:00Z",
            },
            "newsletter": {
                "topic_id": topic_id,
                "subject_line": "subject",
                "preview_text": "preview",
                "sections": [{"heading": "h", "body": "b"}],
                "cta": "cta",
                "claims_used": ["claim"],
                "source_links": ["https://example.com"],
                "review_status": status,
                "generated_at": "2026-05-14T10:03:00Z",
            },
            "thumbnail": {
                "topic_id": topic_id,
                "title_text": "title",
                "supporting_text": "support",
                "visual_metaphor": "metaphor",
                "style": "clean_minimal",
                "negative_prompt": ["none"],
                "readability_notes": "notes",
                "review_status": status,
                "generated_at": "2026-05-14T10:04:00Z",
            },
        }
        subdir = dirs[asset_type]
        with open(tmp_path / "data" / subdir / f"{topic_id}.json", "w") as f:
            json.dump(payloads[asset_type], f)

    def test_build_skips_non_recommended_formats(self, tmp_path):
        """short_video only → carousel and newsletter are skipped, not missing."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(tmp_path, "test123", recommended_formats=["short_video"])

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="test123",
            topic_title="Test Topic",
            source_url="https://example.com",
        )

        assert manifest.assets["carousel"].status == "skipped"
        assert manifest.assets["newsletter"].status == "skipped"
        assert manifest.assets["script"].status == "missing"

    def test_skipped_assets_do_not_affect_overall_status(self, tmp_path):
        """brief=approved, script=approved, rest skipped → overall_status complete."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(tmp_path, "test123", recommended_formats=["short_video"], status="approved")
        self._write_asset(tmp_path, "script", "test123", status="approved")
        self._write_asset(tmp_path, "thumbnail", "test123", status="approved")

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="test123",
            topic_title="Test Topic",
            source_url="https://example.com",
        )

        assert manifest.assets["carousel"].status == "skipped"
        assert manifest.assets["newsletter"].status == "skipped"
        assert manifest.overall_status == "complete"

    def test_ready_for_planner_when_non_skipped_are_approved(self, tmp_path):
        """ready_for_planner True when all non-skipped assets are approved."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(tmp_path, "test123", recommended_formats=["short_video"], status="approved")
        self._write_asset(tmp_path, "script", "test123", status="approved")
        self._write_asset(tmp_path, "thumbnail", "test123", status="approved")

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="test123",
            topic_title="Test Topic",
            source_url="https://example.com",
        )

        assert manifest.ready_for_planner is True
        assert manifest.overall_status == "complete"

    def test_thumbnail_always_required_not_skipped(self, tmp_path):
        """Thumbnail is missing even when not in recommended_formats."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(tmp_path, "test123", recommended_formats=["short_video"])

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="test123",
            topic_title="Test Topic",
            source_url="https://example.com",
        )

        assert manifest.assets["thumbnail"].status == "missing"
        assert manifest.assets["thumbnail"].status != "skipped"

    def test_list_briefs_logs_warning_on_invalid_json(self, tmp_path, caplog):
        """list_briefs logs warning and continues when one brief has invalid JSON."""
        from content_creation.storage.local import LocalStorage

        storage = LocalStorage(tmp_path)
        self._write_brief(tmp_path, "valid_brief")

        bad_path = tmp_path / "data" / "briefs" / "bad_brief.json"
        bad_path.write_text("{not valid json", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            briefs = storage.list_briefs()

        assert len(briefs) == 1
        assert briefs[0].topic_id == "valid_brief"
        assert any(
            "bad_brief.json" in record.message for record in caplog.records
        )
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_manifest_blocking_reasons_and_readiness(self, tmp_path):
        """Test manifest blocking reasons and readiness reporting under various asset status combinations."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        builder = ManifestBuilder(storage)

        def run_build(brief_status, script_status, carousel_status, newsletter_status, thumbnail_status, recommended_formats=None):
            # Clean up directories
            for sub in ["briefs", "scripts", "carousels", "newsletters", "thumbnails"]:
                dir_path = tmp_path / "data" / sub
                if dir_path.exists():
                    for f in dir_path.glob("*.json"):
                        f.unlink()

            # Write brief if not missing
            if brief_status != "missing":
                self._write_brief(tmp_path, "t1", recommended_formats=recommended_formats, status=brief_status)
            # Write other assets if not missing
            if script_status != "missing":
                self._write_asset(tmp_path, "script", "t1", status=script_status)
            if carousel_status != "missing":
                self._write_asset(tmp_path, "carousel", "t1", status=carousel_status)
            if newsletter_status != "missing":
                self._write_asset(tmp_path, "newsletter", "t1", status=newsletter_status)
            if thumbnail_status != "missing":
                self._write_asset(tmp_path, "thumbnail", "t1", status=thumbnail_status)

            return builder.build(
                topic_id="t1",
                topic_title="Test Topic",
                source_url="https://example.com",
            )

        # 1. A manifest with all non-skipped assets approved has:
        # ready_for_planner == True
        # blocking_reasons == []
        # overall_status == "complete"
        manifest = run_build(
            brief_status="approved",
            script_status="approved",
            carousel_status="approved",
            newsletter_status="approved",
            thumbnail_status="approved",
            recommended_formats=["short_video", "carousel", "newsletter"]
        )
        assert manifest.ready_for_planner is True
        assert manifest.blocking_reasons == []
        assert manifest.overall_status == "complete"

        # 2. A manifest with one draft required asset has:
        # ready_for_planner == False
        # blocking_reasons includes "thumbnail: draft"
        # overall_status == "partial"
        manifest = run_build(
            brief_status="approved",
            script_status="approved",
            carousel_status="missing",
            newsletter_status="missing",
            thumbnail_status="draft",
            recommended_formats=["short_video"]
        )
        assert manifest.ready_for_planner is False
        assert "thumbnail: draft" in manifest.blocking_reasons
        assert manifest.overall_status == "partial"

        # 3. A manifest with one needs_review asset still includes: carousel: needs_review
        manifest = run_build(
            brief_status="approved",
            script_status="approved",
            carousel_status="needs_review",
            newsletter_status="approved",
            thumbnail_status="approved",
            recommended_formats=["short_video", "carousel", "newsletter"]
        )
        assert manifest.ready_for_planner is False
        assert "carousel: needs_review" in manifest.blocking_reasons

        # 4. A manifest with one reviewed asset includes: script: reviewed
        manifest = run_build(
            brief_status="approved",
            script_status="reviewed",
            carousel_status="approved",
            newsletter_status="approved",
            thumbnail_status="approved",
            recommended_formats=["short_video", "carousel", "newsletter"]
        )
        assert manifest.ready_for_planner is False
        assert "script: reviewed" in manifest.blocking_reasons

        # 5. A manifest with one missing asset includes: brief: missing
        manifest = run_build(
            brief_status="missing",
            script_status="approved",
            carousel_status="approved",
            newsletter_status="approved",
            thumbnail_status="approved",
            recommended_formats=["short_video", "carousel", "newsletter"]
        )
        assert manifest.ready_for_planner is False
        assert "brief: missing" in manifest.blocking_reasons

        # 6. A manifest with skipped optional assets does not include skipped assets in blocking_reasons
        manifest = run_build(
            brief_status="approved",
            script_status="approved",
            carousel_status="missing",
            newsletter_status="missing",
            thumbnail_status="approved",
            recommended_formats=["short_video"]
        )
        assert manifest.ready_for_planner is True
        assert manifest.blocking_reasons == []
        assert manifest.assets["carousel"].status == "skipped"
        assert manifest.assets["newsletter"].status == "skipped"

        # 7. ready_for_planner remains false whenever any non-skipped asset is not approved
        # Tested by case 2, 3, 4, 5 above, where ready_for_planner is False.

    def test_recommended_formats_filters_review_status_leak(self, tmp_path, caplog):
        """Review status ('needs_review') in recommended_formats must be filtered, avoiding format leaks."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_leak",
            recommended_formats=["carousel", "needs_review"],
            status="approved",
        )
        self._write_asset(tmp_path, "carousel", "topic_leak", status="approved")
        self._write_asset(tmp_path, "thumbnail", "topic_leak", status="approved")

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id="topic_leak",
                topic_title="Topic Leak Test",
                source_url="https://example.com",
            )

        # Script must be skipped (not forced to short_video by needs_review)
        assert manifest.assets["script"].status == "skipped"
        assert manifest.assets["carousel"].status == "approved"
        assert manifest.assets["newsletter"].status == "skipped"
        assert manifest.overall_status == "complete"
        assert manifest.ready_for_planner is True

        # No warning about needs_review being an unknown format
        assert not any("needs_review" in r.message for r in caplog.records)

    def test_recommended_formats_with_only_review_status_defaults_cleanly(self, tmp_path, caplog):
        """Brief with only review status placeholder cleanly defaults to short_video without warning."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_fallback",
            recommended_formats=["needs_review"],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id="topic_fallback",
                topic_title="Fallback Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "skipped"
        assert not any("needs_review" in r.message for r in caplog.records)

    def test_recommended_formats_genuine_unknown_format_logs_warning(self, tmp_path, caplog):
        """Genuine unknown formats still log a warning and default to short_video."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_unknown",
            recommended_formats=["podcast"],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id="topic_unknown",
                topic_title="Unknown Format Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "missing"
        assert any("Unknown format 'podcast'" in r.message for r in caplog.records)

    @pytest.mark.parametrize("status_val", [
        "draft",
        "needs_review",
        "reviewed",
        "approved",
        "rejected",
    ])
    def test_recommended_formats_matrix_all_review_statuses_filtered(self, tmp_path, caplog, status_val):
        """Covers ERR-005: all 5 ReviewStatus enum values in recommended_formats are filtered and cleanly fallback."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            f"topic_{status_val}",
            recommended_formats=[status_val],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id=f"topic_{status_val}",
                topic_title="Filter Test",
                source_url="https://example.com",
            )

        # Filters review status, defaults to short_video (script missing)
        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "skipped"
        assert manifest.assets["newsletter"].status == "skipped"
        # Must not log an unknown format warning
        assert not any(f"Unknown format '{status_val}'" in r.message for r in caplog.records)

    @pytest.mark.parametrize("status_val", [
        "draft",
        "needs_review",
        "reviewed",
        "approved",
        "rejected",
    ])
    def test_recommended_formats_matrix_review_status_mixed_with_carousel(self, tmp_path, caplog, status_val):
        """Covers ERR-005: each ReviewStatus value mixed with carousel only maps carousel without video format leak."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            f"topic_mixed_{status_val}",
            recommended_formats=["carousel", status_val],
            status="approved",
        )
        self._write_asset(tmp_path, "carousel", f"topic_mixed_{status_val}", status="approved")
        self._write_asset(tmp_path, "thumbnail", f"topic_mixed_{status_val}", status="approved")

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id=f"topic_mixed_{status_val}",
                topic_title="Mixed Format Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "skipped"
        assert manifest.assets["carousel"].status == "approved"
        assert manifest.assets["newsletter"].status == "skipped"
        assert manifest.overall_status == "complete"
        assert not any(status_val in r.message for r in caplog.records)

    def test_recommended_formats_whitespace_and_case_insensitive_filtering(self, tmp_path, caplog):
        """Covers ERR-005: review status filtering handles leading/trailing whitespace and mixed case."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_ws",
            recommended_formats=["  NEEDS_REVIEW \n", "\tDraft\t", "ReVieWed", "  APPROVED  ", "ReJeCtEd "],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id="topic_ws",
                topic_title="Whitespace Test",
                source_url="https://example.com",
            )

        # All review statuses are filtered, defaults cleanly to short_video
        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "skipped"
        assert manifest.assets["newsletter"].status == "skipped"
        assert not any("Unknown format" in r.message for r in caplog.records)

    def test_recommended_formats_uppercase_valid_formats(self, tmp_path):
        """Covers ERR-005: case-insensitive mapping for valid formats like SHORT_VIDEO and Carousel."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_upper",
            recommended_formats=["SHORT_VIDEO", " Carousel "],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="topic_upper",
            topic_title="Upper Format Test",
            source_url="https://example.com",
        )

        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "missing"
        assert manifest.assets["newsletter"].status == "skipped"

    def test_recommended_formats_freetext_mapping(self, tmp_path, caplog):
        """Covers ERR-005: freetext formats like 'video', 'case study', 'email' are mapped correctly."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_freetext",
            recommended_formats=["video", "case study", "email"],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.INFO):
            manifest = builder.build(
                topic_id="topic_freetext",
                topic_title="Freetext Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "missing"
        assert manifest.assets["newsletter"].status == "missing"
        assert any("Mapped format 'video' → 'short_video'" in r.message for r in caplog.records)

    def test_recommended_formats_non_string_elements_resilience(self, tmp_path, caplog):
        """Covers ERR-005: non-string elements and empty strings in recommended_formats are safely ignored."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_non_str",
            recommended_formats=[None, 123, 45.6, True, {}, [], "", "   ", "carousel", "needs_review"],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id="topic_non_str",
                topic_title="Non-String Resilience Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "skipped"
        assert manifest.assets["carousel"].status == "missing"
        assert manifest.assets["newsletter"].status == "skipped"
        assert not any("needs_review" in r.message for r in caplog.records)

    def test_recommended_formats_single_string_instead_of_list(self, tmp_path):
        """Covers ERR-005: single string recommended_formats is normalized to list without error."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_str_fmt",
            recommended_formats="carousel",
            status="approved",
        )

        builder = ManifestBuilder(storage)
        manifest = builder.build(
            topic_id="topic_str_fmt",
            topic_title="Single String Test",
            source_url="https://example.com",
        )

        assert manifest.assets["carousel"].status == "missing"
        assert manifest.assets["script"].status == "skipped"

    def test_recommended_formats_empty_list_defaults_cleanly(self, tmp_path, caplog):
        """Covers ERR-005: empty recommended_formats list defaults cleanly to short_video without warnings."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            "topic_empty_list",
            recommended_formats=[],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id="topic_empty_list",
                topic_title="Empty List Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "skipped"
        assert len(caplog.records) == 0

    @pytest.mark.parametrize("unknown_fmt", [
        "podcast",
        "webinar",
        "interactive_quiz",
        "whitepaper",
    ])
    def test_recommended_formats_authentic_unknown_formats_matrix(self, tmp_path, caplog, unknown_fmt):
        """Covers ERR-005: authentic unknown formats continue to log warning and default to short_video."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        self._write_brief(
            tmp_path,
            f"topic_unk_{unknown_fmt}",
            recommended_formats=[unknown_fmt],
            status="approved",
        )

        builder = ManifestBuilder(storage)
        with caplog.at_level(logging.WARNING):
            manifest = builder.build(
                topic_id=f"topic_unk_{unknown_fmt}",
                topic_title="Unknown Format Matrix Test",
                source_url="https://example.com",
            )

        assert manifest.assets["script"].status == "missing"
        assert manifest.assets["carousel"].status == "skipped"
        assert any(f"Unknown format '{unknown_fmt}'" in r.message for r in caplog.records)

    def test_manifest_builder_load_json_handles_zero_byte_and_corrupt_files(self, tmp_path, caplog):
        """Covers ERR-006: ManifestBuilder._load_json safely catches JSONDecodeError and returns empty dict."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        builder = ManifestBuilder(storage)

        empty_file = tmp_path / "empty.json"
        empty_file.write_text("", encoding="utf-8")

        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text('{"unclosed": "brace', encoding="utf-8")

        nonexistent_file = tmp_path / "does_not_exist.json"

        non_dict_file = tmp_path / "list.json"
        non_dict_file.write_text("[1, 2, 3]", encoding="utf-8")

        with caplog.at_level(logging.ERROR):
            assert builder._load_json(empty_file) == {}
            assert builder._load_json(corrupt_file) == {}
            assert builder._load_json(nonexistent_file) == {}
            assert builder._load_json(non_dict_file) == {}

        assert any("Failed to load or parse JSON from" in r.message for r in caplog.records)

    def test_manifest_builder_build_all_handles_zero_byte_and_corrupt_briefs(self, tmp_path):
        """Covers ERR-006: build_all continues processing when encountering 0-byte or corrupted briefs."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        (tmp_path / "data" / "briefs").mkdir(parents=True, exist_ok=True)

        # 1 valid brief
        self._write_brief(tmp_path, "valid_topic_1", recommended_formats=["short_video"])

        # 1 0-byte brief
        (tmp_path / "data" / "briefs" / "empty_brief.json").write_text("", encoding="utf-8")

        # 1 corrupt JSON brief
        (tmp_path / "data" / "briefs" / "corrupt_brief.json").write_text("{broken", encoding="utf-8")

        builder = ManifestBuilder(storage)
        manifests = builder.build_all()

        assert len(manifests) == 1
        assert manifests[0].topic_id == "valid_topic_1"

    def test_manifest_builder_build_all_empty_storage_or_failure(self, tmp_path, caplog):
        """Covers ERR-006: build_all handles empty storage and recovers gracefully from individual build failures."""
        from content_creation.storage.local import LocalStorage
        from content_creation.manifest import ManifestBuilder

        storage = LocalStorage(tmp_path)
        builder = ManifestBuilder(storage)

        # 1. Empty storage returns [] and logs warning
        with caplog.at_level(logging.WARNING):
            manifests = builder.build_all()
            assert manifests == []
            assert any("No briefs found" in r.message for r in caplog.records)

        # 2. Individual brief build failure is skipped
        caplog.clear()
        self._write_brief(tmp_path, "topic_fail_1", recommended_formats=["short_video"])
        self._write_brief(tmp_path, "topic_ok_2", recommended_formats=["short_video"])

        with patch.object(builder, "build", side_effect=[RuntimeError("Build crashed"), MagicMock()]):
            with caplog.at_level(logging.WARNING):
                manifests = builder.build_all()
                assert len(manifests) == 1
                assert any("Skipping manifest for topic_fail_1" in r.message for r in caplog.records)

        # 3. Storage exception in list_briefs handled gracefully
        caplog.clear()
        with patch.object(storage, "list_briefs", side_effect=OSError("Storage IO error")):
            with caplog.at_level(logging.WARNING):
                manifests = builder.build_all()
                assert manifests == []
                assert any("manifest build_all() returning empty list: Storage IO error" in r.message for r in caplog.records)


class TestStoryboardFaultInjectionAndUpstreamProbes:
    """Covers fault injection and upstream generator contract probes."""

    def test_load_storyboard_handles_empty_or_truncated_file(self, tmp_path, caplog):
        """Covers ERR-006: LocalStorage.get_storyboard handles 0-byte or truncated JSON files returning None without crashing."""
        from content_creation.storage.local import LocalStorage

        storage = LocalStorage(tmp_path)
        (tmp_path / "data" / "storyboards").mkdir(parents=True, exist_ok=True)

        # 0-byte storyboard
        empty_sb = tmp_path / "data" / "storyboards" / "empty_topic.json"
        empty_sb.write_text("", encoding="utf-8")

        # Truncated storyboard
        corrupt_sb = tmp_path / "data" / "storyboards" / "corrupt_topic.json"
        corrupt_sb.write_text('{"topic_id": "corrupt_topic", "scenes":', encoding="utf-8")

        with caplog.at_level(logging.ERROR):
            assert storage.get_storyboard("empty_topic") is None
            assert storage.get_storyboard("corrupt_topic") is None
            assert storage.get_storyboard("nonexistent_topic") is None

        assert any("Failed to load Storyboard empty_topic" in r.message for r in caplog.records)
        assert any("Failed to load Storyboard corrupt_topic" in r.message for r in caplog.records)

    def test_asset_generation_skips_when_storyboard_is_zero_byte(self, tmp_path, caplog):
        """Covers ERR-006: AssetGenerationService triggers Storyboard Presence Gate when storyboard is 0 bytes."""
        from content_creation.application.context import ApplicationContext
        from content_creation.application.asset_generation_service import AssetGenerationService

        ctx = ApplicationContext.create(tmp_path)
        brief_data = {
            "topic_id": "topic_zb",
            "why_it_matters": "Test matter",
            "plain_english_summary": ["one", "two", "three"],
            "student_takeaway": "takeaway",
            "analogy": "analogy",
            "limitation": "limitation",
            "audience_fit": "audience",
            "recommended_formats": ["short_video"],
            "source_url": "https://example.com",
            "review_status": "approved",
            "generated_at": "2026-11-20T00:00:00Z",
        }
        with open(ctx.storage.briefs_dir / "topic_zb.json", "w", encoding="utf-8") as f:
            json.dump(brief_data, f)

        # Write 0-byte storyboard file
        (ctx.storage.storyboards_dir / "topic_zb.json").write_text("", encoding="utf-8")

        svc = AssetGenerationService()
        with caplog.at_level(logging.WARNING):
            result = svc.run(ctx)

        # Storyboard presence gate skips topic_zb cleanly
        assert result.skipped_count >= 1
        assert result.failed_count == 0
        assert any("Skipping asset generation for topic_zb because storyboard artifact is missing" in r.message for r in caplog.records)

    @pytest.mark.xfail(strict=True, reason="ERR-005: upstream brief.py:71 fallback leaks needs_review into recommended_formats")
    def test_upstream_brief_generator_fallback_does_not_leak_review_status(self, tmp_path):
        """Covers ERR-005: upstream brief generator fallback must not populate recommended_formats with ReviewStatus enum values."""
        from content_creation.generation.brief import generate_brief
        from content_creation.models.topic import ScoredTopicItem

        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text(
            "Template {{ topic.title }} {{ topic.source }} {{ topic.url }} {{ topic.raw_text }}",
            encoding="utf-8",
        )
        item = ScoredTopicItem(
            id="test_upstream_leak",
            title="Test Topic",
            url="https://example.com/item",
            source="arxiv",
            published_at="2026-11-20T00:00:00Z",
            raw_text="Machine learning research paper summary with sufficient text length for brief generation threshold " * 5,
            priority_score=85.0,
        )

        with patch("content_creation.generation.brief.InferenceManager") as mock_inference_class:
            mock_manager = MagicMock()
            mock_manager.generate.return_value = MagicMock(success=False, error="Quota exhausted 429")
            mock_inference_class.return_value = mock_manager

            brief = generate_brief(item, prompt_file)

            # Upstream defect in frozen src/content_creation/generation/brief.py:71 sets
            # recommended_formats=["needs_review"]. This assertion fails as expected, producing an XFAIL.
            assert "needs_review" not in brief.recommended_formats
            assert all(fmt in {"short_video", "carousel", "newsletter"} for fmt in brief.recommended_formats)