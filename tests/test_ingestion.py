"""Tests for ingestion components."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from content_creation.collectors.rss import RSSCollector
from content_creation.ingestion import IngestionEngine
from content_creation.models.topic import TopicItem


def test_rss_collector_fetch_errors():
    """Test RSSCollector error handling during fetch."""
    config = {"id": "test_feed", "source": "test_source", "url": "https://example.com/feed"}
    collector = RSSCollector(config)
    
    # Mock HTTP error
    with patch("feedparser.parse") as mock_parse:
        mock_result = MagicMock()
        mock_result.get.return_value = 404
        mock_parse.return_value = mock_result
        with pytest.raises(ValueError, match="HTTP error 404"):
            collector.fetch()
            
    # Mock bozo (diagnostic only)
    with patch("feedparser.parse") as mock_parse:
        mock_result = MagicMock(bozo=True, bozo_exception=Exception("test"), entries=[{"link": "http://x.com"}])
        mock_result.get.return_value = 200
        mock_parse.return_value = mock_result
        result = collector.fetch()
        assert result.bozo is True
        assert len(result.entries) == 1

    # Mock bozo with no entries (should fail)
    with patch("feedparser.parse") as mock_parse:
        mock_result = MagicMock(bozo=True, bozo_exception=Exception("fatal"), entries=[])
        mock_result.get.return_value = 200
        mock_parse.return_value = mock_result
        with pytest.raises(ValueError, match="Feed parse failed with bozo error and no entries"):
            collector.fetch()


def test_rss_collector_missing_url():
    """Test RSSCollector raises error for missing URLs."""
    config = {"id": "test_feed", "source": "test_source"}
    collector = RSSCollector(config)
    
    # Missing both link and id
    record = {"title": "No URL"}
    with pytest.raises(ValueError, match="Record has no link or id"):
        collector.normalize(record)


def test_rss_collector_defensive_author():
    """Test RSSCollector handles various author structures defensively."""
    config = {"id": "test_feed", "source": "test_source"}
    collector = RSSCollector(config)
    
    # Authors list with dict
    record = {
        "link": "http://x.com",
        "authors": [{"name": "Author A"}]
    }
    item = collector.normalize(record)
    assert item.author == "Author A"
    
    # Authors list with string
    record = {
        "link": "http://y.com",
        "authors": ["Author B"]
    }
    item = collector.normalize(record)
    assert item.author == "Author B"
    
    # Missing author
    record = {"link": "http://z.com"}
    item = collector.normalize(record)
    assert item.author == "unknown"


def test_rss_collector_source_validation():
    """Test RSSCollector validates source name in config."""
    with pytest.raises(ValueError, match="missing 'source' field"):
        RSSCollector({"id": "test"})


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
