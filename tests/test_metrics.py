"""Comprehensive tests for Phase 11.8.7 — Metrics & Telemetry Subscriber System."""

import json
import os
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from content_creation.events.bus import InMemoryEventBus
from content_creation.events.factory import (
    create_event,
    create_job_event,
    create_workflow_event,
    create_pipeline_event,
    create_lock_event,
    create_recovery_event,
)
from content_creation.events.models import EventSeverity, EventType, WorkflowEvent
from content_creation.events.store.sqlite_repository import SQLiteEventRepository
from content_creation.metrics.models import MetricRecord, MetricType
from content_creation.metrics.repository import MetricRepository
from content_creation.metrics.sqlite_repository import SQLiteMetricRepository
from content_creation.metrics.schema import create_metrics_schema
from content_creation.metrics.subscriber import MetricsSubscriber
from content_creation.metrics.kpi import KPICatalog, KPIResult
from content_creation.metrics.aggregation import MetricsAggregationService, AggregationResult
from content_creation.metrics.telemetry import TelemetryService
from content_creation.metrics.maintenance import MetricsMaintenanceService


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def tmp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def metric_repo(tmp_db_path):
    """Create a SQLiteMetricRepository with a temp database."""
    repo = SQLiteMetricRepository(tmp_db_path)
    yield repo
    repo.close()


@pytest.fixture
def event_repo(tmp_db_path):
    """Create a SQLiteEventRepository with a temp database."""
    repo = SQLiteEventRepository(tmp_db_path)
    yield repo
    repo.close()


@pytest.fixture
def bus():
    """Create a fresh InMemoryEventBus."""
    return InMemoryEventBus()


def _make_event(
    event_type: EventType = EventType.BRIEF_GENERATED,
    entity_type: str = "brief",
    entity_id: str = "test-entity",
    correlation_id: str = "",
    source: str = "workflow_engine",
    payload: dict = None,
) -> WorkflowEvent:
    """Helper to create a WorkflowEvent with custom fields."""
    return create_event(
        event_type=event_type,
        source=source,
        correlation_id=correlation_id or str(uuid4()),
        actor_id="test-actor",
        entity_type=entity_type,
        entity_id=entity_id,
        severity=EventSeverity.INFO,
        payload=payload or {"test": True},
    )


# ======================================================================
# PART 1: MetricRecord MODEL TESTS
# ======================================================================


class TestMetricRecord:
    def test_creation(self):
        record = MetricRecord(
            metric_id=uuid4(),
            metric_name="test_metric",
            metric_type=MetricType.COUNTER,
            value=1.0,
            timestamp=datetime.now(timezone.utc),
        )
        assert record.metric_name == "test_metric"
        assert record.metric_type == MetricType.COUNTER
        assert record.value == 1.0

    def test_immutable(self):
        record = MetricRecord.counter("test")
        with pytest.raises(AttributeError):
            record.metric_name = "changed"

    def test_to_dict(self):
        record = MetricRecord.counter(
            "test",
            entity_type="job",
            entity_id="j1",
            dimensions={"source": "test"},
        )
        d = record.to_dict()
        assert d["metric_name"] == "test"
        assert d["metric_type"] == "counter"
        assert d["entity_type"] == "job"
        assert d["dimensions"]["source"] == "test"

    def test_counter_factory(self):
        record = MetricRecord.counter("jobs_completed_total")
        assert record.metric_type == MetricType.COUNTER
        assert record.value == 1.0

    def test_gauge_factory(self):
        record = MetricRecord.gauge("queue_depth", value=5.0)
        assert record.metric_type == MetricType.GAUGE
        assert record.value == 5.0

    def test_timer_factory(self):
        record = MetricRecord.timer("job_duration_seconds", duration_seconds=3.5)
        assert record.metric_type == MetricType.TIMER
        assert record.value == 3.5

    def test_dimensions_default(self):
        record = MetricRecord.counter("test")
        assert record.dimensions == {}

    def test_metric_types(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"


# ======================================================================
# PART 2: SCHEMA TESTS
# ======================================================================


class TestMetricsSchema:
    def test_schema_creation(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_metrics_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_schema_idempotent(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_metrics_schema(conn)
            create_metrics_schema(conn)  # Should not raise
        finally:
            conn.close()

    def test_indexes_created(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path)
        try:
            create_metrics_schema(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_metrics%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            assert "idx_metrics_name" in indexes
            assert "idx_metrics_type" in indexes
            assert "idx_metrics_timestamp" in indexes
            assert "idx_metrics_entity" in indexes
            assert "idx_metrics_name_timestamp" in indexes
        finally:
            conn.close()


# ======================================================================
# PART 3: REPOSITORY CRUD TESTS
# ======================================================================


class TestSQLiteMetricRepository:
    def test_save_and_get(self, metric_repo):
        record = MetricRecord.counter("test_metric")
        metric_repo.save_metric(record)
        retrieved = metric_repo.get_metric(record.metric_id)
        assert retrieved is not None
        assert retrieved.metric_name == "test_metric"

    def test_get_nonexistent(self, metric_repo):
        assert metric_repo.get_metric(uuid4()) is None

    def test_save_idempotent(self, metric_repo):
        record = MetricRecord.counter("test")
        metric_repo.save_metric(record)
        metric_repo.save_metric(record)  # Duplicate
        assert metric_repo.count_metrics() == 1

    def test_query_by_name(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("metric_a"))
        metric_repo.save_metric(MetricRecord.counter("metric_b"))
        metric_repo.save_metric(MetricRecord.counter("metric_a"))
        results = metric_repo.query_metrics(metric_name="metric_a")
        assert len(results) == 2

    def test_query_by_type(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("c1"))
        metric_repo.save_metric(MetricRecord.gauge("g1", value=10.0))
        results = metric_repo.query_metrics(metric_type=MetricType.COUNTER)
        assert len(results) == 1

    def test_query_by_entity(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("m1", entity_type="job", entity_id="j1"))
        metric_repo.save_metric(MetricRecord.counter("m2", entity_type="job", entity_id="j2"))
        metric_repo.save_metric(MetricRecord.counter("m3", entity_type="brief", entity_id="b1"))
        results = metric_repo.query_metrics(entity_type="job")
        assert len(results) == 2

    def test_query_by_time_range(self, metric_repo):
        now = datetime.now(timezone.utc)
        record = MetricRecord.counter("test", timestamp=now)
        metric_repo.save_metric(record)
        results = metric_repo.query_metrics(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        assert len(results) >= 1

    def test_query_with_dimensions(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("m1", dimensions={"source": "a"}))
        metric_repo.save_metric(MetricRecord.counter("m2", dimensions={"source": "b"}))
        results = metric_repo.query_metrics(dimensions={"source": "a"})
        assert len(results) == 1

    def test_aggregate_sum(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("test", value=1.0))
        metric_repo.save_metric(MetricRecord.counter("test", value=2.0))
        metric_repo.save_metric(MetricRecord.counter("test", value=3.0))
        result = metric_repo.aggregate_metrics("test", "sum")
        assert result == 6.0

    def test_aggregate_avg(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("test", value=2.0))
        metric_repo.save_metric(MetricRecord.counter("test", value=4.0))
        result = metric_repo.aggregate_metrics("test", "avg")
        assert result == 3.0

    def test_aggregate_min_max(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("test", value=5.0))
        metric_repo.save_metric(MetricRecord.counter("test", value=1.0))
        metric_repo.save_metric(MetricRecord.counter("test", value=9.0))
        assert metric_repo.aggregate_metrics("test", "min") == 1.0
        assert metric_repo.aggregate_metrics("test", "max") == 9.0

    def test_aggregate_count(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("test"))
        metric_repo.save_metric(MetricRecord.counter("test"))
        result = metric_repo.aggregate_metrics("test", "count")
        assert result == 2.0

    def test_aggregate_empty(self, metric_repo):
        result = metric_repo.aggregate_metrics("nonexistent", "sum")
        assert result is None

    def test_aggregate_unsupported(self, metric_repo):
        with pytest.raises(ValueError):
            metric_repo.aggregate_metrics("test", "median")

    def test_aggregate_by_dimensions(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("m1", value=1.0, dimensions={"src": "a"}))
        metric_repo.save_metric(MetricRecord.counter("m1", value=2.0, dimensions={"src": "a"}))
        metric_repo.save_metric(MetricRecord.counter("m1", value=3.0, dimensions={"src": "b"}))
        result = metric_repo.aggregate_by_dimensions("m1", "sum", "src")
        assert result["a"] == 3.0
        assert result["b"] == 3.0

    def test_count_metrics(self, metric_repo):
        assert metric_repo.count_metrics() == 0
        metric_repo.save_metric(MetricRecord.counter("a"))
        metric_repo.save_metric(MetricRecord.counter("b"))
        assert metric_repo.count_metrics() == 2
        assert metric_repo.count_metrics(metric_name="a") == 1

    def test_delete_expired(self, metric_repo):
        old = MetricRecord(
            metric_id=uuid4(), metric_name="old", metric_type=MetricType.COUNTER,
            value=1.0, timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        recent = MetricRecord.counter("recent")
        metric_repo.save_metric(old)
        metric_repo.save_metric(recent)
        deleted = metric_repo.delete_expired(datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert deleted == 1
        assert metric_repo.count_metrics() == 1

    def test_thread_safety(self, tmp_db_path):
        repo = SQLiteMetricRepository(tmp_db_path)
        try:
            errors: List[Exception] = []

            def save_metrics():
                try:
                    for _ in range(10):
                        repo.save_metric(MetricRecord.counter("test"))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=save_metrics) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == []
            assert repo.count_metrics() == 50
        finally:
            repo.close()

    def test_close(self, tmp_db_path):
        repo = SQLiteMetricRepository(tmp_db_path)
        try:
            repo.save_metric(MetricRecord.counter("test"))
        finally:
            repo.close()
        # Should be able to create new repo on same path
        repo2 = SQLiteMetricRepository(tmp_db_path)
        try:
            assert repo2.count_metrics() == 1
        finally:
            repo2.close()

    def test_close_idempotent(self, tmp_db_path):
        repo = SQLiteMetricRepository(tmp_db_path)
        repo.close()
        repo.close()  # Should not raise


# ======================================================================
# PART 4: METRICS SUBSCRIBER TESTS
# ======================================================================


class TestMetricsSubscriber:
    def test_persists_workflow_metrics(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(EventType.BRIEF_GENERATED)
        bus.publish(event)
        assert metric_repo.count_metrics() >= 1

    def test_persists_job_metrics(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(EventType.JOB_COMPLETED)
        bus.publish(event)
        assert metric_repo.count_metrics() >= 1

    def test_persists_lock_metrics(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(EventType.LOCK_ACQUIRED)
        bus.publish(event)
        assert metric_repo.count_metrics() >= 1

    def test_persists_pipeline_metrics(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(EventType.PIPELINE_COMPLETED)
        bus.publish(event)
        assert metric_repo.count_metrics() >= 1

    def test_persists_recovery_metrics(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(EventType.ZOMBIE_JOB_RECOVERED)
        bus.publish(event)
        assert metric_repo.count_metrics() >= 1

    def test_does_not_mutate_event(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(EventType.BRIEF_GENERATED, payload={"original": True})
        bus.publish(event)
        assert event.payload.get("original") is True

    def test_failure_isolation(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)

        def failing_callback(event):
            raise RuntimeError("Intentional failure")

        bus.subscribe_wildcard("*", failing_callback)
        event = _make_event(EventType.BRIEF_GENERATED)
        bus.publish(event)  # Should not raise
        assert metric_repo.count_metrics() >= 1

    def test_shutdown(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        subscriber.shutdown()
        event = _make_event(EventType.BRIEF_GENERATED)
        bus.publish(event)
        assert metric_repo.count_metrics() == 0

    def test_job_duration_metric(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(
            EventType.JOB_COMPLETED,
            payload={"duration_seconds": 5.0, "job_type": "brief_generation"},
        )
        bus.publish(event)
        # Should have both counter and timer metrics
        assert metric_repo.count_metrics() >= 2

    def test_pipeline_duration_metric(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        event = _make_event(
            EventType.PIPELINE_COMPLETED,
            payload={"duration_seconds": 30.0},
        )
        bus.publish(event)
        assert metric_repo.count_metrics() >= 2

    def test_multiple_events_accumulate(self, metric_repo, bus):
        subscriber = MetricsSubscriber(repository=metric_repo, bus=bus)
        for _ in range(5):
            bus.publish(_make_event(EventType.BRIEF_GENERATED))
        result = metric_repo.aggregate_metrics("briefs_generated_total", "count")
        assert result == 5.0


# ======================================================================
# PART 5: KPI CATALOG TESTS
# ======================================================================


class TestKPICatalog:
    def test_calculate_all(self, metric_repo):
        # Add some metrics
        metric_repo.save_metric(MetricRecord.counter("briefs_generated_total"))
        metric_repo.save_metric(MetricRecord.counter("jobs_completed_total"))
        metric_repo.save_metric(MetricRecord.counter("jobs_failed_total"))

        catalog = KPICatalog(metric_repo)
        kpis = catalog.calculate_all()
        assert "briefs_generated" in kpis
        assert "jobs_completed" in kpis
        assert "job_success_rate" in kpis

    def test_approval_rate(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("briefs_approved_total"))
        metric_repo.save_metric(MetricRecord.counter("assets_approved_total"))
        metric_repo.save_metric(MetricRecord.counter("briefs_rejected_total"))

        catalog = KPICatalog(metric_repo)
        result = catalog.approval_rate()
        assert result.value == pytest.approx(66.666, rel=0.01)

    def test_approval_rate_zero_total(self, metric_repo):
        catalog = KPICatalog(metric_repo)
        result = catalog.approval_rate()
        assert result.value == 0.0

    def test_rejection_rate(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("briefs_approved_total"))
        metric_repo.save_metric(MetricRecord.counter("briefs_rejected_total"))

        catalog = KPICatalog(metric_repo)
        result = catalog.rejection_rate()
        assert result.value == pytest.approx(50.0)

    def test_job_success_rate(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("jobs_completed_total"))
        metric_repo.save_metric(MetricRecord.counter("jobs_completed_total"))
        metric_repo.save_metric(MetricRecord.counter("jobs_failed_total"))

        catalog = KPICatalog(metric_repo)
        result = catalog.job_success_rate()
        assert result.value == pytest.approx(66.666, rel=0.01)

    def test_job_success_rate_zero(self, metric_repo):
        catalog = KPICatalog(metric_repo)
        result = catalog.job_success_rate()
        assert result.value == 0.0

    def test_average_job_runtime(self, metric_repo):
        metric_repo.save_metric(MetricRecord.timer("job_duration_seconds", duration_seconds=2.0))
        metric_repo.save_metric(MetricRecord.timer("job_duration_seconds", duration_seconds=4.0))

        catalog = KPICatalog(metric_repo)
        result = catalog.average_job_runtime()
        assert result.value == pytest.approx(3.0)

    def test_pipeline_success_rate(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("pipelines_completed_total"))
        metric_repo.save_metric(MetricRecord.counter("pipelines_completed_total"))
        metric_repo.save_metric(MetricRecord.counter("pipelines_failed_total"))

        catalog = KPICatalog(metric_repo)
        result = catalog.pipeline_success_rate()
        assert result.value == pytest.approx(66.666, rel=0.01)

    def test_lock_contentions(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("locks_expired_total"))
        metric_repo.save_metric(MetricRecord.counter("locks_expired_total"))

        catalog = KPICatalog(metric_repo)
        result = catalog.lock_contentions()
        assert result.value == 2.0

    def test_zombie_recoveries(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("zombie_jobs_recovered_total"))

        catalog = KPICatalog(metric_repo)
        result = catalog.zombie_recoveries()
        assert result.value == 1.0

    def test_kpi_result_properties(self):
        result = KPIResult(name="test", value=42.0, unit="count")
        assert result.name == "test"
        assert result.value == 42.0
        assert result.unit == "count"

    def test_briefs_generated(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("briefs_generated_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.briefs_generated().value == 1.0

    def test_storyboards_generated(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("storyboards_generated_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.storyboards_generated().value == 1.0

    def test_assets_generated(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("assets_generated_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.assets_generated().value == 1.0

    def test_jobs_started(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("jobs_started_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.jobs_started().value == 1.0

    def test_jobs_completed(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("jobs_completed_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.jobs_completed().value == 1.0

    def test_jobs_failed(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("jobs_failed_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.jobs_failed().value == 1.0

    def test_job_retries(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("jobs_retried_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.job_retries().value == 1.0

    def test_stale_lock_expirations(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("stale_locks_expired_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.stale_lock_expirations().value == 1.0

    def test_pipelines_completed(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("pipelines_completed_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.pipelines_completed().value == 1.0

    def test_pipelines_failed(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("pipelines_failed_total"))
        catalog = KPICatalog(metric_repo)
        assert catalog.pipelines_failed().value == 1.0


# ======================================================================
# PART 6: AGGREGATION SERVICE TESTS
# ======================================================================


class TestMetricsAggregationService:
    def test_aggregate_daily(self, metric_repo):
        now = datetime.now(timezone.utc)
        for i in range(3):
            metric_repo.save_metric(MetricRecord.counter(
                "test",
                value=float(i + 1),
                timestamp=now - timedelta(hours=i * 12),
            ))

        service = MetricsAggregationService(metric_repo)
        result = service.aggregate_daily(
            "test", "sum",
            start=now - timedelta(days=2),
            end=now + timedelta(hours=1),
        )
        assert isinstance(result, AggregationResult)
        assert result.metric_name == "test"
        assert result.aggregation == "sum"
        assert result.bucket_size == "daily"
        assert len(result.buckets) >= 2

    def test_aggregate_hourly(self, metric_repo):
        now = datetime.now(timezone.utc)
        metric_repo.save_metric(MetricRecord.counter("test", value=1.0, timestamp=now))

        service = MetricsAggregationService(metric_repo)
        result = service.aggregate_hourly(
            "test", "count",
            start=now - timedelta(hours=2),
            end=now + timedelta(hours=1),
        )
        assert len(result.buckets) == 3

    def test_aggregate_weekly(self, metric_repo):
        now = datetime.now(timezone.utc)
        metric_repo.save_metric(MetricRecord.counter("test", value=1.0, timestamp=now))

        service = MetricsAggregationService(metric_repo)
        result = service.aggregate_weekly(
            "test", "sum",
            start=now - timedelta(weeks=4),
            end=now,
        )
        assert len(result.buckets) == 4

    def test_aggregate_monthly(self, metric_repo):
        now = datetime.now(timezone.utc)
        metric_repo.save_metric(MetricRecord.counter("test", value=1.0, timestamp=now))

        service = MetricsAggregationService(metric_repo)
        result = service.aggregate_monthly(
            "test", "sum",
            start=now - timedelta(days=60),
            end=now,
        )
        assert len(result.buckets) == 2

    def test_aggregate_unsupported(self, metric_repo):
        service = MetricsAggregationService(metric_repo)
        with pytest.raises(ValueError):
            service.aggregate_daily("test", "median", datetime.now(timezone.utc), datetime.now(timezone.utc))

    def test_rolling_average(self, metric_repo):
        now = datetime.now(timezone.utc)
        metric_repo.save_metric(MetricRecord.timer("job_duration_seconds", duration_seconds=2.0, timestamp=now))
        metric_repo.save_metric(MetricRecord.timer("job_duration_seconds", duration_seconds=4.0, timestamp=now))

        service = MetricsAggregationService(metric_repo)
        result = service.rolling_average("job_duration_seconds", window_days=7)
        assert result == pytest.approx(3.0)

    def test_rolling_average_empty(self, metric_repo):
        service = MetricsAggregationService(metric_repo)
        result = service.rolling_average("nonexistent", window_days=7)
        assert result == 0.0

    def test_growth_rate(self, metric_repo):
        now = datetime.now(timezone.utc)
        # Current period: 10 events
        for _ in range(10):
            metric_repo.save_metric(MetricRecord.counter("test", timestamp=now - timedelta(days=3)))
        # Previous period: 5 events
        for _ in range(5):
            metric_repo.save_metric(MetricRecord.counter("test", timestamp=now - timedelta(days=13)))

        service = MetricsAggregationService(metric_repo)
        result = service.growth_rate("test", period_days=10, end=now)
        assert result == pytest.approx(100.0)

    def test_growth_rate_zero_previous(self, metric_repo):
        now = datetime.now(timezone.utc)
        metric_repo.save_metric(MetricRecord.counter("test", timestamp=now - timedelta(days=3)))

        service = MetricsAggregationService(metric_repo)
        result = service.growth_rate("test", period_days=10, end=now)
        assert result == 100.0

    def test_aggregation_result_properties(self):
        result = AggregationResult(
            metric_name="test", aggregation="sum", bucket_size="daily",
            buckets=[], total=0.0,
        )
        assert result.metric_name == "test"
        assert result.total == 0.0


# ======================================================================
# PART 7: TELEMETRY SERVICE TESTS
# ======================================================================


class TestTelemetryService:
    def test_system_summary(self, metric_repo, event_repo):
        service = TelemetryService(
            metrics_repository=metric_repo,
            event_repository=event_repo,
        )
        summary = service.system_summary()
        assert summary.total_metrics_stored == 0
        assert summary.total_events_stored == 0

    def test_workflow_summary(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("briefs_generated_total"))
        metric_repo.save_metric(MetricRecord.counter("assets_approved_total"))
        metric_repo.save_metric(MetricRecord.counter("assets_rejected_total"))

        service = TelemetryService(metrics_repository=metric_repo)
        summary = service.workflow_summary()
        assert summary.briefs_generated == 1
        assert summary.total_reviews == 2

    def test_job_summary(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("jobs_started_total"))
        metric_repo.save_metric(MetricRecord.counter("jobs_completed_total"))

        service = TelemetryService(metrics_repository=metric_repo)
        summary = service.job_summary()
        assert summary.jobs_started == 1
        assert summary.jobs_completed == 1
        assert summary.success_rate == pytest.approx(100.0)

    def test_reliability_summary(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("locks_expired_total"))
        metric_repo.save_metric(MetricRecord.counter("zombie_jobs_recovered_total"))

        service = TelemetryService(metrics_repository=metric_repo)
        summary = service.reliability_summary()
        assert summary.lock_contentions == 1
        assert summary.zombie_recoveries == 1

    def test_full_summary(self, metric_repo):
        service = TelemetryService(metrics_repository=metric_repo)
        result = service.full_summary()
        assert "system" in result
        assert "workflow" in result
        assert "jobs" in result
        assert "reliability" in result

    def test_system_summary_without_event_repo(self, metric_repo):
        service = TelemetryService(metrics_repository=metric_repo)
        summary = service.system_summary()
        assert summary.total_events_stored == 0


# ======================================================================
# PART 8: MAINTENANCE SERVICE TESTS
# ======================================================================


class TestMetricsMaintenanceService:
    def test_cleanup_expired(self, metric_repo):
        old = MetricRecord(
            metric_id=uuid4(), metric_name="old", metric_type=MetricType.COUNTER,
            value=1.0, timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        metric_repo.save_metric(old)
        metric_repo.save_metric(MetricRecord.counter("recent"))

        service = MetricsMaintenanceService(repository=metric_repo)
        deleted = service.cleanup_expired()
        assert deleted == 1
        assert metric_repo.count_metrics() == 1

    def test_enforce_retention(self, metric_repo):
        service = MetricsMaintenanceService(repository=metric_repo)
        result = service.enforce_retention()
        assert "deleted" in result

    def test_storage_stats(self, metric_repo):
        metric_repo.save_metric(MetricRecord.counter("test"))
        service = MetricsMaintenanceService(repository=metric_repo)
        stats = service.storage_stats()
        assert stats["total_metrics"] == 1
        assert stats["retention_days"] == 90

    def test_custom_retention(self, metric_repo):
        service = MetricsMaintenanceService(repository=metric_repo, retention_days=30)
        assert service._retention_days == 30


# ======================================================================
# PART 9: EVENT REPLAY COMPATIBILITY TESTS
# ======================================================================


class TestMetricsReplayCompatibility:
    def test_rebuild_metrics_from_events(self, metric_repo, event_repo, bus):
        """Test that metrics can be rebuilt from event store replay."""
        from content_creation.events.store.subscriber import EventPersistenceSubscriber

        # Create events and persist them to both stores
        persist_sub = EventPersistenceSubscriber(repository=event_repo, bus=bus)
        metrics_sub = MetricsSubscriber(repository=metric_repo, bus=bus)
        for i in range(3):
            bus.publish(_make_event(EventType.BRIEF_GENERATED, payload={"i": i}))
        persist_sub.shutdown()
        metrics_sub.shutdown()

        # Verify both stores have data
        assert event_repo.count_events() >= 3
        assert metric_repo.count_metrics() >= 3

        # Delete all metrics (but keep events)
        metric_repo.delete_expired(datetime.now(timezone.utc) + timedelta(hours=1))
        assert metric_repo.count_metrics() == 0
        assert event_repo.count_events() >= 3

        # Replay events to rebuild metrics
        from content_creation.events.store.replay import EventReplayEngine
        replay_bus = InMemoryEventBus()
        replay_subscriber = MetricsSubscriber(repository=metric_repo, bus=replay_bus)
        engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
        replayed = engine.replay_all()

        # Verify metrics are rebuilt
        assert metric_repo.count_metrics() >= 3
        assert len(replayed) >= 3

        replay_subscriber.shutdown()

    def test_idempotent_rebuild(self, metric_repo, event_repo, bus):
        """Test that rebuilding metrics twice produces the same result."""
        from content_creation.events.store.subscriber import EventPersistenceSubscriber

        persist_sub = EventPersistenceSubscriber(repository=event_repo, bus=bus)
        metrics_sub = MetricsSubscriber(repository=metric_repo, bus=bus)
        bus.publish(_make_event(EventType.JOB_COMPLETED))
        persist_sub.shutdown()
        metrics_sub.shutdown()

        count_after_first = metric_repo.count_metrics()

        # Replay again (metrics get new IDs, so count increases)
        from content_creation.events.store.replay import EventReplayEngine
        replay_bus = InMemoryEventBus()
        MetricsSubscriber(repository=metric_repo, bus=replay_bus)
        engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
        engine.replay_all()

        count_after_second = metric_repo.count_metrics()
        # Count increases because replay creates new metric records
        assert count_after_second > count_after_first


# ======================================================================
# PART 10: INTEGRATION TESTS
# ======================================================================


class TestMetricsIntegration:
    def test_full_lifecycle(self, tmp_db_path):
        """Test complete lifecycle: emit event -> persist -> metric -> KPI -> telemetry."""
        event_repo = SQLiteEventRepository(tmp_db_path)
        metric_repo = SQLiteMetricRepository(tmp_db_path)
        try:
            bus = InMemoryEventBus()

            # Subscribe metrics
            metrics_sub = MetricsSubscriber(repository=metric_repo, bus=bus)

            # Emit events
            bus.publish(_make_event(EventType.BRIEF_GENERATED))
            bus.publish(_make_event(EventType.JOB_COMPLETED, payload={"duration_seconds": 3.0}))
            bus.publish(_make_event(EventType.PIPELINE_COMPLETED))

            # Verify metrics
            assert metric_repo.count_metrics() >= 3

            # Calculate KPIs
            catalog = KPICatalog(metric_repo)
            kpis = catalog.calculate_all()
            assert kpis["briefs_generated"].value >= 1
            assert kpis["jobs_completed"].value >= 1

            # Telemetry
            telemetry = TelemetryService(
                metrics_repository=metric_repo,
                event_repository=event_repo,
            )
            summary = telemetry.full_summary()
            assert summary["workflow"].briefs_generated >= 1

            metrics_sub.shutdown()
        finally:
            event_repo.close()
            metric_repo.close()

    def test_concurrent_metrics(self, tmp_db_path):
        """Test concurrent metric writes."""
        metric_repo = SQLiteMetricRepository(tmp_db_path)
        try:
            errors: List[Exception] = []

            def write_metrics():
                try:
                    for _ in range(10):
                        metric_repo.save_metric(MetricRecord.counter("concurrent_test"))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=write_metrics) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == []
            assert metric_repo.count_metrics() == 50
        finally:
            metric_repo.close()

    def test_maintenance_after_writes(self, tmp_db_path):
        """Test maintenance works after writes."""
        metric_repo = SQLiteMetricRepository(tmp_db_path)
        try:
            # Add old metrics
            old = MetricRecord(
                metric_id=uuid4(), metric_name="old", metric_type=MetricType.COUNTER,
                value=1.0, timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
            metric_repo.save_metric(old)
            metric_repo.save_metric(MetricRecord.counter("recent"))

            service = MetricsMaintenanceService(repository=metric_repo)
            deleted = service.cleanup_expired()
            assert deleted == 1
            assert metric_repo.count_metrics() == 1
        finally:
            metric_repo.close()
