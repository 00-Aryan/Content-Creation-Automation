"""Canonical workflow state model for the content-creation system.

``ArtifactLifecycleState`` is the unified vocabulary that all future
dependency rules, action engines, and notification systems will use.
It does **not** replace existing domain enums — it provides a
mapping layer that bridges them.

Usage::

    from content_creation.workflow.states import ArtifactLifecycleState

    state = ArtifactLifecycleState.APPROVED
    if is_terminal(state):
        print("No further actions possible")
"""

from enum import Enum


class ArtifactLifecycleState(str, Enum):
    """Canonical lifecycle state for all content artifacts.

    This enum provides a single vocabulary that spans topics, reviews,
    manifests, and workflow stages.  Existing domain-specific enums
    (``ReviewStatus``, ``TopicStatus``, ``AssetEntry.status``, etc.)
    are mapped to these states via dedicated mapper classes.

    Semantics
    ---------
    PENDING
        Artifact not yet started or still in progress.
    DRAFT
        Initial artifact produced by a generator; not yet submitted
        for review.
    NEEDS_REVIEW
        Artifact flagged for operator review (fallback, quality gate,
        or explicit flag).
    REVIEWED
        Operator has reviewed the artifact but not yet decided
        (approve / reject).
    APPROVED
        Operator approved; artifact is consumed by downstream services.
        **Terminal.**
    REJECTED
        Operator rejected; requires regeneration or archival.
        **Terminal.**
    MISSING
        Artifact file does not exist in storage (system-computed).
        **Terminal.**
    SKIPPED
        Artifact generation was intentionally skipped (system-computed).
        **Terminal.**
    FAILED
        Generation or processing failed with an error.  Retryable.
    """

    PENDING = "pending"
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    MISSING = "missing"
    SKIPPED = "skipped"
    FAILED = "failed"


# ------------------------------------------------------------------
# Terminal-state set (computed once at import time)
# ------------------------------------------------------------------

TERMINAL_STATES: frozenset[ArtifactLifecycleState] = frozenset(
    {ArtifactLifecycleState.APPROVED, ArtifactLifecycleState.REJECTED,
     ArtifactLifecycleState.MISSING, ArtifactLifecycleState.SKIPPED}
)


# ------------------------------------------------------------------
# Convenience queries
# ------------------------------------------------------------------

def is_terminal(state: ArtifactLifecycleState) -> bool:
    """Return True if *state* is terminal (no outgoing transitions).

    Parameters
    ----------
    state:
        The lifecycle state to check.

    Returns
    -------
    bool
        True for ``APPROVED``, ``REJECTED``, ``MISSING``, ``SKIPPED``.
    """
    return state in TERMINAL_STATES


def is_reviewable(state: ArtifactLifecycleState) -> bool:
    """Return True if *state* can be acted on by an operator review.

    Reviewable states are ``DRAFT``, ``NEEDS_REVIEW``, and ``REVIEWED``.
    ``PENDING`` is not reviewable (generation has not completed).
    ``APPROVED`` / ``REJECTED`` / ``MISSING`` / ``SKIPPED`` are terminal.
    ``FAILED`` is not reviewable (needs re-generation, not review).

    Parameters
    ----------
    state:
        The lifecycle state to check.

    Returns
    -------
    bool
    """
    return state in {
        ArtifactLifecycleState.DRAFT,
        ArtifactLifecycleState.NEEDS_REVIEW,
        ArtifactLifecycleState.REVIEWED,
    }


def is_approvable(state: ArtifactLifecycleState) -> bool:
    """Return True if *state* can transition to ``APPROVED``.

    Approvable states are ``DRAFT``, ``NEEDS_REVIEW``, and ``REVIEWED``.
    These correspond to the valid ``→ APPROVED`` edges in the review
    transition graph.

    Parameters
    ----------
    state:
        The lifecycle state to check.

    Returns
    -------
    bool
    """
    return state in {
        ArtifactLifecycleState.DRAFT,
        ArtifactLifecycleState.NEEDS_REVIEW,
        ArtifactLifecycleState.REVIEWED,
    }


def get_lifecycle_state(
    *,
    review_status: str | None = None,
    topic_status: str | None = None,
    asset_entry_status: str | None = None,
    artifact_state_status: str | None = None,
    manifest_overall_status: str | None = None,
) -> ArtifactLifecycleState:
    """Derive a canonical ``ArtifactLifecycleState`` from domain values.

    This is a convenience function that delegates to the appropriate
    mapper.  At least one keyword argument must be provided.

    Parameters
    ----------
    review_status:
        A ``ReviewStatus.value`` string (e.g. ``"approved"``).
    topic_status:
        A ``TopicStatus.value`` string (e.g. ``"scored"``).
    asset_entry_status:
        An ``AssetEntry.status`` literal (e.g. ``"missing"``).
    artifact_state_status:
        An ``ArtifactState.status`` string (e.g. ``"completed"``).
    manifest_overall_status:
        A ``TopicManifest.overall_status`` literal (e.g. ``"complete"``).

    Returns
    -------
    ArtifactLifecycleState
        The canonical lifecycle state.

    Raises
    ------
    ValueError
        If no keyword arguments are provided or if a provided value
        cannot be mapped.
    """
    from content_creation.workflow.state_mappers import (
        ArtifactStateStatusMapper,
        AssetStatusMapper,
        ManifestStatusMapper,
        ReviewStatusMapper,
        TopicStatusMapper,
    )

    if review_status is not None:
        return ReviewStatusMapper.to_lifecycle_state(review_status)
    if topic_status is not None:
        return TopicStatusMapper.to_lifecycle_state(topic_status)
    if asset_entry_status is not None:
        return AssetStatusMapper.to_lifecycle_state(asset_entry_status)
    if artifact_state_status is not None:
        return ArtifactStateStatusMapper.to_lifecycle_state(artifact_state_status)
    if manifest_overall_status is not None:
        return ManifestStatusMapper.to_lifecycle_state(manifest_overall_status)

    raise ValueError("At least one status keyword argument must be provided")
