"""State mappers: domain-specific status → canonical ArtifactLifecycleState.

Each mapper converts a domain-specific status value into the canonical
``ArtifactLifecycleState``.  Mappers accept **string values** (not enum
instances) so that callers can pass raw JSON values without importing
domain enums.

Usage::

    from content_creation.workflow.state_mappers import ReviewStatusMapper

    lifecycle = ReviewStatusMapper.to_lifecycle_state("approved")
    assert lifecycle == ArtifactLifecycleState.APPROVED

All mappers are pure functions with no side effects, no storage, and
no service dependencies.
"""

from __future__ import annotations

import logging
from typing import Dict

from content_creation.workflow.states import ArtifactLifecycleState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base helpers
# ---------------------------------------------------------------------------

def _build_reverse_map(mapping: Dict[str, ArtifactLifecycleState]) -> Dict[str, str]:
    """Return a human-readable reverse map for error messages."""
    return {k: v.value for k, v in mapping.items()}


# ---------------------------------------------------------------------------
# TopicStatus mapper
# ---------------------------------------------------------------------------

class TopicStatusMapper:
    """Maps ``TopicStatus.value`` → ``ArtifactLifecycleState``.

    Mapping rationale
    -----------------
    * ``RAW``, ``STAGED``, ``SCORED`` → ``PENDING``
      All three represent pre-generation states where the topic is
      progressing through the pipeline but no artifact exists yet.
    * ``APPROVED`` → ``APPROVED``
      Operator approved the topic for content generation.
    * ``REJECTED`` → ``REJECTED``
      Topic rejected; no further processing.
    * ``REVIEW`` → ``NEEDS_REVIEW``
      Topic flagged for human review.
    """

    _MAP: Dict[str, ArtifactLifecycleState] = {
        "raw": ArtifactLifecycleState.PENDING,
        "staged": ArtifactLifecycleState.PENDING,
        "scored": ArtifactLifecycleState.PENDING,
        "approved": ArtifactLifecycleState.APPROVED,
        "rejected": ArtifactLifecycleState.REJECTED,
        "review": ArtifactLifecycleState.NEEDS_REVIEW,
    }

    @classmethod
    def to_lifecycle_state(cls, status: str) -> ArtifactLifecycleState:
        """Convert a TopicStatus value string to ArtifactLifecycleState.

        Parameters
        ----------
        status:
            A ``TopicStatus.value`` string (e.g. ``"scored"``).

        Returns
        -------
        ArtifactLifecycleState

        Raises
        ------
        ValueError
            If *status* is not a known TopicStatus value.
        """
        result = cls._MAP.get(status)
        if result is None:
            raise ValueError(
                f"Unknown TopicStatus value: {status!r}. "
                f"Known values: {sorted(cls._MAP.keys())}"
            )
        return result

    @classmethod
    def get_mapped_values(cls) -> Dict[str, str]:
        """Return all mapped values as {source_value: lifecycle_value}."""
        return _build_reverse_map(cls._MAP)


# ---------------------------------------------------------------------------
# ReviewStatus mapper
# ---------------------------------------------------------------------------

class ReviewStatusMapper:
    """Maps ``ReviewStatus.value`` → ``ArtifactLifecycleState``.

    Mapping rationale
    -----------------
    All five ReviewStatus values have direct 1:1 mappings because
    the ReviewStatus enum was designed with the same semantic intent
    as the lifecycle states.
    """

    _MAP: Dict[str, ArtifactLifecycleState] = {
        "draft": ArtifactLifecycleState.DRAFT,
        "needs_review": ArtifactLifecycleState.NEEDS_REVIEW,
        "reviewed": ArtifactLifecycleState.REVIEWED,
        "approved": ArtifactLifecycleState.APPROVED,
        "rejected": ArtifactLifecycleState.REJECTED,
    }

    @classmethod
    def to_lifecycle_state(cls, status: str) -> ArtifactLifecycleState:
        """Convert a ReviewStatus value string to ArtifactLifecycleState.

        Parameters
        ----------
        status:
            A ``ReviewStatus.value`` string (e.g. ``"needs_review"``).

        Returns
        -------
        ArtifactLifecycleState

        Raises
        ------
        ValueError
            If *status* is not a known ReviewStatus value.
        """
        result = cls._MAP.get(status)
        if result is None:
            raise ValueError(
                f"Unknown ReviewStatus value: {status!r}. "
                f"Known values: {sorted(cls._MAP.keys())}"
            )
        return result

    @classmethod
    def get_mapped_values(cls) -> Dict[str, str]:
        """Return all mapped values as {source_value: lifecycle_value}."""
        return _build_reverse_map(cls._MAP)


# ---------------------------------------------------------------------------
# AssetEntry.status mapper
# ---------------------------------------------------------------------------

class AssetStatusMapper:
    """Maps ``AssetEntry.status`` → ``ArtifactLifecycleState``.

    Mapping rationale
    -----------------
    The AssetEntry Literal extends ReviewStatus with two system-computed
    values (``missing``, ``skipped``).  These map directly to their
    lifecycle equivalents.
    """

    _MAP: Dict[str, ArtifactLifecycleState] = {
        "draft": ArtifactLifecycleState.DRAFT,
        "needs_review": ArtifactLifecycleState.NEEDS_REVIEW,
        "reviewed": ArtifactLifecycleState.REVIEWED,
        "approved": ArtifactLifecycleState.APPROVED,
        "rejected": ArtifactLifecycleState.REJECTED,
        "missing": ArtifactLifecycleState.MISSING,
        "skipped": ArtifactLifecycleState.SKIPPED,
    }

    @classmethod
    def to_lifecycle_state(cls, status: str) -> ArtifactLifecycleState:
        """Convert an AssetEntry.status literal to ArtifactLifecycleState.

        Parameters
        ----------
        status:
            An ``AssetEntry.status`` string (e.g. ``"missing"``).

        Returns
        -------
        ArtifactLifecycleState

        Raises
        ------
        ValueError
            If *status* is not a known AssetEntry.status value.
        """
        result = cls._MAP.get(status)
        if result is None:
            raise ValueError(
                f"Unknown AssetEntry status: {status!r}. "
                f"Known values: {sorted(cls._MAP.keys())}"
            )
        return result

    @classmethod
    def get_mapped_values(cls) -> Dict[str, str]:
        """Return all mapped values as {source_value: lifecycle_value}."""
        return _build_reverse_map(cls._MAP)


# ---------------------------------------------------------------------------
# ArtifactState.status mapper
# ---------------------------------------------------------------------------

class ArtifactStateStatusMapper:
    """Maps ``ArtifactState.status`` → ``ArtifactLifecycleState``.

    Mapping rationale
    -----------------
    * ``pending`` → ``PENDING`` (direct)
    * ``completed`` → ``APPROVED`` (completed generation = ready for review/approval)
    * ``failed`` → ``FAILED`` (generation error)
    * ``needs_review`` → ``NEEDS_REVIEW`` (degraded output)
    """

    _MAP: Dict[str, ArtifactLifecycleState] = {
        "pending": ArtifactLifecycleState.PENDING,
        "completed": ArtifactLifecycleState.APPROVED,
        "failed": ArtifactLifecycleState.FAILED,
        "needs_review": ArtifactLifecycleState.NEEDS_REVIEW,
    }

    @classmethod
    def to_lifecycle_state(cls, status: str) -> ArtifactLifecycleState:
        """Convert an ArtifactState.status string to ArtifactLifecycleState.

        Parameters
        ----------
        status:
            An ``ArtifactState.status`` string (e.g. ``"completed"``).

        Returns
        -------
        ArtifactLifecycleState

        Raises
        ------
        ValueError
            If *status* is not a known ArtifactState.status value.
        """
        result = cls._MAP.get(status)
        if result is None:
            raise ValueError(
                f"Unknown ArtifactState status: {status!r}. "
                f"Known values: {sorted(cls._MAP.keys())}"
            )
        return result

    @classmethod
    def get_mapped_values(cls) -> Dict[str, str]:
        """Return all mapped values as {source_value: lifecycle_value}."""
        return _build_reverse_map(cls._MAP)


# ---------------------------------------------------------------------------
# TopicManifest.overall_status mapper
# ---------------------------------------------------------------------------

class ManifestStatusMapper:
    """Maps ``TopicManifest.overall_status`` → ``ArtifactLifecycleState``.

    Mapping rationale
    -----------------
    * ``complete`` → ``APPROVED`` (all assets approved)
    * ``partial`` → ``PENDING`` (still in progress)
    * ``blocked`` → ``REJECTED`` (blocked by missing/rejected assets)
    """

    _MAP: Dict[str, ArtifactLifecycleState] = {
        "complete": ArtifactLifecycleState.APPROVED,
        "partial": ArtifactLifecycleState.PENDING,
        "blocked": ArtifactLifecycleState.REJECTED,
    }

    @classmethod
    def to_lifecycle_state(cls, status: str) -> ArtifactLifecycleState:
        """Convert a TopicManifest.overall_status literal to ArtifactLifecycleState.

        Parameters
        ----------
        status:
            A ``TopicManifest.overall_status`` string (e.g. ``"complete"``).

        Returns
        -------
        ArtifactLifecycleState

        Raises
        ------
        ValueError
            If *status* is not a known overall_status value.
        """
        result = cls._MAP.get(status)
        if result is None:
            raise ValueError(
                f"Unknown manifest overall_status: {status!r}. "
                f"Known values: {sorted(cls._MAP.keys())}"
            )
        return result

    @classmethod
    def get_mapped_values(cls) -> Dict[str, str]:
        """Return all mapped values as {source_value: lifecycle_value}."""
        return _build_reverse_map(cls._MAP)
