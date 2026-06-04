"""Centralized review-state transition engine.

This module is the single source of truth for all review-state transitions
across briefs, storyboards, assets, and manifests. It validates transitions
without side effects — no storage, UI, or service imports.

Usage::

    from content_creation.workflow.review_transition_engine import ReviewTransitionEngine

    engine = ReviewTransitionEngine()
    result = engine.validate_transition(ReviewStatus.DRAFT, ReviewStatus.APPROVED)
    if result.valid:
        # proceed with transition
        pass
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from content_creation.shared.enums import ReviewStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReviewTransition:
    """A single directed edge in the review-state graph."""

    from_status: ReviewStatus
    to_status: ReviewStatus
    description: str = ""


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of a transition validation check."""

    valid: bool
    from_status: ReviewStatus
    to_status: ReviewStatus
    reason: str = ""


# ---------------------------------------------------------------------------
# Canonical transition graph
# ---------------------------------------------------------------------------

# Valid transitions for content artifacts (brief, storyboard, script,
# carousel, newsletter, thumbnail).  Derived from the Phase 11.1 audit
# Section 7.2 and the transition inventory in phase11_1_1.
#
# Terminal states (APPROVED, REJECTED) have no outgoing edges.
#
# The graph is intentionally asset-type agnostic — all reviewable content
# artifacts share the same review-state lifecycle.

_CANONICAL_TRANSITIONS: List[ReviewTransition] = [
    # DRAFT → downstream
    ReviewTransition(
        from_status=ReviewStatus.DRAFT,
        to_status=ReviewStatus.NEEDS_REVIEW,
        description="Generator fallback or operator flag",
    ),
    ReviewTransition(
        from_status=ReviewStatus.DRAFT,
        to_status=ReviewStatus.APPROVED,
        description="Auto-approve (batch or pipeline)",
    ),
    # NEEDS_REVIEW → downstream
    ReviewTransition(
        from_status=ReviewStatus.NEEDS_REVIEW,
        to_status=ReviewStatus.REVIEWED,
        description="Operator marks reviewed",
    ),
    ReviewTransition(
        from_status=ReviewStatus.NEEDS_REVIEW,
        to_status=ReviewStatus.APPROVED,
        description="Operator approves directly",
    ),
    ReviewTransition(
        from_status=ReviewStatus.NEEDS_REVIEW,
        to_status=ReviewStatus.REJECTED,
        description="Operator rejects",
    ),
    # REVIEWED → downstream
    ReviewTransition(
        from_status=ReviewStatus.REVIEWED,
        to_status=ReviewStatus.APPROVED,
        description="Operator approves",
    ),
    ReviewTransition(
        from_status=ReviewStatus.REVIEWED,
        to_status=ReviewStatus.REJECTED,
        description="Operator rejects",
    ),
    # Terminal states have no outgoing transitions:
    #   APPROVED — consumed by downstream services
    #   REJECTED — requires new artifact generation
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ReviewTransitionEngine:
    """Single source of truth for review-state transitions.

    The engine holds a canonical transition graph and exposes query methods
    for validating and inspecting transitions.  It has **no** side effects:
    no storage, no UI, no filesystem, no service imports.

    All methods are pure and deterministic.
    """

    def __init__(
        self,
        extra_transitions: Optional[List[ReviewTransition]] = None,
    ) -> None:
        """Initialise the engine with the canonical transition graph.

        Parameters
        ----------
        extra_transitions:
            Optional additional transitions to merge into the graph.
            Useful for extending the graph in future phases without
            modifying this module.
        """
        self._transitions: List[ReviewTransition] = list(_CANONICAL_TRANSITIONS)
        if extra_transitions:
            self._transitions.extend(extra_transitions)

        # Build adjacency index: from_status → set of allowed to_status
        self._graph: Dict[ReviewStatus, Set[ReviewStatus]] = {
            status: set() for status in ReviewStatus
        }
        self._transition_map: Dict[Tuple[ReviewStatus, ReviewStatus], ReviewTransition] = {}

        for t in self._transitions:
            self._graph[t.from_status].add(t.to_status)
            self._transition_map[(t.from_status, t.to_status)] = t

        logger.debug(
            "[review-transition-engine] initialised with %d transitions",
            len(self._transitions),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_transition(
        self, from_status: ReviewStatus, to_status: ReviewStatus
    ) -> bool:
        """Return True if the transition is allowed by the canonical graph.

        Parameters
        ----------
        from_status:
            Current review status.
        to_status:
            Desired target status.

        Returns
        -------
        bool
            True if the transition is valid.
        """
        return to_status in self._graph.get(from_status, set())

    def validate_transition(
        self, from_status: ReviewStatus, to_status: ReviewStatus
    ) -> TransitionResult:
        """Validate a proposed transition and return a detailed result.

        Parameters
        ----------
        from_status:
            Current review status.
        to_status:
            Desired target status.

        Returns
        -------
        TransitionResult
            Contains ``valid``, ``from_status``, ``to_status``, and
            an optional ``reason`` explaining why the transition is
            invalid (or the trigger description if valid).
        """
        if from_status == to_status:
            return TransitionResult(
                valid=False,
                from_status=from_status,
                to_status=to_status,
                reason=f"No-op transition: already in {from_status.value}",
            )

        if to_status in self._graph.get(from_status, set()):
            edge = self._transition_map.get((from_status, to_status))
            description = edge.description if edge else ""
            return TransitionResult(
                valid=True,
                from_status=from_status,
                to_status=to_status,
                reason=description,
            )

        # Build a human-readable rejection reason
        allowed = self._graph.get(from_status, set())
        if not allowed:
            reason = (
                f"Terminal state: {from_status.value} has no outgoing transitions"
            )
        else:
            allowed_values = ", ".join(s.value for s in sorted(allowed, key=lambda s: s.value))
            reason = (
                f"Invalid transition: {from_status.value} → {to_status.value}. "
                f"Allowed targets from {from_status.value}: [{allowed_values}]"
            )

        return TransitionResult(
            valid=False,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )

    def get_available_transitions(
        self, from_status: ReviewStatus
    ) -> List[ReviewTransition]:
        """Return all transitions originating from the given status.

        Parameters
        ----------
        from_status:
            Current review status.

        Returns
        -------
        list[ReviewTransition]
            Ordered list of allowed transitions.  Empty for terminal states.
        """
        allowed_targets = self._graph.get(from_status, set())
        result = [
            self._transition_map[(from_status, target)]
            for target in sorted(allowed_targets, key=lambda s: s.value)
        ]
        return result

    def get_all_transitions(self) -> List[ReviewTransition]:
        """Return every transition in the canonical graph.

        Returns
        -------
        list[ReviewTransition]
            All edges, ordered by from_status then to_status.
        """
        return sorted(
            self._transitions,
            key=lambda t: (t.from_status.value, t.to_status.value),
        )

    def is_terminal(self, status: ReviewStatus) -> bool:
        """Return True if the status is a terminal state (no outgoing edges).

        Parameters
        ----------
        status:
            Review status to check.

        Returns
        -------
        bool
            True if no transitions originate from this status.
        """
        return len(self._graph.get(status, set())) == 0

    def get_terminal_states(self) -> Set[ReviewStatus]:
        """Return the set of terminal review states.

        Returns
        -------
        set[ReviewStatus]
            Statuses with no outgoing transitions.
        """
        return {status for status in ReviewStatus if self.is_terminal(status)}
