"""High-signal QA test suite for fix/phase1b-data-and-schemas.

Validates:
- ERR-005: Fallback brief generation format sanitization & ManifestBuilder defensive filter logging.
- SCHEMA-001 / SCHEMA-002 (ERR-013, ERR-014): TopicMetadata and TopicItem/ScoredTopicItem schema tightening,
  attribute & dict-like accessors, round-trip serialization, and extra dynamic fields preservation.
- SCHEMA-003 (ERR-015): PublishingConfigSnapshot typing, dict-like compatibility, and WeeklyCalendar persistence.
- SCHEMA-004 (ERR-016): ContentIntelligence.quality_status QualityStatus enum/literal validation & reject policy.
- SCHEMA-005 (ERR-017): AssetCheck.review_status DryRunReviewStatus enum/literal validation & reject policy.
- ERR-007: ScoreConsistencyRule BVA on float rounding drift tolerance (0.01 pass, 0.05 boundary, >0.05 fail).
- ERR-011: LocalStorage CP1252 smart quotes fallback decoding, warning observability, and enforced UTF-8 writes.
- ERR-018: 0-byte and truncated/malformed JSON handling across staged, scored, and analytics storage backends.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from content_creation.domains.content_intelligence.model import (
    ContentIntelligence,
    ContrastPair,
    EmotionalRegister,
    Hook,
    TopicType,
)
from content_creation.domains.content_intelligence.quality import QualityStatus
from content_creation.generation.brief import generate_brief
from content_creation.inference import InferenceManager, InferenceResult
from content_creation.manifest import ManifestBuilder
from content_creation.models.brief import Brief
from content_creation.models.calendar import PublishingConfigSnapshot, ScheduledPost, WeeklyCalendar
from content_creation.models.dryrun import AssetCheck, DryRunReport
from content_creation.models.review_history import ReviewHistoryEntry
from content_creation.models.topic import (
    ScoredTopicItem,
    TopicCategory,
    TopicItem,
    TopicMetadata,
    TopicStatus,
)
from content_creation.scoring.config import ValidationConfig
from content_creation.scoring.validation import ScoreConsistencyRule
from content_creation.shared.enums import ReviewStatus
from content_creation.storage.local import LocalStorage


# ============================================================================
# 1. ERR-005: Fallback Brief Generation & ManifestBuilder Defensive Filter
# ============================================================================

class TestBriefFallbackAndManifestDefense:
    """Covers ERR-005: Brief fallback format integrity and ManifestBuilder filter observability."""

    @pytest.fixture
    def scored_item_fixture(self) -> ScoredTopicItem:
        return ScoredTopicItem(
            id="topic-qa-001",
            title="Transformer Attention Optimizations",
            url="https://arxiv.org/abs/2601.00001",
            source="arxiv",
            published_at="2026-05-01T12:00:00Z",
            raw_text="A comprehensive investigation into flash attention mechanics and KV cache quantization for LLMs. " * 3,
            category=TopicCategory.PAPER,
            priority_score=85.0,
        )

    def test_fallback_brief_generates_valid_short_video_without_leak(self, tmp_path, scored_item_fixture):
        """Covers ERR-005: verify fallback generator populates recommended_formats=['short_video'] instead of 'needs_review'."""
        prompt_file = tmp_path / "summarize.md"
        prompt_file.write_text("Summarize {{ topic.title }} from {{ topic.source }}: {{ topic.raw_text }}", encoding="utf-8")

        mock_failed_result = InferenceResult(
            success=False,
            text="",
            error="Simulated upstream quota exhaustion (429)",
            provider="mock",
            model="mock",
            retries=0,
            duration_seconds=0.1,
        )

        with patch("content_creation.generation.brief.InferenceManager") as mock_mgr_cls:
            mock_mgr = MagicMock()
            mock_mgr.generate.return_value = mock_failed_result
            mock_mgr_cls.return_value = mock_mgr

            fallback_brief = generate_brief(scored_item_fixture, prompt_path=prompt_file)

        assert isinstance(fallback_brief, Brief)
        assert fallback_brief.topic_id == scored_item_fixture.id
        assert fallback_brief.review_status == ReviewStatus.NEEDS_REVIEW
        assert fallback_brief.recommended_formats == ["short_video"]
        assert "needs_review" not in fallback_brief.recommended_formats
        assert fallback_brief.why_it_matters == "needs_review"
        assert len(fallback_brief.plain_english_summary) == 3

    def test_fallback_brief_triggered_by_malformed_json_response(self, tmp_path, scored_item_fixture):
        """Covers ERR-005 / RISK-002: malformed LLM response triggers clean fallback with valid format list."""
        prompt_file = tmp_path / "summarize.md"
        prompt_file.write_text("Summarize: {{ topic.raw_text }}", encoding="utf-8")

        mock_malformed_result = InferenceResult(
            success=True,
            text="```json\n{\n  unquoted_key: 'malformed_value',\n  trailing_comma: True,\n",  # Invalid JSON
            error=None,
            provider="mock",
            model="mock",
            retries=0,
            duration_seconds=0.1,
        )

        with patch("content_creation.generation.brief.InferenceManager") as mock_mgr_cls:
            mock_mgr = MagicMock()
            mock_mgr.generate.return_value = mock_malformed_result
            mock_mgr_cls.return_value = mock_mgr

            fallback_brief = generate_brief(scored_item_fixture, prompt_path=prompt_file)

        assert fallback_brief.recommended_formats == ["short_video"]
        assert "needs_review" not in fallback_brief.recommended_formats

    @pytest.mark.parametrize("status_val", ["needs_review", "NEEDS_REVIEW", "  needs_review  ", "draft", "approved", "rejected", "reviewed"])
    def test_manifest_builder_filters_all_review_status_leak_variants(self, tmp_path, caplog, status_val):
        """Covers ERR-005: defensive filter in ManifestBuilder logs WARNING and prevents review status leakage."""
        storage = LocalStorage(tmp_path)
        topic_id = f"test-topic-{abs(hash(status_val))}"
        brief_data = {
            "topic_id": topic_id,
            "recommended_formats": [status_val],
        }
        brief_file = storage.briefs_dir / f"{topic_id}.json"
        brief_file.write_text(json.dumps(brief_data), encoding="utf-8")

        builder = ManifestBuilder(storage)

        with caplog.at_level(logging.WARNING):
            asset_types = builder._recommended_asset_types(topic_id)

        # Filters leaked review status and cleanly falls back to short_video
        assert "script" in asset_types  # short_video maps to script
        assert not any(status_val.strip().lower() == a for a in asset_types)

        # Warning observability check: must be logged at WARNING level
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            f"Filtered review status '{status_val.strip()}'" in r.message
            and topic_id in r.message
            for r in warning_records
        )

    def test_manifest_builder_preserves_valid_formats_in_mixed_list(self, tmp_path, caplog):
        """Covers ERR-005: mixed list filters review status with WARNING while preserving valid formats."""
        storage = LocalStorage(tmp_path)
        topic_id = "test-topic-mixed"
        brief_data = {
            "topic_id": topic_id,
            "recommended_formats": ["needs_review", "carousel", "newsletter"],
        }
        brief_file = storage.briefs_dir / f"{topic_id}.json"
        brief_file.write_text(json.dumps(brief_data), encoding="utf-8")

        builder = ManifestBuilder(storage)

        with caplog.at_level(logging.WARNING):
            asset_types = builder._recommended_asset_types(topic_id)

        assert "carousel" in asset_types
        assert "newsletter" in asset_types
        # Valid formats were present, so short_video fallback was not triggered
        assert "script" not in asset_types

        # Warning must still be logged for the filtered element
        assert any("Filtered review status 'needs_review'" in r.message for r in caplog.records)

    @pytest.mark.parametrize("corrupt_input", [
        [None, 123, 45.67],
        ["", "   "],
        [],
    ])
    def test_manifest_builder_handles_non_string_and_empty_formats(self, tmp_path, corrupt_input):
        """Covers ERR-005 negative testing: non-string elements and empty lists default safely to short_video."""
        storage = LocalStorage(tmp_path)
        topic_id = f"test-topic-corrupt-{abs(hash(str(corrupt_input)))}"
        brief_data = {
            "topic_id": topic_id,
            "recommended_formats": corrupt_input,
        }
        brief_file = storage.briefs_dir / f"{topic_id}.json"
        brief_file.write_text(json.dumps(brief_data), encoding="utf-8")

        builder = ManifestBuilder(storage)

        asset_types = builder._recommended_asset_types(topic_id)
        assert asset_types == {"script"}  # short_video maps to script

    def test_manifest_builder_genuine_unknown_format_warning(self, tmp_path, caplog):
        """Covers ERR-005: genuine unknown formats log distinct 'Unknown format' warning."""
        storage = LocalStorage(tmp_path)
        topic_id = "test-topic-unknown"
        brief_data = {
            "topic_id": topic_id,
            "recommended_formats": ["hologram_projection"],
        }
        brief_file = storage.briefs_dir / f"{topic_id}.json"
        brief_file.write_text(json.dumps(brief_data), encoding="utf-8")

        builder = ManifestBuilder(storage)

        with caplog.at_level(logging.WARNING):
            asset_types = builder._recommended_asset_types(topic_id)

        assert asset_types == {"script"}
        assert any("Unknown format 'hologram_projection'" in r.message for r in caplog.records)


# ============================================================================
# 2. SCHEMA-001 / SCHEMA-002: TopicMetadata & TopicItem / ScoredTopicItem
# ============================================================================

class TestTopicMetadataAndItemSchema:
    """Covers SCHEMA-001 (ERR-013) & SCHEMA-002 (ERR-014): TopicMetadata typing and dict compatibility."""

    def test_topic_metadata_typed_and_dynamic_attributes(self):
        """Covers SCHEMA-001: TopicMetadata supports typed fields and dynamic extra attributes."""
        meta = TopicMetadata(
            source_type="arxiv_feed",
            feed_id="cs.CL",
            published_date="2026-05-01",
            recommended_formats=["short_video", "carousel"],
            student_usefulness_score=8.5,
            novelty_score=9.0,
            credibility_score=10.0,
            explainability_score=7.5,
            hook_potential_score=8.0,
            custom_pipeline_id="pipe-42",  # dynamic extra
        )

        # 1. Typed attribute access
        assert meta.source_type == "arxiv_feed"
        assert meta.feed_id == "cs.CL"
        assert meta.student_usefulness_score == 8.5

        # 2. Dict-like indexing access
        assert meta["source_type"] == "arxiv_feed"
        assert meta["feed_id"] == "cs.CL"
        assert meta["custom_pipeline_id"] == "pipe-42"

        # 3. get() method with defaults
        assert meta.get("source_type") == "arxiv_feed"
        assert meta.get("custom_pipeline_id") == "pipe-42"
        assert meta.get("nonexistent_key", "default_val") == "default_val"

        # 4. in operator
        assert "source_type" in meta
        assert "custom_pipeline_id" in meta
        assert "nonexistent_key" not in meta
        assert 123 not in meta

    def test_topic_metadata_mutation_and_keyerror(self):
        """Covers SCHEMA-001: __setitem__ adds/updates fields and __getitem__ raises KeyError on missing keys."""
        meta = TopicMetadata()

        # Set declared attribute via dict syntax
        meta["source_type"] = "rss"
        assert meta.source_type == "rss"
        assert meta["source_type"] == "rss"

        # Set extra dynamic attribute via dict syntax
        meta["extra_metric"] = 99.9
        assert meta["extra_metric"] == 99.9
        assert "extra_metric" in meta

        # Missing key raises KeyError
        with pytest.raises(KeyError):
            _ = meta["missing_nonexistent_key"]

    def test_topic_item_roundtrip_preserves_extra_metadata_fields(self):
        """Covers SCHEMA-001: TopicItem JSON round-trip retains extra metadata attributes."""
        url = "https://example.com/research/paper-1"
        item = TopicItem(
            id=TopicItem.generate_id(url),
            title="Deep Residual Learning",
            url=url,
            source="arxiv",
            published_at="2026-05-01T10:00:00Z",
            raw_text="Deep residual networks are easier to optimize and gain accuracy from increased depth. " * 3,
            metadata=TopicMetadata(
                source_type="deep_learning",
                feed_id="feed-99",
                extra_batch_id="batch-2026-05",
                embedding_vector=[0.12, 0.45, 0.78],
            ),
        )

        # Round-trip through JSON string
        json_data = item.model_dump_json()
        reconstituted = TopicItem.model_validate_json(json_data)

        assert isinstance(reconstituted.metadata, TopicMetadata)
        assert reconstituted.metadata.source_type == "deep_learning"
        assert reconstituted.metadata["extra_batch_id"] == "batch-2026-05"
        assert reconstituted.metadata["embedding_vector"] == [0.12, 0.45, 0.78]

    def test_scored_topic_item_inherits_topic_metadata_cleanly(self):
        """Covers SCHEMA-002 (ERR-014): ScoredTopicItem uses typed TopicMetadata with dynamic persistence."""
        url = "https://example.com/ai/scored-paper"
        scored = ScoredTopicItem(
            id=TopicItem.generate_id(url),
            title="Attention Is All You Need",
            url=url,
            source="arxiv",
            published_at="2026-05-02T12:00:00Z",
            raw_text="The dominant sequence transduction models are based on complex recurrent or convolutional networks. " * 3,
            priority_score=92.5,
            student_usefulness_score=18.5,
            novelty_score=18.5,
            credibility_score=18.5,
            explainability_score=18.5,
            hook_potential_score=18.5,
            metadata={
                "source_type": "seminal_paper",
                "custom_evaluator": "gpt-4o-auditor",
                "cluster_label": "nlp_transformers",
            },
        )

        assert isinstance(scored.metadata, TopicMetadata)
        assert scored.metadata.source_type == "seminal_paper"
        assert scored.metadata["custom_evaluator"] == "gpt-4o-auditor"
        assert scored.metadata.get("cluster_label") == "nlp_transformers"

        # Dump to dictionary and validate schema reconstruction
        dumped = scored.model_dump()
        reloaded = ScoredTopicItem.model_validate(dumped)
        assert isinstance(reloaded.metadata, TopicMetadata)
        assert reloaded.metadata["custom_evaluator"] == "gpt-4o-auditor"

    @pytest.mark.parametrize("priority_val,is_valid", [
        (-0.01, False),
        (0.0, True),
        (50.0, True),
        (100.0, True),
        (100.01, False),
    ])
    def test_scored_topic_item_priority_score_bva(self, priority_val, is_valid):
        """Covers BVA on ScoredTopicItem priority_score bounds [0.0, 100.0]."""
        base_kwargs = dict(
            id="t-bva",
            title="BVA Topic",
            url="https://example.com/bva",
            source="arxiv",
            published_at="2026-05-01T12:00:00Z",
            raw_text="Content for testing boundary value analysis on score fields. " * 3,
            priority_score=priority_val,
        )
        if is_valid:
            item = ScoredTopicItem(**base_kwargs)
            assert item.priority_score == priority_val
        else:
            with pytest.raises(ValidationError):
                ScoredTopicItem(**base_kwargs)

    def test_topic_storage_roundtrip_with_extra_metadata(self, tmp_path):
        """Covers SCHEMA-001 & SCHEMA-002: LocalStorage saves and loads staged/scored items preserving extra metadata."""
        storage = LocalStorage(tmp_path)
        url = "https://example.com/staged-and-scored"
        topic_id = TopicItem.generate_id(url)

        item = TopicItem(
            id=topic_id,
            title="RLHF Alignment Frontiers",
            url=url,
            source="rss",
            published_at="2026-05-01T10:00:00Z",
            raw_text="Direct Preference Optimization and Reinforcement Learning from Human Feedback mechanics. " * 3,
            metadata=TopicMetadata(
                source_type="alignment",
                extra_run_id="run-007",
                annotator_flags=["verified", "high_interest"],
            ),
        )

        storage.save_staged(item)
        loaded_staged = storage.get_staged(topic_id)
        assert loaded_staged is not None
        assert isinstance(loaded_staged.metadata, TopicMetadata)
        assert loaded_staged.metadata.source_type == "alignment"
        assert loaded_staged.metadata["extra_run_id"] == "run-007"
        assert loaded_staged.metadata["annotator_flags"] == ["verified", "high_interest"]

        # Save scored variant
        scored = ScoredTopicItem(
            **item.model_dump(),
            priority_score=88.0,
            student_usefulness_score=17.6,
            novelty_score=17.6,
            credibility_score=17.6,
            explainability_score=17.6,
            hook_potential_score=17.6,
        )
        storage.save_scored(scored)
        loaded_scored = storage.get_scored(topic_id)
        assert loaded_scored is not None
        assert isinstance(loaded_scored.metadata, TopicMetadata)
        assert loaded_scored.metadata["extra_run_id"] == "run-007"


# ============================================================================
# 3. SCHEMA-003: PublishingConfigSnapshot & WeeklyCalendar
# ============================================================================

class TestPublishingConfigSnapshotAndCalendar:
    """Covers SCHEMA-003 (ERR-015): PublishingConfigSnapshot typing, dict compatibility, and calendar persistence."""

    def test_publishing_config_snapshot_typed_access_and_dict_compatibility(self):
        """Covers SCHEMA-003: PublishingConfigSnapshot supports typed fields and dict accessor methods."""
        snapshot = PublishingConfigSnapshot(
            weekly_targets={"short_video": 3, "carousel": 2},
            scheduling_rules={"max_per_day": 2, "time_slots_utc": "09:00,15:00"},
            diversity_rules={"max_per_source": 1},
            custom_feature_flag=True,  # dynamic extra
        )

        # 1. Attribute access
        assert snapshot.weekly_targets == {"short_video": 3, "carousel": 2}
        assert snapshot.scheduling_rules["max_per_day"] == 2

        # 2. Dict-like indexing
        assert snapshot["weekly_targets"] == {"short_video": 3, "carousel": 2}
        assert snapshot["custom_feature_flag"] is True

        # 3. get() method
        assert snapshot.get("diversity_rules") == {"max_per_source": 1}
        assert snapshot.get("custom_feature_flag") is True
        assert snapshot.get("nonexistent_option", "fallback") == "fallback"

        # 4. in operator
        assert "weekly_targets" in snapshot
        assert "custom_feature_flag" in snapshot
        assert "nonexistent_option" not in snapshot
        assert 42 not in snapshot

    def test_publishing_config_snapshot_mutation_and_keyerror(self):
        """Covers SCHEMA-003: mutation via __setitem__ and KeyError on unknown keys."""
        snapshot = PublishingConfigSnapshot()

        snapshot["weekly_targets"] = {"newsletter": 1}
        assert snapshot.weekly_targets == {"newsletter": 1}

        snapshot["custom_queue_priority"] = "high"
        assert snapshot["custom_queue_priority"] == "high"
        assert "custom_queue_priority" in snapshot

        with pytest.raises(KeyError):
            _ = snapshot["unknown_missing_rule"]

    def test_weekly_calendar_storage_roundtrip_with_config_snapshot_mutations(self, tmp_path):
        """Covers SCHEMA-003: WeeklyCalendar with PublishingConfigSnapshot round-trips via LocalStorage."""
        storage = LocalStorage(tmp_path)

        calendar = WeeklyCalendar(
            week_start="2026-05-18",
            week_end="2026-05-24",
            total_posts=1,
            posts=[
                ScheduledPost(
                    day=1,
                    date="2026-05-18",
                    topic_id="top-01",
                    topic_title="Topic 1",
                    format="short_video",
                    asset_path="data/scripts/top-01.json",
                    source_url="https://arxiv.org/abs/2605.00001",
                    scheduled_at="2026-05-17T08:00:00Z",
                )
            ],
            format_counts={"short_video": 1},
            topics_used=["top-01"],
            generated_at="2026-05-17T08:00:00Z",
            config_snapshot=PublishingConfigSnapshot(
                weekly_targets={"short_video": 3},
                diversity_rules={"max_per_source": 2},
                runtime_experiment="adaptive_scheduling_v2",
            ),
        )

        saved_path = storage.save_calendar(calendar)
        assert saved_path.exists()

        calendars = storage.list_calendars()
        assert len(calendars) == 1
        loaded = calendars[0]

        assert isinstance(loaded.config_snapshot, PublishingConfigSnapshot)
        assert loaded.config_snapshot.weekly_targets == {"short_video": 3}
        assert loaded.config_snapshot["runtime_experiment"] == "adaptive_scheduling_v2"
        assert loaded.config_snapshot.get("runtime_experiment") == "adaptive_scheduling_v2"

        # Mutate config snapshot and re-save
        loaded.config_snapshot["ab_variant"] = "B"
        storage.save_calendar(loaded)

        reloaded = storage.list_calendars()[0]
        assert reloaded.config_snapshot["ab_variant"] == "B"


# ============================================================================
# 4. SCHEMA-004: ContentIntelligence.quality_status Enum / Literal Typing
# ============================================================================

class TestContentIntelligenceQualityStatus:
    """Covers SCHEMA-004 (ERR-016): ContentIntelligence.quality_status validation policy."""

    @pytest.fixture
    def base_ci_kwargs(self) -> Dict[str, Any]:
        return dict(
            topic_id="ci-test-01",
            generated_at="2026-05-01T12:00:00Z",
            topic_type=TopicType.PAPER,
            timeliness_hook="Breaking breakthrough in attention mechanisms",
            primary_hook=Hook(hook_text="Did you know transformers can run 10x faster?", hook_type="question", source_field="summary"),
            secondary_hook=Hook(hook_text="KV cache compression breaks latency records.", hook_type="bold_claim", source_field="takeaway"),
            story_angle="Engineering efficiency meets theoretical elegance.",
            curiosity_gap="How can sub-quadratic attention maintain 100% perplexity scores?",
            contrast_pair=ContrastPair(before="Slow quadratic O(N^2) memory footprint", after="Linear memory streaming inference"),
            emotional_register=EmotionalRegister.AWE,
        )

    @pytest.mark.parametrize("status_val,expected_enum", [
        (QualityStatus.READY, QualityStatus.READY),
        (QualityStatus.DEGRADED, QualityStatus.DEGRADED),
        (QualityStatus.BLOCKED, QualityStatus.BLOCKED),
        ("ready", QualityStatus.READY),
        ("degraded", QualityStatus.DEGRADED),
        ("blocked", QualityStatus.BLOCKED),
        (None, None),
    ])
    def test_content_intelligence_quality_status_valid_variants(self, base_ci_kwargs, status_val, expected_enum):
        """Covers SCHEMA-004: valid QualityStatus enums, lowercase literal strings, and None pass validation."""
        ci = ContentIntelligence(**base_ci_kwargs, quality_status=status_val)
        assert ci.quality_status == expected_enum

    @pytest.mark.parametrize("invalid_status", [
        "READY",  # uppercase string not matching enum value
        "pending",
        "approved",
        "rejected",
        "unknown",
        "in_review",
        "",
        123,
        True,
        ["ready"],
    ])
    def test_content_intelligence_quality_status_invalid_variants_reject(self, base_ci_kwargs, invalid_status):
        """Covers SCHEMA-004: unvalidated arbitrary strings or invalid types raise ValidationError."""
        with pytest.raises(ValidationError):
            ContentIntelligence(**base_ci_kwargs, quality_status=invalid_status)

    def test_content_intelligence_storage_roundtrip(self, tmp_path, base_ci_kwargs):
        """Covers SCHEMA-004: ContentIntelligence with typed quality_status persists and reloads cleanly."""
        storage = LocalStorage(tmp_path)
        ci = ContentIntelligence(**base_ci_kwargs, quality_status="degraded")

        storage.save_content_intelligence(ci)
        loaded_list = storage.list_content_intelligence()

        assert len(loaded_list) == 1
        loaded_ci = loaded_list[0]
        assert loaded_ci.quality_status == QualityStatus.DEGRADED
        assert loaded_ci.topic_id == "ci-test-01"


# ============================================================================
# 5. SCHEMA-005: AssetCheck.review_status Enum / Literal Typing
# ============================================================================

class TestDryRunAssetCheckReviewStatus:
    """Covers SCHEMA-005 (ERR-017): AssetCheck.review_status validation policy."""

    @pytest.fixture
    def base_check_kwargs(self) -> Dict[str, Any]:
        return dict(
            topic_id="top-dryrun-01",
            topic_title="Self-Supervised Vision Transformers",
            format="short_video",
            asset_path="data/scripts/top-dryrun-01.json",
            is_ready=False,
        )

    @pytest.mark.parametrize("valid_status", [
        ReviewStatus.DRAFT,
        ReviewStatus.NEEDS_REVIEW,
        ReviewStatus.REVIEWED,
        ReviewStatus.APPROVED,
        ReviewStatus.REJECTED,
        "draft",
        "needs_review",
        "reviewed",
        "approved",
        "rejected",
        "missing",
        "error",
        "unknown",
    ])
    def test_asset_check_review_status_valid_variants(self, base_check_kwargs, valid_status):
        """Covers SCHEMA-005: all ReviewStatus enum members and literal strings ('missing', 'error', 'unknown') pass."""
        check = AssetCheck(**base_check_kwargs, review_status=valid_status)
        if isinstance(valid_status, ReviewStatus):
            assert check.review_status == valid_status
        else:
            # String input maps to ReviewStatus enum or literal string
            expected = ReviewStatus(valid_status) if valid_status in ReviewStatus._value2member_map_ else valid_status
            assert check.review_status == expected

    @pytest.mark.parametrize("invalid_status", [
        "skipped",
        "published",
        "pending",
        "in_progress",
        "passed",
        "failed",
        "",
        123,
        None,  # review_status is non-optional
    ])
    def test_asset_check_review_status_invalid_variants_reject(self, base_check_kwargs, invalid_status):
        """Covers SCHEMA-005: arbitrary unvalidated string values or None raise ValidationError."""
        with pytest.raises(ValidationError):
            AssetCheck(**base_check_kwargs, review_status=invalid_status)

    def test_dryrun_report_storage_roundtrip(self, tmp_path, base_check_kwargs):
        """Covers SCHEMA-005: DryRunReport with constrained AssetCheck items round-trips via LocalStorage."""
        storage = LocalStorage(tmp_path)

        check1_kwargs = dict(base_check_kwargs, is_ready=True, review_status=ReviewStatus.APPROVED)
        check1 = AssetCheck(**check1_kwargs)
        check2 = AssetCheck(
            topic_id="top-dryrun-02",
            topic_title="Multimodal Fusion",
            format="carousel",
            asset_path="data/carousels/top-dryrun-02.json",
            review_status="missing",
            is_ready=False,
            warning="Carousel artifact not generated on disk",
        )

        report = DryRunReport(
            week_start="2026-05-18",
            week_end="2026-05-24",
            total_scheduled=2,
            ready_count=1,
            warning_count=0,
            blocked_count=1,
            checks=[check1, check2],
            warnings=["Missing carousel asset for topic top-dryrun-02"],
            recommended_actions=["Generate missing carousel before publishing"],
            generated_at="2026-05-17T12:00:00Z",
        )

        saved_path = storage.save_dryrun(report)
        assert saved_path.exists()

        reports = storage.list_dryruns()
        assert len(reports) == 1
        loaded = reports[0]

        assert loaded.checks[0].review_status == ReviewStatus.APPROVED
        assert loaded.checks[0].is_ready is True
        assert loaded.checks[1].review_status == "missing"
        assert loaded.checks[1].is_ready is False


# ============================================================================
# 6. ERR-007: ScoreConsistencyRule Float Rounding Drift Tolerance (BVA)
# ============================================================================

class TestScoreConsistencyRuleBVA:
    """Covers ERR-007: ScoreConsistencyRule tolerance threshold and boundary value analysis."""

    @pytest.fixture
    def base_item(self) -> ScoredTopicItem:
        return ScoredTopicItem(
            id="score-item-01",
            title="Boundary Value Topic",
            url="https://example.com/bva-topic",
            source="arxiv",
            published_at="2026-05-01T12:00:00Z",
            raw_text="Text content for testing scoring consistency rule floating point tolerance. " * 3,
            category=TopicCategory.PAPER,
            priority_score=50.0,
            student_usefulness_score=10.0,
            novelty_score=10.0,
            credibility_score=10.0,
            explainability_score=10.0,
            hook_potential_score=10.0,  # sum of components = 50.00
        )

    @pytest.mark.parametrize("priority_val,expected_warning", [
        (50.00, False),  # Exact match (delta = 0.00)
        (50.01, False),  # Harmless float rounding delta (delta = 0.01)
        (49.99, False),  # Negative rounding delta (delta = 0.01)
        (50.049, False), # Just below upper boundary of 0.05
        (50.050, False), # Exact upper boundary (delta = 0.05) -> passes <= 0.05
        (49.950, False), # Exact lower boundary (delta = -0.05) -> passes
        (50.051, True),  # Just above boundary (delta = 0.051) -> flags inconsistency
        (49.949, True),  # Just below lower boundary (delta = -0.051) -> flags inconsistency
        (50.10, True),   # Significant positive drift -> flags inconsistency
        (49.00, True),   # Significant negative drift -> flags inconsistency
        (75.00, True),   # Massive score mismatch -> flags inconsistency
    ])
    def test_score_consistency_rule_drift_bva(self, base_item, priority_val, expected_warning):
        """Covers ERR-007 BVA: drift <= 0.05 passes cleanly, drift > 0.05 flags Score inconsistency."""
        rule = ScoreConsistencyRule(ValidationConfig(check_consistency=True))
        base_item.priority_score = priority_val

        warning = rule.validate(base_item)
        if expected_warning:
            assert warning is not None
            assert "Score inconsistency" in warning
        else:
            assert warning is None

    def test_score_consistency_rule_disabled_when_config_false(self, base_item):
        """Covers ERR-007: consistency check skips validation when check_consistency=False."""
        rule = ScoreConsistencyRule(ValidationConfig(check_consistency=False))
        base_item.priority_score = 99.9  # Massive delta from component sum 50.0
        assert rule.validate(base_item) is None

    def test_score_consistency_rule_with_none_excerpt(self, base_item):
        """Covers ERR-007 robustness: ScoredTopicItem handles None or unknown excerpt without crashing validator."""
        rule = ScoreConsistencyRule(ValidationConfig(check_consistency=True))
        base_item.excerpt = "unknown"
        assert rule.validate(base_item) is None


# ============================================================================
# 7. ERR-011: LocalStorage CP1252 Fallback Decoding & UTF-8 Write Enforcement
# ============================================================================

class TestLocalStorageEncodingAndSmartQuotes:
    """Covers ERR-011: UTF-8 primary read, CP1252 smart quotes fallback, and explicit UTF-8 on writes."""

    def test_read_json_clean_utf8_does_not_log_fallback_warning(self, tmp_path, caplog):
        """Covers ERR-011: clean UTF-8 JSON file decodes without invoking CP1252 fallback or logging warning."""
        storage = LocalStorage(tmp_path)
        file_path = storage.staged_dir / "clean_utf8.json"

        payload = {"id": "clean_utf8", "title": "Standard ASCII and UTF-8 Title: 🚀"}
        file_path.write_text(json.dumps(payload), encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            data = storage._read_json(file_path)

        assert data["id"] == "clean_utf8"
        assert "🚀" in data["title"]
        assert not any("falling back to cp1252" in r.message for r in caplog.records)

    def test_read_json_cp1252_smart_punctuation_suite(self, tmp_path, caplog):
        """Covers ERR-011: CP1252 smart quotes (0x93, 0x94, 0x91, 0x92) and dashes (0x96, 0x97) decode with warning."""
        storage = LocalStorage(tmp_path)
        file_path = storage.staged_dir / "cp1252_smart_chars.json"

        # Byte sequences containing Windows-1252 smart punctuation:
        # \x93 (left double quote), \x94 (right double quote)
        # \x91 (left single quote), \x92 (right single quote)
        # \x96 (en-dash), \x97 (em-dash), \x85 (ellipsis)
        raw_text_content = "\u201cAI Breakthrough\u201d \u2014 \u2018Next-Gen\u2019 Models 2024\u20132026\u2026"
        json_str = (
            '{\n'
            f'  "id": "cp1252_smart",\n'
            f'  "title": "{raw_text_content}",\n'
            '  "url": "https://example.com/cp1252",\n'
            '  "source": "rss",\n'
            '  "published_at": "2026-05-01T12:00:00Z",\n'
            f'  "raw_text": "{raw_text_content} repeated content for length requirement."\n'
            '}'
        )

        encoded_cp1252_bytes = json_str.encode("cp1252")
        file_path.write_bytes(encoded_cp1252_bytes)

        with caplog.at_level(logging.WARNING):
            data = storage._read_json(file_path)

        # Assert successful decoding through fallback
        assert data["id"] == "cp1252_smart"
        assert "AI Breakthrough" in data["title"]

        # Assert warning log observability
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("falling back to cp1252" in r.message for r in warning_records)

    def test_storage_write_methods_enforce_utf8(self, tmp_path):
        """Covers ERR-011: storage writes enforce UTF-8 encoding across staged, scored, and review history."""
        storage = LocalStorage(tmp_path)
        url = "https://example.com/utf8-write-test"
        topic_id = TopicItem.generate_id(url)

        # 1. TopicItem write
        unicode_title = "“Quantum Computing” — 🚀 ニューラルネットワーク"
        item = TopicItem(
            id=topic_id,
            title=unicode_title,
            url=url,
            source="rss",
            published_at="2026-05-01T10:00:00Z",
            raw_text="Rich UTF-8 content with Japanese characters: 自然言語処理. " * 3,
        )
        storage.save_staged(item)

        staged_file = storage.staged_dir / f"{topic_id}.json"
        raw_bytes = staged_file.read_bytes()
        # Verify bytes are valid UTF-8 and contain decoded Japanese / emoji strings
        decoded_content = raw_bytes.decode("utf-8")
        assert unicode_title in decoded_content

        # 2. Review history write
        history_entry = ReviewHistoryEntry(
            topic_id=topic_id,
            asset_type="brief",
            action="approve",
            previous_status=ReviewStatus.DRAFT,
            new_status=ReviewStatus.APPROVED,
            timestamp="2026-05-01T12:00:00Z",
            notes="“Approved with high distinction” — Excellent work 🌟",
        )
        storage.save_review_history_entry(history_entry)

        history_file = storage.review_history_dir / f"{topic_id}.json"
        history_bytes = history_file.read_bytes()
        history_decoded = history_bytes.decode("utf-8")
        assert "Approved with high distinction" in history_decoded
        # Verify unicode content preserves cleanly when reloaded via domain storage
        loaded_history = storage.get_review_history(topic_id)
        assert len(loaded_history) == 1
        assert loaded_history[0].notes == "“Approved with high distinction” — Excellent work 🌟"


# ============================================================================
# 8. ERR-018: 0-Byte and Truncated/Malformed JSON Storage Handling
# ============================================================================

class TestCorruptAndZeroByteFiles:
    """Covers ERR-018 (and ERR-006): resilient handling of 0-byte or corrupted JSON files in local storage."""

    def test_list_staged_handles_zero_byte_file_gracefully(self, tmp_path, caplog):
        """Covers ERR-018: 0-byte JSON file in staged directory logs error and does not abort batch sweep."""
        storage = LocalStorage(tmp_path)

        # Write 1 valid staged item
        valid_item = TopicItem(
            id="valid-topic-01",
            title="Valid Topic",
            url="https://example.com/valid",
            source="arxiv",
            published_at="2026-05-01T12:00:00Z",
            raw_text="Valid text content exceeding one hundred characters requirement for normalization testing. " * 2,
        )
        storage.save_staged(valid_item)

        # Write 1 zero-byte corrupted file in staged_dir
        zero_byte_file = storage.staged_dir / "05738f6c55b7147880500b666d1a96e73b80de79c9a4453c521b0ffc55549d70.json"
        zero_byte_file.write_bytes(b"")

        with caplog.at_level(logging.WARNING):
            items = storage.list_staged()

        # Batch sweep continues and returns the valid item
        assert len(items) == 1
        assert items[0].id == "valid-topic-01"

        # Warning/error is logged for the 0-byte file
        assert any(
            "Failed to load staged item" in r.message
            and "05738f6c" in r.message
            for r in caplog.records
        )

    def test_get_staged_handles_zero_byte_file(self, tmp_path, caplog):
        """Covers ERR-018: get_staged on a 0-byte file returns None without unhandled exception."""
        storage = LocalStorage(tmp_path)
        empty_id = "empty-staged-id"
        empty_file = storage.staged_dir / f"{empty_id}.json"
        empty_file.write_bytes(b"")

        with caplog.at_level(logging.ERROR):
            result = storage.get_staged(empty_id)

        assert result is None
        assert any("Failed to load staged item" in r.message for r in caplog.records)

    def test_list_and_get_scored_handles_zero_byte_file(self, tmp_path, caplog):
        """Covers ERR-018: 0-byte JSON in scored directory logs warning and returns None without crash."""
        storage = LocalStorage(tmp_path)
        empty_id = "empty-scored-id"
        empty_file = storage.scored_dir / f"{empty_id}.json"
        empty_file.write_bytes(b"")

        with caplog.at_level(logging.WARNING):
            scored_list = storage.list_scored()
            scored_item = storage.get_scored(empty_id)

        assert scored_list == []
        assert scored_item is None
        assert any("Failed to load scored item" in r.message for r in caplog.records)

    def test_list_and_get_analytics_handles_zero_byte_file(self, tmp_path, caplog):
        """Covers ERR-018: 0-byte JSON in analytics directory logs warning and returns None."""
        storage = LocalStorage(tmp_path)
        empty_id = "empty-analytics-id"
        empty_file = storage.analytics_dir / f"{empty_id}.json"
        empty_file.write_bytes(b"")

        with caplog.at_level(logging.WARNING):
            analytics_list = storage.list_analytics()
            analytics_item = storage.get_analytics(empty_id)

        assert analytics_list == []
        assert analytics_item is None
        assert any("Failed to load analytics" in r.message for r in caplog.records)

    def test_list_staged_handles_corrupt_non_dict_json(self, tmp_path, caplog):
        """Covers ERR-018: JSON array or literal in staged directory is handled without crashing batch sweep."""
        storage = LocalStorage(tmp_path)
        array_file = storage.staged_dir / "array_payload.json"
        array_file.write_text("[1, 2, 3]", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            items = storage.list_staged()

        assert items == []
        assert any("Failed to load staged item" in r.message for r in caplog.records)

    def test_save_staged_deduplication_atomic_mode_x(self, tmp_path):
        """Covers idempotency & concurrency: mode 'x' raises FileExistsError on duplicate ingestion writes."""
        storage = LocalStorage(tmp_path)
        url = "https://example.com/duplicate-test"
        item = TopicItem(
            id=TopicItem.generate_id(url),
            title="Duplicate Test Topic",
            url=url,
            source="arxiv",
            published_at="2026-05-01T12:00:00Z",
            raw_text="Testing atomic creation with mode 'x' to ensure race condition safety during ingestion. " * 2,
        )

        storage.save_staged(item)
        assert storage.exists(item.id) is True

        # Second atomic write to same target path must raise FileExistsError
        with pytest.raises(FileExistsError):
            storage.save_staged(item)
