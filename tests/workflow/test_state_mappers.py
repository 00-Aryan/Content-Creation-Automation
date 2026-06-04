"""Tests for ArtifactLifecycleState, state mappers, and workflow convenience API."""

from pathlib import Path

import pytest

from content_creation.workflow.states import (
    ArtifactLifecycleState,
    TERMINAL_STATES,
    get_lifecycle_state,
    is_approvable,
    is_reviewable,
    is_terminal,
)
from content_creation.workflow.state_mappers import (
    ArtifactStateStatusMapper,
    AssetStatusMapper,
    ManifestStatusMapper,
    ReviewStatusMapper,
    TopicStatusMapper,
)


# =========================================================================
# ArtifactLifecycleState enum
# =========================================================================

class TestArtifactLifecycleState:
    """Verify the canonical enum has all expected values."""

    EXPECTED_VALUES = {
        "pending", "draft", "needs_review", "reviewed",
        "approved", "rejected", "missing", "skipped", "failed",
    }

    def test_has_all_values(self):
        actual = {s.value for s in ArtifactLifecycleState}
        assert actual == self.EXPECTED_VALUES

    def test_count(self):
        assert len(ArtifactLifecycleState) == 9

    def test_values_are_strings(self):
        for s in ArtifactLifecycleState:
            assert isinstance(s.value, str)

    def test_is_str_subclass(self):
        assert issubclass(ArtifactLifecycleState, str)


# =========================================================================
# Terminal states
# =========================================================================

class TestTerminalStates:
    """APPROVED, REJECTED, MISSING, SKIPPED are terminal."""

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {
            ArtifactLifecycleState.APPROVED,
            ArtifactLifecycleState.REJECTED,
            ArtifactLifecycleState.MISSING,
            ArtifactLifecycleState.SKIPPED,
        }

    def test_approved_is_terminal(self):
        assert is_terminal(ArtifactLifecycleState.APPROVED) is True

    def test_rejected_is_terminal(self):
        assert is_terminal(ArtifactLifecycleState.REJECTED) is True

    def test_missing_is_terminal(self):
        assert is_terminal(ArtifactLifecycleState.MISSING) is True

    def test_skipped_is_terminal(self):
        assert is_terminal(ArtifactLifecycleState.SKIPPED) is True

    def test_pending_is_not_terminal(self):
        assert is_terminal(ArtifactLifecycleState.PENDING) is False

    def test_draft_is_not_terminal(self):
        assert is_terminal(ArtifactLifecycleState.DRAFT) is False

    def test_needs_review_is_not_terminal(self):
        assert is_terminal(ArtifactLifecycleState.NEEDS_REVIEW) is False

    def test_reviewed_is_not_terminal(self):
        assert is_terminal(ArtifactLifecycleState.REVIEWED) is False

    def test_failed_is_not_terminal(self):
        assert is_terminal(ArtifactLifecycleState.FAILED) is False


# =========================================================================
# Reviewable states
# =========================================================================

class TestReviewableStates:
    """DRAFT, NEEDS_REVIEW, REVIEWED are reviewable."""

    def test_draft_is_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.DRAFT) is True

    def test_needs_review_is_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.NEEDS_REVIEW) is True

    def test_reviewed_is_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.REVIEWED) is True

    def test_pending_is_not_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.PENDING) is False

    def test_approved_is_not_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.APPROVED) is False

    def test_rejected_is_not_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.REJECTED) is False

    def test_missing_is_not_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.MISSING) is False

    def test_skipped_is_not_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.SKIPPED) is False

    def test_failed_is_not_reviewable(self):
        assert is_reviewable(ArtifactLifecycleState.FAILED) is False


# =========================================================================
# Approvable states
# =========================================================================

class TestApprovableStates:
    """DRAFT, NEEDS_REVIEW, REVIEWED are approvable."""

    def test_draft_is_approvable(self):
        assert is_approvable(ArtifactLifecycleState.DRAFT) is True

    def test_needs_review_is_approvable(self):
        assert is_approvable(ArtifactLifecycleState.NEEDS_REVIEW) is True

    def test_reviewed_is_approvable(self):
        assert is_approvable(ArtifactLifecycleState.REVIEWED) is True

    def test_pending_is_not_approvable(self):
        assert is_approvable(ArtifactLifecycleState.PENDING) is False

    def test_approved_is_not_approvable(self):
        assert is_approvable(ArtifactLifecycleState.APPROVED) is False

    def test_rejected_is_not_approvable(self):
        assert is_approvable(ArtifactLifecycleState.REJECTED) is False

    def test_missing_is_not_approvable(self):
        assert is_approvable(ArtifactLifecycleState.MISSING) is False

    def test_skipped_is_not_approvable(self):
        assert is_approvable(ArtifactLifecycleState.SKIPPED) is False

    def test_failed_is_not_approvable(self):
        assert is_approvable(ArtifactLifecycleState.FAILED) is False


# =========================================================================
# TopicStatusMapper
# =========================================================================

class TestTopicStatusMapper:
    """All 6 TopicStatus values map correctly."""

    def test_raw_maps_to_pending(self):
        assert TopicStatusMapper.to_lifecycle_state("raw") == ArtifactLifecycleState.PENDING

    def test_staged_maps_to_pending(self):
        assert TopicStatusMapper.to_lifecycle_state("staged") == ArtifactLifecycleState.PENDING

    def test_scored_maps_to_pending(self):
        assert TopicStatusMapper.to_lifecycle_state("scored") == ArtifactLifecycleState.PENDING

    def test_approved_maps_to_approved(self):
        assert TopicStatusMapper.to_lifecycle_state("approved") == ArtifactLifecycleState.APPROVED

    def test_rejected_maps_to_rejected(self):
        assert TopicStatusMapper.to_lifecycle_state("rejected") == ArtifactLifecycleState.REJECTED

    def test_review_maps_to_needs_review(self):
        assert TopicStatusMapper.to_lifecycle_state("review") == ArtifactLifecycleState.NEEDS_REVIEW

    def test_all_six_values_mapped(self):
        mapped = TopicStatusMapper.get_mapped_values()
        assert len(mapped) == 6

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError, match="Unknown TopicStatus"):
            TopicStatusMapper.to_lifecycle_state("nonexistent")


# =========================================================================
# ReviewStatusMapper
# =========================================================================

class TestReviewStatusMapper:
    """All 5 ReviewStatus values map correctly (1:1)."""

    def test_draft_maps_to_draft(self):
        assert ReviewStatusMapper.to_lifecycle_state("draft") == ArtifactLifecycleState.DRAFT

    def test_needs_review_maps_to_needs_review(self):
        assert ReviewStatusMapper.to_lifecycle_state("needs_review") == ArtifactLifecycleState.NEEDS_REVIEW

    def test_reviewed_maps_to_reviewed(self):
        assert ReviewStatusMapper.to_lifecycle_state("reviewed") == ArtifactLifecycleState.REVIEWED

    def test_approved_maps_to_approved(self):
        assert ReviewStatusMapper.to_lifecycle_state("approved") == ArtifactLifecycleState.APPROVED

    def test_rejected_maps_to_rejected(self):
        assert ReviewStatusMapper.to_lifecycle_state("rejected") == ArtifactLifecycleState.REJECTED

    def test_all_five_values_mapped(self):
        mapped = ReviewStatusMapper.get_mapped_values()
        assert len(mapped) == 5

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError, match="Unknown ReviewStatus"):
            ReviewStatusMapper.to_lifecycle_state("nonexistent")


# =========================================================================
# AssetStatusMapper
# =========================================================================

class TestAssetStatusMapper:
    """All 7 AssetEntry.status values map correctly."""

    def test_draft_maps_to_draft(self):
        assert AssetStatusMapper.to_lifecycle_state("draft") == ArtifactLifecycleState.DRAFT

    def test_needs_review_maps_to_needs_review(self):
        assert AssetStatusMapper.to_lifecycle_state("needs_review") == ArtifactLifecycleState.NEEDS_REVIEW

    def test_reviewed_maps_to_reviewed(self):
        assert AssetStatusMapper.to_lifecycle_state("reviewed") == ArtifactLifecycleState.REVIEWED

    def test_approved_maps_to_approved(self):
        assert AssetStatusMapper.to_lifecycle_state("approved") == ArtifactLifecycleState.APPROVED

    def test_rejected_maps_to_rejected(self):
        assert AssetStatusMapper.to_lifecycle_state("rejected") == ArtifactLifecycleState.REJECTED

    def test_missing_maps_to_missing(self):
        assert AssetStatusMapper.to_lifecycle_state("missing") == ArtifactLifecycleState.MISSING

    def test_skipped_maps_to_skipped(self):
        assert AssetStatusMapper.to_lifecycle_state("skipped") == ArtifactLifecycleState.SKIPPED

    def test_all_seven_values_mapped(self):
        mapped = AssetStatusMapper.get_mapped_values()
        assert len(mapped) == 7

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError, match="Unknown AssetEntry status"):
            AssetStatusMapper.to_lifecycle_state("nonexistent")


# =========================================================================
# ArtifactStateStatusMapper
# =========================================================================

class TestArtifactStateStatusMapper:
    """All 4 ArtifactState.status values map correctly."""

    def test_pending_maps_to_pending(self):
        assert ArtifactStateStatusMapper.to_lifecycle_state("pending") == ArtifactLifecycleState.PENDING

    def test_completed_maps_to_approved(self):
        assert ArtifactStateStatusMapper.to_lifecycle_state("completed") == ArtifactLifecycleState.APPROVED

    def test_failed_maps_to_failed(self):
        assert ArtifactStateStatusMapper.to_lifecycle_state("failed") == ArtifactLifecycleState.FAILED

    def test_needs_review_maps_to_needs_review(self):
        assert ArtifactStateStatusMapper.to_lifecycle_state("needs_review") == ArtifactLifecycleState.NEEDS_REVIEW

    def test_all_four_values_mapped(self):
        mapped = ArtifactStateStatusMapper.get_mapped_values()
        assert len(mapped) == 4

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError, match="Unknown ArtifactState status"):
            ArtifactStateStatusMapper.to_lifecycle_state("nonexistent")


# =========================================================================
# ManifestStatusMapper
# =========================================================================

class TestManifestStatusMapper:
    """All 3 TopicManifest.overall_status values map correctly."""

    def test_complete_maps_to_approved(self):
        assert ManifestStatusMapper.to_lifecycle_state("complete") == ArtifactLifecycleState.APPROVED

    def test_partial_maps_to_pending(self):
        assert ManifestStatusMapper.to_lifecycle_state("partial") == ArtifactLifecycleState.PENDING

    def test_blocked_maps_to_rejected(self):
        assert ManifestStatusMapper.to_lifecycle_state("blocked") == ArtifactLifecycleState.REJECTED

    def test_all_three_values_mapped(self):
        mapped = ManifestStatusMapper.get_mapped_values()
        assert len(mapped) == 3

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError, match="Unknown manifest overall_status"):
            ManifestStatusMapper.to_lifecycle_state("nonexistent")


# =========================================================================
# get_lifecycle_state convenience function
# =========================================================================

class TestGetLifecycleState:
    """Convenience function delegates to the correct mapper."""

    def test_review_status(self):
        result = get_lifecycle_state(review_status="approved")
        assert result == ArtifactLifecycleState.APPROVED

    def test_topic_status(self):
        result = get_lifecycle_state(topic_status="scored")
        assert result == ArtifactLifecycleState.PENDING

    def test_asset_entry_status(self):
        result = get_lifecycle_state(asset_entry_status="missing")
        assert result == ArtifactLifecycleState.MISSING

    def test_artifact_state_status(self):
        result = get_lifecycle_state(artifact_state_status="completed")
        assert result == ArtifactLifecycleState.APPROVED

    def test_manifest_overall_status(self):
        result = get_lifecycle_state(manifest_overall_status="complete")
        assert result == ArtifactLifecycleState.APPROVED

    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            get_lifecycle_state()

    def test_review_status_takes_precedence(self):
        """When multiple args provided, review_status is checked first."""
        result = get_lifecycle_state(
            review_status="draft",
            topic_status="approved",
        )
        assert result == ArtifactLifecycleState.DRAFT


# =========================================================================
# Mapper coverage: every value maps without error
# =========================================================================

class TestCompleteMapperCoverage:
    """Every enum value across all 5 systems maps successfully."""

    def test_all_topic_status_values(self):
        values = ["raw", "staged", "scored", "approved", "rejected", "review"]
        for v in values:
            result = TopicStatusMapper.to_lifecycle_state(v)
            assert isinstance(result, ArtifactLifecycleState)

    def test_all_review_status_values(self):
        values = ["draft", "needs_review", "reviewed", "approved", "rejected"]
        for v in values:
            result = ReviewStatusMapper.to_lifecycle_state(v)
            assert isinstance(result, ArtifactLifecycleState)

    def test_all_asset_entry_status_values(self):
        values = ["draft", "needs_review", "reviewed", "approved", "rejected", "missing", "skipped"]
        for v in values:
            result = AssetStatusMapper.to_lifecycle_state(v)
            assert isinstance(result, ArtifactLifecycleState)

    def test_all_artifact_state_status_values(self):
        values = ["pending", "completed", "failed", "needs_review"]
        for v in values:
            result = ArtifactStateStatusMapper.to_lifecycle_state(v)
            assert isinstance(result, ArtifactLifecycleState)

    def test_all_manifest_overall_status_values(self):
        values = ["complete", "partial", "blocked"]
        for v in values:
            result = ManifestStatusMapper.to_lifecycle_state(v)
            assert isinstance(result, ArtifactLifecycleState)


# =========================================================================
# Mapper consistency: same string → same lifecycle state across mappers
# =========================================================================

class TestMapperConsistency:
    """Shared string values map to the same lifecycle state across mappers."""

    def test_draft_consistency(self):
        """'draft' appears in ReviewStatus, AssetEntry, and should map identically."""
        r = ReviewStatusMapper.to_lifecycle_state("draft")
        a = AssetStatusMapper.to_lifecycle_state("draft")
        assert r == a == ArtifactLifecycleState.DRAFT

    def test_needs_review_consistency(self):
        """'needs_review' appears in ReviewStatus, AssetEntry, ArtifactState."""
        r = ReviewStatusMapper.to_lifecycle_state("needs_review")
        a = AssetStatusMapper.to_lifecycle_state("needs_review")
        w = ArtifactStateStatusMapper.to_lifecycle_state("needs_review")
        assert r == a == w == ArtifactLifecycleState.NEEDS_REVIEW

    def test_approved_consistency(self):
        """'approved' appears in ReviewStatus, AssetEntry, and TopicStatus."""
        r = ReviewStatusMapper.to_lifecycle_state("approved")
        a = AssetStatusMapper.to_lifecycle_state("approved")
        t = TopicStatusMapper.to_lifecycle_state("approved")
        assert r == a == t == ArtifactLifecycleState.APPROVED

    def test_rejected_consistency(self):
        """'rejected' appears in ReviewStatus, AssetEntry, TopicStatus."""
        r = ReviewStatusMapper.to_lifecycle_state("rejected")
        a = AssetStatusMapper.to_lifecycle_state("rejected")
        t = TopicStatusMapper.to_lifecycle_state("rejected")
        assert r == a == t == ArtifactLifecycleState.REJECTED


# =========================================================================
# Architecture constraints
# =========================================================================

class TestArchitectureConstraints:
    """Verify the new modules have no disallowed imports."""

    def _read_source(self, filename: str) -> str:
        path = Path(__file__).resolve().parent.parent.parent / "src" / "content_creation" / "workflow" / filename
        return path.read_text()

    def test_states_no_streamlit(self):
        assert "streamlit" not in self._read_source("states.py").lower()

    def test_states_no_storage(self):
        source = self._read_source("states.py")
        assert "from content_creation.storage" not in source
        assert "import storage" not in source

    def test_states_no_filesystem(self):
        source = self._read_source("states.py")
        assert "from pathlib" not in source
        assert "import os" not in source
        assert "import json" not in source

    def test_states_no_services(self):
        source = self._read_source("states.py")
        assert "from content_creation.application" not in source

    def test_mappers_no_streamlit(self):
        assert "streamlit" not in self._read_source("state_mappers.py").lower()

    def test_mappers_no_storage(self):
        source = self._read_source("state_mappers.py")
        assert "from content_creation.storage" not in source
        assert "import storage" not in source

    def test_mappers_no_filesystem(self):
        source = self._read_source("state_mappers.py")
        assert "from pathlib" not in source
        assert "import os" not in source
        assert "import json" not in source

    def test_mappers_no_services(self):
        source = self._read_source("state_mappers.py")
        assert "from content_creation.application" not in source

    def test_mappers_no_cli(self):
        source = self._read_source("state_mappers.py")
        assert "from content_creation.cli" not in source

    def test_mappers_only_workflow_import(self):
        """Mappers should only import from workflow.states and stdlib."""
        source = self._read_source("state_mappers.py")
        import_lines = [
            line for line in source.split("\n")
            if line.startswith("from content_creation")
        ]
        for line in import_lines:
            assert "workflow.states" in line, f"Disallowed import: {line}"


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_string_raises_for_all_mappers(self):
        with pytest.raises(ValueError):
            TopicStatusMapper.to_lifecycle_state("")
        with pytest.raises(ValueError):
            ReviewStatusMapper.to_lifecycle_state("")
        with pytest.raises(ValueError):
            AssetStatusMapper.to_lifecycle_state("")
        with pytest.raises(ValueError):
            ArtifactStateStatusMapper.to_lifecycle_state("")
        with pytest.raises(ValueError):
            ManifestStatusMapper.to_lifecycle_state("")

    def test_case_sensitivity(self):
        """Mappings are case-sensitive — uppercase should fail."""
        with pytest.raises(ValueError):
            ReviewStatusMapper.to_lifecycle_state("APPROVED")
        with pytest.raises(ValueError):
            TopicStatusMapper.to_lifecycle_state("RAW")

    def test_terminal_states_frozen(self):
        """TERMINAL_STATES is a frozenset and cannot be modified."""
        assert isinstance(TERMINAL_STATES, frozenset)
        with pytest.raises(AttributeError):
            TERMINAL_STATES.add(ArtifactLifecycleState.PENDING)  # type: ignore[attr-defined]

    def test_lifecycle_state_is_str(self):
        """ArtifactLifecycleState values can be used as strings."""
        state = ArtifactLifecycleState.APPROVED
        assert state == "approved"
        assert isinstance(state, str)
