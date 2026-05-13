"""Tests for local storage."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch
from content_creation.storage.local import LocalStorage
from content_creation.models.topic import TopicItem, TopicCategory


def test_local_storage_not_writeable(tmp_path):
    """Test LocalStorage fails if base directory is not writeable."""
    # We can simulate this by mocking 'open' to raise OSError for the write test file
    with patch("builtins.open") as mock_file:
        mock_file.side_effect = OSError("Read-only file system")
        with pytest.raises(OSError, match="is not writeable"):
            LocalStorage(tmp_path)


def test_local_storage_save_and_load(tmp_path):
    """Test saving and loading a staged item."""
    storage = LocalStorage(tmp_path)
    
    url = "https://example.com/item"
    item = TopicItem(
        id=TopicItem.generate_id(url),
        title="Test Item",
        url=url,
        source="test",
        published_at="2026-04-30T12:00:00Z",
        raw_text="Some content",
        category=TopicCategory.TOOL
    )
    
    storage.save_staged(item)
    assert storage.exists(item.id)
    
    loaded_item = storage.get_staged(item.id)
    assert loaded_item is not None
    assert loaded_item.title == "Test Item"
    assert loaded_item.category == TopicCategory.TOOL


def test_local_storage_list_staged(tmp_path):
    """Test listing staged items."""
    storage = LocalStorage(tmp_path)
    
    for i in range(3):
        url = f"https://example.com/item{i}"
        item = TopicItem(
            id=TopicItem.generate_id(url),
            title=f"Item {i}",
            url=url,
            source="test",
            published_at="2026-04-30T12:00:00Z",
            raw_text="Some content"
        )
        storage.save_staged(item)
    
    items = storage.list_staged()
    assert len(items) == 3
    titles = [it.title for it in items]
    assert "Item 0" in titles
    assert "Item 1" in titles
    assert "Item 2" in titles
