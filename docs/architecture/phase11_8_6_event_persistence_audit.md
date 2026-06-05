# Phase 11.8.6 — Event Persistence & Replay Audit

## Current Event Lifecycle

```
Producers → InMemoryEventBus → Subscribers → Notifications → SSE → UI
                                  ↓
                          EventPersistenceSubscriber
                                  ↓
                          SQLiteEventRepository (WAL mode)
                                  ↓
                          EventStore (events table)
```

Events are published to `InMemoryEventBus` and dispatched synchronously to registered subscribers. The `EventPersistenceSubscriber` captures every event and persists it to the SQLite-backed EventStore, creating a durable historical record.

## Event Loss Scenarios

| Scenario | Impact | Recovery |
|---|---|---|
| Process crash | In-memory events lost | EventStore survives — replay from store |
| Subscriber failure | Event delivered to other subscribers, but failed subscriber's side effects lost | Re-publish from source |
| SSE client disconnect | Client misses events during disconnect | Last-Event-ID replay from EventStore |
| Bus overload | `put_nowait` on full queue drops events silently | None (mitigated by synchronous dispatch) |
| Dual-process restart | New process has empty bus, no history | EventStore provides full history |

## Event Volume Estimates

Based on current pipeline:
- Workflow events: ~5-10 per pipeline run (brief, CI, storyboard, asset, manifest, approvals)
- Job events: ~3-5 per job (created, queued, started, completed)
- Lock events: ~2-4 per topic (acquire, release)
- Recovery events: ~1-2 per sweep
- **Estimated steady state:** 50-200 events/day during active operation
- **Peak load:** ~500 events/day during full pipeline execution

## Storage Growth Projections

### Per-Event Storage
- EventRecord overhead: ~200 bytes (UUIDs, timestamps, category strings)
- Average payload: ~500 bytes (JSON-serialized event data)
- **Average event size:** ~700 bytes
- SQLite row overhead: ~100 bytes
- **Total per event:** ~800 bytes

### Growth Rates
| Period | Events | Storage | Cumulative |
|---|---|---|---|
| Daily (steady state) | 100-200 | 80-160 KB | 80-160 KB |
| Weekly | 700-1,400 | 560 KB-1.1 MB | 560 KB-1.1 MB |
| Monthly | 3,000-6,000 | 2.4-4.8 MB | 2.4-4.8 MB |
| 90 days (workflow/job) | 9,000-18,000 | 7.2-14.4 MB | 7.2-14.4 MB |
| 1 year (pipeline) | 36,500-73,000 | 29-58 MB | 29-58 MB |

### Index Overhead
- 4 indexes (timestamp, category, entity, correlation): ~30% additional storage
- **Total with indexes:** ~38-75 MB at 1-year steady state

### Worst-Case Scenario
- Full pipeline execution: 500 events/day
- 1-year accumulation: ~182,500 events
- Storage: ~146 MB (with indexes ~190 MB)

**Verdict:** Storage is negligible for the expected workload. SQLite handles this scale effortlessly.

## Retention Requirements

| Category | Retention | Rationale |
|---|---|---|
| Workflow | 90 days | Audit trail for content decisions |
| Review | 90 days | Approval/rejection history |
| Job | 90 days | Operational history |
| Lock | 30 days | Transient coordination |
| Recovery | 90 days | Incident investigation |
| Pipeline | 365 days | Compliance and reporting |

## Cleanup Strategy

### Automatic Retention Enforcement
- `EventMaintenanceService.enforce_retention()` deletes events exceeding per-category retention
- Designed for scheduler integration (cron, APScheduler, or manual invocation)
- Runs atomically: each category cleanup is a separate transaction

### Manual Cleanup
- CLI command: `event-cleanup` with optional `--category` and `--dry-run`
- Dry-run mode previews what would be deleted without modifying data

### Archive Strategy (Future)
- Export events to Parquet/JSON before deletion
- Compressed archives for long-term compliance storage
- Not implemented in current phase — retention alone suffices

## Query Frequency Estimates

| Query | Frequency | Use Case |
|---|---|---|
| `list_events` | High | Timeline dashboard, recent events |
| `list_by_entity` | High | Entity history, workflow tracking |
| `list_by_correlation` | Medium | Operation tracing, debugging |
| `list_by_time_range` | Medium | Date-range queries, analytics |
| `list_after_event` | Medium (SSE recovery) | Client reconnection replay |
| `count_events` | Low | Statistics, monitoring |
| `delete_expired` | Low (scheduled) | Retention enforcement |

### Index Usage
- `idx_events_timestamp`: Supports time-range queries and ordering
- `idx_events_category`: Supports category filtering
- `idx_events_entity`: Supports entity history queries (composite index)
- `idx_events_correlation`: Supports correlation-based tracing

## Replay Candidates

1. **SSE recovery** — Client reconnects with `Last-Event-ID`, server replays missed events
2. **Notification recovery** — Operator reconnects, system restores missed notification state
3. **Audit replay** — Historical event timeline for debugging and compliance
4. **Pipeline reconstruction** — Replay events to reconstruct pipeline state

## Audit Requirements

- Every event must be immutably stored with full payload
- Events must be queryable by entity, correlation, category, and time range
- Event history must survive process restarts
- Storage must be append-only (no updates/deletes except retention cleanup)

## Architecture Validation

### Required Architecture (Implemented)
```
Workflow → EventBus → EventPersistenceSubscriber → EventRepository → SQLiteEventRepository
```

### Replay Path (Implemented)
```
EventStore → ReplayEngine → EventBus → Subscribers
```

### Strictly Enforced Constraints
- ✅ UI → Repository direct access: **Prohibited** (UI uses TimelineService)
- ✅ Worker → EventStore direct writes: **Prohibited** (writes via EventBus only)
- ✅ Executor → EventStore direct writes: **Prohibited** (writes via EventBus only)
- ✅ Replay bypassing EventBus: **Prohibited** (replay goes through EventBus)
- ✅ Subscriber mutating stored events: **Prohibited** (EventRecord is frozen)
