"""Tests for ReviewTransitionEngine — centralized review-state transition validation."""

from pathlib import Path

import pytest

from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.review_transition_engine import (
    ReviewTransition,
    ReviewTransitionEngine,
    TransitionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> ReviewTransitionEngine:
    """Default engine with canonical transitions only."""
    return ReviewTransitionEngine()


# ---------------------------------------------------------------------------
# Test: Valid transitions
# ---------------------------------------------------------------------------

class TestValidTransitions:
    """Every legal transition from the canonical graph."""

    def test_draft_to_needs_review(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.NEEDS_REVIEW)
        assert result.valid is True
        assert result.from_status == ReviewStatus.DRAFT
        assert result.to_status == ReviewStatus.NEEDS_REVIEW
        assert result.reason  # has description

    def test_draft_to_approved(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.APPROVED)
        assert result.valid is True

    def test_needs_review_to_reviewed(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.NEEDS_REVIEW, ReviewStatus.REVIEWED)
        assert result.valid is True

    def test_needs_review_to_approved(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.NEEDS_REVIEW, ReviewStatus.APPROVED)
        assert result.valid is True

    def test_needs_review_to_rejected(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.NEEDS_REVIEW, ReviewStatus.REJECTED)
        assert result.valid is True

    def test_reviewed_to_approved(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REVIEWED, ReviewStatus.APPROVED)
        assert result.valid is True

    def test_reviewed_to_rejected(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REVIEWED, ReviewStatus.REJECTED)
        assert result.valid is True

    def test_all_valid_transitions_pass(self, engine: ReviewTransitionEngine):
        """Verify every edge in the canonical graph is valid."""
        all_transitions = engine.get_all_transitions()
        assert len(all_transitions) == 7  # 7 canonical edges
        for t in all_transitions:
            result = engine.validate_transition(t.from_status, t.to_status)
            assert result.valid, f"Expected valid: {t.from_status.value} → {t.to_status.value}"


# ---------------------------------------------------------------------------
# Test: Invalid transitions
# ---------------------------------------------------------------------------

class TestInvalidTransitions:
    """Every illegal transition should be rejected."""

    def test_approved_to_draft(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.APPROVED, ReviewStatus.DRAFT)
        assert result.valid is False
        assert "Terminal state" in result.reason

    def test_approved_to_needs_review(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVIEW)
        assert result.valid is False
        assert "Terminal state" in result.reason

    def test_approved_to_reviewed(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.APPROVED, ReviewStatus.REVIEWED)
        assert result.valid is False

    def test_approved_to_rejected(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.APPROVED, ReviewStatus.REJECTED)
        assert result.valid is False

    def test_rejected_to_draft(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REJECTED, ReviewStatus.DRAFT)
        assert result.valid is False
        assert "Terminal state" in result.reason

    def test_rejected_to_needs_review(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REJECTED, ReviewStatus.NEEDS_REVIEW)
        assert result.valid is False

    def test_rejected_to_reviewed(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REJECTED, ReviewStatus.REVIEWED)
        assert result.valid is False

    def test_rejected_to_approved(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REJECTED, ReviewStatus.APPROVED)
        assert result.valid is False

    def test_draft_to_reviewed(self, engine: ReviewTransitionEngine):
        """DRAFT → REVIEWED is not allowed; must go through NEEDS_REVIEW."""
        result = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.REVIEWED)
        assert result.valid is False
        assert "Invalid transition" in result.reason

    def test_draft_to_rejected(self, engine: ReviewTransitionEngine):
        """DRAFT → REJECTED is not allowed; must go through NEEDS_REVIEW."""
        result = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.REJECTED)
        assert result.valid is False

    def test_reviewed_to_draft(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REVIEWED, ReviewStatus.DRAFT)
        assert result.valid is False

    def test_reviewed_to_needs_review(self, engine: ReviewTransitionEngine):
        result = engine.validate_transition(ReviewStatus.REVIEWED, ReviewStatus.NEEDS_REVIEW)
        assert result.valid is False

    def test_all_invalid_transitions_fail(self, engine: ReviewTransitionEngine):
        """Verify all non-edges are rejected."""
        valid_edges = {
            (t.from_status, t.to_status) for t in engine.get_all_transitions()
        }
        all_statuses = list(ReviewStatus)
        for from_s in all_statuses:
            for to_s in all_statuses:
                if from_s == to_s:
                    continue  # tested separately as no-op
                if (from_s, to_s) in valid_edges:
                    continue
                result = engine.validate_transition(from_s, to_s)
                assert not result.valid, (
                    f"Expected invalid: {from_s.value} → {to_s.value}"
                )


# ---------------------------------------------------------------------------
# Test: No-op transitions
# ---------------------------------------------------------------------------

class TestNoopTransitions:
    """Same-status transitions are always invalid."""

    @pytest.mark.parametrize("status", list(ReviewStatus))
    def test_noop_is_invalid(self, engine: ReviewTransitionEngine, status: ReviewStatus):
        result = engine.validate_transition(status, status)
        assert result.valid is False
        assert "No-op" in result.reason


# ---------------------------------------------------------------------------
# Test: Terminal states
# ---------------------------------------------------------------------------

class TestTerminalStates:
    """APPROVED and REJECTED should be terminal."""

    def test_approved_is_terminal(self, engine: ReviewTransitionEngine):
        assert engine.is_terminal(ReviewStatus.APPROVED) is True

    def test_rejected_is_terminal(self, engine: ReviewTransitionEngine):
        assert engine.is_terminal(ReviewStatus.REJECTED) is True

    def test_draft_is_not_terminal(self, engine: ReviewTransitionEngine):
        assert engine.is_terminal(ReviewStatus.DRAFT) is False

    def test_needs_review_is_not_terminal(self, engine: ReviewTransitionEngine):
        assert engine.is_terminal(ReviewStatus.NEEDS_REVIEW) is False

    def test_reviewed_is_not_terminal(self, engine: ReviewTransitionEngine):
        assert engine.is_terminal(ReviewStatus.REVIEWED) is False

    def test_terminal_states_set(self, engine: ReviewTransitionEngine):
        terminal = engine.get_terminal_states()
        assert terminal == {ReviewStatus.APPROVED, ReviewStatus.REJECTED}


# ---------------------------------------------------------------------------
# Test: can_transition
# ---------------------------------------------------------------------------

class TestCanTransition:
    """Boolean check for transition validity."""

    def test_can_transition_valid(self, engine: ReviewTransitionEngine):
        assert engine.can_transition(ReviewStatus.DRAFT, ReviewStatus.NEEDS_REVIEW) is True

    def test_can_transition_invalid(self, engine: ReviewTransitionEngine):
        assert engine.can_transition(ReviewStatus.APPROVED, ReviewStatus.DRAFT) is False

    def test_can_transition_terminal(self, engine: ReviewTransitionEngine):
        assert engine.can_transition(ReviewStatus.REJECTED, ReviewStatus.APPROVED) is False


# ---------------------------------------------------------------------------
# Test: get_available_transitions
# ---------------------------------------------------------------------------

class TestGetAvailableTransitions:
    """Query allowed targets from each status."""

    def test_draft_has_two_targets(self, engine: ReviewTransitionEngine):
        transitions = engine.get_available_transitions(ReviewStatus.DRAFT)
        targets = {t.to_status for t in transitions}
        assert targets == {ReviewStatus.NEEDS_REVIEW, ReviewStatus.APPROVED}

    def test_needs_review_has_three_targets(self, engine: ReviewTransitionEngine):
        transitions = engine.get_available_transitions(ReviewStatus.NEEDS_REVIEW)
        targets = {t.to_status for t in transitions}
        assert targets == {ReviewStatus.REVIEWED, ReviewStatus.APPROVED, ReviewStatus.REJECTED}

    def test_reviewed_has_two_targets(self, engine: ReviewTransitionEngine):
        transitions = engine.get_available_transitions(ReviewStatus.REVIEWED)
        targets = {t.to_status for t in transitions}
        assert targets == {ReviewStatus.APPROVED, ReviewStatus.REJECTED}

    def test_approved_has_no_targets(self, engine: ReviewTransitionEngine):
        assert engine.get_available_transitions(ReviewStatus.APPROVED) == []

    def test_rejected_has_no_targets(self, engine: ReviewTransitionEngine):
        assert engine.get_available_transitions(ReviewStatus.REJECTED) == []


# ---------------------------------------------------------------------------
# Test: get_all_transitions
# ---------------------------------------------------------------------------

class TestGetAllTransitions:
    """Full graph inspection."""

    def test_all_transitions_count(self, engine: ReviewTransitionEngine):
        assert len(engine.get_all_transitions()) == 7

    def test_all_transitions_are_review_transition(self, engine: ReviewTransitionEngine):
        for t in engine.get_all_transitions():
            assert isinstance(t, ReviewTransition)

    def test_all_transitions_sorted(self, engine: ReviewTransitionEngine):
        all_t = engine.get_all_transitions()
        for i in range(len(all_t) - 1):
            a = (all_t[i].from_status.value, all_t[i].to_status.value)
            b = (all_t[i + 1].from_status.value, all_t[i + 1].to_status.value)
            assert a <= b, f"Not sorted: {a} > {b}"


# ---------------------------------------------------------------------------
# Test: Extra transitions
# ---------------------------------------------------------------------------

class TestExtraTransitions:
    """Engine accepts additional transitions via constructor."""

    def test_extra_transitions_merged(self):
        extra = [
            ReviewTransition(
                from_status=ReviewStatus.APPROVED,
                to_status=ReviewStatus.DRAFT,
                description="Admin override",
            ),
        ]
        engine = ReviewTransitionEngine(extra_transitions=extra)
        assert engine.can_transition(ReviewStatus.APPROVED, ReviewStatus.DRAFT) is True
        # Original graph still works
        assert engine.can_transition(ReviewStatus.DRAFT, ReviewStatus.NEEDS_REVIEW) is True

    def test_extra_transitions_in_get_all(self):
        extra = [
            ReviewTransition(
                from_status=ReviewStatus.APPROVED,
                to_status=ReviewStatus.DRAFT,
                description="Admin override",
            ),
        ]
        engine = ReviewTransitionEngine(extra_transitions=extra)
        all_t = engine.get_all_transitions()
        assert len(all_t) == 8  # 7 canonical + 1 extra

    def test_extra_transitions_override_terminal(self):
        """Adding an edge from a terminal state un-terminates it."""
        extra = [
            ReviewTransition(
                from_status=ReviewStatus.APPROVED,
                to_status=ReviewStatus.DRAFT,
                description="Reopen",
            ),
        ]
        engine = ReviewTransitionEngine(extra_transitions=extra)
        assert engine.is_terminal(ReviewStatus.APPROVED) is False


# ---------------------------------------------------------------------------
# Test: TransitionResult dataclass
# ---------------------------------------------------------------------------

class TestTransitionResult:
    """TransitionResult is a frozen dataclass."""

    def test_frozen(self):
        result = TransitionResult(
            valid=True,
            from_status=ReviewStatus.DRAFT,
            to_status=ReviewStatus.APPROVED,
            reason="test",
        )
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]

    def test_defaults(self):
        result = TransitionResult(
            valid=False,
            from_status=ReviewStatus.DRAFT,
            to_status=ReviewStatus.REJECTED,
        )
        assert result.reason == ""


# ---------------------------------------------------------------------------
# Test: ReviewTransition dataclass
# ---------------------------------------------------------------------------

class TestReviewTransition:
    """ReviewTransition is a frozen dataclass."""

    def test_frozen(self):
        t = ReviewTransition(
            from_status=ReviewStatus.DRAFT,
            to_status=ReviewStatus.NEEDS_REVIEW,
            description="test",
        )
        with pytest.raises(AttributeError):
            t.description = "changed"  # type: ignore[misc]

    def test_default_description(self):
        t = ReviewTransition(
            from_status=ReviewStatus.DRAFT,
            to_status=ReviewStatus.APPROVED,
        )
        assert t.description == ""


# ---------------------------------------------------------------------------
# Test: Architecture constraints
# ---------------------------------------------------------------------------

class TestArchitectureConstraints:
    """Verify the engine has no disallowed imports."""

    def _read_engine_source(self) -> str:
        module_file = Path(__file__).resolve().parent.parent.parent / "src" / "content_creation" / "workflow" / "review_transition_engine.py"
        return module_file.read_text()

    def test_no_streamlit_imports(self):
        source = self._read_engine_source()
        assert "streamlit" not in source.lower()

    def test_no_storage_imports(self):
        source = self._read_engine_source()
        assert "from content_creation.storage" not in source
        assert "import storage" not in source

    def test_no_filesystem_imports(self):
        source = self._read_engine_source()
        assert "from pathlib" not in source
        assert "import os" not in source
        assert "import json" not in source

    def test_no_service_imports(self):
        source = self._read_engine_source()
        assert "from content_creation.application" not in source
        assert "import service" not in source.lower()

    def test_only_imports_from_shared_enums(self):
        """The only content_creation import should be ReviewStatus from shared.enums."""
        source = self._read_engine_source()
        # Check only top-level import lines (not indented docstring/example code)
        import_lines = [
            line for line in source.split("\n")
            if line.startswith("from content_creation")
        ]
        assert len(import_lines) == 1
        assert "shared.enums" in import_lines[0]


# ---------------------------------------------------------------------------
# Test: Pure determinism
# ---------------------------------------------------------------------------

class TestPureDeterminism:
    """Engine methods are pure — same inputs always produce same outputs."""

    def test_validate_transition_deterministic(self, engine: ReviewTransitionEngine):
        r1 = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.APPROVED)
        r2 = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.APPROVED)
        assert r1 == r2

    def test_get_available_transitions_deterministic(self, engine: ReviewTransitionEngine):
        t1 = engine.get_available_transitions(ReviewStatus.NEEDS_REVIEW)
        t2 = engine.get_available_transitions(ReviewStatus.NEEDS_REVIEW)
        assert t1 == t2

    def test_can_transition_deterministic(self, engine: ReviewTransitionEngine):
        assert engine.can_transition(ReviewStatus.DRAFT, ReviewStatus.APPROVED) is True
        assert engine.can_transition(ReviewStatus.DRAFT, ReviewStatus.APPROVED) is True
