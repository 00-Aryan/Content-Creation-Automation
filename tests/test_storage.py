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


def test_local_storage_cp1252_smart_quotes_decoding_fallback(tmp_path, caplog):
    """Covers ERR-011: LocalStorage gracefully handles Windows CP1252 smart quotes with warning."""
    import logging

    storage = LocalStorage(tmp_path)
    file_path = storage.staged_dir / "cp1252_item.json"

    # Write JSON payload encoded in cp1252 containing smart quotes and em-dash (0x93, 0x94, 0x97)
    raw_cp1252 = (
        '{\n'
        '  "id": "cp1252_item",\n'
        '  "title": "\\u201cAI Research\\u201d \\u2014 Breakthrough",\n'
        '  "url": "https://example.com/item",\n'
        '  "source": "rss",\n'
        '  "published_at": "2026-04-30T12:00:00Z",\n'
        '  "raw_text": "Content with smart quotes \\u201ctest\\u201d and em-dash \\u2014 here."\n'
        '}'
    )
    # Convert unicode characters to raw cp1252 bytes
    encoded_bytes = (
        '{\n'
        '  "id": "cp1252_item",\n'
        '  "title": "\u201cAI Research\u201d \u2014 Breakthrough",\n'
        '  "url": "https://example.com/item",\n'
        '  "source": "rss",\n'
        '  "published_at": "2026-04-30T12:00:00Z",\n'
        '  "raw_text": "Content with smart quotes \u201ctest\u201d and em-dash \u2014 here."\n'
        '}'
    ).encode("cp1252")
    file_path.write_bytes(encoded_bytes)

    with caplog.at_level(logging.WARNING):
        item = storage.get_staged("cp1252_item")

    assert item is not None
    assert "AI Research" in item.title
    assert any("falling back to cp1252" in r.message for r in caplog.records)
