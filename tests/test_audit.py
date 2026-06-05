"""Comprehensive tests for Phase 11.8.8 — Audit Trail & Compliance System."""

import json
import os
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

import pytest

from content_creation.events.bus import InMemoryEventBus
from content_creation.events.factory import create_event
from content_creation.events.models import EventSeverity, EventType, WorkflowEvent
from content_creation.events.store.sqlite_repository import SQLiteEventRepository
from content_creation.events.store.subscriber import EventPersistenceSubscriber
from content_creation.events.store.replay import EventReplayEngine
from content_creation.audit.models import AuditRecord, AuditSeverity, AuditActorType, AuditSource
from content_creation.audit.repository import AuditRepository
from content_creation.audit.sqlite_repository import SQLiteAuditRepository
from content_creation.audit.schema import create_audit_schema
from content_creation.audit.subscriber import AuditSubscriber
from content_creation.audit.service import AuditQueryService, AuditPage
from content_creation.audit.compliance import (
    ComplianceReportService,
    ActorActivityReport,
    WorkflowDecisionReport,
    JobExecutionReport,
    IncidentTimeline,
    ComplianceSummary,
)


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def tmp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def audit_repo(tmp_db_path):
    repo = SQLiteAuditRepository(tmp_db_path)
    yield repo
    repo.close()


@pytest.fixture
def event_repo(tmp_db_path):
    repo = SQLiteEventRepository(tmp_db_path)
    yield repo
    repo.close()


@pytest.fixture
def bus():
    return InMemoryEventBus()


def _make_event(
    event_type: EventType = EventType.BRIEF_GENERATED,
    entity_type: str = "brief",
    entity_id: str = "test-entity",
    correlation_id: str = "",
    source: str = "workflow_engine",
    actor_id: str = "operator-1",
    payload: dict = None,
    severity: EventSeverity = EventSeverity.INFO,
) -> WorkflowEvent:
    return create_event(
        event_type=event_type,
        source=source,
        correlation_id=correlation_id or str(uuid4()),
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        payload=payload or {"test": True},
    )


def _make_audit_record(
    action_type: str = "test_action",
    entity_type: str = "brief",
    entity_id: str = "test-entity",
    actor_id: str = "operator-1",
    source: AuditSource = AuditSource.WORKFLOW,
    severity: AuditSeverity = AuditSeverity.INFO,
    event_type: str = "test_event",
) -> AuditRecord:
    return AuditRecord(
        audit_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        actor_type=AuditActorType.OPERATOR,
        actor_id=actor_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        correlation_id=str(uuid4()),
        source=source,
        severity=severity,
    )


# ======================================================================
# PART 1: AuditRecord MODEL TESTS
# ======================================================================


class TestAuditRecord:
    def test_creation(self):
        record = _make_audit_record()
        assert record.action_type == "test_action"
        assert record.entity_type == "brief"
        assert record.actor_type == AuditActorType.OPERATOR

    def test_immutable(self):
        record = _make_audit_record()
        with pytest.raises(AttributeError):
            record.action_type = "changed"

    def test_to_dict(self):
        record = AuditRecord(
            audit_id=uuid4(), timestamp=datetime.now(timezone.utc),
            actor_type=AuditActorType.OPERATOR, actor_id="operator-1",
            action_type="test_action", entity_type="job", entity_id="j1",
            event_type="test_event", correlation_id=str(uuid4()),
            metadata={"key": "value"},
        )
        d = record.to_dict()
        assert d["action_type"] == "test_action"
        assert d["entity_type"] == "job"
        assert d["metadata"]["key"] == "value"
        assert "audit_id" in d
        assert "timestamp" in d

    def test_from_workflow_event(self):
        event = _make_event(
            EventType.BRIEF_APPROVED,
            entity_type="brief",
            entity_id="b1",
            actor_id="operator-1",
            payload={"previous_status": "pending", "new_status": "approved"},
        )
        record = AuditRecord.from_workflow_event(event)
        assert record.event_type == "brief_approved"
        assert record.entity_type == "brief"
        assert record.entity_id == "b1"
        assert record.action_type == "approve_brief"
        assert record.previous_state == "pending"
        assert record.new_state == "approved"
        assert record.source == AuditSource.REVIEW

    def test_from_workflow_event_job(self):
        event = _make_event(
            EventType.JOB_COMPLETED,
            entity_type="job",
            entity_id="j1",
            payload={"status": "completed"},
        )
        record = AuditRecord.from_workflow_event(event)
        assert record.source == AuditSource.JOB
        assert record.action_type == "complete_job"

    def test_from_workflow_event_lock(self):
        event = _make_event(EventType.LOCK_ACQUIRED, entity_type="lock")
        record = AuditRecord.from_workflow_event(event)
        assert record.source == AuditSource.LOCK

    def test_from_workflow_event_recovery(self):
        event = _make_event(
            EventType.ZOMBIE_JOB_RECOVERED,
            actor_id="recovery_supervisor",
        )
        record = AuditRecord.from_workflow_event(event)
        assert record.actor_type == AuditActorType.RECOVERY
        assert record.source == AuditSource.RECOVERY

    def test_from_workflow_event_pipeline(self):
        event = _make_event(EventType.PIPELINE_STARTED, entity_type="pipeline")
        record = AuditRecord.from_workflow_event(event)
        assert record.source == AuditSource.PIPELINE

    def test_severity_mapping(self):
        event = _make_event(
            EventType.JOB_FAILED,
            severity=EventSeverity.CRITICAL,
        )
        record = AuditRecord.from_workflow_event(event)
        assert record.severity == AuditSeverity.CRITICAL

    def test_audit_enums(self):
        assert AuditSeverity.INFO.value == "INFO"
        assert AuditActorType.OPERATOR.value == "operator"
        assert AuditSource.WORKFLOW.value == "workflow"


# ======================================================================
# PART 2: SCHEMA TESTS
# ======================================================================


class TestAuditSchema:
    def test_schema_creation(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_audit_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_schema_idempotent(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_audit_schema(conn)
            create_audit_schema(conn)
        finally:
            conn.close()

    def test_indexes_created(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_audit_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_audit%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            assert "idx_audit_timestamp" in indexes
            assert "idx_audit_entity" in indexes
            assert "idx_audit_actor" in indexes
            assert "idx_audit_correlation" in indexes
            assert "idx_audit_event" in indexes
            assert "idx_audit_source" in indexes
            assert "idx_audit_action" in indexes
        finally:
            conn.close()


# ======================================================================
# PART 3: REPOSITORY CRUD TESTS
# ======================================================================


class TestSQLiteAuditRepository:
    def test_create_and_get(self, audit_repo):
        record = _make_audit_record()
        audit_repo.create_record(record)
        retrieved = audit_repo.get_record(record.audit_id)
        assert retrieved is not None
        assert retrieved.action_type == "test_action"

    def test_get_nonexistent(self, audit_repo):
        assert audit_repo.get_record(uuid4()) is None

    def test_create_idempotent(self, audit_repo):
        record = _make_audit_record()
        audit_repo.create_record(record)
        audit_repo.create_record(record)
        assert audit_repo.count_records() == 1

    def test_query_by_entity(self, audit_repo):
        audit_repo.create_record(_make_audit_record(entity_type="brief", entity_id="b1"))
        audit_repo.create_record(_make_audit_record(entity_type="brief", entity_id="b1"))
        audit_repo.create_record(_make_audit_record(entity_type="brief", entity_id="b2"))
        results = audit_repo.query_by_entity("brief", "b1")
        assert len(results) == 2

    def test_query_by_actor(self, audit_repo):
        audit_repo.create_record(_make_audit_record(actor_id="op1"))
        audit_repo.create_record(_make_audit_record(actor_id="op1"))
        audit_repo.create_record(_make_audit_record(actor_id="op2"))
        results = audit_repo.query_by_actor("op1")
        assert len(results) == 2

    def test_query_by_correlation(self, audit_repo):
        cid = "corr-123"
        r1 = _make_audit_record()
        r2 = AuditRecord(
            audit_id=uuid4(), timestamp=datetime.now(timezone.utc),
            actor_type=AuditActorType.SYSTEM, actor_id="sys",
            action_type="test", entity_type="brief", entity_id="b1",
            event_type="test", correlation_id=cid,
        )
        audit_repo.create_record(r1)
        audit_repo.create_record(r2)
        results = audit_repo.query_by_correlation(cid)
        assert len(results) == 1

    def test_query_records_filters(self, audit_repo):
        audit_repo.create_record(_make_audit_record(source=AuditSource.WORKFLOW))
        audit_repo.create_record(_make_audit_record(source=AuditSource.JOB))
        audit_repo.create_record(_make_audit_record(source=AuditSource.WORKFLOW))
        results = audit_repo.query_records(source=AuditSource.WORKFLOW)
        assert len(results) == 2

    def test_query_by_severity(self, audit_repo):
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.INFO))
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.CRITICAL))
        results = audit_repo.query_records(severity=AuditSeverity.CRITICAL)
        assert len(results) == 1

    def test_query_by_time_range(self, audit_repo):
        now = datetime.now(timezone.utc)
        record = _make_audit_record()
        audit_repo.create_record(record)
        results = audit_repo.query_records(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        assert len(results) >= 1

    def test_count_records(self, audit_repo):
        assert audit_repo.count_records() == 0
        audit_repo.create_record(_make_audit_record())
        assert audit_repo.count_records() == 1
        audit_repo.create_record(_make_audit_record(actor_id="op2"))
        assert audit_repo.count_records() == 2
        assert audit_repo.count_records(actor_id="op2") == 1

    def test_delete_expired(self, audit_repo):
        old = AuditRecord(
            audit_id=uuid4(),
            timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
            actor_type=AuditActorType.SYSTEM, actor_id="sys",
            action_type="old", entity_type="", entity_id="",
            event_type="old", correlation_id="",
        )
        recent = _make_audit_record()
        audit_repo.create_record(old)
        audit_repo.create_record(recent)
        deleted = audit_repo.delete_expired(datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert deleted == 1
        assert audit_repo.count_records() == 1

    def test_thread_safety(self, tmp_db_path):
        repo = SQLiteAuditRepository(tmp_db_path)
        errors: List[Exception] = []

        def write_records():
            try:
                for _ in range(10):
                    repo.create_record(_make_audit_record())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_records) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert repo.count_records() == 50

    def test_close(self, tmp_db_path):
        repo = SQLiteAuditRepository(tmp_db_path)
        repo.create_record(_make_audit_record())
        repo.close()
        repo2 = SQLiteAuditRepository(tmp_db_path)
        assert repo2.count_records() == 1
        repo2.close()

    def test_close_idempotent(self, tmp_db_path):
        repo = SQLiteAuditRepository(tmp_db_path)
        repo.close()
        repo.close()


# ======================================================================
# PART 4: AUDIT SUBSCRIBER TESTS
# ======================================================================


class TestAuditSubscriber:
    def test_persists_workflow_events(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        event = _make_event(EventType.BRIEF_GENERATED)
        bus.publish(event)
        assert audit_repo.count_records() == 1

    def test_persists_job_events(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        event = _make_event(EventType.JOB_COMPLETED)
        bus.publish(event)
        record = audit_repo.query_records(limit=1)[0]
        assert record.source == AuditSource.JOB

    def test_persists_lock_events(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        event = _make_event(EventType.LOCK_ACQUIRED)
        bus.publish(event)
        record = audit_repo.query_records(limit=1)[0]
        assert record.source == AuditSource.LOCK

    def test_persists_pipeline_events(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        event = _make_event(EventType.PIPELINE_COMPLETED)
        bus.publish(event)
        record = audit_repo.query_records(limit=1)[0]
        assert record.source == AuditSource.PIPELINE

    def test_persists_review_events(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        event = _make_event(EventType.ASSET_APPROVED)
        bus.publish(event)
        record = audit_repo.query_records(limit=1)[0]
        assert record.source == AuditSource.REVIEW

    def test_does_not_mutate_event(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        event = _make_event(EventType.BRIEF_GENERATED, payload={"original": True})
        bus.publish(event)
        assert event.payload.get("original") is True

    def test_failure_isolation(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)

        def failing_callback(event):
            raise RuntimeError("Intentional failure")

        bus.subscribe_wildcard("*", failing_callback)
        event = _make_event(EventType.BRIEF_GENERATED)
        bus.publish(event)
        assert audit_repo.count_records() == 1

    def test_shutdown(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        subscriber.shutdown()
        event = _make_event(EventType.BRIEF_GENERATED)
        bus.publish(event)
        assert audit_repo.count_records() == 0

    def test_multiple_events_accumulate(self, audit_repo, bus):
        subscriber = AuditSubscriber(repository=audit_repo, bus=bus)
        for _ in range(5):
            bus.publish(_make_event(EventType.BRIEF_GENERATED))
        assert audit_repo.count_records() == 5


# ======================================================================
# PART 5: AUDIT QUERY SERVICE TESTS
# ======================================================================


class TestAuditQueryService:
    def test_recent_records(self, audit_repo):
        for _ in range(5):
            audit_repo.create_record(_make_audit_record())

        service = AuditQueryService(repository=audit_repo)
        page = service.recent_records(page_size=3)
        assert isinstance(page, AuditPage)
        assert len(page.records) == 3
        assert page.total == 5
        assert page.total_pages == 2
        assert page.has_next is True
        assert page.has_previous is False

    def test_search_by_entity(self, audit_repo):
        audit_repo.create_record(_make_audit_record(entity_type="brief", entity_id="b1"))
        audit_repo.create_record(_make_audit_record(entity_type="job", entity_id="j1"))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_entity("brief", "b1")
        assert len(results) == 1

    def test_search_by_entity_type_only(self, audit_repo):
        audit_repo.create_record(_make_audit_record(entity_type="brief"))
        audit_repo.create_record(_make_audit_record(entity_type="brief"))
        audit_repo.create_record(_make_audit_record(entity_type="job"))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_entity("brief")
        assert len(results) == 2

    def test_search_by_actor(self, audit_repo):
        audit_repo.create_record(_make_audit_record(actor_id="op1"))
        audit_repo.create_record(_make_audit_record(actor_id="op2"))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_actor("op1")
        assert len(results) == 1

    def test_search_by_correlation(self, audit_repo):
        r = _make_audit_record()
        audit_repo.create_record(r)
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_correlation(r.correlation_id)
        assert len(results) == 1

    def test_search_by_date_range(self, audit_repo):
        audit_repo.create_record(_make_audit_record())
        service = AuditQueryService(repository=audit_repo)
        now = datetime.now(timezone.utc)
        results = service.search_by_date_range(
            now - timedelta(hours=1), now + timedelta(hours=1),
        )
        assert len(results) >= 1

    def test_search_by_event_type(self, audit_repo):
        audit_repo.create_record(_make_audit_record(event_type="brief_generated"))
        audit_repo.create_record(_make_audit_record(event_type="job_completed"))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_event_type("brief_generated")
        assert len(results) == 1

    def test_search_by_action(self, audit_repo):
        audit_repo.create_record(_make_audit_record(action_type="approve_brief"))
        audit_repo.create_record(_make_audit_record(action_type="complete_job"))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_action("approve_brief")
        assert len(results) == 1

    def test_search_by_severity(self, audit_repo):
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.INFO))
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.CRITICAL))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_by_severity(AuditSeverity.CRITICAL)
        assert len(results) == 1

    def test_search_records(self, audit_repo):
        audit_repo.create_record(_make_audit_record(action_type="approve_brief"))
        service = AuditQueryService(repository=audit_repo)
        results = service.search_records("approve")
        assert len(results) == 1

    def test_get_record(self, audit_repo):
        record = _make_audit_record()
        audit_repo.create_record(record)
        service = AuditQueryService(repository=audit_repo)
        retrieved = service.get_record(record.audit_id)
        assert retrieved is not None

    def test_record_count(self, audit_repo):
        audit_repo.create_record(_make_audit_record())
        service = AuditQueryService(repository=audit_repo)
        assert service.record_count() == 1


# ======================================================================
# PART 6: COMPLIANCE REPORT SERVICE TESTS
# ======================================================================


class TestComplianceReportService:
    def test_operator_activity_report(self, audit_repo):
        audit_repo.create_record(_make_audit_record(actor_id="op1", action_type="approve_brief"))
        audit_repo.create_record(_make_audit_record(actor_id="op1", action_type="reject_brief"))
        audit_repo.create_record(_make_audit_record(actor_id="op2", action_type="approve_brief"))

        service = ComplianceReportService(repository=audit_repo)
        reports = service.operator_activity_report()
        assert len(reports) == 2
        assert reports[0].actor_id == "op1"
        assert reports[0].total_actions == 2

    def test_workflow_decision_report(self, audit_repo):
        audit_repo.create_record(_make_audit_record(
            source=AuditSource.REVIEW, event_type="brief_approved",
        ))
        audit_repo.create_record(_make_audit_record(
            source=AuditSource.REVIEW, event_type="brief_approved",
        ))
        audit_repo.create_record(_make_audit_record(
            source=AuditSource.REVIEW, event_type="brief_rejected",
        ))

        service = ComplianceReportService(repository=audit_repo)
        report = service.workflow_decision_report()
        assert report.total_decisions == 3
        assert report.approvals == 2
        assert report.rejections == 1
        assert report.approval_rate == pytest.approx(66.666, rel=0.01)

    def test_workflow_decision_report_empty(self, audit_repo):
        service = ComplianceReportService(repository=audit_repo)
        report = service.workflow_decision_report()
        assert report.total_decisions == 0
        assert report.approval_rate == 0.0

    def test_job_execution_report(self, audit_repo):
        audit_repo.create_record(_make_audit_record(
            source=AuditSource.JOB, event_type="job_completed",
        ))
        audit_repo.create_record(_make_audit_record(
            source=AuditSource.JOB, event_type="job_completed",
        ))
        audit_repo.create_record(_make_audit_record(
            source=AuditSource.JOB, event_type="job_failed",
        ))

        service = ComplianceReportService(repository=audit_repo)
        report = service.job_execution_report()
        assert report.total_jobs == 3
        assert report.completed == 2
        assert report.failed == 1
        assert report.success_rate == pytest.approx(66.666, rel=0.01)

    def test_job_execution_report_empty(self, audit_repo):
        service = ComplianceReportService(repository=audit_repo)
        report = service.job_execution_report()
        assert report.total_jobs == 0

    def test_incident_timeline(self, audit_repo):
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.CRITICAL))
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.WARNING))
        audit_repo.create_record(_make_audit_record(severity=AuditSeverity.INFO))

        service = ComplianceReportService(repository=audit_repo)
        timeline = service.incident_timeline()
        assert timeline.total_critical == 1
        assert timeline.total_warning == 1
        assert len(timeline.events) == 2

    def test_compliance_summary(self, audit_repo):
        audit_repo.create_record(_make_audit_record(actor_id="op1"))
        audit_repo.create_record(_make_audit_record(actor_id="op2"))

        service = ComplianceReportService(repository=audit_repo)
        summary = service.compliance_summary()
        assert summary.total_audit_records == 2
        assert summary.actors_active == 2
        assert summary.unique_entities >= 1


# ======================================================================
# PART 7: REPLAY COMPATIBILITY TESTS
# ======================================================================


class TestAuditReplayCompatibility:
    def test_rebuild_audit_from_events(self, audit_repo, event_repo, bus):
        """Test that audit records can be rebuilt from event store replay."""
        persist_sub = EventPersistenceSubscriber(repository=event_repo, bus=bus)
        audit_sub = AuditSubscriber(repository=audit_repo, bus=bus)

        for i in range(3):
            bus.publish(_make_event(EventType.BRIEF_GENERATED, payload={"i": i}))
        persist_sub.shutdown()
        audit_sub.shutdown()

        assert event_repo.count_events() >= 3
        assert audit_repo.count_records() >= 3

        # Delete audit records
        audit_repo.delete_expired(datetime.now(timezone.utc) + timedelta(hours=1))
        assert audit_repo.count_records() == 0

        # Replay events to rebuild audit trail
        replay_bus = InMemoryEventBus()
        AuditSubscriber(repository=audit_repo, bus=replay_bus)
        engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
        replayed = engine.replay_all()

        assert audit_repo.count_records() >= 3
        assert len(replayed) >= 3

    def test_replay_preserves_action_types(self, audit_repo, event_repo, bus):
        """Test that replayed events produce correct action types."""
        persist_sub = EventPersistenceSubscriber(repository=event_repo, bus=bus)
        audit_sub = AuditSubscriber(repository=audit_repo, bus=bus)

        bus.publish(_make_event(EventType.BRIEF_APPROVED))
        bus.publish(_make_event(EventType.JOB_COMPLETED))
        persist_sub.shutdown()
        audit_sub.shutdown()

        # Clear and rebuild
        audit_repo.delete_expired(datetime.now(timezone.utc) + timedelta(hours=1))

        replay_bus = InMemoryEventBus()
        AuditSubscriber(repository=audit_repo, bus=replay_bus)
        engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
        engine.replay_all()

        records = audit_repo.query_records(limit=10)
        action_types = {r.action_type for r in records}
        assert "approve_brief" in action_types
        assert "complete_job" in action_types


# ======================================================================
# PART 8: INTEGRATION TESTS
# ======================================================================


class TestAuditIntegration:
    def test_full_lifecycle(self, tmp_db_path):
        """Test complete lifecycle: emit event -> audit record -> query -> report."""
        event_repo = SQLiteEventRepository(tmp_db_path)
        audit_repo = SQLiteAuditRepository(tmp_db_path)
        bus = InMemoryEventBus()

        persist_sub = EventPersistenceSubscriber(repository=event_repo, bus=bus)
        audit_sub = AuditSubscriber(repository=audit_repo, bus=bus)

        # Emit events
        bus.publish(_make_event(EventType.BRIEF_GENERATED))
        bus.publish(_make_event(EventType.BRIEF_APPROVED))
        bus.publish(_make_event(EventType.JOB_COMPLETED))

        persist_sub.shutdown()
        audit_sub.shutdown()

        # Query
        query_service = AuditQueryService(repository=audit_repo)
        page = query_service.recent_records()
        assert page.total >= 3

        # Compliance report
        compliance = ComplianceReportService(repository=audit_repo)
        summary = compliance.compliance_summary()
        assert summary.total_audit_records >= 3

        decision_report = compliance.workflow_decision_report()
        assert decision_report.approvals >= 1

    def test_concurrent_writes(self, tmp_db_path):
        repo = SQLiteAuditRepository(tmp_db_path)
        errors: List[Exception] = []

        def write_records():
            try:
                for _ in range(10):
                    repo.create_record(_make_audit_record())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_records) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert repo.count_records() == 50
