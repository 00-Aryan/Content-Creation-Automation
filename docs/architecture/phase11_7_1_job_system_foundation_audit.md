# Phase 11.7.1 — Job System Foundation Audit

**Date:** 2026-06-04  
**Status:** COMPLETE  
**Author:** Principal Distributed Systems Architect (Content Ingestion & Synthesis Factory)

---

## 1. Long-Running Action Inventory

The table below catalogs every mutating operator action in the Content Ingestion & Synthesis Factory that is candidate for transition to asynchronous background job execution.

| Action ID | Action Name | Est. Exec Time | Inputs | Outputs | Side Effects | Retry Safety / Idempotency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A01: `collect`** | Collect Topics | 5s – 30s | Source filter | Stage files, count | Appends new topics to staging repository | **Safe / Idempotent**: Uses unique IDs derived from feed entries; duplicate runs overwrite with same data. |
| **A02: `score_topics`** | Score Topics | 2s – 10s | Limit | Scored topic records | Transitions Topic status to `SCORED` or `REJECTED` | **Safe / Idempotent**: Re-evaluating scored topics overwrites scores deterministically. |
| **A03: `generate_briefs`**| Generate Briefs | 10s – 60s | Top-N, API Key | Brief JSON files | Saves briefs to storage, updates workflow stage | **Safe / Idempotent**: Overwrites existing files if forced, or skips if already generated. |
| **A04: `generate_ci`** | Generate Content Intelligence | 10s – 60s | Top-N, API Key | CI JSON files | Saves CI analysis, updates workflow stage | **Safe / Idempotent**: Overwrites existing CI files. |
| **A05: `generate_storyboards`**| Generate Storyboards | 15s – 90s | Top-N, API Key | Storyboard JSON | Saves Storyboard files, updates workflow stage | **Safe / Idempotent**: Overwrites storyboard files. |
| **A06: `generate_assets`**| Generate Assets | 20s – 120s | Top-N, API Key | Assets suite (JSON) | Saves scripts, carousels, newsletters, thumbnails | **Safe / Idempotent**: Overwrites asset files. |
| **A17: `build_manifest`**| Build Manifest | 1s – 3s | Topic ID | Manifest JSON | Generates compiled topic manifests | **Safe / Idempotent**: Rebuilds manifest deterministically from asset states. |
| **A19: `plan_week`** | Plan Week | 1s – 5s | Week start date | Weekly calendar JSON| Writes planned post mappings | **Safe / Idempotent**: Overwrites weekly calendar structure. |
| **A20: `dry_run`** | Dry Run | 2s – 10s | Week start date | Validation report | Saves dryrun reports | **Safe / Idempotent**: Overwrites validation reports. |
| **A23: `run_pipeline`** | Run Pipeline | 60s – 300s | Top-N, source, auto-approve, API key | Logs & stages summary| Runs stages 1-8 sequentially | **Partially Safe / Non-Idempotent**: Safe if individual sub-stages are idempotent, but runs multi-step mutations sequentially. |

---

## 2. Async Opportunity Matrix

This matrix evaluates current execution bottlenecks and user waiting points, identifying opportunities for background execution.

| Action ID | Current Flow | User UX Impact | Async Benefit | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **A01: `collect`** | UI/CLI blocking | High (blocks page load) | High (run in background, notify on finish) | **Convert to Async Job** |
| **A02: `score_topics`** | UI/CLI blocking | Medium (quick computation) | Low | **Keep Synchronous** (or run as initial step of pipeline job) |
| **A03: `generate_briefs`**| UI/CLI blocking | High (wait for Gemini LLM) | High (free up UI thread) | **Convert to Async Job** |
| **A04: `generate_ci`** | UI/CLI blocking | High (Gemini latency) | High | **Convert to Async Job** |
| **A05: `generate_storyboards`**| UI/CLI blocking | High (Gemini latency) | High | **Convert to Async Job** |
| **A06: `generate_assets`**| UI/CLI blocking | High (Multi-LLM synthesis) | High | **Convert to Async Job** |
| **A08–A15: Reviews** | UI blocking | Low (instant file update) | N/A | **Keep Synchronous** (requires instant human feedback) |
| **A19: `plan_week`** | CLI blocking | Low | Low | **Keep Synchronous** |
| **A20: `dry_run`** | CLI blocking | Low | Low | **Keep Synchronous** |
| **A23: `run_pipeline`** | UI/CLI blocking | High (runs up to 5 mins) | Extremely High (run asynchronously in queue) | **Convert to Async Job** |

---

## 3. Concurrency Risk Assessment & Locking

Introducing background execution introduces several critical race conditions:

### Risk 1: Double Generation on Same Topic
* **Scenario**: A user double-clicks the "Generate Storyboards" button in the UI, or a background worker and CLI operator run storyboard generation on the same `topic_id` concurrently.
* **Impact**: Duplicate LLM API calls, rate limit exceptions, and file-writing conflicts (corruption or partial writes).
* **Lock Type Required**: **Topic Lock** (Exclusive, scoped to a single `topic_id`).

### Risk 2: Manifest Generation during Review Mutations
* **Scenario**: A background job is running `build_all_manifests` while a human operator is applying asset decisions (`approve_asset` / `reject_asset`) on the UI.
* **Impact**: The manifest is rebuilt with half-applied review states, creating stale or corrupted pipeline descriptors.
* **Lock Type Required**: **Manifest Lock** (Shared-Exclusive lock on `topic_id` manifest).

### Risk 3: Weekly Planning Conflict
* **Scenario**: Multiple weekly planner jobs are scheduled or triggered for the same `week_start` calendar date.
* **Impact**: Overlapping post schedules, duplicate calendars, and dry-run check failures.
* **Lock Type Required**: **Calendar Lock** (Exclusive lock scoped to a specific `week_start` date).

---

## 4. Failure Recovery Requirements

Background jobs must fail gracefully and recover cleanly without corrupting the content factory status:

1. **Retryable Failures (Transient Errors)**:
   * **Examples**: LLM Provider Rate Limits (HTTP 429), temporary Gemini timeout (HTTP 503), storage network latency.
   * **Recovery Policy**: Exponential backoff retry (e.g. base delay 5s, backoff factor 2, max 3 retries).
2. **Non-Retryable Failures (Permanent Errors)**:
   * **Examples**: Invalid Gemini API key, prompt template syntax corruption, validation failures, schema drift.
   * **Recovery Policy**: Halted state transition, job state marked as `FAILED`, write detailed error summary to the operational logs.
3. **Resume / Resume-On-Boot Points**:
   * If the worker crashes or restarts mid-execution, the pipeline state manager must read incomplete workflow stages and resume from the first uncompleted stage (e.g., if CI is approved butStoryboard is missing, resume withStoryboard generation).
4. **Cancellation Requirements**:
   * Jobs marked `CANCELLED` must abort immediately between stages (non-destructive interruption) and release all held topic locks.

---

## 5. Job System Requirements

We define the specifications for the async job processing engine:

### 1. Job Model
Encapsulates metadata and execution records:
* `job_id`: UUID
* `action_id`: str (e.g. `generate_briefs`)
* `status`: PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
* `payload`: dict (parameters like `topic_id`, `top_n`)
* `created_at` / `started_at` / `completed_at`: ISO-8601 timestamps
* `error_message`: Optional string containing exception traces.

### 2. Job Queue
A FIFO task queue that supports priority levels (e.g. human UI clicks have higher priority than scheduled cron ingestions).

### 3. Worker
A stateless worker daemon that polls the queue, resolves the job, executes it, updates the job state, and publishes completion events.

### 4. Lock Manager
A file-based lock provider (`data/locks/{lock_name}.lock`) or database-level lock system supporting:
* `acquire(lock_name, timeout)`
* `release(lock_name)`

### 5. Governance Execution Policy
* The distributed worker must **never** call domain services or generators directly.
* A job **must** unpack its payload, instantiate a `WorkflowActionExecutor`, and invoke `.execute()` to pass all availability, state transitions, and dependency validation logic.

---

## 6. Governance Compatibility Review

```
Background Worker
       │
       │ (1) dequeue job
       ▼
   Job Runner
       │
       │ (2) execute(action_id, payload)
       ▼
WorkflowActionExecutor
       │
       │ (3) is_action_available()
       ▼
ActionAvailabilityEngine
       │
       │ (returns allowed=True)
       ▼
WorkflowActionExecutor
       │
       │ (4) validate_transition()
       ▼
ReviewTransitionEngine
       │
       │ (returns valid=True)
       ▼
WorkflowActionExecutor
       │
       │ (5) run()
       ▼
Application Service
```

This strict architectural pipeline guarantees that background jobs:
* **Cannot run out-of-order**: E.g., a background job attempting storyboard generation for a missing brief will be aborted by the executor since `ActionAvailabilityEngine` will return blocked.
* **Record audit trails**: Every background review or auto-approval writes `ReviewHistoryEntry` rows.

---

## 7. Recommended Distributed Architecture

For local portfolios and full-stack deployments (IIT Madras ProductivOS stack standard), we recommend a **stateless file-based SQLite background queue** (or Supabase direct queue if deployed on cloud).

```
   ┌─────────────────────────────────────────────────────────┐
   │                       Streamlit UI                      │
   └─────────────────────────────────────────────────────────┘
                                │
                                │ (1) Queue Job (database write)
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │                     Database/SQLite                     │
   │                [ jobs | locks | history ]               │
   └─────────────────────────────────────────────────────────┘
                                ▲
                                │ (2) Poll / Lock Topic
                                │
   ┌─────────────────────────────────────────────────────────┐
   │                   Background Worker                     │
   │               (WorkflowActionExecutor)                  │
   └─────────────────────────────────────────────────────────┘
```

* **Storage**: SQLite database `data/jobs.db` containing a `jobs` metadata table and a `locks` table.
* **Concurrency**: Cooperative file-based locking or SQLite transactional locks.
* **Worker Process**: A separate, lightweight Python daemon (`python -m content_creation.jobs.worker`) managed concurrently.

---

## 8. Readiness Assessment

### Verdict: READY

The foundation audit is completed, and the platform is fully ready to implement the async background Job System in Phase 11.7.2.
