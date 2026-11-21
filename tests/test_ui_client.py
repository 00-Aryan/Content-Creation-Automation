"""Unit tests for ServiceClient operations snapshot, event timeline, and storyboard existence checks."""

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
import pytest

from content_creation.application.context import ApplicationContext
from content_creation.events.store.schema import create_event_store_schema
from content_creation.events.store.sqlite_repository import SQLiteEventRepository
from content_creation.events.store.models import EventRecord
from content_creation.ui.services.client import ServiceClient
from content_creation.ui.components.timeline import render_event_timeline


@pytest.fixture
def test_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Fixture that configures an isolated workspace root for ServiceClient."""
    from content_creation.ui.services.client import (
        get_context,
        get_notification_db,
        get_sse_infrastructure,
    )
    get_context.clear()
    get_notification_db.clear()
    get_sse_infrastructure.clear()
    monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "storyboards").mkdir(parents=True, exist_ok=True)
    yield tmp_path
    get_context.clear()
    get_notification_db.clear()
    get_sse_infrastructure.clear()


def test_dead_003_properties_removed() -> None:
    """DEAD-003: Verify legacy wrapper properties were removed from ServiceClient."""
    dead_properties = [
        "collect",
        "brief",
        "content_intelligence",
        "asset_generation",
        "asset_review",
        "brief_review",
    ]
    for prop in dead_properties:
        assert not hasattr(ServiceClient, prop), f"Property {prop} should be removed per DEAD-003"


def test_storyboard_file_exists(test_workspace: Path) -> None:
    """Verify storyboard_file_exists correctly identifies disk presence."""
    client = ServiceClient()
    topic_id = "test-topic-123"

    assert client.storyboard_file_exists(topic_id) is False

    # Create empty (0-byte) storyboard file
    storyboard_file = test_workspace / "data" / "storyboards" / f"{topic_id}.json"
    storyboard_file.write_bytes(b"")

    # File exists on disk, even if 0-byte
    assert client.storyboard_file_exists(topic_id) is True


def test_get_operations_snapshot(test_workspace: Path) -> None:
    """Verify ServiceClient.get_operations_snapshot returns valid snapshot without locking."""
    client = ServiceClient()
    snapshot = client.get_operations_snapshot()

    assert snapshot is not None
    assert hasattr(snapshot, "overall_status")
    assert hasattr(snapshot, "components")
    assert isinstance(snapshot.components, list)
    assert hasattr(snapshot, "queue_metrics")
    assert hasattr(snapshot, "worker_metrics")


def test_get_event_timeline_empty(test_workspace: Path) -> None:
    """Verify get_event_timeline returns empty list when no events exist."""
    client = ServiceClient()
    events = client.get_event_timeline(limit=10)
    assert events == []


def test_get_event_timeline_with_events(test_workspace: Path) -> None:
    """Verify get_event_timeline queries and returns event records."""
    data_dir = test_workspace / "data"
    event_db_path = data_dir / "events.db"

    # Seed events.db
    from uuid import uuid4
    repo = SQLiteEventRepository(str(event_db_path))
    record = EventRecord(
        event_id=uuid4(),
        event_name="topic_scored",
        category="workflow",
        source="unit_test",
        correlation_id="corr-123",
        entity_type="topic",
        entity_id="t-1",
        payload_json="{}",
        created_at=datetime.now(timezone.utc),
    )
    repo.save_event(record)
    repo.close()

    client = ServiceClient()
    events = client.get_event_timeline(limit=10)

    assert len(events) == 1
    assert events[0].event_name == "topic_scored"
    assert events[0].entity_id == "t-1"


@dataclass
class DummyEvent:
    event_name: str
    category: str
    entity_type: str
    entity_id: str
    source: str
    created_at: datetime
    correlation_id: str = "corr-1"


def test_timeline_component_rendering() -> None:
    """Verify timeline component renders without requiring backend SQLite or EventRecord imports."""
    dummy_events = [
        DummyEvent(
            event_name="topic_collected",
            category="workflow",
            entity_type="topic",
            entity_id="topic-abc-123",
            source="collector",
            created_at=datetime.now(timezone.utc),
        )
    ]
    # Should execute without throwing any exception
    render_event_timeline(events=dummy_events, title="Test Timeline")
