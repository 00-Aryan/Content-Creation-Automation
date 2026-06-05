"""Comprehensive tests for the Workflow Event System."""

import concurrent.futures
from datetime import datetime, timedelta, timezone
import pytest
import sqlite3
import threading
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from content_creation.events.bus import (
    InMemoryEventBus,
    get_event_bus,
)
from content_creation.events.factory import (
    create_event,
    create_job_event,
    create_lock_event,
    create_pipeline_event,
    create_recovery_event,
    create_workflow_event,
)
from content_creation.events.models import (
    EventMetadata,
    EventSeverity,
    EventType,
    WorkflowEvent,
)
from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType
from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
from content_creation.jobs.queue_engine import QueueEngine
from content_creation.jobs.recovery_supervisor import (
    RecoveryConfig,
    RecoverySupervisor,
)
from content_creation.jobs.schema import create_schema
from content_creation.jobs.sqlite_lock_repository import SQLiteLockRepository
from content_creation.jobs.sqlite_repository import SQLiteJobRepository
from content_creation.jobs.worker_daemon import WorkerConfig, WorkerDaemon
from content_creation.workflow.workflow_action_executor import (
    ActionExecutionResult,
    ActionExecutionStatus,
    WorkflowActionExecutor,
)


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Fixture providing in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def queue_system(db_conn: sqlite3.Connection) -> QueueEngine:
    repo = SQLiteJobRepository(db_conn)
    lock_repo = SQLiteLockRepository(db_conn)
    lock_mgr = LockManager(lock_repo)
    return QueueEngine(repo, lock_mgr)


# ======================================================================
# DOMAIN MODELS & HELPERS TESTS
# ======================================================================


def test_event_models_immutability() -> None:
    """Verify that WorkflowEvent and EventMetadata are immutable (frozen)."""
    meta = EventMetadata(
        source="src",
        correlation_id="corr",
        actor_id="actor",
        entity_type="type",
        entity_id="id",
    )
    evt = WorkflowEvent(
        event_id=uuid4(),
        event_type=EventType.JOB_CREATED,
        timestamp=datetime.now(timezone.utc),
        source=meta.source,
        correlation_id=meta.correlation_id,
        actor_id=meta.actor_id,
        entity_type=meta.entity_type,
        entity_id=meta.entity_id,
        severity=EventSeverity.INFO,
        payload={"foo": "bar"},
    )

    with pytest.raises(AttributeError):
        evt.payload = {}  # type: ignore

    with pytest.raises(AttributeError):
        meta.source = "new_src"  # type: ignore


def test_event_factories() -> None:
    """Verify factory helper functions build valid event structures."""
    corr_id = "test-corr"
    actor = "test-actor"

    # Workflow Event
    wf_evt = create_workflow_event(
        event_type=EventType.BRIEF_GENERATED,
        topic_id="topic-1",
        operator_id=actor,
        correlation_id=corr_id,
        extra_payload={"gen_details": "ok"},
    )
    assert wf_evt.event_type == EventType.BRIEF_GENERATED
    assert wf_evt.entity_type == "brief"
    assert wf_evt.correlation_id == corr_id
    assert wf_evt.payload["topic_id"] == "topic-1"
    assert wf_evt.payload["gen_details"] == "ok"
    assert wf_evt.severity == EventSeverity.INFO

    # Workflow Event Rejected
    wf_rej = create_workflow_event(
        event_type=EventType.BRIEF_REJECTED,
        topic_id="topic-1",
        operator_id=actor,
        correlation_id=corr_id,
    )
    assert wf_rej.severity == EventSeverity.WARNING

    # Job Event
    job_id = uuid4()
    job_evt = create_job_event(
        event_type=EventType.JOB_FAILED,
        job_id=job_id,
        job_type="COLLECT",
        status="FAILED",
        operator_id=actor,
        correlation_id=corr_id,
        target_type="topic",
        target_id="t1",
        error_message="critical crash",
    )
    assert job_evt.event_type == EventType.JOB_FAILED
    assert job_evt.severity == EventSeverity.CRITICAL
    assert job_evt.payload["job_id"] == str(job_id)
    assert job_evt.payload["error_message"] == "critical crash"

    # Lock Event
    lock_id = uuid4()
    lock_evt = create_lock_event(
        event_type=EventType.LOCK_EXPIRED,
        lock_id=lock_id,
        lock_type="TOPIC",
        resource_id="res-1",
        owner_job_id=job_id,
        correlation_id=corr_id,
    )
    assert lock_evt.event_type == EventType.LOCK_EXPIRED
    assert lock_evt.severity == EventSeverity.WARNING
    assert lock_evt.payload["lock_id"] == str(lock_id)

    # Pipeline Event
    pipeline_evt = create_pipeline_event(
        event_type=EventType.PIPELINE_FAILED,
        week_start="2026-06-01",
        operator_id=actor,
        correlation_id=corr_id,
        error_message="failed step",
    )
    assert pipeline_evt.event_type == EventType.PIPELINE_FAILED
    assert pipeline_evt.severity == EventSeverity.CRITICAL
    assert pipeline_evt.payload["error_message"] == "failed step"

    # Recovery Event
    rec_evt = create_recovery_event(
        event_type=EventType.ZOMBIE_JOB_RECOVERED,
        entity_type="job",
        entity_id="job-1",
        correlation_id=corr_id,
        details={"status": "reclaimed"},
    )
    assert rec_evt.event_type == EventType.ZOMBIE_JOB_RECOVERED
    assert rec_evt.severity == EventSeverity.WARNING
    assert rec_evt.payload["status"] == "reclaimed"


# ======================================================================
# EVENT BUS ROUTING & ORDERING TESTS
# ======================================================================


def test_bus_exact_and_wildcard_delivery() -> None:
    """Verify in-memory event bus exact and wildcard subscriptions work."""
    bus = InMemoryEventBus()
    received_exact = []
    received_wildcard_job = []
    received_wildcard_all = []

    def exact_cb(e: WorkflowEvent) -> None:
        received_exact.append(e)

    def wildcard_job_cb(e: WorkflowEvent) -> None:
        received_wildcard_job.append(e)

    def wildcard_all_cb(e: WorkflowEvent) -> None:
        received_wildcard_all.append(e)

    # Subscribe
    bus.subscribe(EventType.JOB_CREATED, exact_cb)
    bus.subscribe_wildcard("job.*", wildcard_job_cb)
    bus.subscribe_wildcard("*", wildcard_all_cb)

    # Publish JOB_CREATED
    evt1 = create_job_event(
        event_type=EventType.JOB_CREATED,
        job_id=uuid4(),
        job_type="COLLECT",
        status="PENDING",
        operator_id="user",
        correlation_id="corr-1",
        target_type="topic",
        target_id="t1",
    )
    bus.publish(evt1)

    assert len(received_exact) == 1
    assert len(received_wildcard_job) == 1
    assert len(received_wildcard_all) == 1
    assert received_exact[0].event_id == evt1.event_id

    # Publish BRIEF_GENERATED
    evt2 = create_workflow_event(
        event_type=EventType.BRIEF_GENERATED,
        topic_id="topic-1",
        operator_id="user",
        correlation_id="corr-1",
    )
    bus.publish(evt2)

    assert len(received_exact) == 1  # No change
    assert len(received_wildcard_job) == 1  # No change
    assert len(received_wildcard_all) == 2  # Receives all

    # Unsubscribe
    bus.unsubscribe(EventType.JOB_CREATED, exact_cb)
    bus.unsubscribe_wildcard("job.*", wildcard_job_cb)
    bus.unsubscribe_wildcard("*", wildcard_all_cb)

    bus.publish(evt1)
    assert len(received_exact) == 1  # No change
    assert len(received_wildcard_job) == 1  # No change
    assert len(received_wildcard_all) == 2  # No change


def test_bus_publish_ordering_and_isolation() -> None:
    """Verify callbacks execute in registration order and exceptions are isolated."""
    bus = InMemoryEventBus()
    execution_trace = []

    def cb_first(e: WorkflowEvent) -> None:
        execution_trace.append("first")

    def cb_broken(e: WorkflowEvent) -> None:
        execution_trace.append("broken")
        raise RuntimeError("simulated listener error")

    def cb_second(e: WorkflowEvent) -> None:
        execution_trace.append("second")

    bus.subscribe(EventType.JOB_CREATED, cb_first)
    bus.subscribe(EventType.JOB_CREATED, cb_broken)
    bus.subscribe(EventType.JOB_CREATED, cb_second)

    evt = create_job_event(
        event_type=EventType.JOB_CREATED,
        job_id=uuid4(),
        job_type="COLLECT",
        status="PENDING",
        operator_id="user",
        correlation_id="corr-1",
        target_type="topic",
        target_id="t1",
    )

    # Should not raise exception
    bus.publish(evt)

    # All three callbacks must execute in exact registered order
    assert execution_trace == ["first", "broken", "second"]


def test_bus_thread_safety() -> None:
    """Verify the event bus handles concurrent operations without race conditions."""
    bus = InMemoryEventBus()
    counter = 0
    cnt_lock = threading.Lock()

    def cb(e: WorkflowEvent) -> None:
        nonlocal counter
        with cnt_lock:
            counter += 1

    bus.subscribe_wildcard("job.*", cb)

    # Spin up 5 concurrent publishers
    evt = create_job_event(
        event_type=EventType.JOB_CREATED,
        job_id=uuid4(),
        job_type="COLLECT",
        status="PENDING",
        operator_id="user",
        correlation_id="corr-1",
        target_type="topic",
        target_id="t1",
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(bus.publish, evt) for _ in range(20)]
        concurrent.futures.wait(futures)

    assert counter == 20


# ======================================================================
# COMPONENT INTEGRATION TESTS
# ======================================================================


def test_executor_emission(db_conn: sqlite3.Connection) -> None:
    """Verify WorkflowActionExecutor publishes events on success and pipeline failures."""
    bus = get_event_bus()
    emitted = []

    def cb(e: WorkflowEvent) -> None:
        emitted.append(e)

    bus.subscribe_wildcard("workflow.*", cb)
    bus.subscribe_wildcard("pipeline.*", cb)
    bus.subscribe_wildcard("review.*", cb)

    mock_avail = MagicMock()
    mock_avail.is_action_available.return_value = True

    mock_trans = MagicMock()
    mock_trans.validate_transition.return_value.valid = True

    executor = WorkflowActionExecutor(availability_engine=mock_avail, transition_engine=mock_trans)

    # Mock dynamic service dispatch
    executor._dispatch_to_service = MagicMock(return_value=({"brief_path": "path/1"}, MagicMock()))

    # Trigger action
    mock_ctx = MagicMock()
    mock_brief = MagicMock()
    mock_brief.review_status.value = "needs_review"
    mock_ctx.storage.get_brief.return_value = mock_brief

    res = executor.execute(
        ctx=mock_ctx,
        action_id="approve_brief",
        target_artifact_type="brief",
        target_artifact_id="topic-1",
        payload={},
        operator_id="client",
    )

    assert res.success is True
    assert len(emitted) == 1
    assert emitted[0].event_type == EventType.BRIEF_APPROVED
    assert emitted[0].actor_id == "client"
    assert emitted[0].entity_id == "topic-1"

    # Pipeline failure case
    executor._dispatch_to_service = MagicMock(side_effect=RuntimeError("pipeline broke"))
    res_pipeline = executor.execute(
        ctx=MagicMock(),
        action_id="run_pipeline",
        target_artifact_type="pipeline",
        target_artifact_id="week_1",
        payload={},
        operator_id="client",
    )
    assert res_pipeline.success is False

    # Check that both pipeline_started and pipeline_failed were published
    pipe_events = [e for e in emitted if e.event_type in (EventType.PIPELINE_STARTED, EventType.PIPELINE_FAILED)]
    assert len(pipe_events) == 2
    assert pipe_events[0].event_type == EventType.PIPELINE_STARTED
    assert pipe_events[1].event_type == EventType.PIPELINE_FAILED
    assert pipe_events[1].payload["error_message"] == "pipeline broke"


def test_queue_engine_emissions(queue_system: QueueEngine) -> None:
    """Verify QueueEngine publishes job_created, job_queued, job_retried, and job_cancelled."""
    bus = get_event_bus()
    emitted = []

    def cb(e: WorkflowEvent) -> None:
        emitted.append(e)

    bus.subscribe_wildcard("job.*", cb)

    # Submit job
    res = queue_system.submit_job(
        job_type="COLLECT",
        action_id="collect",
        operator_id="user-1",
        target_type="all",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )

    # Should emit job_created and job_queued
    job_events = [e for e in emitted if e.event_type in (EventType.JOB_CREATED, EventType.JOB_QUEUED)]
    assert len(job_events) == 2
    assert job_events[0].event_type == EventType.JOB_CREATED
    assert job_events[1].event_type == EventType.JOB_QUEUED
    assert job_events[0].payload["job_id"] == str(res.job_id)

    # Cancel job
    queue_system.cancel_job(res.job_id)
    cancel_evt = [e for e in emitted if e.event_type == EventType.JOB_CANCELLED]
    assert len(cancel_evt) == 1
    assert cancel_evt[0].payload["job_id"] == str(res.job_id)

    # Retry job enqueuing
    res2 = queue_system.submit_job(
        job_type="COLLECT",
        action_id="collect",
        operator_id="user-1",
        target_type="all",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )
    queue_system.schedule_retry(res2.job_id, "transient error")
    retry_evt = [e for e in emitted if e.event_type == EventType.JOB_RETRIED]
    assert len(retry_evt) == 1
    assert retry_evt[0].payload["job_id"] == str(res2.job_id)
    assert retry_evt[0].payload["error_message"] == "transient error"


def test_worker_daemon_emissions(queue_system: QueueEngine) -> None:
    """Verify WorkerDaemon run publishes job_started and job_completed."""
    bus = get_event_bus()
    emitted = []

    def cb(e: WorkflowEvent) -> None:
        emitted.append(e)

    bus.subscribe_wildcard("job.*", cb)

    # Submit job
    res = queue_system.submit_job(
        job_type=JobType.DRY_RUN.value,
        action_id="dry_run",
        operator_id="user-1",
        target_type="all",
        target_id="all",
        payload={},
        correlation_id="corr-1",
    )

    mock_executor = MagicMock()
    mock_executor.execute.return_value = ActionExecutionResult(
        action_id="dry_run",
        success=True,
        execution_status=ActionExecutionStatus.SUCCESS,
        affected_artifacts={},
        warnings=[],
        blocking_reasons=[],
        execution_time=0.1,
    )

    worker = WorkerDaemon(
        ctx=None,
        queue_engine=queue_system,
        lock_manager=queue_system._locks,
        executor=mock_executor,
        config=WorkerConfig(
            poll_interval_seconds=0.1,
            heartbeat_interval_seconds=10.0,
            zombie_timeout_seconds=30.0,
            max_concurrent_jobs=1,
            worker_id="test_worker_events",
        ),
    )

    worker.run_once()

    # Check job_started and job_completed events
    start_evt = [e for e in emitted if e.event_type == EventType.JOB_STARTED]
    comp_evt = [e for e in emitted if e.event_type == EventType.JOB_COMPLETED]
    assert len(start_evt) == 1
    assert len(comp_evt) == 1
    assert start_evt[0].payload["job_id"] == str(res.job_id)
    assert comp_evt[0].payload["job_id"] == str(res.job_id)


def test_lock_manager_emissions(queue_system: QueueEngine) -> None:
    """Verify LockManager publishes lock_acquired and lock_released events."""
    bus = get_event_bus()
    emitted = []

    def cb(e: WorkflowEvent) -> None:
        emitted.append(e)

    bus.subscribe_wildcard("lock.*", cb)

    lock_mgr = queue_system._locks
    job_id = uuid4()

    # Acquire lock
    lock = lock_mgr.acquire_topic_lock(job_id, "topic-abc")
    assert len(emitted) == 1
    assert emitted[0].event_type == EventType.LOCK_ACQUIRED
    assert emitted[0].payload["lock_id"] == str(lock.lock_id)

    # Release lock
    lock_mgr.release_lock(lock.lock_id)
    assert len(emitted) == 2
    assert emitted[1].event_type == EventType.LOCK_RELEASED
    assert emitted[1].payload["lock_id"] == str(lock.lock_id)


def test_recovery_supervisor_emissions(
    queue_system: QueueEngine, db_conn: sqlite3.Connection
) -> None:
    """Verify RecoverySupervisor publishes zombie_job_recovered, stale_lock_expired, and lock_expired."""
    bus = get_event_bus()
    emitted = []

    def cb(e: WorkflowEvent) -> None:
        emitted.append(e)

    bus.subscribe_wildcard("recovery.*", cb)
    bus.subscribe_wildcard("lock.*", cb)

    repo = queue_system._repo
    lock_repo = queue_system._locks._repo
    now = datetime.now(timezone.utc)

    # Create stale running job
    job_id = uuid4()
    job = Job(
        job_id=job_id,
        job_type=JobType.DRY_RUN.value,
        status=JobStatus.RUNNING,
        priority=100,
        created_at=now - timedelta(seconds=20),
        started_at=now - timedelta(seconds=15),
        last_heartbeat=now - timedelta(seconds=10),
        operator_id="test_user",
        target_type="calendar",
        target_id="week_23",
        payload={"action_id": "dry_run"},
        correlation_id="corr-1",
        retry_count=0,
        max_retries=3,
    )
    cursor = db_conn.cursor()
    cursor.execute(
        """
        INSERT INTO jobs (
            job_id, job_type, status, priority, action_id, operator_id,
            target_type, target_id, payload_json, result_json,
            retry_count, max_retries, created_at, queued_at,
            started_at, completed_at, run_after, last_heartbeat,
            correlation_id, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        repo._to_row(job),
    )

    # Create stale active lock
    lock_id = uuid4()
    lock_data = (
        str(lock_id),
        LockType.CALENDAR.value,
        "week_23",
        str(uuid4()),
        LockStatus.ACTIVE.value,
        (now - timedelta(seconds=15)).isoformat(),
        (now - timedelta(seconds=10)).isoformat(),
        None,
        "{}",
    )
    cursor.execute(
        """
        INSERT INTO locks (
            lock_id, lock_type, resource_id, owner_job_id, status,
            acquired_at, last_heartbeat, released_at, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        lock_data,
    )
    db_conn.commit()

    supervisor = RecoverySupervisor(
        repo,
        lock_repo,
        queue_system,
        RecoveryConfig(
            heartbeat_timeout_seconds=5,
            sweep_interval_seconds=10,
            max_recovery_batch_size=10,
        ),
    )

    # Run recovery
    supervisor.run_sweep()

    # Check emissions
    zombie_evt = [e for e in emitted if e.event_type == EventType.ZOMBIE_JOB_RECOVERED]
    stale_lock_evt = [e for e in emitted if e.event_type == EventType.STALE_LOCK_EXPIRED]
    lock_exp_evt = [e for e in emitted if e.event_type == EventType.LOCK_EXPIRED]

    assert len(zombie_evt) == 1
    assert len(stale_lock_evt) == 1
    assert len(lock_exp_evt) == 1

    assert zombie_evt[0].payload["job_id"] == str(job_id)
    assert stale_lock_evt[0].payload["lock_id"] == str(lock_id)
    assert lock_exp_evt[0].payload["lock_id"] == str(lock_id)
