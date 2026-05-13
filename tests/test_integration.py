"""Integration tests for the ingestion pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from content_creation.ingestion import IngestionEngine
from content_creation.storage.local import LocalStorage


def test_concurrent_ingestion_deduplication(tmp_path):
    """Test that ingestion engine handles concurrent writes gracefully."""
    storage = LocalStorage(tmp_path)
    config = {
        "feeds": [
            {
                "id": "test_feed",
                "url": "https://example.com/rss",
                "source": "test_source",
                "enabled": True
            }
        ]
    }
    engine = IngestionEngine(config, storage)
    
    mock_item = MagicMock()
    mock_item.id = "shared-id"
    
    # Mock collector to return one record
    mock_collector = MagicMock()
    mock_collector.source_id = "test_feed"
    mock_collector.fetch.return_value = MagicMock(entries=[{"link": "shared-link"}])
    mock_collector.parse.return_value = [{"link": "shared-link"}]
    mock_collector.normalize.return_value = mock_item
    
    with patch.object(engine, "get_collectors", return_value=[mock_collector]):
        # Simulate race condition: 
        # 1. exists() returns False (passed)
        # 2. But save_staged() raises FileExistsError (someone else won the race)
        with patch.object(storage, "exists", return_value=False):
            with patch.object(storage, "save_staged", side_effect=FileExistsError):
                new_items = engine.run()
                
                # Should handle the error, return 0 new items, and log it (implicitly)
                assert len(new_items) == 0
                # The engine logs "Completed ...: 0 new, 1 duplicates."
@patch("content_creation.collectors.rss.feedparser.parse")
def test_full_ingestion_loop(mock_parse, tmp_path):
    """Test full ingestion loop from fetch to storage."""
    # 1. Setup mock data
    mock_feed = MagicMock()
    mock_entry = {
        "link": "https://example.com/test-paper",
        "title": "Test Paper Title",
        "published_parsed": (2026, 4, 30, 10, 0, 0, 3, 120, 0),
        "author": "Test Author",
        "summary": "Test summary content",
        "tags": [{"term": "ML"}, {"term": "AI"}]
    }
    mock_feed.entries = [mock_entry]
    mock_feed.get.return_value = 200
    mock_feed.bozo = False
    mock_parse.return_value = mock_feed

    # 2. Setup engine with temp storage
    config = {
        "feeds": [
            {
                "id": "test_feed",
                "name": "Test Feed",
                "url": "https://example.com/rss",
                "source": "test_source",
                "category": "paper",
                "enabled": True
            }
        ]
    }
    storage = LocalStorage(tmp_path)
    engine = IngestionEngine(config, storage)

    # 3. Run ingestion
    new_items = engine.run()

    # 4. Verify results
    assert len(new_items) == 1
    item = new_items[0]
    assert item.title == "Test Paper Title"
    assert item.source == "test_source"
    
    # 5. Verify persistence
    assert storage.exists(item.id)
    staged_item = storage.get_staged(item.id)
    assert staged_item.id == item.id
    
    # Verify raw storage
    raw_files = list((tmp_path / "data" / "raw").glob("*.json"))
    assert len(raw_files) == 1
