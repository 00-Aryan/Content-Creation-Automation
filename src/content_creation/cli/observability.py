"""Observability CLI subcommands: event store, metrics, telemetry, and audit reporting."""

from datetime import datetime, timedelta, timezone
from typing import Optional, cast

import typer

from content_creation.audit.models import AuditRecord
from content_creation.cli.common import get_context
from content_creation.metrics.telemetry import (
    JobSummary,
    ReliabilitySummary,
    SystemSummary,
    WorkflowSummary,
)


def event_timeline(
    category: Optional[str] = typer.Option(
        None,
        "--category",
        help="Filter by category (workflow, review, job, lock, recovery, pipeline)",
    ),
    limit: int = typer.Option(20, "--limit", help="Maximum number of events to show"),
    entity_type: Optional[str] = typer.Option(
        None, "--entity-type", help="Filter by entity type"
    ),
    entity_id: Optional[str] = typer.Option(
        None, "--entity-id", help="Filter by entity ID"
    ),
    correlation_id: Optional[str] = typer.Option(
        None, "--correlation-id", help="Filter by correlation ID"
    ),
) -> int:
    """View recent events from the event store."""
    from content_creation.events.store import (
        EventTimelineService,
        SQLiteEventRepository,
    )

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "events.db"
    if not db_path.exists():
        print(
            "No event store found. Events will appear after running pipeline actions."
        )
        return 0

    repo = SQLiteEventRepository(str(db_path))
    try:
        service = EventTimelineService(repository=repo)
        if correlation_id:
            events = service.timeline_for_correlation(correlation_id)
        elif entity_type and entity_id:
            events = service.entity_history(entity_type, entity_id, limit=limit)
        elif entity_type:
            events = service.entity_history(entity_type, "__all__", limit=limit)
        else:
            page = service.recent_events(page_size=limit, category=category)
            events = page.events

        if not events:
            print("No events found.")
            return 0

        print(
            f"\n{'Timestamp':<20} {'Event':<25} {'Category':<12} {'Source':<20} {'Entity':<15}"
        )
        print("-" * 92)
        for e in events:
            ts = e.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ent = (
                f"{e.entity_type}:{e.entity_id[:12]}"
                if e.entity_type
                else "-"
            )
            print(
                f"{ts:<20} {e.event_name:<25} {e.category:<12} {e.source:<20} {ent:<15}"
            )

        print(f"\nTotal: {len(events)} events")
        return 0
    finally:
        repo.close()


def event_stats() -> int:
    """Show event store statistics."""
    from content_creation.events.store import (
        EventMaintenanceService,
        SQLiteEventRepository,
    )

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "events.db"
    if not db_path.exists():
        print("No event store found.")
        return 0

    repo = SQLiteEventRepository(str(db_path))
    try:
        service = EventMaintenanceService(repository=repo)
        stats = service.storage_stats()

        print("\n=== Event Store Statistics ===")
        for cat, count in sorted(stats.items()):
            print(f"  {cat:<15} {count:>6} events")
        print("-" * 25)
        print(f"  {'TOTAL':<15} {stats.get('total', 0):>6} events")
        return 0
    finally:
        repo.close()


def event_store() -> int:
    """Show event store location and statistics summary."""
    return event_stats()


def event_tail(
    limit: int = typer.Option(20, "--limit", help="Number of recent events to display"),
    category: Optional[str] = typer.Option(
        None, "--category", help="Filter by event category"
    ),
) -> int:
    """Tail recent events from the event store."""
    return event_timeline(category=category, limit=limit)


def event_replay(
    category: Optional[str] = typer.Option(
        None, "--category", help="Replay events from a specific category"
    ),
    correlation_id: Optional[str] = typer.Option(
        None, "--correlation-id", help="Replay events by correlation ID"
    ),
    entity_type: Optional[str] = typer.Option(
        None, "--entity-type", help="Replay events by entity type"
    ),
    entity_id: Optional[str] = typer.Option(
        None, "--entity-id", help="Replay events by entity ID"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Inspect events without re-emitting"
    ),
    limit: int = typer.Option(
        100, "--limit", help="Maximum number of events to replay"
    ),
) -> int:
    """Replay events from the event store."""
    from content_creation.events.bus import InMemoryEventBus
    from content_creation.events.store import (
        EventReplayEngine,
        SQLiteEventRepository,
    )

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "events.db"
    if not db_path.exists():
        print("No event store found.")
        return 0

    repo = SQLiteEventRepository(str(db_path))
    try:
        bus = InMemoryEventBus()
        engine = EventReplayEngine(repository=repo, bus=bus)

        dry_run_label = " (dry-run)" if dry_run else ""

        if correlation_id:
            events = engine.replay_by_correlation(correlation_id, dry_run=dry_run)
            print(
                f"Replayed {len(events)} events for correlation {correlation_id}{dry_run_label}"
            )
        elif entity_type and entity_id:
            events = engine.replay_by_entity(entity_type, entity_id, dry_run=dry_run)
            print(
                f"Replayed {len(events)} events for {entity_type}:{entity_id}{dry_run_label}"
            )
        elif category:
            events = engine.replay_by_category(category, limit=limit, dry_run=dry_run)
            print(
                f"Replayed {len(events)} events from category '{category}'{dry_run_label}"
            )
        else:
            events = engine.replay_all(limit=limit, dry_run=dry_run)
            print(f"Replayed {len(events)} events{dry_run_label}")

        if events and dry_run:
            print(f"\n{'Timestamp':<20} {'Event':<25} {'Entity':<15}")
            print("-" * 60)
            for e in events[:20]:
                ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ent = (
                    f"{e.entity_type}:{e.entity_id[:12]}"
                    if e.entity_type
                    else "-"
                )
                print(f"{ts:<20} {e.event_type.value:<25} {ent:<15}")
            if len(events) > 20:
                print(f"  ... and {len(events) - 20} more")

        return 0
    finally:
        repo.close()


def event_cleanup(
    category: Optional[str] = typer.Option(
        None, "--category", help="Cleanup events from a specific category"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview cleanup without deleting"
    ),
) -> int:
    """Run event store retention cleanup."""
    from content_creation.events.store import (
        EventMaintenanceService,
        SQLiteEventRepository,
    )

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "events.db"
    if not db_path.exists():
        print("No event store found.")
        return 0

    repo = SQLiteEventRepository(str(db_path))
    try:
        service = EventMaintenanceService(repository=repo)
        if dry_run:
            stats = service.storage_stats()
            print("Dry-run mode — no events will be deleted.")
            print("\nCurrent event counts:")
            for cat, count in sorted(stats.items()):
                print(f"  {cat:<15} {count:>6}")
        else:
            if category:
                deleted = service.cleanup_expired(category=category)
                print(f"Deleted {deleted} expired events from category '{category}'")
            else:
                summary = service.enforce_retention()
                total = sum(summary.values())
                print(f"Retention enforcement complete: {total} events deleted")
                if summary:
                    for cat, count in summary.items():
                        print(f"  {cat}: {count} deleted")
        return 0
    finally:
        repo.close()


def metrics_kpi(
    days: int = typer.Option(30, "--days", help="Lookback period in days"),
) -> int:
    """Show KPI metrics from the metrics store."""
    from content_creation.metrics import KPICatalog, SQLiteMetricRepository

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "metrics.db"
    if not db_path.exists():
        print("No metrics store found. Run pipeline actions first to generate metrics.")
        return 0

    repo = SQLiteMetricRepository(str(db_path))
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        catalog = KPICatalog(repo)
        kpis = catalog.calculate_all(start=start, end=end)

        print(f"\n=== KPI Report (last {days} days) ===\n")

        print("Workflow KPIs:")
        for name in [
            "briefs_generated",
            "storyboards_generated",
            "assets_generated",
            "approval_rate",
            "rejection_rate",
        ]:
            kpi = kpis[name]
            print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

        print("\nJob KPIs:")
        for name in [
            "jobs_started",
            "jobs_completed",
            "jobs_failed",
            "job_success_rate",
            "job_retries",
            "average_job_runtime",
        ]:
            kpi = kpis[name]
            print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

        print("\nSystem KPIs:")
        for name in [
            "lock_contentions",
            "zombie_recoveries",
            "stale_lock_expirations",
        ]:
            kpi = kpis[name]
            print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

        print("\nPipeline KPIs:")
        for name in [
            "pipelines_completed",
            "pipelines_failed",
            "pipeline_success_rate",
        ]:
            kpi = kpis[name]
            print(f"  {name:<25} {kpi.value:>8.1f} {kpi.unit}")

        return 0
    finally:
        repo.close()


def metrics_summary(
    days: int = typer.Option(30, "--days", help="Lookback period in days"),
) -> int:
    """Show telemetry summary."""
    from content_creation.events.store import SQLiteEventRepository
    from content_creation.metrics import SQLiteMetricRepository, TelemetryService

    ctx = get_context()
    metrics_db = ctx.base_dir / "data" / "metrics.db"
    events_db = ctx.base_dir / "data" / "events.db"

    metrics_repo = None
    event_repo = None
    try:
        if metrics_db.exists():
            metrics_repo = SQLiteMetricRepository(str(metrics_db))
        if events_db.exists():
            event_repo = SQLiteEventRepository(str(events_db))

        if metrics_repo is None:
            print("No metrics store found.")
            return 0

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        service = TelemetryService(
            metrics_repository=metrics_repo,
            event_repository=event_repo,
        )
        summary = service.full_summary(start=start, end=end)

        print(f"\n=== Telemetry Summary (last {days} days) ===\n")

        sys_summary = cast(SystemSummary, summary["system"])
        print("System:")
        print(f"  Events stored:    {sys_summary.total_events_stored}")
        print(f"  Metrics stored:   {sys_summary.total_metrics_stored}")

        wf = cast(WorkflowSummary, summary["workflow"])
        print("\nWorkflow:")
        print(f"  Briefs generated:     {wf.briefs_generated}")
        print(f"  Storyboards:          {wf.storyboards_generated}")
        print(f"  Assets generated:     {wf.assets_generated}")
        print(f"  Approval rate:        {wf.approval_rate:.1f}%")

        jobs = cast(JobSummary, summary["jobs"])
        print("\nJobs:")
        print(f"  Started:          {jobs.jobs_started}")
        print(f"  Completed:        {jobs.jobs_completed}")
        print(f"  Failed:           {jobs.jobs_failed}")
        print(f"  Success rate:     {jobs.success_rate:.1f}%")
        print(f"  Avg runtime:      {jobs.average_runtime_seconds:.1f}s")

        rel = cast(ReliabilitySummary, summary["reliability"])
        print("\nReliability:")
        print(f"  Lock contentions:     {rel.lock_contentions}")
        print(f"  Zombie recoveries:    {rel.zombie_recoveries}")
        print(f"  Pipeline success:     {rel.pipeline_success_rate:.1f}%")

        return 0
    finally:
        if metrics_repo:
            metrics_repo.close()
        if event_repo:
            event_repo.close()


def metrics_query(
    name: Optional[str] = typer.Option(None, "--name", help="Filter by metric name"),
    type: Optional[str] = typer.Option(
        None,
        "--type",
        help="Filter by metric type (counter, gauge, histogram, timer)",
    ),
    limit: int = typer.Option(20, "--limit", help="Maximum number of results"),
) -> int:
    """Query metrics from the store."""
    from content_creation.metrics import MetricType, SQLiteMetricRepository

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "metrics.db"
    if not db_path.exists():
        print("No metrics store found.")
        return 0

    repo = SQLiteMetricRepository(str(db_path))
    try:
        metric_type = MetricType(type) if type else None
        results = repo.query_metrics(
            metric_name=name,
            metric_type=metric_type,
            limit=limit,
        )

        if not results:
            print("No metrics found.")
            return 0

        print(f"\n{'Timestamp':<20} {'Metric':<30} {'Type':<10} {'Value':>10}")
        print("-" * 70)
        for r in results:
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{ts:<20} {r.metric_name:<30} {r.metric_type.value:<10} {r.value:>10.2f}"
            )

        print(f"\nTotal: {len(results)} metrics")
        return 0
    finally:
        repo.close()


def metrics_cleanup(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview cleanup without deleting"
    ),
) -> int:
    """Run metrics store retention cleanup."""
    from content_creation.metrics import (
        MetricsMaintenanceService,
        SQLiteMetricRepository,
    )

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "metrics.db"
    if not db_path.exists():
        print("No metrics store found.")
        return 0

    repo = SQLiteMetricRepository(str(db_path))
    try:
        service = MetricsMaintenanceService(repository=repo)
        if dry_run:
            stats = service.storage_stats()
            print("Dry-run mode — no metrics will be deleted.")
            print(f"\nCurrent metrics: {stats['total_metrics']}")
            print(f"Retention: {stats['retention_days']} days")
        else:
            result = service.enforce_retention()
            print(f"Deleted {result['deleted']} expired metrics")
        return 0
    finally:
        repo.close()


def metrics_rebuild(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview rebuild without writing"
    ),
) -> int:
    """Rebuild metrics from event store."""
    from content_creation.events.bus import InMemoryEventBus
    from content_creation.events.store import (
        EventReplayEngine,
        SQLiteEventRepository,
    )
    from content_creation.metrics import (
        MetricsSubscriber,
        SQLiteMetricRepository,
    )

    ctx = get_context()
    metrics_db = ctx.base_dir / "data" / "metrics.db"
    events_db = ctx.base_dir / "data" / "events.db"

    if not events_db.exists():
        print("No event store found. Cannot rebuild metrics.")
        return 0

    event_repo = SQLiteEventRepository(str(events_db))
    metric_repo = SQLiteMetricRepository(str(metrics_db))
    try:
        if dry_run:
            event_count = event_repo.count_events()
            metric_count = metric_repo.count_metrics()
            print("Dry-run mode — no metrics will be written.")
            print(f"Events in store: {event_count}")
            print(f"Current metrics: {metric_count}")
            print(f"\nReplay would process {event_count} events.")
        else:
            deleted = metric_repo.delete_expired(
                datetime.now(timezone.utc) + timedelta(days=365)
            )
            print(f"Cleared {deleted} existing metrics.")

            replay_bus = InMemoryEventBus()
            MetricsSubscriber(repository=metric_repo, bus=replay_bus)
            engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
            replayed = engine.replay_all()

            print(f"Replayed {len(replayed)} events.")
            print(f"Metrics store now has {metric_repo.count_metrics()} metrics.")
        return 0
    finally:
        event_repo.close()
        metric_repo.close()


def audit_query(
    limit: int = typer.Option(20, "--limit", help="Maximum number of results"),
    entity_type: Optional[str] = typer.Option(
        None, "--entity-type", help="Filter by entity type"
    ),
    action: Optional[str] = typer.Option(
        None, "--action", help="Filter by action type"
    ),
    actor_id: Optional[str] = typer.Option(
        None, "--actor-id", help="Filter by actor ID"
    ),
    event_type: Optional[str] = typer.Option(
        None, "--event-type", help="Filter by event type"
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        help="Filter by severity (INFO, WARNING, ERROR, CRITICAL)",
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        help="Filter by source (workflow, review, job, lock, recovery, pipeline, system)",
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Start date (YYYY-MM-DD)"
    ),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
) -> int:
    """Query audit trail records."""
    from content_creation.audit import AuditQueryService, SQLiteAuditRepository
    from content_creation.audit.models import AuditSeverity, AuditSource

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "audit.db"
    if not db_path.exists():
        print(
            "No audit store found. Run pipeline actions first to generate audit records."
        )
        return 0

    repo = SQLiteAuditRepository(str(db_path))
    try:
        service = AuditQueryService(repository=repo)

        start_dt = (
            datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if start
            else None
        )
        end_dt = (
            datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if end
            else None
        )

        sev = AuditSeverity(severity) if severity else None
        src = AuditSource(source) if source else None

        query_term = action or event_type
        records: list[AuditRecord]
        if query_term:
            records = service.search_records(query=query_term, limit=1000)
        else:
            records = service.recent_records(page=1, page_size=1000).records

        if entity_type:
            records = [r for r in records if r.entity_type == entity_type]
        if actor_id:
            records = [r for r in records if r.actor_id == actor_id]
        if sev:
            records = [r for r in records if r.severity == sev]
        if src:
            records = [r for r in records if r.source == src]
        if start_dt:
            records = [r for r in records if r.timestamp >= start_dt]
        if end_dt:
            records = [r for r in records if r.timestamp <= end_dt]

        records = records[:limit]
        if not records:
            print("No audit records found.")
            return 0

        print(
            f"\n{'Timestamp':<20} {'Action':<20} {'Entity':<20} {'Actor':<15} {'Severity':<10}"
        )
        print("-" * 85)
        for r in records:
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ent = f"{r.entity_type}:{r.entity_id[:12]}" if r.entity_type else "-"
            print(
                f"{ts:<20} {r.action_type:<20} {ent:<20} {r.actor_id[:15]:<15} {r.severity.value:<10}"
            )

        print(f"\nTotal: {len(records)} audit records")
        return 0
    finally:
        repo.close()


def audit_entity(
    entity_type: str = typer.Option(
        ..., "--entity-type", help="Entity type (brief, job, asset, etc.)"
    ),
    entity_id: Optional[str] = typer.Option(
        None, "--entity-id", help="Specific entity ID"
    ),
    limit: int = typer.Option(20, "--limit", help="Maximum number of results"),
) -> int:
    """Search audit trail by entity."""
    from content_creation.audit import AuditQueryService, SQLiteAuditRepository

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "audit.db"
    if not db_path.exists():
        print("No audit store found.")
        return 0

    repo = SQLiteAuditRepository(str(db_path))
    try:
        service = AuditQueryService(repository=repo)
        records = service.search_by_entity(entity_type, entity_id)
        records = records[:limit]

        if not records:
            print(
                f"No audit records found for {entity_type}"
                + (f":{entity_id}" if entity_id else "")
            )
            return 0

        print(
            f"\nAudit Trail for {entity_type}"
            + (f":{entity_id}" if entity_id else "")
            + ":"
        )
        print(f"{'Timestamp':<20} {'Action':<20} {'Actor':<15} {'Severity':<10}")
        print("-" * 65)
        for r in records:
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{ts:<20} {r.action_type:<20} {r.actor_id[:15]:<15} {r.severity.value:<10}"
            )

        print(f"\nTotal: {len(records)} records")
        return 0
    finally:
        repo.close()


def audit_actor(
    actor_id: str = typer.Option(
        ..., "--actor-id", help="Actor ID to search for"
    ),
    limit: int = typer.Option(20, "--limit", help="Maximum number of results"),
) -> int:
    """Search audit trail by actor."""
    from content_creation.audit import AuditQueryService, SQLiteAuditRepository

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "audit.db"
    if not db_path.exists():
        print("No audit store found.")
        return 0

    repo = SQLiteAuditRepository(str(db_path))
    try:
        service = AuditQueryService(repository=repo)
        records = service.search_by_actor(actor_id)
        records = records[:limit]

        if not records:
            print(f"No audit records found for actor '{actor_id}'")
            return 0

        print(f"\nAudit Trail for Actor: {actor_id}")
        print(f"{'Timestamp':<20} {'Action':<20} {'Entity':<20} {'Severity':<10}")
        print("-" * 70)
        for r in records:
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ent = f"{r.entity_type}:{r.entity_id[:12]}" if r.entity_type else "-"
            print(
                f"{ts:<20} {r.action_type:<20} {ent:<20} {r.severity.value:<10}"
            )

        print(f"\nTotal: {len(records)} records")
        return 0
    finally:
        repo.close()


def audit_report(
    type: str = typer.Option(
        ...,
        "--type",
        help="Report type (operator, decision, job, incident, summary)",
    ),
) -> int:
    """Generate compliance reports from audit trail."""
    from content_creation.audit import (
        ComplianceReportService,
        SQLiteAuditRepository,
    )

    ctx = get_context()
    db_path = ctx.base_dir / "data" / "audit.db"
    if not db_path.exists():
        print("No audit store found.")
        return 0

    repo = SQLiteAuditRepository(str(db_path))
    try:
        service = ComplianceReportService(repository=repo)

        if type == "summary":
            s = service.compliance_summary()
            critical_count = s.severity_breakdown.get("CRITICAL", 0)
            print("\n=== Compliance Summary ===")
            print(f"  Total audit records:     {s.total_audit_records}")
            print(f"  Active actors:           {s.actors_active}")
            print(f"  Unique entities:         {s.unique_entities}")
            print(f"  Critical events:         {critical_count}")
            print(
                f"  Date range:              {s.date_range_start} to {s.date_range_end}"
            )

        elif type == "operator":
            reports = service.operator_activity_report()
            if not reports:
                print("No operator activity found.")
                return 0
            print("\n=== Operator Activity Report ===")
            print(f"{'Actor ID':<15} {'Actions':>8} {'First Seen':<20} {'Last Seen':<20}")
            print("-" * 65)
            for rep in reports:
                first = rep.first_action or "-"
                last = rep.last_action or "-"
                print(
                    f"{rep.actor_id[:15]:<15} {rep.total_actions:>8} {first:<20} {last:<20}"
                )

        elif type == "decision":
            d_report = service.workflow_decision_report()
            print("\n=== Workflow Decision Report ===")
            print(f"  Total decisions:    {d_report.total_decisions}")
            print(f"  Approvals:          {d_report.approvals}")
            print(f"  Rejections:         {d_report.rejections}")
            print(f"  Approval rate:      {d_report.approval_rate:.1f}%")

        elif type == "job":
            j_report = service.job_execution_report()
            print("\n=== Job Execution Report ===")
            print(f"  Total jobs:         {j_report.total_jobs}")
            print(f"  Completed:          {j_report.completed}")
            print(f"  Failed:             {j_report.failed}")
            print(f"  Success rate:       {j_report.success_rate:.1f}%")

        elif type == "incident":
            timeline = service.incident_timeline()
            print("\n=== Incident Timeline ===")
            print(f"  Critical events:    {timeline.total_critical}")
            print(f"  Warning events:     {timeline.total_warning}")
            if timeline.events:
                print(
                    f"\n{'Timestamp':<20} {'Action':<20} {'Severity':<10} {'Entity':<20}"
                )
                print("-" * 70)
                for ev in timeline.events[:20]:
                    ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    ent = (
                        f"{ev.entity_type}:{ev.entity_id[:12]}"
                        if ev.entity_type
                        else "-"
                    )
                    print(
                        f"{ts:<20} {ev.action_type:<20} {ev.severity.value:<10} {ent:<20}"
                    )

        return 0
    finally:
        repo.close()


def audit_rebuild(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview rebuild without writing"
    ),
) -> int:
    """Rebuild audit trail from event store."""
    from content_creation.audit import AuditSubscriber, SQLiteAuditRepository
    from content_creation.events.bus import InMemoryEventBus
    from content_creation.events.store import (
        EventReplayEngine,
        SQLiteEventRepository,
    )

    ctx = get_context()
    events_db = ctx.base_dir / "data" / "events.db"
    audit_db = ctx.base_dir / "data" / "audit.db"

    if not events_db.exists():
        print("No event store found. Cannot rebuild audit trail.")
        return 0

    event_repo = SQLiteEventRepository(str(events_db))
    audit_repo = SQLiteAuditRepository(str(audit_db))
    try:
        if dry_run:
            event_count = event_repo.count_events()
            audit_count = audit_repo.count_records()
            print("Dry-run mode — no audit records will be written.")
            print(f"Events in store: {event_count}")
            print(f"Current audit records: {audit_count}")
            print(f"\nReplay would process {event_count} events.")
        else:
            deleted = audit_repo.delete_expired(
                datetime.now(timezone.utc) + timedelta(days=365)
            )
            print(f"Cleared {deleted} existing audit records.")

            replay_bus = InMemoryEventBus()
            AuditSubscriber(repository=audit_repo, bus=replay_bus)
            engine = EventReplayEngine(repository=event_repo, bus=replay_bus)
            replayed = engine.replay_all()

            print(f"Replayed {len(replayed)} events.")
            print(f"Audit store now has {audit_repo.count_records()} records.")
        return 0
    finally:
        event_repo.close()
        audit_repo.close()


def register_observability_commands(app: typer.Typer) -> None:
    """Register observability subcommands to the Typer application."""
    app.command("event-timeline", help="View recent events from the event store")(
        event_timeline
    )
    app.command("event-stats", help="Show event store statistics")(event_stats)
    app.command("event-store", help="Show event store statistics summary")(
        event_store
    )
    app.command("event-tail", help="Tail recent events from the event store")(
        event_tail
    )
    app.command("event-replay", help="Replay events from the event store")(
        event_replay
    )
    app.command("event-cleanup", help="Run event store retention cleanup")(
        event_cleanup
    )
    app.command("metrics-kpi", help="Show KPI metrics from the metrics store")(
        metrics_kpi
    )
    app.command("metrics-summary", help="Show telemetry summary")(metrics_summary)
    app.command("metrics-query", help="Query metrics from the store")(metrics_query)
    app.command(
        "metrics-cleanup", help="Run metrics store retention cleanup"
    )(metrics_cleanup)
    app.command("metrics-rebuild", help="Rebuild metrics from event store")(
        metrics_rebuild
    )
    app.command("audit-query", help="Query audit trail records")(audit_query)
    app.command("audit-entity", help="Search audit trail by entity")(audit_entity)
    app.command("audit-actor", help="Search audit trail by actor")(audit_actor)
    app.command(
        "audit-report", help="Generate compliance reports from audit trail"
    )(audit_report)
    app.command("audit-rebuild", help="Rebuild audit trail from event store")(
        audit_rebuild
    )
