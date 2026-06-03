"""Tests for Content Intelligence and Storyboard storage integration."""

import pytest
from pathlib import Path
from content_creation.storage.local import LocalStorage
from content_creation.application.context import ApplicationContext
from content_creation.domains.content_intelligence import (
    ContentIntelligence,
    Hook,
    ContrastPair,
    EmotionalRegister,
    TopicType,
)
from content_creation.domains.storyboard import Storyboard


def test_storage_integration_directories(tmp_path):
    """Test that Content Intelligence and Storyboard directories are correctly setup."""
    storage = LocalStorage(tmp_path)
    
    assert storage.content_intelligence_dir == tmp_path / "data" / "content_intelligence"
    assert storage.storyboards_dir == tmp_path / "data" / "storyboards"
    
    assert storage.content_intelligence_dir.exists()
    assert storage.storyboards_dir.exists()


def test_application_context_getters(tmp_path):
    """Test that ApplicationContext exposes directory getters dynamically."""
    ctx = ApplicationContext.create(tmp_path)
    
    assert ctx.content_intelligence_dir == tmp_path / "data" / "content_intelligence"
    assert ctx.storyboards_dir == tmp_path / "data" / "storyboards"


def test_content_intelligence_save_and_list(tmp_path):
    """Test saving and listing Content Intelligence items."""
    storage = LocalStorage(tmp_path)
    
    ci = ContentIntelligence(
        topic_id="test_topic_ci",
        generated_at="2026-05-30T10:00:00+00:00",
        topic_type=TopicType.PAPER,
        timeliness_hook="Published this week",
        primary_hook=Hook(hook_text="Why?", hook_type="question", source_field="why_it_matters"),
        secondary_hook=Hook(hook_text="X is dead.", hook_type="bold_claim", source_field="limitation"),
        story_angle="The paradigm shift",
        curiosity_gap="How does it work?",
        contrast_pair=ContrastPair(before="old way", after="new way"),
        emotional_register=EmotionalRegister.SURPRISE,
    )
    
    # Save the item
    saved_path = storage.save_content_intelligence(ci)
    assert saved_path == storage.content_intelligence_dir / "test_topic_ci.json"
    assert saved_path.exists()
    
    # List the items
    all_ci = storage.list_content_intelligence()
    assert len(all_ci) == 1
    assert all_ci[0].topic_id == "test_topic_ci"
    assert all_ci[0].story_angle == "The paradigm shift"


def test_storyboard_save_and_list(tmp_path):
    """Test saving and listing Storyboard items."""
    storage = LocalStorage(tmp_path)
    
    sb = Storyboard(
        topic_id="test_topic_sb",
        generated_at="2026-05-31T00:00:00+00:00",
        formats_planned=["short_video", "carousel"],
        script_hook="Hook A",
        carousel_hook="Hook B",
        newsletter_hook="Hook C",
        thumbnail_hook="Six Words Max Here",
        script_cta="See the carousel",
        carousel_cta="Read the newsletter",
        newsletter_cta="Watch the video",
        script_claims=["claim1"],
        carousel_claims=["claim2"],
        newsletter_claims=["claim3"],
        visual_style="diagram_overlay",
        visual_metaphor="A librarian scanning books",
    )
    
    # Save the item
    saved_path = storage.save_storyboard(sb)
    assert saved_path == storage.storyboards_dir / "test_topic_sb.json"
    assert saved_path.exists()
    
    # List the items
    all_sb = storage.list_storyboards()
    assert len(all_sb) == 1
    assert all_sb[0].topic_id == "test_topic_sb"
    assert all_sb[0].visual_style == "diagram_overlay"
