"""Input quality evaluation for Content Intelligence generation."""

from enum import Enum

from content_creation.models.brief import Brief


class QualityStatus(str, Enum):
    """Whether a Brief is suitable for CI generation."""
    READY = "ready"        # All key fields present
    DEGRADED = "degraded"  # Some fields missing; CI will be partial
    BLOCKED = "blocked"    # Insufficient data; CI should not be generated


# Fields evaluated for quality. Weights reflect importance to CI generation.
_REQUIRED_FIELDS = ("why_it_matters", "plain_english_summary", "student_takeaway")
_OPTIONAL_FIELDS = ("analogy", "limitation", "audience_fit")


def _is_usable(value) -> bool:
    """Return True if a field has real content (not needs_review/empty)."""
    if isinstance(value, list):
        return all(v != "needs_review" and v.strip() for v in value)
    return isinstance(value, str) and value != "needs_review" and value.strip() != ""


def evaluate_brief_quality(brief: Brief) -> QualityStatus:
    """Assess whether a Brief has enough usable data for CI generation."""
    required_available = sum(1 for f in _REQUIRED_FIELDS if _is_usable(getattr(brief, f)))
    optional_available = sum(1 for f in _OPTIONAL_FIELDS if _is_usable(getattr(brief, f)))

    # All required fields must be present to proceed at all
    if required_available < len(_REQUIRED_FIELDS):
        return QualityStatus.BLOCKED

    # If all optional fields also present, fully ready
    if optional_available == len(_OPTIONAL_FIELDS):
        return QualityStatus.READY

    # Some optional fields missing — CI can proceed but quality is reduced
    return QualityStatus.DEGRADED
