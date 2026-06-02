"""Tests for workflow integration of new stages."""

import json
import pytest
from pathlib import Path
from content_creation.workflow.state import (
    WorkflowState,
    WorkflowStateManager,
    ArtifactState,
)


def test_workflow_state_initialization():
    """Verify that all target workflow stages are initialized to pending by default."""
    state = WorkflowState(topic_id="test_topic")
    
    expected_stages = [
        "brief",
        "content_intelligence",
        "storyboard",
        "thumbnail",
        "script",
        "carousel",
        "newsletter",
    ]
    
    assert state.topic_id == "test_topic"
    for stage in expected_stages:
        assert stage in state.stages
        assert state.stages[stage].status == "pending"
        assert state.stages[stage].topic_id == "test_topic"


def test_workflow_state_serialization(tmp_path):
    """Verify that serializing and loading a workflow state preserves the new stages."""
    manager = WorkflowStateManager(tmp_path)
    topic_id = "test_serialization_topic"
    
    # Save a default pending state
    state = manager.load_state(topic_id)
    manager.save_state(state)
    
    # Load and verify it was written and read properly
    loaded_state = manager.load_state(topic_id)
    assert loaded_state.topic_id == topic_id
    assert "content_intelligence" in loaded_state.stages
    assert loaded_state.stages["content_intelligence"].status == "pending"
    assert "storyboard" in loaded_state.stages
    assert loaded_state.stages["storyboard"].status == "pending"


def test_workflow_mark_completed_and_checks(tmp_path):
    """Verify that new stages can be marked completed and checked."""
    manager = WorkflowStateManager(tmp_path)
    topic_id = "topic_abc"
    
    # Initially stages are not completed
    assert not manager.stage_completed(topic_id, "content_intelligence")
    assert not manager.stage_completed(topic_id, "storyboard")
    
    # Mark content_intelligence completed
    manager.mark_completed(
        topic_id=topic_id,
        stage="content_intelligence",
        provider="gemini",
        retries=1,
        artifact_path="/path/to/ci.json",
    )
    
    assert manager.stage_completed(topic_id, "content_intelligence")
    assert not manager.stage_completed(topic_id, "storyboard")
    
    # Mark storyboard completed
    manager.mark_completed(
        topic_id=topic_id,
        stage="storyboard",
        provider="gemini",
        retries=0,
        artifact_path="/path/to/sb.json",
    )
    
    assert manager.stage_completed(topic_id, "content_intelligence")
    assert manager.stage_completed(topic_id, "storyboard")
    
    # Reload and check from disk
    loaded_state = manager.load_state(topic_id)
    assert loaded_state.stages["content_intelligence"].status == "completed"
    assert loaded_state.stages["content_intelligence"].provider == "gemini"
    assert loaded_state.stages["content_intelligence"].retries == 1
    assert loaded_state.stages["content_intelligence"].artifact_path == "/path/to/ci.json"
    
    assert loaded_state.stages["storyboard"].status == "completed"
    assert loaded_state.stages["storyboard"].provider == "gemini"
    assert loaded_state.stages["storyboard"].retries == 0
    assert loaded_state.stages["storyboard"].artifact_path == "/path/to/sb.json"


def test_workflow_mark_failed(tmp_path):
    """Verify that new stages can be marked failed."""
    manager = WorkflowStateManager(tmp_path)
    topic_id = "topic_failed_test"
    
    manager.mark_failed(topic_id=topic_id, stage="content_intelligence", retries=2)
    manager.mark_failed(topic_id=topic_id, stage="storyboard", retries=3)
    
    assert not manager.stage_completed(topic_id, "content_intelligence")
    assert not manager.stage_completed(topic_id, "storyboard")
    
    loaded_state = manager.load_state(topic_id)
    assert loaded_state.stages["content_intelligence"].status == "failed"
    assert loaded_state.stages["content_intelligence"].retries == 2
    
    assert loaded_state.stages["storyboard"].status == "failed"
    assert loaded_state.stages["storyboard"].retries == 3


def test_workflow_pending_stages(tmp_path):
    """Verify that pending stages correctly identifies new uncompleted stages."""
    manager = WorkflowStateManager(tmp_path)
    topic_id = "topic_pending_test"
    
    all_stages = [
        "brief",
        "content_intelligence",
        "storyboard",
        "thumbnail",
        "script",
        "carousel",
        "newsletter",
    ]
    
    # All are initially pending/not completed
    pending = manager.get_pending_stages(topic_id, all_stages)
    assert len(pending) == 7
    
    # Mark content_intelligence completed
    manager.mark_completed(topic_id, "content_intelligence")
    
    pending = manager.get_pending_stages(topic_id, all_stages)
    assert len(pending) == 6
    assert "content_intelligence" not in pending
    assert "storyboard" in pending
