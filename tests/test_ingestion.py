"""Tests for ingestion components."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from content_creation.collectors.rss import RSSCollector
from content_creation.ingestion import IngestionEngine
from content_creation.models.topic import TopicItem


def test_rss_collector_normalization():
    """Test RSS record normalization."""
    config = {"id": "test_feed", "source": "test_source", "category": "news"}
    collector = RSSCollector(config)
    
    record = {
        "link": "https://example.com/item1",
        "title": "Item 1",
        "published_parsed": (2026, 4, 30, 12, 0, 0, 3, 120, 0),
        "author": "John Doe",
        "summary": "This is a summary."
    }
    
    item = collector.normalize(record)
    assert isinstance(item, TopicItem)
    assert item.title == "Item 1"
    assert item.author == "John Doe"
    assert item.published_at == "2026-04-30T12:00:00"
    assert item.source == "test_source"


def test_ingestion_engine_filter():
    """Test IngestionEngine collector filtering."""
    config = {
        "feeds": [
            {"id": "feed1", "source": "src1", "enabled": True},
            {"id": "feed2", "source": "src2", "enabled": True},
            {"id": "feed3", "source": "src1", "enabled": False},
        ]
    }
    
    # Mock storage
    mock_storage = MagicMock()
    engine = IngestionEngine(config, mock_storage)
    
    # Filter by source
    collectors = engine.get_collectors(source_filter="src1")
    assert len(collectors) == 1
    assert collectors[0].source_id == "feed1"
    
    # Filter by ID
    collectors = engine.get_collectors(source_filter="feed2")
    assert len(collectors) == 1
    assert collectors[0].source_id == "feed2"
    
    # All enabled
    collectors = engine.get_collectors()
    assert len(collectors) == 2
