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


def test_timeline_component_convenience_renderers(test_workspace: Path) -> None:
    """UI-003: Verify workflow, job, and pipeline convenience renderers execute cleanly."""
    from content_creation.ui.components.timeline import (
        render_workflow_timeline,
        render_job_timeline,
        render_pipeline_timeline,
    )
    client = ServiceClient()

    # None of these should crash
    render_workflow_timeline(client, topic_id="topic-abc-123456789")
    render_job_timeline(client, job_id="job-999")
    render_pipeline_timeline(client)


def test_timeline_component_timestamp_parsing_variants() -> None:
    """UI-003: Verify _render_event_row handles string ISO timestamps, naive datetimes, and None."""
    from content_creation.ui.components.timeline import _render_event_row

    # String ISO timestamp
    e_str = DummyEvent(
        event_name="topic_ingested",
        category="workflow",
        entity_type="topic",
        entity_id="t-iso",
        source="rss",
        created_at="2026-11-21T12:00:00Z",  # type: ignore[arg-type]
    )
    _render_event_row(e_str)

    # Naive datetime
    e_naive = DummyEvent(
        event_name="topic_ingested",
        category="job",
        entity_type="job",
        entity_id="j-naive",
        source="worker",
        created_at=datetime(2026, 11, 21, 12, 0, 0),
    )
    _render_event_row(e_naive)

    # None timestamp
    e_none = DummyEvent(
        event_name="topic_ingested",
        category="recovery",
        entity_type="",
        entity_id="",
        source="system",
        created_at=None,  # type: ignore[arg-type]
    )
    _render_event_row(e_none)



def test_get_operations_snapshot_worker_idle_healthy_when_no_jobs(
    test_workspace: Path,
) -> None:
    """UI-002 / ERR-020: Worker component status maps to HEALTHY when no jobs are queued."""
    from content_creation.platform.observability.health import HealthStatus, ComponentType, AlertSeverity

    client = ServiceClient()
    snapshot = client.get_operations_snapshot()

    assert snapshot is not None
    worker_comp = next((c for c in snapshot.components if c.component == ComponentType.WORKER), None)
    assert worker_comp is not None
    assert worker_comp.status == HealthStatus.HEALTHY
    assert "Not running (expected in manual operation mode)" in worker_comp.message

    worker_alert = next((a for a in snapshot.alerts if a.rule_id == "WORKER_OFFLINE"), None)
    if worker_alert:
        assert worker_alert.severity == AlertSeverity.INFO

    # UI-007: SSE component must be excluded from snapshot components
    assert not any(c.component == ComponentType.SSE for c in snapshot.components)


def test_get_operations_snapshot_with_populated_subsystems(test_workspace: Path) -> None:
    """UI-002 / ERR-020: Snapshot reflects populated queue, worker alert, and metrics."""
    import sqlite3
    from uuid import uuid4
    from content_creation.jobs.schema import create_job_schema
    from content_creation.jobs.sqlite_repository import SQLiteJobRepository
    from content_creation.jobs.models import Job, JobStatus
    from content_creation.platform.observability.health import HealthStatus, ComponentType

    data_dir = test_workspace / "data"
    job_conn = sqlite3.connect(str(data_dir / "jobs.db"))
    create_job_schema(job_conn)
    job_repo = SQLiteJobRepository(job_conn)

    # Insert a queued job
    job = Job(
        job_id=uuid4(),
        job_type="generate_assets",
        status=JobStatus.QUEUED,
        priority=1,
        created_at=datetime.now(timezone.utc),
        operator_id="test-operator",
        target_type="topic",
        target_id="t1",
        payload={"topic_id": "t1"},
        correlation_id="corr-101",
    )
    job_repo.create_job(job)
    job_repo.enqueue_job(job.job_id)
    job_conn.commit()
    job_conn.close()

    client = ServiceClient()
    snapshot = client.get_operations_snapshot()

    assert snapshot is not None
    q_metrics = snapshot.queue_metrics or {}
    assert q_metrics.get("queued_count", 0) >= 1

    # Since worker is offline and jobs are queued, worker should be UNHEALTHY
    worker_comp = next((c for c in snapshot.components if c.component == ComponentType.WORKER), None)
    assert worker_comp is not None
    assert worker_comp.status == HealthStatus.UNHEALTHY
    assert "No active workers but jobs are queued" in worker_comp.message


def test_get_operations_snapshot_corrupted_db_fallback(
    test_workspace: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """UI-002 / ERR-020: Corrupted SQLite database produces graceful snapshot without crash."""
    data_dir = test_workspace / "data"
    # Write corrupt data to jobs.db
    (data_dir / "jobs.db").write_text("THIS IS NOT A VALID SQLITE DATABASE", encoding="utf-8")

    client = ServiceClient()
    snapshot = client.get_operations_snapshot()

    # Should not crash; snapshot is returned with available subsystems or unknown status
    assert snapshot is not None
    assert hasattr(snapshot, "overall_status")


def test_get_operations_snapshot_critical_failure_fallback(
    test_workspace: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """UI-002 / ERR-020: Critical unhandled exception returns fallback DashboardSnapshot."""
    import logging
    from content_creation.platform.observability.health import HealthStatus
    from content_creation.platform.observability.service import ObservabilityService

    def failing_snapshot(self: Any) -> Any:
        raise RuntimeError("Simulated total engine breakdown")

    monkeypatch.setattr(ObservabilityService, "snapshot", failing_snapshot)

    client = ServiceClient()
    with caplog.at_level(logging.ERROR):
        snapshot = client.get_operations_snapshot()

    assert snapshot is not None
    assert snapshot.overall_status == HealthStatus.UNKNOWN
    assert any("Failed to build operations snapshot" in r.message for r in caplog.records)


def test_get_event_timeline_filtering_and_limits(test_workspace: Path) -> None:
    """UI-003 / ERR-021: Verify event timeline category and entity filtering with limits."""
    from uuid import uuid4
    data_dir = test_workspace / "data"
    event_db_path = data_dir / "events.db"
    repo = SQLiteEventRepository(str(event_db_path))

    # Seed 3 events: 2 workflow, 1 system
    e1 = EventRecord(
        event_id=uuid4(),
        event_name="topic_collected",
        category="workflow",
        source="unit_test",
        correlation_id="c-1",
        entity_type="topic",
        entity_id="topic-alpha",
        payload_json="{}",
        created_at=datetime.now(timezone.utc),
    )
    e2 = EventRecord(
        event_id=uuid4(),
        event_name="topic_scored",
        category="workflow",
        source="unit_test",
        correlation_id="c-2",
        entity_type="topic",
        entity_id="topic-beta",
        payload_json="{}",
        created_at=datetime.now(timezone.utc),
    )
    e3 = EventRecord(
        event_id=uuid4(),
        event_name="system_reboot",
        category="system",
        source="unit_test",
        correlation_id="c-3",
        entity_type="host",
        entity_id="host-1",
        payload_json="{}",
        created_at=datetime.now(timezone.utc),
    )
    repo.save_event(e1)
    repo.save_event(e2)
    repo.save_event(e3)
    repo.close()

    client = ServiceClient()

    # Category filter
    wf_events = client.get_event_timeline(category="workflow")
    assert len(wf_events) == 2
    assert all(e.category == "workflow" for e in wf_events)

    # Entity filter
    alpha_events = client.get_event_timeline(entity_type="topic", entity_id="topic-alpha")
    assert len(alpha_events) == 1
    assert alpha_events[0].entity_id == "topic-alpha"

    # Limit parameter
    limited = client.get_event_timeline(limit=1)
    assert len(limited) == 1


def test_get_event_timeline_corrupt_db_returns_empty_list(
    test_workspace: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """UI-003 / ERR-021: Corrupt events.db returns empty list with structured warning."""
    import logging
    data_dir = test_workspace / "data"
    (data_dir / "events.db").write_text("CORRUPTED SQLITE BYTES", encoding="utf-8")

    client = ServiceClient()
    with caplog.at_level(logging.WARNING):
        events = client.get_event_timeline()

    assert events == []
    assert any("Failed to query event timeline" in r.message for r in caplog.records)


def test_storyboard_file_exists_and_get_storyboard_matrix(test_workspace: Path) -> None:
    """UI-001 / ERR-006: Verify interaction of storyboard_file_exists with get_storyboard."""
    import json
    client = ServiceClient()

    # Case 1: Topic does not exist
    assert client.storyboard_file_exists("ghost-topic") is False
    assert client.get_storyboard("ghost-topic") is None

    # Case 2: 0-byte corrupted file on disk
    zero_topic = "zero-topic"
    (test_workspace / "data" / "storyboards" / f"{zero_topic}.json").write_bytes(b"")
    assert client.storyboard_file_exists(zero_topic) is True
    assert client.get_storyboard(zero_topic) is None  # JsonRepository returns None on 0-byte

    # Case 3: Valid storyboard file on disk
    valid_topic = "valid-topic"
    valid_storyboard_dict = {
        "topic_id": valid_topic,
        "generated_at": "2026-11-21T00:00:00Z",
        "formats_planned": ["short_video", "carousel"],
        "script_hook": "Hook",
        "script_cta": "CTA",
        "script_claims": ["claim 1"],
        "carousel_hook": "Carousel Hook",
        "carousel_cta": "Carousel CTA",
        "carousel_claims": ["claim 1"],
        "newsletter_hook": "News Hook",
        "newsletter_cta": "News CTA",
        "newsletter_claims": ["claim 1"],
        "thumbnail_hook": "Thumb Hook",
        "visual_metaphor": "Metaphor",
        "visual_style": "clean_minimal",
    }
    (test_workspace / "data" / "storyboards" / f"{valid_topic}.json").write_text(
        json.dumps(valid_storyboard_dict), encoding="utf-8"
    )
    assert client.storyboard_file_exists(valid_topic) is True
    loaded_sb = client.get_storyboard(valid_topic)
    assert loaded_sb is not None
    assert loaded_sb.topic_id == valid_topic
    assert loaded_sb.script_hook == "Hook"


def test_deprecated_sse_shims_are_safe_noops(test_workspace: Path) -> None:
    """UI-004 / DEAD-004: Deprecated SSE methods are non-raising no-op shims."""
    client = ServiceClient()
    assert client.sse_port == 8502

    # Should execute without throwing exceptions
    client.publish_notification_event(None)
    client.publish_read_event("notif-123")
    client.publish_archive_event("notif-123")


def test_notification_facade_methods(test_workspace: Path) -> None:
    """UI-004: ServiceClient provides notification unread count and summary."""
    client = ServiceClient()
    unread = client.get_notification_unread_count()
    assert isinstance(unread, int)
    assert unread >= 0

    summary = client.get_notification_summary()
    assert summary is not None
    assert hasattr(summary, "total_unread")


def test_create_manual_topic_persists_valid_topic(test_workspace: Path) -> None:
    """Verify ServiceClient.create_manual_topic persists a valid TopicItem to data/staged."""
    import json
    from content_creation.models.topic import TopicStatus
    client = ServiceClient()
    topic = client.create_manual_topic(
        title="FlashAttention-3: Ultra Fast Attention",
        notes="Novel kernel optimizations for hopper architecture.",
        url="https://arxiv.org/abs/2407.08608",
        source_id="arxiv",
    )
    assert topic.id is not None
    assert topic.title == "FlashAttention-3: Ultra Fast Attention"
    assert topic.status == TopicStatus.STAGED
    assert topic.source == "arxiv"
    assert topic.url == "https://arxiv.org/abs/2407.08608"

    # Verify presence on disk
    target_file = test_workspace / "data" / "staged" / f"{topic.id}.json"
    assert target_file.exists()
    content = json.loads(target_file.read_text(encoding="utf-8"))
    assert content["id"] == topic.id
    assert content["title"] == topic.title
    assert content["status"] == "staged"


def test_create_manual_topic_validation(test_workspace: Path) -> None:
    """Verify ServiceClient.create_manual_topic rejects empty titles."""
    client = ServiceClient()
    with pytest.raises(ValueError, match="title cannot be empty"):
        client.create_manual_topic(title="   ", notes="Some notes")


def test_format_voiceover_script_and_production_cue_sheet(test_workspace: Path) -> None:
    """Verify ServiceClient formatting utilities for TTS voiceover and production cue sheet."""
    import json
    client = ServiceClient()
    topic_id = "test-cue-topic"

    # Empty case
    vo_empty = client.format_voiceover_script(topic_id)
    assert "No video script found" in vo_empty
    cue_empty = client.format_production_cue_sheet(topic_id)
    assert "No script or storyboard assets found" in cue_empty

    # Seed script and storyboard
    scripts_dir = test_workspace / "data" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_payload = {
        "topic_id": topic_id,
        "format": "short_video",
        "hook": "Ever wondered how flash attention works?",
        "script_sections": ["First, it breaks matrices into tiles.", "Second, it computes softmax online."],
        "cta": "Check the repo link below.",
        "claims_used": ["Fast GPU compute"],
        "source_links": ["https://arxiv.org/abs/2407.08608"],
        "review_status": "draft",
        "generated_at": "2026-11-22T00:00:00Z",
        "shorts_segments": [
            {
                "section": "hook",
                "time_range": "0:00-0:05",
                "visual": "Zoom into glowing GPU die",
                "audio": "Synth drop",
                "spoken": "Ever wondered how flash attention works?",
            },
            {
                "section": "explanation",
                "time_range": "0:05-0:30",
                "visual": "Tiled memory animation",
                "audio": "Upbeat ambient",
                "spoken": "It computes softmax online without writing intermediate values.",
            },
            {
                "section": "cta",
                "time_range": "0:30-0:35",
                "visual": "Paper title screen",
                "audio": "Fade out",
                "spoken": "Follow for more ML deep dives.",
            },
        ],
    }
    (scripts_dir / f"{topic_id}.json").write_text(json.dumps(script_payload), encoding="utf-8")

    storyboards_dir = test_workspace / "data" / "storyboards"
    storyboards_dir.mkdir(parents=True, exist_ok=True)
    sb_payload = {
        "topic_id": topic_id,
        "generated_at": "2026-11-22T00:00:00Z",
        "formats_planned": ["short_video"],
        "script_hook": "Hook",
        "script_cta": "CTA",
        "script_claims": ["claim 1"],
        "carousel_hook": "Hook",
        "carousel_cta": "CTA",
        "carousel_claims": ["claim 1"],
        "newsletter_hook": "Hook",
        "newsletter_cta": "CTA",
        "newsletter_claims": ["claim 1"],
        "thumbnail_hook": "Thumb",
        "visual_metaphor": "Memory conveyor belt",
        "visual_style": "clean_minimal",
    }
    (storyboards_dir / f"{topic_id}.json").write_text(json.dumps(sb_payload), encoding="utf-8")

    # Verify voiceover extraction
    vo = client.format_voiceover_script(topic_id)
    assert "Ever wondered how flash attention works?" in vo
    assert "It computes softmax online" in vo
    assert "Follow for more ML deep dives." in vo

    # Verify cue sheet formatting
    cue = client.format_production_cue_sheet(topic_id)
    assert "PRODUCTION CUE SHEET" in cue
    assert "Visual Metaphor: Memory conveyor belt" in cue
    assert "SCENE 1: [0:00-0:05] - HOOK" in cue
    assert "👁️ VISUAL:  Zoom into glowing GPU die" in cue
    assert "🎙️ SPOKEN:  \"Ever wondered how flash attention works?\"" in cue


def test_ensure_database_initialized(test_workspace: Path) -> None:
    """REL-002: Verify ensure_database_initialized idempotently bootstraps database tables."""
    from content_creation.ui.services.client import ensure_database_initialized
    from content_creation.platform.storage.database import get_db_path, create_connection

    ensure_database_initialized.clear()
    res = ensure_database_initialized()
    assert res is True

    # Check that tables exist
    target_db = get_db_path(test_workspace)
    assert target_db.exists()
    conn = create_connection(target_db)
    try:
        tables = [
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        ]
        assert "jobs" in tables
        assert "events" in tables
        assert "notifications" in tables
        assert "metrics" in tables
        assert "audit" in tables
    finally:
        conn.close()


def test_get_operations_snapshot_excludes_retired_sse_and_downgrades_worker_alert(
    test_workspace: Path,
) -> None:
    """UI-007 & UI-008: Operations snapshot excludes SSE component and downgrades worker offline alert to INFO."""
    from content_creation.platform.observability.health import ComponentType, AlertSeverity

    client = ServiceClient()
    snapshot = client.get_operations_snapshot()
    assert snapshot is not None

    # UI-007: SSE component must be completely absent from snapshot components
    assert not any(c.component == ComponentType.SSE for c in snapshot.components)
    assert not any(c.name.lower() == "sse" for c in snapshot.components)

    # UI-008: In manual operation mode without jobs, WORKER_OFFLINE is INFO severity
    worker_alert = next((a for a in snapshot.alerts if a.rule_id == "WORKER_OFFLINE"), None)
    if worker_alert:
        assert worker_alert.severity == AlertSeverity.INFO
        assert "manual mode" in worker_alert.title


# ---------------------------------------------------------------------------
# High-Signal BVA, Fault Injection, and Idempotency Suites (Phase 2D QA)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "empty_title",
    ["", "   ", "\t", "\n", " \t \r\n "],
)
def test_create_manual_topic_bva_empty_and_whitespace_titles(
    test_workspace: Path,
    empty_title: str,
) -> None:
    """ERR-013: Boundary Value Analysis on manual topic creation rejecting empty/whitespace titles."""
    client = ServiceClient()
    with pytest.raises(ValueError, match="title cannot be empty"):
        client.create_manual_topic(title=empty_title, notes="Some contextual notes")


def test_create_manual_topic_whitespace_normalization_and_defaults(
    test_workspace: Path,
) -> None:
    """Stage 1 Contract: Verify whitespace normalization and fallback defaults in create_manual_topic."""
    client = ServiceClient()
    topic = client.create_manual_topic(
        title="   Attention Is All You Need   \n",
        notes="   Classic transformer architecture paper.   \t",
        url="   ",
        source_id="   ",
    )
    assert topic.title == "Attention Is All You Need"
    assert topic.raw_text == "Classic transformer architecture paper."
    assert topic.source == "manual"
    assert topic.url.startswith("urn:manual:")
    assert topic.author == "creator"
    assert "manual" in topic.topic_tags
    assert topic.metadata.source_type == "manual"


def test_create_manual_topic_unicode_and_smart_punctuation_persistence(
    test_workspace: Path,
) -> None:
    """ERR-011: Verify create_manual_topic correctly encodes and persists Unicode, smart quotes, and emojis."""
    import json
    client = ServiceClient()
    unicode_title = "FlashAttention-3: 🚀 極速 ‘Smart Quotes’ & — En-dash"
    unicode_notes = "Key breakthrough: reduced latency by 50% under H100 GPU architecture. “Innovative tiling”."
    
    topic = client.create_manual_topic(
        title=unicode_title,
        notes=unicode_notes,
        url="https://arxiv.org/abs/2407.08608",
        source_id="arxiv",
    )
    assert topic.title == unicode_title
    assert topic.raw_text == unicode_notes

    # Read directly from disk with UTF-8
    disk_file = test_workspace / "data" / "staged" / f"{topic.id}.json"
    assert disk_file.exists()
    disk_data = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_data["title"] == unicode_title
    assert disk_data["raw_text"] == unicode_notes


def test_create_manual_topic_extreme_length_boundary(
    test_workspace: Path,
) -> None:
    """BVA: Verify manual topic handles extreme character lengths cleanly with excerpt truncation."""
    import json
    client = ServiceClient()
    long_title = "Title Boundary Test " + ("A" * 2000)
    long_notes = "Detailed research notes " + ("B" * 5000)

    topic = client.create_manual_topic(
        title=long_title,
        notes=long_notes,
        url="https://example.com/long-topic",
    )
    assert topic.title == long_title
    assert topic.raw_text == long_notes
    assert len(topic.excerpt) == 200  # Excerpt constrained to first 200 characters

    # Disk persistence verification
    disk_file = test_workspace / "data" / "staged" / f"{topic.id}.json"
    assert disk_file.exists()
    disk_data = json.loads(disk_file.read_text(encoding="utf-8"))
    assert disk_data["title"] == long_title
    assert len(disk_data["excerpt"]) == 200


def test_create_manual_topic_deterministic_id_generation(
    test_workspace: Path,
) -> None:
    """Stage 1 Contract: Verify deterministic SHA-256 topic ID hashing across invocations."""
    client = ServiceClient()
    # Identical URL yields identical topic ID
    t1 = client.create_manual_topic(
        title="Title Variation A",
        notes="Notes A",
        url="https://arxiv.org/abs/2407.08608",
    )
    t2 = client.create_manual_topic(
        title="Title Variation B",
        notes="Notes B",
        url="https://arxiv.org/abs/2407.08608",
    )
    assert t1.id == t2.id

    # Same title and source without URL yields identical topic ID
    t3 = client.create_manual_topic(title="Unique Idea", notes="Idea 1", source_id="brainstorm")
    t4 = client.create_manual_topic(title="Unique Idea", notes="Idea 2", source_id="brainstorm")
    assert t3.id == t4.id

    # Different URL yields different topic ID
    t5 = client.create_manual_topic(title="Unique Idea", notes="Idea 1", url="https://example.com/other")
    assert t5.id != t3.id


def test_format_voiceover_script_edge_cases(
    test_workspace: Path,
) -> None:
    """Phase 2D Feature: Edge cases for format_voiceover_script including empty segments and standard fallback."""
    import json
    client = ServiceClient()
    topic_id = "test-vo-edges"

    # Case 1: Topic with empty shorts_segments list falls back to hook + script_sections + cta
    scripts_dir = test_workspace / "data" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    payload_fallback = {
        "topic_id": topic_id,
        "format": "short_video",
        "hook": "Fallback Hook",
        "script_sections": ["Section 1", "Section 2"],
        "cta": "Fallback CTA",
        "claims_used": [],
        "source_links": [],
        "review_status": "draft",
        "generated_at": "2026-11-22T00:00:00Z",
        "shorts_segments": [],
    }
    (scripts_dir / f"{topic_id}.json").write_text(json.dumps(payload_fallback), encoding="utf-8")

    vo_fallback = client.format_voiceover_script(topic_id)
    assert "Fallback Hook" in vo_fallback
    assert "Section 1" in vo_fallback
    assert "Section 2" in vo_fallback
    assert "Fallback CTA" in vo_fallback

    # Case 2: Populated shorts_segments with valid sections and spoken dialog
    payload_valid_segs = {
        "topic_id": topic_id,
        "format": "short_video",
        "hook": "Unused Hook",
        "script_sections": [],
        "cta": "Unused CTA",
        "claims_used": [],
        "source_links": [],
        "review_status": "draft",
        "generated_at": "2026-11-22T00:00:00Z",
        "shorts_segments": [
            {"section": "hook", "time_range": "0:00-0:05", "visual": "V1", "audio": "A1", "spoken": "Valid Spoken Text 1"},
            {"section": "payoff", "time_range": "0:05-0:10", "visual": "V2", "audio": "A2", "spoken": "Valid Spoken Text 2"},
        ],
    }
    (scripts_dir / f"{topic_id}.json").write_text(json.dumps(payload_valid_segs), encoding="utf-8")
    vo_segs = client.format_voiceover_script(topic_id)
    assert "Valid Spoken Text 1" in vo_segs
    assert "Valid Spoken Text 2" in vo_segs
    assert len(vo_segs.split("\n\n")) == 2

    # Case 3: Script with no spoken lines anywhere (empty hook, empty sections, empty cta)
    payload_all_empty = {
        "topic_id": topic_id,
        "format": "short_video",
        "hook": "",
        "script_sections": [],
        "cta": "",
        "claims_used": [],
        "source_links": [],
        "review_status": "draft",
        "generated_at": "2026-11-22T00:00:00Z",
        "shorts_segments": [],
    }
    (scripts_dir / f"{topic_id}.json").write_text(json.dumps(payload_all_empty), encoding="utf-8")
    vo_none = client.format_voiceover_script(topic_id)
    assert f"No voiceover text found for topic {topic_id}." == vo_none


def test_format_production_cue_sheet_storyboard_only(
    test_workspace: Path,
) -> None:
    """Phase 2D Feature: Production cue sheet formats storyboard directions when video script is not yet generated."""
    import json
    client = ServiceClient()
    topic_id = "test-sb-only-cue"

    storyboards_dir = test_workspace / "data" / "storyboards"
    storyboards_dir.mkdir(parents=True, exist_ok=True)
    sb_payload = {
        "topic_id": topic_id,
        "generated_at": "2026-11-22T00:00:00Z",
        "formats_planned": ["short_video"],
        "script_hook": "Hook from Storyboard",
        "script_cta": "CTA from Storyboard",
        "script_claims": ["Claim 1"],
        "carousel_hook": "Hook",
        "carousel_cta": "CTA",
        "carousel_claims": ["Claim 1"],
        "newsletter_hook": "Hook",
        "newsletter_cta": "CTA",
        "newsletter_claims": ["Claim 1"],
        "thumbnail_hook": "Thumbnail",
        "visual_metaphor": "Gears turning inside silicon chips",
        "visual_style": "metaphor_illustration",
    }
    (storyboards_dir / f"{topic_id}.json").write_text(json.dumps(sb_payload), encoding="utf-8")

    cue = client.format_production_cue_sheet(topic_id)
    assert "PRODUCTION CUE SHEET" in cue
    assert "Visual Style: metaphor_illustration" in cue
    assert "Visual Metaphor: Gears turning inside silicon chips" in cue
    assert "SCENE 1: HOOK" in cue
    assert "👁️ VISUAL:  Gears turning inside silicon chips" in cue
    assert "🎙️ HOOK:    \"Hook from Storyboard\"" in cue
    assert "SCENE 2: CTA" in cue
    assert "🎙️ CTA:     \"CTA from Storyboard\"" in cue


def test_format_production_cue_sheet_script_only_fallback(
    test_workspace: Path,
) -> None:
    """Phase 2D Feature: Production cue sheet formats script sections when shorts_segments is absent."""
    import json
    client = ServiceClient()
    topic_id = "test-script-sections-cue"

    scripts_dir = test_workspace / "data" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_payload = {
        "topic_id": topic_id,
        "format": "short_video",
        "hook": "Attention ML students!",
        "script_sections": [
            "Section 1: Attention mechanisms compute similarity.",
            "Section 2: Multi-head attention allows diverse representations.",
        ],
        "cta": "Like and subscribe for more AI lessons.",
        "claims_used": ["Self-attention scales quadratically"],
        "source_links": [],
        "review_status": "draft",
        "generated_at": "2026-11-22T00:00:00Z",
    }
    (scripts_dir / f"{topic_id}.json").write_text(json.dumps(script_payload), encoding="utf-8")

    cue = client.format_production_cue_sheet(topic_id)
    assert "PRODUCTION CUE SHEET" in cue
    assert "SCENE 1: HOOK" in cue
    assert "🎙️ SPOKEN:  \"Attention ML students!\"" in cue
    assert "SCENE 2: BODY" in cue
    assert "🎙️ SPOKEN:  \"Section 1: Attention mechanisms compute similarity.\"" in cue
    assert "SCENE 3: BODY" in cue
    assert "🎙️ SPOKEN:  \"Section 2: Multi-head attention allows diverse representations.\"" in cue
    assert "SCENE 4: CTA" in cue
    assert "🎙️ SPOKEN:  \"Like and subscribe for more AI lessons.\"" in cue


def test_ensure_database_initialized_zero_ddl_when_populated(
    test_workspace: Path,
) -> None:
    """ERR-027 / REL-002: Verify zero DDL statements executed when database tables already exist."""
    import sqlite3
    from content_creation.ui.services.client import ensure_database_initialized
    from content_creation.platform.storage.database import get_db_path, init_content_factory_db

    target_db = get_db_path(test_workspace)
    # Fully initialize database tables first
    init_content_factory_db(target_db)

    ensure_database_initialized.clear()

    # Track executed SQL statements
    executed_statements: list[str] = []
    original_connect = sqlite3.connect

    class QueryTrackingConnection(sqlite3.Connection):
        def execute(self, sql: str, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
            executed_statements.append(sql.strip())
            return super().execute(sql, *args, **kwargs)

    def tracked_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        kwargs["factory"] = QueryTrackingConnection
        return original_connect(*args, **kwargs)

    from unittest.mock import patch
    with patch("sqlite3.connect", side_effect=tracked_connect):
        result = ensure_database_initialized()

    assert result is True
    # Verify ONLY SELECT on sqlite_master was executed, zero DDL statements
    ddl_keywords = ["CREATE TABLE", "CREATE INDEX", "ALTER TABLE", "DROP TABLE"]
    for stmt in executed_statements:
        for ddl in ddl_keywords:
            assert ddl not in stmt.upper(), f"Prohibited DDL '{ddl}' executed on hot path: {stmt}"

    assert any("SELECT name FROM sqlite_master" in stmt for stmt in executed_statements)


def test_ensure_database_initialized_partial_db_heals_all_tables(
    test_workspace: Path,
) -> None:
    """ERR-027 / REL-002: Verify ensure_database_initialized detects partial tables and self-heals."""
    import sqlite3
    from content_creation.ui.services.client import ensure_database_initialized
    from content_creation.platform.storage.database import get_db_path, create_connection
    from content_creation.jobs.schema import create_job_schema

    target_db = get_db_path(test_workspace)
    target_db.parent.mkdir(parents=True, exist_ok=True)
    # Seed only 'jobs' schema, leaving 'events', 'locks', 'notifications', etc. missing
    conn = sqlite3.connect(str(target_db))
    create_job_schema(conn)
    conn.commit()
    conn.close()

    ensure_database_initialized.clear()
    res = ensure_database_initialized()
    assert res is True

    # Confirm all 6 required subsystem tables now exist
    verify_conn = create_connection(target_db)
    try:
        table_names = {
            row["name"]
            for row in verify_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        for expected in ["jobs", "locks", "events", "notifications", "metrics", "audit"]:
            assert expected in table_names, f"Expected table '{expected}' missing after self-heal"
    finally:
        verify_conn.close()


def test_ensure_database_initialized_corrupted_header_fallback(
    test_workspace: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERR-027: Corrupted database file logs warning and attempts graceful initialization."""
    import logging
    from content_creation.ui.services.client import ensure_database_initialized
    from content_creation.platform.storage.database import get_db_path

    target_db = get_db_path(test_workspace)
    target_db.parent.mkdir(parents=True, exist_ok=True)
    target_db.write_text("CORRUPTED HEADER BYTES NOT SQLITE", encoding="utf-8")

    ensure_database_initialized.clear()
    with caplog.at_level(logging.WARNING):
        # sqlite3.connect or execute will raise OperationalError/DatabaseError
        # client.py catches sqlite3.Error and logs warning
        try:
            ensure_database_initialized()
        except Exception:
            pass  # Fallback to init_content_factory_db may fail if file is locked/corrupt, but warning must be logged

    assert any("Failed to inspect sqlite_master" in r.message for r in caplog.records)



