"""Shared enumerations used across all content domains."""

from enum import Enum


class ReviewStatus(str, Enum):
    """Review state machine for all content artifacts."""

    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
