# Phase 11.8.7 — Metrics & Telemetry Audit

## Current State

The platform generates rich event history through the EventBus, persisted by EventPersistenceSubscriber to the EventStore. However, no dedicated telemetry subsystem exists to derive operational intelligence from this data.

### Existing Metrics-Adjacent Code
- `QueueEngine.get_queue_metrics()` — in-memory job queue counts
- `EventMaintenanceService.storage_stats()` — per-category event counts
- `PostAnalytics` / `PerformanceSnapshot` — external platform metrics (views, reach)

None of these provide systematic operational KPIs derived from the event stream.

## Metric Candidates by Event Category

### Workflow Events
| Event | Metric | Type |
|---|---|---|
| brief_generated | briefs_generated_total | counter |
| ci_generated | ci_generated_total | counter |
| storyboard_generated | storyboards_generated_total | counter |
| asset_generated | assets_generated_total | counter |
| manifest_built | manifests_built_total | counter |

### Review Events
| Event | Metric | Type |
|---|---|---|
| brief_approved | briefs_approved_total | counter |
| brief_rejected | briefs_rejected_total | counter |
| storyboard_approved | storyboards_approved_total | counter |
| storyboard_rejected | storyboards_rejected_total | counter |
| asset_approved | assets_approved_total | counter |
| asset_rejected | assets_rejected_total | counter |

### Job Events
| Event | Metric | Type |
|---|---|---|
| job_created | jobs_created_total | counter |
| job_queued | jobs_queued_total | counter |
| job_started | jobs_started_total | counter |
| job_completed | jobs_completed_total | counter |
| job_completed (with duration) | job_duration_seconds | timer |
| job_failed | jobs_failed_total | counter |
| job_cancelled | jobs_cancelled_total | counter |
| job_retried | jobs_retried_total | counter |

### Lock Events
| Event | Metric | Type |
|---|---|---|
| lock_acquired | locks_acquired_total | counter |
| lock_released | locks_released_total | counter |
| lock_expired | locks_expired_total | counter |

### Recovery Events
| Event | Metric | Type |
|---|---|---|
| zombie_job_recovered | zombie_jobs_recovered_total | counter |
| stale_lock_expired | stale_locks_expired_total | counter |

### Pipeline Events
| Event | Metric | Type |
|---|---|---|
| pipeline_started | pipelines_started_total | counter |
| pipeline_completed | pipelines_completed_total | counter |
| pipeline_completed (with duration) | pipeline_duration_seconds | timer |
| pipeline_failed | pipelines_failed_total | counter |

## KPI Inventory

### Workflow KPIs
| KPI | Formula | Unit |
|---|---|---|
| briefs_generated | COUNT(briefs_generated_total) | count |
| storyboards_generated | COUNT(storyboards_generated_total) | count |
| assets_generated | COUNT(assets_generated_total) | count |
| approval_rate | approved / (approved + rejected) * 100 | % |
| rejection_rate | 100 - approval_rate | % |

### Job KPIs
| KPI | Formula | Unit |
|---|---|---|
| jobs_started | COUNT(jobs_started_total) | count |
| jobs_completed | COUNT(jobs_completed_total) | count |
| jobs_failed | COUNT(jobs_failed_total) | count |
| job_success_rate | completed / (completed + failed) * 100 | % |
| job_retries | COUNT(jobs_retried_total) | count |
| average_job_runtime | AVG(job_duration_seconds) | seconds |

### System KPIs
| KPI | Formula | Unit |
|---|---|---|
| lock_contentions | COUNT(locks_expired_total) | count |
| zombie_recoveries | COUNT(zombie_jobs_recovered_total) | count |
| stale_lock_expirations | COUNT(stale_locks_expired_total) | count |

### Pipeline KPIs
| KPI | Formula | Unit |
|---|---|---|
| pipelines_completed | COUNT(pipelines_completed_total) | count |
| pipelines_failed | COUNT(pipelines_failed_total) | count |
| pipeline_success_rate | completed / (completed + failed) * 100 | % |

## Aggregation Requirements

### Time Buckets
- Hourly: 1-hour windows for intraday analysis
- Daily: 24-hour windows for trend analysis
- Weekly: 7-day windows for operational reviews
- Monthly: 30-day windows for strategic reporting

### Operations
- Sum: total counts per period
- Average: mean values per period
- Min/Max: range analysis
- Count: event frequency

### Advanced Analytics
- Rolling averages (7-day, 30-day)
- Growth rates (period-over-period)
- Moving windows for trend detection

## Retention Requirements

| Data | Retention | Rationale |
|---|---|---|
| Raw metrics | 90 days | Matches event retention |
| Aggregated KPIs | 365 days | Strategic reporting |
| Telemetry summaries | Real-time | Dashboard consumption |

## Storage Projections

### Per-Metric Storage
- MetricRecord overhead: ~150 bytes
- Dimensions JSON: ~100 bytes average
- **Total per metric:** ~250 bytes

### Growth Rates
| Period | Metrics | Storage |
|---|---|---|
| Daily | 100-200 | 25-50 KB |
| Monthly | 3,000-6,000 | 750 KB-1.5 MB |
| 90 days | 9,000-18,000 | 2.25-4.5 MB |

**Verdict:** Storage is negligible.

## Architecture Validation

### Required Path (Implemented)
```
EventBus → MetricsSubscriber → MetricRepository → SQLiteMetricRepository
```

### Forbidden Patterns (Enforced)
- ❌ Worker → MetricRepository direct writes
- ❌ Executor → MetricRepository direct writes
- ✅ All metrics originate from events via MetricsSubscriber

### Replay Path (Implemented)
```
EventStore → ReplayEngine → EventBus → MetricsSubscriber → MetricRepository
```

## CLI Commands

| Command | Description |
|---|---|
| `metrics-kpi` | Show KPI metrics for a lookback period |
| `metrics-summary` | Show full telemetry summary |
| `metrics-query` | Query metrics with filtering |
| `metrics-cleanup` | Run retention cleanup |
| `metrics-rebuild` | Rebuild metrics from event store |
