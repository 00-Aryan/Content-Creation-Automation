<!-- Generated on: 2026-11-20 | Commit: 5bbee8401f4d504074e10b74ada0479aff6b4813 | Auditor: pipeline-mapper -->

# Content Creation Automation: Dependencies and Boundaries

## 1. Internal Module Dependency Map & Layer Hierarchy

The repository architecture follows a 6-layer design pattern, moving from pure foundational primitives up to user entrypoints:

- **Layer 1: Core Domain & Models**
  - Paths: `src/content_creation/models/`, `src/content_creation/domains/`, `src/content_creation/shared/`
  - Responsibilities: Pure schema models, domain entities, value types, and shared enumerations (`ReviewStatus`, `TopicStatus`, `ArtifactLifecycleState`).
- **Layer 2: Platform & Storage**
  - Paths: `src/content_creation/platform/`, `src/content_creation/storage/`, `src/content_creation/audit/`, `src/content_creation/events/`, `src/content_creation/jobs/`, `src/content_creation/metrics/`, `src/content_creation/notifications/`
  - Responsibilities: Filesystem operations (`LocalStorage`, `LocalBackend`), SQLite persistence repositories, event bus, job queuing, distributed resource locking, and telemetry.
- **Layer 3: Scoring & Generation**
  - Paths: `src/content_creation/scoring/`, `src/content_creation/generation/`, `src/content_creation/inference/`, `src/content_creation/prompts/`
  - Responsibilities: Topic scoring engine, prompt loading registry, provider inference adapters (`GeminiProvider`, `OpenRouterProvider`), and multi-format LLM generators.
- **Layer 4: Workflow & Planning**
  - Paths: `src/content_creation/workflow/`, `src/content_creation/planning/`, `src/content_creation/manifest.py`
  - Responsibilities: Deterministic state machines (`ActionAvailabilityEngine`, `ReviewTransitionEngine`, `WorkflowActionExecutor`), manifest compilation, weekly content calendar scheduler, and dry-run pre-publication validator.
- **Layer 5: Application Services**
  - Paths: `src/content_creation/application/`
  - Responsibilities: Service layer orchestrating domain operations (`CollectTopicsService`, `ScoreTopicsService`, `BriefGenerationService`, `ContentIntelligenceService`, `StoryboardService`, `AssetGenerationService`, `BriefReviewService`, `StoryboardReviewService`, `AssetReviewService`, `PipelineRunService`).
- **Layer 6: Entrypoints & Presentation**
  - Paths: `src/content_creation/cli.py`, `src/content_creation/ui/`
  - Responsibilities: Operator CLI command dispatch and Streamlit multi-page web console.

---

### 1.1 Circular Import Analysis

Static AST parsing detected **2 circular import cycles** in the codebase:

1. **Cycle 1: Workflow States <-> State Mappers**
   - Path: `content_creation.workflow.states` -> `content_creation.workflow.state_mappers` -> `content_creation.workflow.states`
   - Citations:
     - `src/content_creation/workflow/states.py:182`: `from content_creation.workflow.state_mappers import (`
     - `src/content_creation/workflow/state_mappers.py:24`: `from content_creation.workflow.states import ArtifactLifecycleState`
   - Mechanism: `states.py` defers importing `state_mappers.py` to the end of the file (line 182) to avoid module loading failure when `state_mappers.py` imports `ArtifactLifecycleState` at top-level.

2. **Cycle 2: Workflow Action Executor <-> Pipeline Run Service**
   - Path: `content_creation.workflow.workflow_action_executor` <-> `content_creation.application.pipeline_run_service`
   - Citations:
     - `src/content_creation/workflow/workflow_action_executor.py:753`: `from content_creation.application.pipeline_run_service import PipelineRunService`
     - `src/content_creation/application/pipeline_run_service.py:63, 88, 117, 150, 186, 222, 256, 284`: `from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor`
   - Mechanism: Both modules require each other during action execution. Both files circumvent import failure by using deferred, in-method dynamic imports instead of top-level imports.

---

### 1.2 Architectural Layer Violations

Static analysis identified **19 layer boundary violations** across entrypoints and UI components:

| Violating File:Line | Target Import | Violation Type | Description |
|:---|:---|:---|:---|
| `src/content_creation/cli.py:12` | `content_creation.storage.local.LocalStorage` | CLI -> Storage direct bypass | CLI imports and instantiates `LocalStorage` directly at lines 247, 265, 287, 312, 333 instead of delegating to application services or `ApplicationContext`. |
| `src/content_creation/ui/components/timeline.py:13` | `content_creation.events.store.models.EventEnvelope` | UI -> Event Store direct bypass | UI component imports SQLite event store model directly without going through `client.py` or application service. |
| `src/content_creation/ui/components/timeline.py:14` | `content_creation.events.store.timeline.EventTimelineService` | UI -> Event Store direct bypass | UI component directly binds to backend timeline infrastructure service. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:25` | `content_creation.platform.observability.health` | UI -> Platform direct bypass | UI page directly imports system health monitor. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:51` | `content_creation.platform.observability.service` | UI -> Platform direct bypass | UI page instantiates observability service directly. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:52` | `content_creation.jobs.queue_engine.QueueEngine` | UI -> Jobs direct bypass | UI page interacts directly with queue engine backend. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:53` | `content_creation.jobs.lock_manager.LockManager` | UI -> Jobs direct bypass | UI page accesses lock manager infrastructure directly. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:54` | `content_creation.jobs.sqlite_lock_repository.SQLiteLockRepository` | UI -> Jobs direct bypass | UI page directly binds SQLite lock repository. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:55` | `content_creation.jobs.recovery_supervisor.RecoverySupervisor` | UI -> Jobs direct bypass | UI page calls background recovery supervisor directly. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:56` | `content_creation.events.store.sqlite_repository.SQLiteEventRepository` | UI -> Events direct bypass | UI page queries raw SQLite events database. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:62` | `content_creation.audit.sqlite_repository.SQLiteAuditRepository` | UI -> Audit direct bypass | UI page connects directly to SQLite audit database. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:63` | `content_creation.audit.compliance.AuditComplianceService` | UI -> Audit direct bypass | UI page executes compliance evaluation directly. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:100` | `content_creation.jobs.sqlite_repository.SQLiteJobRepository` | UI -> Jobs direct bypass | UI page inspects low-level job records directly from database. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:101` | `content_creation.jobs.schema.init_jobs_schema` | UI -> Jobs direct bypass | UI page triggers schema migration / initialization logic. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:108` | `content_creation.jobs.schema.init_locks_schema` | UI -> Jobs direct bypass | UI page triggers low-level locks schema setup. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:118` | `content_creation.events.store.schema.init_event_store_schema` | UI -> Events direct bypass | UI page invokes database DDL setup for events. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:145` | `content_creation.audit.schema.init_audit_schema` | UI -> Audit direct bypass | UI page invokes database DDL setup for audit. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:186` | `content_creation.platform.observability.health.HealthCheckService` | UI -> Platform direct bypass | UI page directly runs storage and system health probes. |
| `src/content_creation/ui/pages/6_operations_dashboard.py:271` | `content_creation.platform.observability.health.HealthCheckService` | UI -> Platform direct bypass | Redundant direct health check instantiation in tab view. |

*(Note: Zero violations detected where `domain/` or `models/` import from `application/`, `ui/`, or `cli`)*.

---

### 1.3 High Fan-In Blast-Radius Modules

The following **33 modules** are imported by $\ge 5$ other internal modules across `src/content_creation/`:

| Module | Fan-In (Import Count) | Dependent Subsystems | Risk Profile |
|:---|:---|:---|:---|
| `content_creation.shared.enums` | 30 | models, generation, workflow, application, ui | High — Core lifecycle & status enums; changes force ripple across whole codebase. |
| `content_creation.models.topic` | 17 | scoring, collectors, storage, workflow, application, cli | High — Foundational data model for research topics. |
| `content_creation.events.models` | 17 | events, workflow, subscribers, audit, metrics, ui | High — Base event envelope and event types for pubsub. |
| `content_creation.models.brief` | 16 | generation, domains, storage, workflow, application, ui | High — Educational summary model consumed across multiple generators. |
| `content_creation.events.bus` | 15 | workflow, jobs, audit, subscribers, cli, application | High — Process-wide in-memory event bus singleton. |
| `content_creation.shared.types` | 14 | models, domains, storage, workflow | Medium — Type aliases (`TopicId`, `TimestampIso`). |
| `content_creation.application.context` | 12 | application services, workflow executor, cli | High — Service dependency container. |
| `content_creation.notifications.models` | 12 | notifications, subscribers, streaming, ui | Medium — Notification record contracts. |
| `content_creation.notifications.repository` | 9 | notifications, streaming, ui | Medium — Notification storage interfaces. |
| `content_creation.domains.storyboard.model` | 8 | storyboard domain, asset generators, workflow, ui | High — Flat storyboard blueprint model. |
| `content_creation.events.store.models` | 8 | events.store, audit, metrics, ui | Medium — Persisted event records. |
| `content_creation.audit.models` | 7 | audit, workflow, compliance, ui | Medium — Audit trail entry schema. |
| `content_creation.events.factory` | 7 | workflow, events, application | Medium — Convenience factory creating event envelopes. |
| `content_creation.metrics.repository` | 7 | metrics, subscribers, ui | Medium — Metrics persistence interfaces. |
| `content_creation.events.store.repository` | 7 | events.store, replay, subscribers, ui | Medium — Event store repository contracts. |
| `content_creation.ui.state.session` | 7 | ui pages 1 through 6, app.py | Medium — Streamlit session state management. |
| `content_creation.storage.local` | 6 | application services, manifest, cli | High — Filesystem storage abstraction. |
| `content_creation.utils.config` | 6 | collectors, scoring, planning, cli | Medium — YAML configuration loading utilities. |
| `content_creation.models.review_history` | 6 | application, review services, workflow, storage | Medium — Human operator audit trail records. |
| `content_creation.inference.providers.base` | 6 | inference manager, gemini, openrouter | High — Base abstract LLM provider interface. |
| `content_creation.jobs.lock_models` | 6 | jobs, lock manager, recovery, sqlite lock repo | Medium — Lock definitions and statuses. |
| `content_creation.jobs.models` | 6 | jobs, queue engine, worker, recovery | Medium — Background job schema. |
| `content_creation.ui.components.status` | 6 | ui pages 1 through 5, app.py | Low — UI badge and alert rendering helpers. |
| `content_creation.ui.services.client` | 6 | ui pages 1 through 6, app.py | High — UI-to-Application facade client. |
| `content_creation.platform.storage.json_repository` | 6 | platform, domain repositories | Medium — Low-level atomic JSON serializer. |
| `content_creation.workflow.workflow_action_executor` | 5 | pipeline run service, cli, ui client | High — Central action dispatcher and gate evaluator. |
| `content_creation.models.manifest` | 5 | manifest builder, planner, workflow, storage | Medium — Final asset bundle contract. |
| `content_creation.audit.repository` | 5 | audit, subscribers, compliance, ui | Medium — Audit database interface. |
| `content_creation.jobs.repository` | 5 | jobs, queue engine, supervisor, ui | Medium — Job storage repository interface. |
| `content_creation.metrics.models` | 5 | metrics, telemetry, kpi, ui | Medium — Telemetry record schemas. |
| `content_creation.notifications.service` | 5 | subscribers, ui, components | Medium — Notification dispatch and summary service. |
| `content_creation.subscribers.models` | 5 | subscribers, dispatcher, platform | Low — Subscriber payload definitions. |
| `content_creation.notifications.streaming.connection_manager` | 5 | streaming server, pubsub, ui | Medium — SSE active socket connection registry. |

---

## 2. Third-Party Dependencies Audit

### Declared in `pyproject.toml`
All **7 dependencies** declared in `pyproject.toml:14-22` are actively imported and utilized in `src/content_creation/`:

- `requests>=2.31.0`:
  - Imported in `src/content_creation/inference/providers/openrouter.py:5` (`import requests`)
- `pydantic>=2.0.0`:
  - Imported across 19 files, including `src/content_creation/models/topic.py:10`, `src/content_creation/models/brief.py:1`, `src/content_creation/domains/storyboard/model.py:6`, `src/content_creation/generation/script.py:8`
- `python-dotenv>=1.0.0`:
  - Imported in `src/content_creation/cli.py:24`, `src/content_creation/ui/app.py:3`, `src/content_creation/utils/config.py:8` (`from dotenv import load_dotenv`)
- `feedparser>=6.0.10`:
  - Imported in `src/content_creation/collectors/rss.py:8` (`import feedparser`)
- `pyyaml>=6.0.0`:
  - Imported in `src/content_creation/utils/config.py:7` (`import yaml`)
- `google-genai>=2.2.0`:
  - Imported in `src/content_creation/inference/providers/gemini.py:5-6` (`import google`, `from google import genai`)
- `streamlit>=1.30.0`:
  - Imported across 14 UI files and `src/content_creation/inference/credentials.py:16` (`import streamlit as st`)

### Undeclared Transitive Imports
- **None detected.** Every non-standard library import in `src/content_creation/` maps directly to a declared requirement in `pyproject.toml`.

---

## 3. External Configurations, Prompts, LLM Models & Secrets

### 3.1 YAML Configuration Files
- `config/feeds.yaml`: Loaded at `src/content_creation/utils/config.py:18` (`def load_feeds_config(...)`). Defines RSS and technical sources.
- `config/publishing.yaml`: Loaded at `src/content_creation/workflow/workflow_action_executor.py:680` and `src/content_creation/cli.py:686`. Defines posting times, platform targets, and format slot requirements.
- `config/scoring.yaml`: Loaded at `src/content_creation/scoring/config.py:13` (`def load_scoring_config(...)`). Defines criteria weights and threshold scores.

### 3.2 Prompt Templates
Templates are loaded dynamically via `PromptRegistry` (`src/content_creation/prompts/registry.py:8-15`):
- `prompts/summarize.md`: Registered at `src/content_creation/prompts/registry.py:8`
- `prompts/short_video.md`: Registered at `src/content_creation/prompts/registry.py:9`
- `prompts/carousel.md`: Registered at `src/content_creation/prompts/registry.py:10`
- `prompts/newsletter.md`: Registered at `src/content_creation/prompts/registry.py:11`
- `prompts/thumbnail.md`: Registered at `src/content_creation/prompts/registry.py:12`
- `prompts/content_intelligence.md`: Registered at `src/content_creation/prompts/registry.py:13`
- `prompts/storyboard.md`: Registered at `src/content_creation/prompts/registry.py:14`
- `prompts/linkedin_post.md`: Registered at `src/content_creation/prompts/registry.py:15`

### 3.3 Hardcoded LLM Model Strings
- `gemini-2.5-flash`: `src/content_creation/inference/providers/gemini.py:71` (`def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):`)
- `meta-llama/llama-3.1-8b-instruct:free`: `src/content_creation/inference/providers/openrouter.py:13` (`_DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"`)

### 3.4 Referenced Environment Variables (Names Only)
- `CONTENT_FACTORY_ROOT`:
  - `src/content_creation/ui/services/client.py:50` (`root_env = os.environ.get("CONTENT_FACTORY_ROOT")`)
  - `src/content_creation/ui/services/client.py:68` (`root_env = os.environ.get("CONTENT_FACTORY_ROOT")`)
- `GEMINI_API_KEY`:
  - `src/content_creation/cli.py:371, 390, 437` (`api_key = os.environ.get("GEMINI_API_KEY")`)
  - `src/content_creation/inference/manager.py:31, 48` (`resolve_credential("GEMINI_API_KEY")`)
  - `src/content_creation/ui/services/client.py:203, 255, 277, 299, 321` (`os.environ.get("GEMINI_API_KEY")`)
- `OPENROUTER_API_KEY`:
  - `src/content_creation/inference/manager.py:50, 56` (`resolve_credential("OPENROUTER_API_KEY")`)

### 3.5 Secret File Presence
- `.env`: **Present on disk** (`Path(".env").exists() == True`).
- `.streamlit/secrets.toml`: **Present on disk** (`Path(".streamlit/secrets.toml").exists() == True`).
*(Zero credential values have been read, logged, or printed).*

---

## 4. State & Side-Effect Boundaries

### 4.1 Filesystem Persistence
Artifact storage relies on `LocalStorage` (`src/content_creation/storage/local.py`) backed by `LocalBackend` (`src/content_creation/platform/storage/local_backend.py`):

| Data Path | Write Pattern (Atomic vs Direct) | Resumability / Idempotency Key | Serialization Format |
|:---|:---|:---|:---|
| `data/raw/` | Direct write via `save_raw` | `<source_id>_<timestamp>` | Raw XML / RSS string |
| `data/staged/` | Atomic write (`_atomic_write` temp file + rename) | `TopicItem.id` (SHA256 of URL) | JSON (`TopicItem`) |
| `data/scored/` | Atomic write | `ScoredTopicItem.id` | JSON (`ScoredTopicItem`) |
| `data/briefs/` | Atomic write | `Brief.topic_id` | JSON (`Brief`) |
| `data/content_intelligence/` | Atomic write | `ContentIntelligence.topic_id` | JSON (`ContentIntelligence`) |
| `data/storyboards/` | Atomic write | `Storyboard.topic_id` | JSON (`Storyboard`) |
| `data/scripts/` | Atomic write | `Script.topic_id` | JSON (`Script`) |
| `data/carousels/` | Atomic write | `Carousel.topic_id` | JSON (`Carousel`) |
| `data/newsletters/` | Atomic write | `Newsletter.topic_id` | JSON (`Newsletter`) |
| `data/thumbnails/` | Atomic write | `ThumbnailPrompt.topic_id` | JSON (`ThumbnailPrompt`) |
| `data/manifests/` | Atomic write | `TopicManifest.topic_id` | JSON (`TopicManifest`) |
| `data/calendars/` | Atomic write | `WeeklyCalendar.week_start` | JSON (`WeeklyCalendar`) |
| `data/dryruns/` | Atomic write | `DryRunReport.week_start` | JSON (`DryRunReport`) |
| `data/analytics/` | Atomic write | `post_id` (`<topic_id>_<format>_<week_start>`) | JSON (`PostAnalytics`) |
| `data/review_history/` | Atomic write | `topic_id` | JSON (`List[ReviewHistoryEntry]`) |
| `data/workflow_state/` | Atomic write | `topic_id` | JSON (`WorkflowState`) |

*Atomic Write Implementation:* Verified in `src/content_creation/platform/storage/local_backend.py:55-75`. Writes payload to temporary file in target directory, then executes atomic replacement via `os.replace(temp_path, final_path)`.

---

### 4.2 SQLite Databases & Concurrency
The system uses 5 discrete SQLite database files in `data/`:

| Database File | Tables | Journal Mode | Concurrency / Locking Mechanism | Transaction Boundaries |
|:---|:---|:---|:---|:---|
| `data/events.db` | `events` | `PRAGMA journal_mode=WAL` (`src/content_creation/events/store/schema.py:37`) | SQLite busy handler + `INSERT OR IGNORE` | `with conn:` auto-commit per event append |
| `data/metrics.db` | `metrics` | `PRAGMA journal_mode=WAL` (`src/content_creation/metrics/schema.py:36`) | Single-connection transaction commit | Explicit `conn.commit()` after save |
| `data/audit.db` | `audit` | `PRAGMA journal_mode=WAL` (`src/content_creation/audit/schema.py:44`) | Single-connection transaction commit | Explicit `conn.commit()` after save |
| `data/jobs.db` | `jobs`, `locks` | `PRAGMA journal_mode=WAL` (`src/content_creation/jobs/schema.py:11, 83`) | `LockManager` exclusivity checks + heartbeat timeouts | Explicit `conn.commit()` on state transitions |
| `data/notifications.db` | `notifications` | `PRAGMA journal_mode=WAL` (`src/content_creation/notifications/schema.py:11`) | Single-connection transaction commit | Explicit `conn.commit()` on insert/update |

---

### 4.3 Module-Level Mutable State & Globals
- `src/content_creation/events/bus.py:11`: `_EVENT_BUS: Optional[EventBus] = None` — process-level singleton instance for in-memory event dispatching.
- `src/content_creation/subscribers/dispatcher.py:12`: `_DISPATCHER: Optional[SubscriberDispatcher] = None` — process-level event subscriber dispatcher.
- `src/content_creation/notifications/streaming/connection_manager.py:27`: `self._connections: Set[Tuple[socket.socket, Any]] = set()` — mutable active socket connection registry held in memory.
- `src/content_creation/ui/state/session.py:10`: `st.session_state` keys (`selected_topic_id`, `selected_brief_id`, `filters`, `page_index`) — Streamlit session state mutated across UI interactions.

---

### 4.4 Concurrency & Execution Model
1. **Synchronous Execution:**
   - Default CLI commands (`collect`, `score-topics`, `generate-briefs`, `generate-assets`, `build-manifest`, `plan-week`, `dry-run`) execute synchronously on the main operating system thread.
   - UI user interactions in `ui/pages/` execute synchronously within the Streamlit thread runner.
2. **Background Daemons & Threading:**
   - `WorkerDaemon` (`src/content_creation/jobs/worker_daemon.py:22`): Runs in a background thread polling `QueueEngine` for queued jobs.
   - `LockManager` heartbeat thread: Background thread refreshing lock ownership timestamps.
   - `NotificationSSEServer` (`src/content_creation/notifications/streaming/server.py:254`): Starts a threaded socket server (`ThreadingHTTPServer`) listening on port 18503 to stream real-time events to web clients.
