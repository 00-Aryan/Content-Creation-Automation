# Phase 11.8.3 — Event Subscriber Audit & Notification Integration

**Date:** 2026-06-04  
**Status:** APPROVED  
**Author:** Principal Distributed Systems & Workflow Infrastructure Architect

---

## 1. Findings & Coupling Summary

Currently, several components inside the Content Ingestion & Synthesis Factory interact via direct function calls, synchronous coupling, or database polling. Resolving these dependencies through event-driven subscribers will improve latency, resilience, and horizontal scalability.

### Key Discoveries:
1. **Synchronous Chain in Workflow Executor**:
   - `WorkflowActionExecutor` directly invokes generator services and state transitions. When an operation succeeds, it logs results to stdout or file, and returns results to the caller synchronously.
   - If UI dashboards or audit trails need to react to these outcomes, they must parse return values or poll the repository, rather than listening to an event stream.
2. **Polling Database for Queue & Heartbeats**:
   - `WorkerDaemon` loops continuously using time-based sleeps to query the job database (`list_jobs` with `status='QUEUED'`).
   - `RecoverySupervisor` queries both `jobs` and `locks` tables in every cycle to detect heartbeat timeouts.
   - Decoupling this through event subscribers would allow the worker or supervisor to be notified instantly on state updates (e.g., when a job is created or a lock is acquired).
3. **Notification Coupling**:
   - Direct execution in services leads to notifications being handled manually.
   - Currently, there is no system-wide mechanism to capture alerts, warnings, or info logs for human operators, leaving the Streamlit UI to query raw table logs to show system health.

---

## 2. Event → Consumer Inventory

Based on Phase 11.8.2 event emissions, the table below maps each canonical event to its target consumers and describes the logic that each subscriber executes.

| Event Type | Producer | Interested Consumers | Subscriber Action |
| :--- | :--- | :--- | :--- |
| `brief_approved` | `WorkflowActionExecutor` | `JobSystemSubscriber`, `NotificationSubscriber` | Enqueues next phase job (e.g. `GENERATE_CI`); creates operator notification. |
| `brief_rejected` | `WorkflowActionExecutor` | `NotificationSubscriber`, `AnalyticsSubscriber` | Records rejection reason; alerts planning operator for remediation. |
| `storyboard_approved` | `WorkflowActionExecutor` | `JobSystemSubscriber`, `NotificationSubscriber` | Enqueues `GENERATE_ASSETS` background job; creates review alert. |
| `storyboard_rejected` | `WorkflowActionExecutor` | `NotificationSubscriber` | Logs audit warning; notifies storyboard author. |
| `asset_approved` | `WorkflowActionExecutor` | `JobSystemSubscriber`, `NotificationSubscriber` | Enqueues `BUILD_MANIFEST` background job; creates success banner. |
| `asset_rejected` | `WorkflowActionExecutor` | `NotificationSubscriber` | Alerts asset generator worker. |
| `job_created` | `QueueEngine` | `NotificationSubscriber` | Logs info audit trail entry for tracking. |
| `job_queued` | `QueueEngine` | `WorkerDaemon` | Triggers immediate worker poll instead of waiting for interval. |
| `job_started` | `WorkerDaemon` | `NotificationSubscriber` | Sets status of associated topic to "RUNNING" or updates operational UI. |
| `job_completed` | `WorkerDaemon` | `NotificationSubscriber`, `MetricsSubscriber` | Records execution time metric; creates success banner for operator. |
| `job_failed` | `WorkerDaemon` | `NotificationSubscriber`, `AlertingSubscriber` | Creates critical warning alert; raises Slack/Email hook notification. |
| `job_cancelled` | `QueueEngine` | `NotificationSubscriber` | Clears local locks; notifies operator. |
| `job_retried` | `QueueEngine` | `NotificationSubscriber` | Records warning notification with remaining attempt details. |
| `lock_acquired` | `LockManager` | `AuditTrailSubscriber` | Records lock ownership for deadlock analysis. |
| `lock_released` | `LockManager` | `AuditTrailSubscriber` | Frees tracking locks. |
| `lock_expired` | `LockManager` | `NotificationSubscriber` | Logs critical resource availability error. |
| `zombie_job_recovered`| `RecoverySupervisor` | `NotificationSubscriber`, `MetricsSubscriber` | Logs warning; increments recovery counter. |
| `stale_lock_expired` | `RecoverySupervisor` | `NotificationSubscriber` | Publishes warning; alerts operations of potential worker death. |
| `pipeline_started` | `WorkflowActionExecutor` | `NotificationSubscriber` | Posts info banner indicating weekly posting calendar pipeline run. |
| `pipeline_completed` | `WorkflowActionExecutor` | `NotificationSubscriber` | Posts overall calendar success banner. |
| `pipeline_failed` | `WorkflowActionExecutor` | `NotificationSubscriber`, `AlertingSubscriber` | Posts critical failure alert. |

---

## 3. Current Coupling Inventory

The table below catalogs existing direct dependencies that can be refactored into event-driven patterns.

| Dependent Component | Target Dependency | Coupling Type | Refactoring Strategy |
| :--- | :--- | :--- | :--- |
| `WorkerDaemon` | `QueueEngine` | Polling for claimable jobs | Introduce event-driven wakeup. When `job_queued` is emitted, notify worker thread immediately. |
| `WorkflowActionExecutor` | Generator Services | Direct synchronous execution | Allow executor to spawn background jobs via `QueueEngine` instead of calling services directly. |
| `RecoverySupervisor` | DB locks / jobs | Time-based database sweeps | Supplement periodic sweeps with real-time lock expiry alerts via Event Bus listeners. |
| Streamlit / CLI UI | SQLite Jobs/Locks | Periodic SQL queries | Stream events directly to UI using SSE or WebSockets connected to an in-memory event bus. |

---

## 4. Recommended Subscriber Boundaries

To preserve strict domain boundaries and avoid circular dependencies, the following constraints are recommended:
1. **Core Domains Emit Only**: The queue engine, worker daemons, and lock managers should remain completely ignorant of how notifications are formatted, stored, or sent. They only publish immutable `WorkflowEvent` objects.
2. **Dedicated Notification Package**: Implement a standalone `notifications` subsystem that manages the notification lifecycle (UNREAD, READ, ARCHIVED) and its SQLite schema.
3. **Pure Subscribers**: Subscribers should act as simple translation layers:
   - Listen to `WorkflowEvent`
   - Map event properties to a `Notification` object
   - Persist it to the `NotificationRepository`
   - Never directly call business logic, workers, or change domain states.

---

## 5. Risks & Mitigations

1. **High Write Load on SQLite**:
   - *Risk*: Rapidly inserting event logs and notification rows into SQLite under concurrent worker sweeps could lead to database lock timeouts (`database is locked` / `SQLITE_BUSY`).
   - *Mitigation*: Run SQLite in WAL (Write-Ahead Logging) mode, execute notification writes in isolated immediate transactions, and configure a busy timeout of 5000ms.
2. **Subscriber Failures**:
   - *Risk*: A bad subscriber callback throwing an error could crash the event bus, aborting delivery to other subscribers and failing the publisher (e.g. crashing a worker daemon mid-job).
   - *Mitigation*: Run subscribers within a try-except block, measure their duration, wrap exceptions in a `SubscriberExecutionResult`, and log errors without raising them.
3. **Database Growth**:
   - *Risk*: As thousands of events fire, the `notifications` table will grow indefinitely, slowing down unread lookups.
   - *Mitigation*: Expose a `cleanup_expired_notifications` capability inside `NotificationRepository` to periodically prune old read or archived records.

---

## 6. Architectural Recommendations

1. **Design EventFilter and Subscription Models**: Build immutable filters so subscribers can declaratively state their criteria (e.g., match specific categories or wildcards like `job.*`).
2. **Implement SQLite WAL by Default**: Configure all sqlite connections in the repository layer to use WAL mode.
3. **Add Database Indexing**: Ensure indexes are created on `status` (unread lookups) and `timestamp` (descending order retrieval) for the `notifications` table.
