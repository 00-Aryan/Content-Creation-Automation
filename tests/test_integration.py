"""Integration tests for the ingestion pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from content_creation.ingestion import IngestionEngine
from content_creation.storage.local import LocalStorage


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
