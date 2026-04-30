"""Tests for TopicItem model."""

import pytest
from content_creation.models.topic import TopicCategory, TopicItem, TopicStatus


def test_topic_item_id_generation():
    """Test deterministic ID generation."""
    url = "https://arxiv.org/abs/2301.00001"
    id1 = TopicItem.generate_id(url)
    id2 = TopicItem.generate_id(url)
    assert id1 == id2
    assert len(id1) == 64  # SHA256 hex length


def test_topic_item_validation():
    """Test Pydantic validation for TopicItem."""
    url = "https://example.com/post"
    item = TopicItem(
        id=TopicItem.generate_id(url),
        title="Test Title",
        url=url,
        source="test",
        published_at="2026-04-30T12:00:00Z",
        raw_text="Some content",
        category=TopicCategory.NEWS
    )
    assert item.status == TopicStatus.RAW
    assert item.author == "unknown"


def test_invalid_date_validation():
    """Test that invalid dates raise an error."""
    url = "https://example.com/post"
    with pytest.raises(ValueError, match="published_at must be an ISO-8601"):
        TopicItem(
            id=TopicItem.generate_id(url),
            title="Test Title",
            url=url,
            source="test",
            published_at="not-a-date",
            raw_text="Some content"
        )
