"""Tests for the UI status formatting helper."""

import pytest
from content_creation.shared.enums import ReviewStatus
from content_creation.ui.components.status import format_review_status


def test_format_review_status_enum_instances() -> None:
    """Verify enum instance values format correctly."""
    assert format_review_status(ReviewStatus.APPROVED) == "Approved"
    assert format_review_status(ReviewStatus.REJECTED) == "Rejected"
    assert format_review_status(ReviewStatus.NEEDS_REVIEW) == "Needs review"
    assert format_review_status(ReviewStatus.DRAFT) == "Draft"
    assert format_review_status(ReviewStatus.REVIEWED) == "Reviewed"


def test_format_review_status_plain_strings() -> None:
    """Verify plain string values format correctly."""
    assert format_review_status("approved") == "Approved"
    assert format_review_status("rejected") == "Rejected"
    assert format_review_status("needs_review") == "Needs review"
    assert format_review_status("draft") == "Draft"
    assert format_review_status("reviewed") == "Reviewed"


def test_format_review_status_raw_prefixes() -> None:
    """Verify strings containing ReviewStatus. prefix format correctly."""
    assert format_review_status("ReviewStatus.APPROVED") == "Approved"
    assert format_review_status("ReviewStatus.NEEDS_REVIEW") == "Needs review"
    assert format_review_status("ReviewStatus.DRAFT") == "Draft"


def test_format_review_status_unknown_and_missing() -> None:
    """Verify unknown or missing values format correctly and do not crash."""
    assert format_review_status(None) == "Unknown"
    assert format_review_status("") == ""
    assert format_review_status("some_random_status") == "Some random status"
    assert format_review_status("RANDOM") == "Random"
