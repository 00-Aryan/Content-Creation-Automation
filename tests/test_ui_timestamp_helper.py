"""Tests for the UI timestamp formatting helper."""

from datetime import datetime, date, timezone
from content_creation.ui.components.status import format_timestamp


def test_format_timestamp_timezone_aware_iso() -> None:
    """Verify timezone-aware ISO timestamp formats into readable text."""
    # UTC
    assert format_timestamp("2026-05-19T11:11:24+00:00") == "May 19, 2026, 11:11 AM UTC"
    assert format_timestamp("2026-05-19T11:11:24Z") == "May 19, 2026, 11:11 AM UTC"
    # Offset
    assert format_timestamp("2026-05-19T11:11:24+05:30") == "May 19, 2026, 11:11 AM +05:30"
    assert format_timestamp("2026-05-19T11:11:24-04:00") == "May 19, 2026, 11:11 AM -04:00"


def test_format_timestamp_with_microseconds() -> None:
    """Verify ISO timestamp with microseconds formats into readable text."""
    assert format_timestamp("2026-05-19T11:11:24.481514+00:00") == "May 19, 2026, 11:11 AM UTC"
    assert format_timestamp("2026-05-19T11:11:24.481514Z") == "May 19, 2026, 11:11 AM UTC"


def test_format_timestamp_datetime_objects() -> None:
    """Verify datetime objects format correctly."""
    dt_utc = datetime(2026, 5, 19, 11, 11, 24, tzinfo=timezone.utc)
    assert format_timestamp(dt_utc) == "May 19, 2026, 11:11 AM UTC"

    dt_naive = datetime(2026, 5, 19, 11, 11, 24)
    assert format_timestamp(dt_naive) == "May 19, 2026, 11:11 AM"


def test_format_timestamp_date_objects_and_strings() -> None:
    """Verify date objects and date strings format correctly."""
    d = date(2026, 5, 19)
    assert format_timestamp(d) == "May 19, 2026"
    assert format_timestamp("2026-05-19") == "May 19, 2026"


def test_format_timestamp_missing_and_none() -> None:
    """Verify missing or None timestamps do not crash and return clear message."""
    assert format_timestamp(None) == "Not available"
    assert format_timestamp("") == "Not available"
    assert format_timestamp("  ") == "Not available"
    assert format_timestamp("None") == "Not available"
    assert format_timestamp("n/a") == "Not available"


def test_format_timestamp_malformed() -> None:
    """Verify malformed/invalid timestamps do not crash."""
    assert format_timestamp("not-a-date") == "not-a-date"
    assert format_timestamp("2026-99-99") == "2026-99-99"
    assert format_timestamp("2026-05-19T99:99:99") == "2026-05-19T99:99:99"


def test_format_timestamp_does_not_contain_raw_iso_markers() -> None:
    """Verify formatted output does not contain raw T, microseconds, or offset style text."""
    res = format_timestamp("2026-05-19T11:11:24.481514+00:00")
    assert "T" not in res.replace("UTC", "")
    assert ".481514" not in res
    assert "+00:00" not in res
    assert "UTC" in res

