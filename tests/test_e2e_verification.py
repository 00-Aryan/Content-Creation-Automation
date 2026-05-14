"""End-to-end verification of Week 1 pipeline."""

import json
import pytest
import sys
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from content_creation.cli import main

@pytest.fixture
def mock_env(tmp_path):
    """Setup a mocked environment for E2E testing."""
    base_dir = tmp_path
    config_dir = base_dir / "config"
    config_dir.mkdir()
    
    # Mock feeds.yaml
    feeds_config = {
        "feeds": [
            {
                "id": "test_feed",
                "source": "test_source",
                "url": "https://example.com/rss",
                "enabled": True,
                "category": "paper"
            }
        ]
    }
    with open(config_dir / "feeds.yaml", "w") as f:
        yaml.dump(feeds_config, f)
        
    # Mock scoring.yaml
    scoring_config = {
    "scoring_rules": {
        "student_usefulness": {"weight": 0.30, "enabled": True},
        "novelty": {"weight": 0.25, "enabled": True},
        "credibility": {"weight": 0.20, "enabled": True},
        "explainability": {"weight": 0.15, "enabled": True},
        "hook_potential": {"weight": 0.10, "enabled": True}
    }
}
    with open(config_dir / "scoring.yaml", "w") as f:
        yaml.dump(scoring_config, f)
        
    return base_dir

@patch("content_creation.collectors.rss.feedparser.parse")
def test_e2e_pipeline(mock_parse, mock_env):
    """Verify end-to-end pipeline: collect -> score."""
    base_dir = mock_env
    
    # 1. Mock RSS feed response
    mock_feed = MagicMock()
    mock_feed.entries = [
        {
            "link": "https://example.com/item1",
            "title": "Item 1",
            "published_parsed": (2026, 5, 1, 12, 0, 0, 4, 121, 0),
            "summary": "This is a detailed summary of the research paper about machine learning techniques that provides enough content to pass the minimum text length filter for scoring.",
            "author": "Author 1"
        }
    ]
    mock_feed.get.return_value = 200
    mock_feed.bozo = False
    mock_parse.return_value = mock_feed
    
    # 2. Run 'collect --all'
    with patch.object(sys, "argv", ["content-creation", "collect", "--all"]):
        with patch("pathlib.Path.cwd", return_value=base_dir):
            result = main()
            assert result == 0
            
    # Verify item is staged
    staged_dir = base_dir / "data" / "staged"
    staged_files = list(staged_dir.glob("*.json"))
    assert len(staged_files) == 1
    
    # 3. Run 'score-topics'
    with patch.object(sys, "argv", ["content-creation", "score-topics"]):
        with patch("pathlib.Path.cwd", return_value=base_dir):
            result = main()
            assert result == 0
            
    # Verify item is scored
    scored_dir = base_dir / "data" / "scored"
    scored_files = list(scored_dir.glob("*.json"))
    assert len(scored_files) == 1
    
    with open(scored_files[0], "r") as f:
        scored_item = json.load(f)
        assert "priority_score" in scored_item
        assert scored_item["status"] == "scored"
