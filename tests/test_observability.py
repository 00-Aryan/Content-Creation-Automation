"""Comprehensive tests for Phase 11.8.9 — Unified Operations Dashboard & Observability."""

import os
import tempfile
import sqlite3
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from content_creation.platform.observability.health import (
    HealthStatus,
    ComponentType,
    SystemComponentHealth,
    OperationalAlert,
    AlertSeverity,
    AlertRule,
    DashboardSnapshot,
)
from content_creation.platform.observability.alerts import (
    ALERT_RULES,
    evaluate_alerts,
    _compare,
)
from content_creation.platform.observability.service import ObservabilityService


# ======================================================================
# FIXTURES
# ======================================================================


@pytest.fixture
def mock_queue_engine():
    engine = MagicMock()
    metrics = MagicMock()
    metrics.queued_count = 5
    metrics.running_count = 2
    metrics.retrying_count = 1
    metrics.completed_count = 100
    metrics.failed_count = 3
    metrics.cancelled_count = 1
    metrics.oldest_queued_age_seconds = 30.0
    engine.get_queue_metrics.return_value = metrics
    return engine


@pytest.fixture
def mock_worker_daemon():
    daemon = MagicMock()
    daemon._running = True
    daemon._worker_id = "worker-001"
    return daemon


@pytest.fixture
def mock_lock_manager():
    manager = MagicMock()
    repo = MagicMock()
    lock1 = MagicMock()
    lock1.lock_type.value = "topic"
    lock2 = MagicMock()
    lock2.lock_type.value = "manifest"
    repo.list_active_locks.return_value = [lock1, lock2]
    manager._repository = repo
    return manager


@pytest.fixture
def mock_event_repository():
    repo = MagicMock()
    repo.count_events.side_effect = lambda category=None: {
        None: 500,
        "workflow": 200,
        "job": 150,
        "review": 50,
        "lock": 30,
        "pipeline": 70,
    }.get(category, 0)
    return repo


@pytest.fixture
def mock_notification_service():
    service = MagicMock()
    summary = MagicMock()
    summary.total_unread = 8
    summary.unread_by_category = {"WORKFLOW": 3, "JOB": 2, "REVIEW": 1, "SYSTEM": 2}
    summary.unread_by_severity = {"INFO": 4, "WARNING": 2, "ERROR": 1, "SUCCESS": 1}
    summary.recent_failures = [MagicMock()]
    summary.recent_approvals = []
    summary.recent_completions = []
    service.summary.return_value = summary
    return service


@pytest.fixture
def mock_connection_manager():
    mgr = MagicMock()
    mgr.active_client_count = 3
    mgr.event_counter = 42
    return mgr


@pytest.fixture
def mock_metrics_repository():
    repo = MagicMock()
    repo.count_metrics.return_value = 150
    return repo


@pytest.fixture
def mock_kpi_catalog():
    catalog = MagicMock()
    kpi1 = MagicMock()
    kpi1.value = 85.5
    kpi1.unit = "%"
    kpi2 = MagicMock()
    kpi2.value = 42.0
    kpi2.unit = "count"
    catalog.calculate_all.return_value = {
        "briefs_generated": kpi1,
        "jobs_completed": kpi2,
    }
    return catalog


@pytest.fixture
def mock_audit_repository():
    repo = MagicMock()
    repo.count_records.return_value = 200
    return repo


@pytest.fixture
def mock_compliance_service():
    service = MagicMock()
    summary = MagicMock()
    summary.total_audit_records = 200
    summary.actors_active = 3
    summary.unique_entities = 15
    service.compliance_summary.return_value = summary
    return service


@pytest.fixture
def mock_recovery_supervisor():
    return MagicMock()


@pytest.fixture
def full_service(
    mock_queue_engine,
    mock_worker_daemon,
    mock_lock_manager,
    mock_event_repository,
    mock_notification_service,
    mock_connection_manager,
    mock_metrics_repository,
    mock_kpi_catalog,
    mock_audit_repository,
    mock_compliance_service,
    mock_recovery_supervisor,
):
    return ObservabilityService(
        queue_engine=mock_queue_engine,
        worker_daemon=mock_worker_daemon,
        lock_manager=mock_lock_manager,
        event_repository=mock_event_repository,
        notification_service=mock_notification_service,
        connection_manager=mock_connection_manager,
        metrics_repository=mock_metrics_repository,
        kpi_catalog=mock_kpi_catalog,
        audit_repository=mock_audit_repository,
        compliance_service=mock_compliance_service,
        recovery_supervisor=mock_recovery_supervisor,
    )


@pytest.fixture
def empty_service():
    return ObservabilityService()


# ======================================================================
# PART 1: HEALTH MODEL TESTS
# ======================================================================


class TestHealthModels:
    def test_health_status_enum(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_component_type_enum(self):
        assert ComponentType.QUEUE.value == "queue"
        assert ComponentType.WORKER.value == "worker"
        assert ComponentType.LOCK.value == "lock"
        assert ComponentType.EVENT.value == "event"
        assert ComponentType.NOTIFICATION.value == "notification"
        assert ComponentType.METRICS.value == "metrics"
        assert ComponentType.AUDIT.value == "audit"
        assert ComponentType.SSE.value == "sse"

    def test_alert_severity_enum(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_system_component_health_creation(self):
        h = SystemComponentHealth(
            component=ComponentType.QUEUE,
            name="Queue Engine",
            status=HealthStatus.HEALTHY,
            message="All good.",
            metrics={"queued": 5},
        )
        assert h.component == ComponentType.QUEUE
        assert h.status == HealthStatus.HEALTHY
        assert h.metrics["queued"] == 5
        assert h.last_checked is not None

    def test_system_component_health_immutable(self):
        h = SystemComponentHealth(
            component=ComponentType.QUEUE,
            name="Queue",
            status=HealthStatus.HEALTHY,
            message="ok",
        )
        with pytest.raises(AttributeError):
            h.status = HealthStatus.UNHEALTHY

    def test_operational_alert_creation(self):
        alert = OperationalAlert(
            rule_id="TEST_RULE",
            severity=AlertSeverity.WARNING,
            component=ComponentType.QUEUE,
            title="Test Alert",
            message="Something happened.",
            recommended_action="Check logs.",
            metrics={"queued": 15},
        )
        assert alert.rule_id == "TEST_RULE"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.timestamp is not None

    def test_alert_rule_creation(self):
        rule = AlertRule(
            rule_id="R1",
            severity=AlertSeverity.WARNING,
            component=ComponentType.QUEUE,
            title="Test",
            message_template="Value is {value}.",
            recommended_action="Do something.",
            warning_threshold=10,
            critical_threshold=50,
            metric_name="value",
            comparator="gte",
        )
        assert rule.rule_id == "R1"
        assert rule.comparator == "gte"

    def test_dashboard_snapshot_creation(self):
        snap = DashboardSnapshot(
            overall_status=HealthStatus.HEALTHY,
            components=[],
            alerts=[],
        )
        assert snap.overall_status == HealthStatus.HEALTHY
        assert snap.timestamp is not None
        assert snap.kpi_summary == {}
        assert snap.queue_metrics == {}


# ======================================================================
# PART 2: ALERT ENGINE TESTS
# ======================================================================


class TestAlertEngine:
    def test_compare_gt(self):
        assert _compare(15, 10, "gt") is True
        assert _compare(5, 10, "gt") is False
        assert _compare(10, 10, "gt") is False

    def test_compare_gte(self):
        assert _compare(10, 10, "gte") is True
        assert _compare(9, 10, "gte") is False

    def test_compare_lt(self):
        assert _compare(5, 10, "lt") is True
        assert _compare(15, 10, "lt") is False

    def test_compare_lte(self):
        assert _compare(10, 10, "lte") is True
        assert _compare(11, 10, "lte") is False

    def test_compare_eq(self):
        assert _compare(10, 10, "eq") is True
        assert _compare(11, 10, "eq") is False

    def test_evaluate_alerts_empty_metrics(self):
        alerts = evaluate_alerts({})
        assert alerts == []

    def test_evaluate_alerts_no_rules_fired(self):
        metrics = {
            "queued_count": 2,
            "failed_count": 1,
            "retry_count": 0,
            "active_workers": 1.0,
            "expired_locks": 0,
            "event_count": 100,
            "unread_count": 3,
            "audit_count": 50,
        }
        alerts = evaluate_alerts(metrics)
        assert alerts == []

    def test_evaluate_alerts_queue_backlog_warning(self):
        metrics = {"queued_count": 15, "failed_count": 0, "retry_count": 0, "active_workers": 1.0}
        alerts = evaluate_alerts(metrics)
        queue_alerts = [a for a in alerts if a.rule_id == "QUEUE_BACKLOG_HIGH"]
        assert len(queue_alerts) == 1
        assert queue_alerts[0].severity == AlertSeverity.WARNING

    def test_evaluate_alerts_queue_backlog_critical(self):
        metrics = {"queued_count": 55, "failed_count": 0, "retry_count": 0, "active_workers": 1.0}
        alerts = evaluate_alerts(metrics)
        queue_alerts = [a for a in alerts if a.rule_id == "QUEUE_BACKLOG_HIGH"]
        assert len(queue_alerts) == 1
        assert queue_alerts[0].severity == AlertSeverity.CRITICAL

    def test_evaluate_alerts_worker_offline(self):
        metrics = {"active_workers": 0.0}
        alerts = evaluate_alerts(metrics)
        worker_alerts = [a for a in alerts if a.rule_id == "WORKER_OFFLINE"]
        assert len(worker_alerts) == 1
        assert worker_alerts[0].severity == AlertSeverity.CRITICAL

    def test_evaluate_alerts_failed_jobs_spike(self):
        metrics = {"failed_count": 25}
        alerts = evaluate_alerts(metrics)
        failed_alerts = [a for a in alerts if a.rule_id == "FAILED_JOBS_SPIKE"]
        assert len(failed_alerts) == 1
        assert failed_alerts[0].severity == AlertSeverity.CRITICAL

    def test_evaluate_alerts_notification_backlog(self):
        metrics = {"unread_count": 30}
        alerts = evaluate_alerts(metrics)
        notif_alerts = [a for a in alerts if a.rule_id == "NOTIFICATION_BACKLOG"]
        assert len(notif_alerts) == 1
        assert notif_alerts[0].severity == AlertSeverity.WARNING

    def test_evaluate_alerts_multiple_rules(self):
        metrics = {
            "queued_count": 15,
            "failed_count": 8,
            "unread_count": 25,
        }
        alerts = evaluate_alerts(metrics)
        rule_ids = {a.rule_id for a in alerts}
        assert "QUEUE_BACKLOG_HIGH" in rule_ids
        assert "FAILED_JOBS_SPIKE" in rule_ids
        assert "NOTIFICATION_BACKLOG" in rule_ids

    def test_evaluate_alerts_custom_rules(self):
        custom = [
            AlertRule(
                rule_id="CUSTOM",
                severity=AlertSeverity.WARNING,
                component=ComponentType.QUEUE,
                title="Custom",
                message_template="Value: {val}",
                recommended_action="Fix it.",
                warning_threshold=5,
                critical_threshold=10,
                metric_name="val",
                comparator="gte",
            )
        ]
        alerts = evaluate_alerts({"val": 7}, rules=custom)
        assert len(alerts) == 1
        assert alerts[0].rule_id == "CUSTOM"

    def test_all_alert_rules_have_valid_structure(self):
        for rule in ALERT_RULES:
            assert isinstance(rule.rule_id, str)
            assert isinstance(rule.severity, AlertSeverity)
            assert isinstance(rule.component, ComponentType)
            assert isinstance(rule.warning_threshold, (int, float))
            assert isinstance(rule.critical_threshold, (int, float))
            assert rule.critical_threshold >= rule.warning_threshold


# ======================================================================
# PART 3: OBSERVABILITY SERVICE TESTS
# ======================================================================


class TestObservabilityService:
    def test_snapshot_with_all_subsystems(self, full_service):
        snap = full_service.snapshot()
        assert isinstance(snap, DashboardSnapshot)
        assert len(snap.components) == 8
        assert snap.overall_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        assert "queued_count" in snap.queue_metrics
        assert "is_running" in snap.worker_metrics

    def test_snapshot_with_no_subsystems(self, empty_service):
        snap = empty_service.snapshot()
        assert snap.overall_status == HealthStatus.UNKNOWN
        assert len(snap.components) == 8
        for comp in snap.components:
            assert comp.status == HealthStatus.UNKNOWN

    def test_queue_health_healthy(self, full_service):
        comp = full_service._check_queue()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.component == ComponentType.QUEUE

    def test_queue_health_degraded(self, mock_queue_engine):
        mock_queue_engine.get_queue_metrics.return_value.queued_count = 25
        svc = ObservabilityService(queue_engine=mock_queue_engine)
        comp = svc._check_queue()
        assert comp.status == HealthStatus.DEGRADED

    def test_queue_health_unhealthy(self, mock_queue_engine):
        mock_queue_engine.get_queue_metrics.return_value.failed_count = 15
        svc = ObservabilityService(queue_engine=mock_queue_engine)
        comp = svc._check_queue()
        assert comp.status == HealthStatus.UNHEALTHY

    def test_worker_health_running(self, full_service):
        comp = full_service._check_worker()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["is_running"] is True

    def test_worker_health_stopped(self, mock_worker_daemon):
        mock_worker_daemon._running = False
        svc = ObservabilityService(worker_daemon=mock_worker_daemon)
        comp = svc._check_worker()
        assert comp.status == HealthStatus.DEGRADED

    def test_lock_health(self, full_service):
        comp = full_service._check_lock()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["active_locks"] == 2

    def test_lock_health_degraded(self, mock_lock_manager):
        mock_lock_manager._repository.list_active_locks.return_value = [MagicMock() for _ in range(15)]
        svc = ObservabilityService(lock_manager=mock_lock_manager)
        comp = svc._check_lock()
        assert comp.status == HealthStatus.DEGRADED

    def test_event_health(self, full_service):
        comp = full_service._check_event()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["event_count"] == 500

    def test_event_health_degraded(self, mock_event_repository):
        mock_event_repository.count_events.side_effect = lambda category=None: 15000 if category is None else 0
        svc = ObservabilityService(event_repository=mock_event_repository)
        comp = svc._check_event()
        assert comp.status == HealthStatus.DEGRADED

    def test_notification_health(self, full_service):
        comp = full_service._check_notification()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["unread_count"] == 8

    def test_notification_health_degraded(self, mock_notification_service):
        mock_notification_service.summary.return_value.total_unread = 60
        svc = ObservabilityService(notification_service=mock_notification_service)
        comp = svc._check_notification()
        assert comp.status == HealthStatus.DEGRADED

    def test_metrics_health(self, full_service):
        comp = full_service._check_metrics()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["total_metrics"] == 150

    def test_audit_health(self, full_service):
        comp = full_service._check_audit()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["audit_count"] == 200

    def test_sse_health(self, full_service):
        comp = full_service._check_sse()
        assert comp.status == HealthStatus.HEALTHY
        assert comp.metrics["active_clients"] == 3

    def test_derive_overall_healthy(self):
        components = [
            SystemComponentHealth(ComponentType.QUEUE, "Q", HealthStatus.HEALTHY, "ok"),
            SystemComponentHealth(ComponentType.WORKER, "W", HealthStatus.HEALTHY, "ok"),
        ]
        assert ObservabilityService._derive_overall_status(components) == HealthStatus.HEALTHY

    def test_derive_overall_degraded(self):
        components = [
            SystemComponentHealth(ComponentType.QUEUE, "Q", HealthStatus.HEALTHY, "ok"),
            SystemComponentHealth(ComponentType.WORKER, "W", HealthStatus.DEGRADED, "slow"),
        ]
        assert ObservabilityService._derive_overall_status(components) == HealthStatus.DEGRADED

    def test_derive_overall_unhealthy(self):
        components = [
            SystemComponentHealth(ComponentType.QUEUE, "Q", HealthStatus.HEALTHY, "ok"),
            SystemComponentHealth(ComponentType.WORKER, "W", HealthStatus.UNHEALTHY, "down"),
        ]
        assert ObservabilityService._derive_overall_status(components) == HealthStatus.UNHEALTHY

    def test_derive_overall_all_unknown(self):
        components = [
            SystemComponentHealth(ComponentType.QUEUE, "Q", HealthStatus.UNKNOWN, "n/a"),
        ]
        assert ObservabilityService._derive_overall_status(components) == HealthStatus.UNKNOWN

    def test_derive_overall_empty(self):
        assert ObservabilityService._derive_overall_status([]) == HealthStatus.UNKNOWN

    def test_exception_handling_queue(self):
        bad_engine = MagicMock()
        bad_engine.get_queue_metrics.side_effect = RuntimeError("db error")
        svc = ObservabilityService(queue_engine=bad_engine)
        comp = svc._check_queue()
        assert comp.status == HealthStatus.UNKNOWN
        assert "Health check failed" in comp.message

    def test_exception_handling_worker(self):
        bad_daemon = MagicMock()
        type(bad_daemon)._running = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("db error"))
        )
        svc = ObservabilityService(worker_daemon=bad_daemon)
        comp = svc._check_worker()
        assert comp.status == HealthStatus.UNKNOWN

    def test_collect_all_metrics(self, full_service):
        metrics = full_service._collect_all_metrics()
        assert "queued_count" in metrics
        assert "active_workers" in metrics
        assert "event_count" in metrics
        assert "unread_count" in metrics
        assert "audit_count" in metrics

    def test_get_kpi_summary(self, full_service):
        kpis = full_service._get_kpi_summary()
        assert "briefs_generated" in kpis
        assert kpis["briefs_generated"]["value"] == 85.5

    def test_get_kpi_summary_empty(self, empty_service):
        assert empty_service._get_kpi_summary() == {}

    def test_snapshot_alerts_generated(self, full_service):
        full_service._queue_engine.get_queue_metrics.return_value.queued_count = 15
        snap = full_service.snapshot()
        queue_alerts = [a for a in snap.alerts if a.rule_id == "QUEUE_BACKLOG_HIGH"]
        assert len(queue_alerts) >= 1


# ======================================================================
# PART 4: INTEGRATION TESTS
# ======================================================================


class TestObservabilityIntegration:
    def test_full_snapshot_flow(self, full_service):
        snap = full_service.snapshot()
        assert snap.overall_status is not None
        assert len(snap.components) == 8
        assert isinstance(snap.timestamp, datetime)
        assert isinstance(snap.kpi_summary, dict)
        assert isinstance(snap.queue_metrics, dict)

    def test_empty_service_snapshot(self):
        svc = ObservabilityService()
        snap = svc.snapshot()
        assert snap.overall_status == HealthStatus.UNKNOWN
        assert all(c.status == HealthStatus.UNKNOWN for c in snap.components)

    def test_alerts_dont_crash_on_missing_metrics(self):
        svc = ObservabilityService()
        snap = svc.snapshot()
        assert isinstance(snap.alerts, list)

    def test_partial_subsystems(self, mock_queue_engine, mock_event_repository):
        svc = ObservabilityService(
            queue_engine=mock_queue_engine,
            event_repository=mock_event_repository,
        )
        snap = svc.snapshot()
        queue_comp = [c for c in snap.components if c.component == ComponentType.QUEUE][0]
        assert queue_comp.status == HealthStatus.HEALTHY
        event_comp = [c for c in snap.components if c.component == ComponentType.EVENT][0]
        assert event_comp.status == HealthStatus.HEALTHY
        worker_comp = [c for c in snap.components if c.component == ComponentType.WORKER][0]
        assert worker_comp.status == HealthStatus.UNKNOWN

    def test_metrics_collected_for_alerts(self, full_service):
        full_service._queue_engine.get_queue_metrics.return_value.failed_count = 25
        full_service._queue_engine.get_queue_metrics.return_value.queued_count = 60
        snap = full_service.snapshot()
        critical_alerts = [a for a in snap.alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical_alerts) >= 1

    def test_lock_repository_fallback(self, mock_lock_manager):
        svc = ObservabilityService(lock_manager=mock_lock_manager)
        comp = svc._check_lock()
        assert comp.metrics["active_locks"] == 2

    def test_notification_summary_fields(self, mock_notification_service):
        svc = ObservabilityService(notification_service=mock_notification_service)
        nm = svc._get_notification_metrics()
        assert nm["unread_count"] == 8
        assert nm["unread_by_category"]["WORKFLOW"] == 3
        assert nm["recent_failures"] == 1

    def test_event_metrics_per_category(self, mock_event_repository):
        svc = ObservabilityService(event_repository=mock_event_repository)
        em = svc._get_event_metrics()
        assert em["workflow_events"] == 200
        assert em["job_events"] == 150
        assert em["review_events"] == 50
