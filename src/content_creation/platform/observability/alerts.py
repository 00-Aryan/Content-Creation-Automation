"""Operational alert rules — threshold-based alert evaluation for platform health."""

from content_creation.platform.observability.health import (
    AlertRule,
    AlertSeverity,
    ComponentType,
    OperationalAlert,
)


ALERT_RULES: list[AlertRule] = [
    AlertRule(
        rule_id="QUEUE_BACKLOG_HIGH",
        severity=AlertSeverity.WARNING,
        component=ComponentType.QUEUE,
        title="Queue backlog high",
        message_template="Queue has {queued_count} pending jobs (threshold: {threshold}).",
        recommended_action="Investigate slow or stalled workers. Check worker logs for errors.",
        warning_threshold=10,
        critical_threshold=50,
        metric_name="queued_count",
        comparator="gte",
    ),
    AlertRule(
        rule_id="WORKER_OFFLINE",
        severity=AlertSeverity.CRITICAL,
        component=ComponentType.WORKER,
        title="No active workers",
        message_template="Zero workers have executed recently.",
        recommended_action="Restart the worker daemon. Check system resources and process status.",
        warning_threshold=-1,
        critical_threshold=0,
        metric_name="active_workers",
        comparator="eq",
    ),
    AlertRule(
        rule_id="LOCK_CONTENTION_HIGH",
        severity=AlertSeverity.WARNING,
        component=ComponentType.LOCK,
        title="Lock contention elevated",
        message_template="{expired_locks} locks expired recently (threshold: {threshold}).",
        recommended_action="Check for long-running jobs holding locks. Review lock timeout settings.",
        warning_threshold=3,
        critical_threshold=10,
        metric_name="expired_locks",
        comparator="gte",
    ),
    AlertRule(
        rule_id="FAILED_JOBS_SPIKE",
        severity=AlertSeverity.CRITICAL,
        component=ComponentType.QUEUE,
        title="Job failure rate high",
        message_template="{failed_count} jobs failed (threshold: {threshold}).",
        recommended_action="Review failed job error messages. Check job payloads and executor health.",
        warning_threshold=5,
        critical_threshold=20,
        metric_name="failed_count",
        comparator="gte",
    ),
    AlertRule(
        rule_id="EVENT_REPLAY_FAILURE",
        severity=AlertSeverity.WARNING,
        component=ComponentType.EVENT,
        title="Event replay backlog",
        message_template="Event store has {event_count} events (threshold: {threshold}).",
        recommended_action="Verify event persistence subscriber is running. Check event store disk space.",
        warning_threshold=1000,
        critical_threshold=10000,
        metric_name="event_count",
        comparator="gte",
    ),
    AlertRule(
        rule_id="NOTIFICATION_BACKLOG",
        severity=AlertSeverity.WARNING,
        component=ComponentType.NOTIFICATION,
        title="Notification backlog",
        message_template="{unread_count} unread notifications (threshold: {threshold}).",
        recommended_action="Review pending notifications. Mark processed items as read.",
        warning_threshold=20,
        critical_threshold=100,
        metric_name="unread_count",
        comparator="gte",
    ),
    AlertRule(
        rule_id="AUDIT_STORAGE_WARNING",
        severity=AlertSeverity.WARNING,
        component=ComponentType.AUDIT,
        title="Audit store growing large",
        message_template="Audit store has {audit_count} records (threshold: {threshold}).",
        recommended_action="Run audit-retention cleanup. Archive old records if needed.",
        warning_threshold=5000,
        critical_threshold=50000,
        metric_name="audit_count",
        comparator="gte",
    ),
    AlertRule(
        rule_id="JOB_RETRY_RATE_HIGH",
        severity=AlertSeverity.WARNING,
        component=ComponentType.QUEUE,
        title="Job retry rate elevated",
        message_template="{retry_count} jobs retrying (threshold: {threshold}).",
        recommended_action="Check for transient failures. Review job error patterns.",
        warning_threshold=5,
        critical_threshold=15,
        metric_name="retry_count",
        comparator="gte",
    ),
]


def _compare(value: float, threshold: float, comparator: str) -> bool:
    """Evaluate a comparison operation."""
    if comparator == "gt":
        return value > threshold
    elif comparator == "gte":
        return value >= threshold
    elif comparator == "lt":
        return value < threshold
    elif comparator == "lte":
        return value <= threshold
    elif comparator == "eq":
        return value == threshold
    return False


def evaluate_alerts(
    metrics: dict[str, float],
    rules: list[AlertRule] | None = None,
) -> list[OperationalAlert]:
    """Evaluate all alert rules against the provided metrics.

    Args:
        metrics: Dictionary of metric_name -> current value.
        rules: Optional list of rules to evaluate (defaults to ALERT_RULES).

    Returns:
        List of OperationalAlert instances for rules that fired.
    """
    if rules is None:
        rules = ALERT_RULES

    alerts: list[OperationalAlert] = []

    for rule in rules:
        if rule.metric_name not in metrics:
            continue
        current_value = metrics[rule.metric_name]

        if _compare(current_value, rule.critical_threshold, rule.comparator):
            alerts.append(
                OperationalAlert(
                    rule_id=rule.rule_id,
                    severity=AlertSeverity.CRITICAL,
                    component=rule.component,
                    title=rule.title,
                    message=rule.message_template.format(
                        threshold=rule.critical_threshold,
                        **{rule.metric_name: current_value},
                    ),
                    recommended_action=rule.recommended_action,
                    metrics={rule.metric_name: current_value},
                )
            )
        elif _compare(current_value, rule.warning_threshold, rule.comparator):
            alerts.append(
                OperationalAlert(
                    rule_id=rule.rule_id,
                    severity=AlertSeverity.WARNING,
                    component=rule.component,
                    title=rule.title,
                    message=rule.message_template.format(
                        threshold=rule.warning_threshold,
                        **{rule.metric_name: current_value},
                    ),
                    recommended_action=rule.recommended_action,
                    metrics={rule.metric_name: current_value},
                )
            )

    return alerts
