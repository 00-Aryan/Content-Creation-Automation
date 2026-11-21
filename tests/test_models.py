"""Tests for TopicItem model."""

import pytest
from content_creation.models.topic import ScoredTopicItem, TopicCategory, TopicItem, TopicStatus


def test_scored_topic_item_status_transition():
    """Test status transitions in ScoredTopicItem."""
    url = "https://example.com/post"
    base_data = {
        "id": TopicItem.generate_id(url),
        "title": "Test Title",
        "url": url,
        "source": "test",
        "published_at": "2026-04-30T12:00:00Z",
        "raw_text": "Some content",
    }
    
    # RAW -> SCORED
    scored1 = ScoredTopicItem(**base_data, status=TopicStatus.RAW)
    assert scored1.status == TopicStatus.SCORED
    
    # STAGED -> SCORED
    scored2 = ScoredTopicItem(**base_data, status=TopicStatus.STAGED)
    assert scored2.status == TopicStatus.SCORED
    
    # APPROVED -> APPROVED (preserved)
    scored3 = ScoredTopicItem(**base_data, status=TopicStatus.APPROVED)
    assert scored3.status == TopicStatus.APPROVED
    
    # REJECTED -> REJECTED (preserved)
    scored4 = ScoredTopicItem(**base_data, status=TopicStatus.REJECTED)
    assert scored4.status == TopicStatus.REJECTED


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


def test_topic_metadata_schema_tightening():
    """Covers SCHEMA-001 & SCHEMA-002: TopicItem and ScoredTopicItem use typed TopicMetadata."""
    from content_creation.models.topic import TopicMetadata

    item = TopicItem(
        id="t1",
        title="Title",
        url="https://example.com/1",
        source="arxiv",
        published_at="2026-04-30T12:00:00Z",
        raw_text="Machine learning research",
        metadata={"source_type": "rss", "feed_id": "openai_blog", "custom_extra": 42},
    )
    assert isinstance(item.metadata, TopicMetadata)
    assert item.metadata.source_type == "rss"
    assert item.metadata.feed_id == "openai_blog"
    assert item.metadata["custom_extra"] == 42
    assert item.metadata.get("feed_id") == "openai_blog"
    assert item.metadata.get("non_existent", "fallback") == "fallback"


def test_weekly_calendar_publishing_config_snapshot():
    """Covers SCHEMA-003: WeeklyCalendar uses typed PublishingConfigSnapshot."""
    from content_creation.models.calendar import PublishingConfigSnapshot, WeeklyCalendar

    cal = WeeklyCalendar(
        week_start="2026-05-18",
        week_end="2026-05-24",
        posts=[],
        total_posts=0,
        format_counts={},
        topics_used=[],
        generated_at="2026-05-16T12:00:00Z",
        config_snapshot={"weekly_targets": {"short_video": 3}, "custom_rule": True},
    )
    assert isinstance(cal.config_snapshot, PublishingConfigSnapshot)
    assert cal.config_snapshot.weekly_targets == {"short_video": 3}
    assert cal.config_snapshot["custom_rule"] is True
    assert cal.config_snapshot.get("weekly_targets") == {"short_video": 3}


def test_content_intelligence_quality_status_schema():
    """Covers SCHEMA-004: ContentIntelligence.quality_status validates against QualityStatus enum."""
    from pydantic import ValidationError
    from content_creation.domains.content_intelligence.model import (
        ContentIntelligence, ContrastPair, EmotionalRegister, Hook, TopicType
    )
    from content_creation.domains.content_intelligence.quality import QualityStatus

    base_kwargs = dict(
        topic_id="t1",
        generated_at="2026-05-16T12:00:00Z",
        topic_type=TopicType.PAPER,
        timeliness_hook="",
        primary_hook=Hook(hook_text="Hook 1", hook_type="question", source_field="f1"),
        secondary_hook=Hook(hook_text="Hook 2", hook_type="bold_claim", source_field="f2"),
        story_angle="Angle",
        curiosity_gap="Gap",
        contrast_pair=ContrastPair(before="B", after="A"),
        emotional_register=EmotionalRegister.CLARITY,
    )

    ci_valid = ContentIntelligence(**base_kwargs, quality_status="ready")
    assert ci_valid.quality_status == QualityStatus.READY

    with pytest.raises(ValidationError):
        ContentIntelligence(**base_kwargs, quality_status="invalid_random_quality")
