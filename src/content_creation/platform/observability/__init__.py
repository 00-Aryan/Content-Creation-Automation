"""Observability module — unified platform health models and aggregation."""

from content_creation.platform.observability.health import (
    HealthStatus,
    ComponentType,
    SystemComponentHealth,
    OperationalAlert,
    AlertSeverity,
    AlertRule,
    DashboardSnapshot,
)
from content_creation.platform.observability.service import ObservabilityService
from content_creation.platform.observability.alerts import (
    ALERT_RULES,
    evaluate_alerts,
)

__all__ = [
    "HealthStatus",
    "ComponentType",
    "SystemComponentHealth",
    "OperationalAlert",
    "AlertSeverity",
    "AlertRule",
    "DashboardSnapshot",
    "ObservabilityService",
    "ALERT_RULES",
    "evaluate_alerts",
]
