<!-- Generated on: 2026-11-20 | Commit: 5bbee8401f4d504074e10b74ada0479aff6b4813 | Auditor: pipeline-mapper -->

# Content Creation Automation: Pipeline Contracts

## 1. End-to-End Pipeline Architecture & Flow

```text
[Ingestion / RSS] -> [Staged Topics]
       |
       v
[Topic Scoring Engine] -> [Scored Topics]
       |
       v (Threshold Gate)
[Brief Generation Service] -> [Educational Briefs]
       |
       v
[Content Intelligence Service] -> [Teaching Hooks & Insights]
       |
       v
[Storyboard Generation Service] -> [Storyboard Blueprint]
       |
       +-------------------------------+-------------------------------+
       |                               |                               |
       v                               v                               v
[Video Script Gen]              [Carousel Gen]                 [Newsletter Gen]
       |                               |                               |
       +-------------------------------+-------------------------------+
                                       |
                                       v
                             [Thumbnail Prompt Gen]
                                       |
                                       v
                              [Manifest Builder]
                                       |
                                       v
                           [Weekly Posting Planner]
                                       |
                                       v
                            [Pre-Publish Dry Run]
                                       |
                                       v
                             [Analytics & Metrics]
```

---

## 2. Stage-by-Stage Contract Master Table

| Stage # | Stage Name | CLI Command | UI Page | Application Service | Input Contract (Type & Source) | Output Contract (Type & Target) | Primary Gate / Precondition |
|:---|:---|:---|:---|:---|:---|:---|:---|
| 1 | Ingestion | `collect` | `1_topic_collection.py` | `CollectTopicsService` | `config/feeds.yaml` (RSS) | `TopicItem` -> `data/staged/*.json` | Feed connectivity & valid feed schema |
| 2 | Scoring | `score-topics` | `2_topic_pipeline.py` | `ScoreTopicsService` | `TopicItem` (`data/staged/`) | `ScoredTopicItem` -> `data/scored/*.json` | Schema validity & non-empty text |
| 3 | Briefs | `generate-briefs` | `3_brief_viewer.py` | `BriefGenerationService` | `ScoredTopicItem` (`data/scored/`) | `Brief` -> `data/briefs/*.json` | Priority score threshold & LLM availability |
| 4 | Intelligence | `generate-briefs` / internal | `3_brief_viewer.py` / `4_storyboard.py` | `ContentIntelligenceService` | `Brief` (`data/briefs/`) | `ContentIntelligence` -> `data/content_intelligence/*.json` | Brief existence on disk |
| 5 | Storyboard | internal / service | `4_storyboard.py` | `StoryboardService` | `Brief` + `ContentIntelligence` | `Storyboard` -> `data/storyboards/*.json` | Brief + Intel approval |
| 6 | Assets | `generate-assets` | `5_asset_workshop.py` | `AssetGenerationService` | `Brief` + `Storyboard` | `Script`, `Carousel`, `Newsletter`, `ThumbnailPrompt` | Storyboard Presence Gate |
| 7 | Review | `review-assets` | `5_asset_workshop.py` | `AssetReviewService` | Asset JSONs (`data/*/`) | `ReviewStatus` -> `data/review_history/` | Human Operator Sign-off & state machine validity |
| 8 | Manifest | `build-manifest` | `5_asset_workshop.py` | `ManifestBuilder` | Topic assets (`data/*/`) | `TopicManifest` -> `data/manifests/*.json` | Approved assets & complete format set |
| 9 | Planning | `plan-week` | `2_topic_pipeline.py` | `PostingPlanner` | `TopicManifest` (`data/manifests/`) | `WeeklyCalendar` -> `data/calendars/*.json` | Manifest completeness (`ready_for_planner == True`) |
| 10 | Dry Run | `dry-run` | `2_topic_pipeline.py` | `DryRunValidator` | `WeeklyCalendar` (`data/calendars/`) | `DryRunReport` -> `data/dryruns/*.json` | 7-day schedule validity & file existence |
| 11 | Analytics | `init-analytics` | `6_operations_dashboard.py` | `WorkflowActionExecutor` | `WeeklyCalendar` (`data/calendars/`) | `PostAnalytics` -> `data/analytics/*.json` | Published post records in calendar |
| 12 | Event Store | `event-*` | `6_operations_dashboard.py` | `SQLiteEventRepository` | `EventEnvelope` / `EventRecord` | `data/events.db` (`events` table) | Valid event envelope & schema |
| 13 | Metrics | `metrics-*` | `6_operations_dashboard.py` | `SQLiteMetricRepository` | `MetricRecord` points | `data/metrics.db` (`metrics` table) | Event ingestion & telemetry collection |
| 14 | Audit | `audit-*` | `6_operations_dashboard.py` | `SQLiteAuditRepository` | `AuditRecord` entries | `data/audit.db` (`audit` table) | State mutations & actor non-repudiation |
| 15 | Jobs | internal / worker | `6_operations_dashboard.py` | `QueueEngine` / `LockManager` | `Job` definitions & locks | `data/jobs.db` (`jobs`, `locks` tables) | Worker lock acquisition & heartbeat |
| 16 | Notifications | internal / SSE | `ui/components/notification_panel` | `NotificationService` | Alerts & broadcasts | `data/notifications.db` (`notifications`) | Event subscription & client connection |

---

## 3. Detailed Stage Breakdowns

### Stage 1: Ingestion
- **Entrypoints:**
  - CLI: `collect` (`src/content_creation/cli.py:56`, dispatch: `src/content_creation/cli.py:229-245`)
  - UI: `1_topic_collection.py` (`src/content_creation/ui/pages/1_topic_collection.py:46` `if st.button("📡 Collect Topics"):`)
  - Service: `CollectTopicsService.run` (`src/content_creation/application/collect_topics_service.py:23` `def run(self, ctx: ApplicationContext, source_filter: Optional[str] = None) -> CollectResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `ApplicationContext` (`src/content_creation/application/context.py:16`), `source_filter: Optional[str]`
  - Upstream disk artifact or SQLite source: `config/feeds.yaml` read via `load_feeds_config` (`src/content_creation/utils/config.py:11` `def load_feeds_config(config_path: Path) -> dict:`)
  - Required fields & invariants: Feed entries must contain `title`, `link` (URL), and source identifier. Missing authors/excerpts normalize to `"unknown"`.
- **Exact Output Contract:**
  - Returned Python type: `CollectResult` (`src/content_creation/application/collect_topics_service.py:12` `@dataclass class CollectResult:`)
  - Written disk path or SQLite table: `data/raw/<source_id>_<timestamp>.xml` and `data/staged/<topic_id>.json` via `LocalStorage.save_topic` (`src/content_creation/storage/local.py:84` `def save_topic(self, topic: TopicItem) -> None:`)
  - Emitted domain events: `topic.collected` via `create_pipeline_event` (`src/content_creation/events/factory.py:144` `def create_pipeline_event(...)`)
- **Validation, Guard & Gate Checkpoints:**
  - Preconditions & acceptance thresholds: Feed connectivity verified by HTTP status code 200 via `FeedCollector.collect` (`src/content_creation/collectors/rss.py:32`).
  - Schema validation: Pydantic model validation on `TopicItem` (`src/content_creation/models/topic.py:34`). Validates ISO-8601 published date via `validate_iso_date` (`src/content_creation/models/topic.py:50`).
  - State machine transition checks: Initial state assigned as `TopicStatus.STAGED` (`src/content_creation/models/topic.py:45`).
- **Conditional Branches & Failure Modes:**
  - Fallbacks & retry handling: Network exceptions caught in `FeedCollector.collect` (`src/content_creation/collectors/rss.py:42`), logs error, continues with remaining feeds.
  - Idempotency skip logic: If topic already exists on disk, `ctx.storage.get_topic(item.id)` returns existing item and skips write (`src/content_creation/application/collect_topics_service.py:48`).
  - Error capture & partial failure recovery: Ingestion errors increment `failed_sources` without aborting other feed fetches.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/application/collect_topics_service.py:20-58`, `src/content_creation/collectors/rss.py:16-52`
  - Supporting utilities & platform plumbing: `src/content_creation/utils/config.py:11-35`, `src/content_creation/platform/storage/local_backend.py:55-75`

---

### Stage 2: Scoring
- **Entrypoints:**
  - CLI: `score-topics` (`src/content_creation/cli.py:72`, dispatch: `src/content_creation/cli.py:294-309`)
  - UI: `2_topic_pipeline.py` (`src/content_creation/ui/pages/2_topic_pipeline.py:108` `if st.button("⚖️ Score Topics"):`)
  - Service: `ScoreTopicsService.run` (`src/content_creation/application/score_topics_service.py:25` `def run(self, ctx: ApplicationContext, limit: Optional[int] = None) -> ScoreResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `TopicItem` (`src/content_creation/models/topic.py:34`), `ScoringConfig` (`src/content_creation/scoring/config.py:17`)
  - Upstream disk artifact or SQLite source: `data/staged/*.json` via `LocalStorage.list_staged_topics` (`src/content_creation/storage/local.py:98`), `config/scoring.yaml` via `ScoringConfigLoader.load` (`src/content_creation/scoring/config.py:10`)
  - Required fields & invariants: `TopicItem.id`, `TopicItem.title`, `TopicItem.raw_text`, `TopicItem.category`.
- **Exact Output Contract:**
  - Returned Python type: `ScoreResult` (`src/content_creation/application/score_topics_service.py:13` `@dataclass class ScoreResult:`)
  - Written disk path or SQLite table: `data/scored/<topic_id>.json` via `LocalStorage.save_scored_topic` (`src/content_creation/storage/local.py:102` `def save_scored_topic(self, topic: ScoredTopicItem) -> None:`)
  - Emitted domain events: `topic.scored` via `create_pipeline_event` (`src/content_creation/events/factory.py:144`)
- **Validation, Guard & Gate Checkpoints:**
  - Preconditions & acceptance thresholds: Weight sum validation `sum(weights.values()) == 1.0` in `ScoringConfigLoader.load` (`src/content_creation/scoring/config.py:32`).
  - Score bounds: Individual rule scores and total `priority_score` constrained between 0.0 and 100.0 (`src/content_creation/models/topic.py:76`).
  - State machine transition checks: `ScoredTopicItem.set_scored_status` validator transitions `RAW` or `STAGED` to `TopicStatus.SCORED` (`src/content_creation/models/topic.py:101`).
- **Conditional Branches & Failure Modes:**
  - Slicing limit: If `limit` is provided, staged topics list is sliced (`src/content_creation/application/score_topics_service.py:34`).
  - Idempotency skip logic: Overwrites scored JSON deterministically; scoring rules firing evaluated purely from input fields and weights.
  - Error capture & partial failure recovery: Malformed topic JSON triggers warning log, item added to `flagged_items`, processing continues.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/scoring/engine.py:35-298`, `src/content_creation/application/score_topics_service.py:22-55`
  - Supporting utilities & platform plumbing: `src/content_creation/scoring/config.py:10-55`, `src/content_creation/storage/local.py:98-112`

---

### Stage 3: Briefs
- **Entrypoints:**
  - CLI: `generate-briefs` (`src/content_creation/cli.py:85`, dispatch: `src/content_creation/cli.py:370-387`)
  - UI: `3_brief_viewer.py` (`src/content_creation/ui/pages/3_brief_viewer.py:126` `if st.button("📝 Generate Briefs"):`)
  - Service: `BriefGenerationService.run` (`src/content_creation/application/brief_generation_service.py:38` `def run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> BriefGenerationResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `ScoredTopicItem` (`src/content_creation/models/topic.py:75`), prompt template `prompts/summarize.md` via `PromptRegistry` (`src/content_creation/prompts/registry.py:8`)
  - Upstream disk artifact or SQLite source: `data/scored/*.json` via `LocalStorage.list_scored_topics` (`src/content_creation/storage/local.py:116`)
  - Required fields & invariants: Topic must be sorted descending by `priority_score`; `top_n` items selected.
- **Exact Output Contract:**
  - Returned Python type: `BriefGenerationResult` (`src/content_creation/application/brief_generation_service.py:25` `@dataclass class BriefGenerationResult:`)
  - Written disk path or SQLite table: `data/briefs/<topic_id>.json` via `LocalStorage.save_brief` (`src/content_creation/storage/local.py:132` `def save_brief(self, brief: Brief) -> None:`)
  - Emitted domain events: `brief.generated` via `create_pipeline_event` (`src/content_creation/events/factory.py:144`)
- **Validation, Guard & Gate Checkpoints:**
  - Pydantic invariants: `Brief.must_have_three_items` validator enforces `len(plain_english_summary) == 3` (`src/content_creation/models/brief.py:21`).
  - Initial review status: Defaults to `ReviewStatus.DRAFT` (`src/content_creation/models/brief.py:17`).
  - Stage completion marker: Recorded via `ctx.workflow.mark_completed(topic.id, "brief")` (`src/content_creation/application/brief_generation_service.py:90`).
- **Conditional Branches & Failure Modes:**
  - Idempotency skip logic: Checks `ctx.storage.get_brief(topic.id) is not None`; skips LLM invocation if already present (`src/content_creation/application/brief_generation_service.py:65`).
  - LLM fallback & retries: Handled by `InferenceManager.call` (`src/content_creation/inference/manager.py:70-110`). If Gemini fails or hits rate limits, falls back to OpenRouter if configured.
  - Failure capture: Exceptions record `ctx.workflow.mark_failed(topic.id, "brief")` and append to `BriefFailure` record (`src/content_creation/application/brief_generation_service.py:97`).
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/generation/brief.py:18-85`, `src/content_creation/application/brief_generation_service.py:35-108`
  - Supporting utilities & platform plumbing: `src/content_creation/inference/manager.py:25-115`, `src/content_creation/prompts/registry.py:8-25`

---

### Stage 4: Content Intelligence
- **Entrypoints:**
  - CLI: `run-pipeline` (`src/content_creation/cli.py:99`, dispatch: `src/content_creation/cli.py:433-620`) / internal action `generate_ci` (`src/content_creation/workflow/workflow_action_executor.py:516`)
  - UI: `4_storyboard.py` (`src/content_creation/ui/pages/4_storyboard.py:73` `if st.button("🎨 Generate Content Intelligence"):`)
  - Service: `ContentIntelligenceService.run` (`src/content_creation/application/content_intelligence_service.py:41` `def run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> ContentIntelligenceGenerationResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `Brief` (`src/content_creation/models/brief.py:8`), prompt template `prompts/content_intelligence.md` (`src/content_creation/prompts/registry.py:13`)
  - Upstream disk artifact or SQLite source: `data/briefs/*.json` via `LocalStorage.list_briefs` (`src/content_creation/storage/local.py:128`)
  - Required fields & invariants: `Brief.topic_id`, `Brief.why_it_matters`, `Brief.student_takeaway`.
- **Exact Output Contract:**
  - Returned Python type: `ContentIntelligenceGenerationResult` (`src/content_creation/application/content_intelligence_service.py:28` `@dataclass class ContentIntelligenceGenerationResult:`)
  - Written disk path or SQLite table: `data/content_intelligence/<topic_id>.json` via `LocalStorage.save_content_intelligence` (`src/content_creation/storage/local.py:145`)
  - Emitted domain events: `content_intelligence.generated` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Preconditions: Upstream `Brief` must exist on disk.
  - Model validations: `ContentIntelligence` Pydantic model (`src/content_creation/domains/content_intelligence/model.py:40`), validating `Hook` types (`HookType = Literal["question", "bold_claim", "contrast", "statistic"]`) and `EmotionalRegister`.
  - Quality assessment gate: Evaluates `quality_status` (`"ready"`, `"degraded"`, `"blocked"`).
- **Conditional Branches & Failure Modes:**
  - Idempotency skip logic: Checks `ctx.storage.get_content_intelligence(brief.topic_id) is not None`; skips if present (`src/content_creation/application/content_intelligence_service.py:68`).
  - Fallback logic: Deterministic fallback generation when LLM response does not match expected schema (`src/content_creation/domains/content_intelligence/generator.py:72`).
  - Error capture: Increments `failure_count`, records failure in `failures` list, and marks workflow state failed.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/domains/content_intelligence/generator.py:15-110`, `src/content_creation/application/content_intelligence_service.py:38-115`
  - Supporting utilities & platform plumbing: `src/content_creation/domains/content_intelligence/repository.py:12-45`

---

### Stage 5: Storyboard
- **Entrypoints:**
  - CLI: `run-pipeline` (`src/content_creation/cli.py:99`) / internal action `generate_storyboards` (`src/content_creation/workflow/workflow_action_executor.py:526`)
  - UI: `4_storyboard.py` (`src/content_creation/ui/pages/4_storyboard.py:94` `if st.button("📋 Generate Storyboards"):`)
  - Service: `StoryboardService.run` (`src/content_creation/application/storyboard_service.py:38` `def run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> StoryboardGenerationResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `Brief` (`src/content_creation/models/brief.py:8`) and `ContentIntelligence` (`src/content_creation/domains/content_intelligence/model.py:40`), prompt `prompts/storyboard.md`
  - Upstream disk artifact or SQLite source: `data/briefs/*.json` and `data/content_intelligence/*.json`
  - Required fields & invariants: Both `Brief` and `ContentIntelligence` must be present for `topic_id`.
- **Exact Output Contract:**
  - Returned Python type: `StoryboardGenerationResult` (`src/content_creation/application/storyboard_service.py:25` `@dataclass class StoryboardGenerationResult:`)
  - Written disk path or SQLite table: `data/storyboards/<topic_id>.json` via `LocalStorage.save_storyboard` (`src/content_creation/storage/local.py:158`)
  - Emitted domain events: `storyboard.generated` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Content intelligence dependency gate: `if ci is None: skipped += 1; continue` (`src/content_creation/application/storyboard_service.py:68`).
  - Model invariants: Flat schema validation on `Storyboard` (`src/content_creation/domains/storyboard/model.py:21`), verifying `VisualStyle` Literal constraint.
  - Review status: Initializes as `ReviewStatus.DRAFT`.
- **Conditional Branches & Failure Modes:**
  - Idempotency skip logic: Checks `ctx.storage.get_storyboard(brief.topic_id) is not None`; skips generation if present (`src/content_creation/application/storyboard_service.py:64`).
  - Failure capture: Records `StoryboardFailure`, sets `ctx.workflow.mark_failed(brief.topic_id, "storyboard")`.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/domains/storyboard/generator.py:16-105`, `src/content_creation/application/storyboard_service.py:35-115`
  - Supporting utilities & platform plumbing: `src/content_creation/domains/storyboard/repository.py:12-45`

---

### Stage 6: Asset Generation
- **Entrypoints:**
  - CLI: `generate-assets` (`src/content_creation/cli.py:89`, dispatch: `src/content_creation/cli.py:389-407`)
  - UI: `5_asset_workshop.py` (`src/content_creation/ui/pages/5_asset_workshop.py:118` `if st.button("⚡ Generate Asset Suite"):`)
  - Service: `AssetGenerationService.run` (`src/content_creation/application/asset_generation_service.py:31` `def run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> AssetGenerationResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `Brief` (`src/content_creation/models/brief.py:8`), `Storyboard` (`src/content_creation/domains/storyboard/model.py:21`), prompt templates `prompts/thumbnail.md`, `prompts/short_video.md`, `prompts/carousel.md`, `prompts/newsletter.md`
  - Upstream disk artifact or SQLite source: `data/briefs/*.json` and `data/storyboards/*.json`
  - Required fields & invariants: `Storyboard` must exist on disk for the target `topic_id`.
- **Exact Output Contract:**
  - Returned Python type: `AssetGenerationResult` (`src/content_creation/application/asset_generation_service.py:19` `@dataclass class AssetGenerationResult:`)
  - Written disk path or SQLite table:
    - `data/thumbnails/<topic_id>.json` via `LocalStorage.save_thumbnail` (`src/content_creation/storage/local.py:162`)
    - `data/scripts/<topic_id>.json` via `LocalStorage.save_script` (`src/content_creation/storage/local.py:166`)
    - `data/carousels/<topic_id>.json` via `LocalStorage.save_carousel` (`src/content_creation/storage/local.py:170`)
    - `data/newsletters/<topic_id>.json` via `LocalStorage.save_newsletter` (`src/content_creation/storage/local.py:174`)
  - Emitted domain events: `asset.generated` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - **Storyboard Presence Gate:** Explicit static check at `src/content_creation/application/asset_generation_service.py:66-72`:
    ```python
    storyboard = ctx.storage.get_storyboard(brief.topic_id)
    if storyboard is None:
        logger.warning(f"Skipping asset generation for {brief.topic_id} because storyboard artifact is missing.")
        skipped += 1
        continue
    ```
  - Format mapping gate: Checks `brief.recommended_formats` against `FORMAT_TO_ASSET` / `FREETEXT_TO_FORMAT` (`src/content_creation/application/asset_generation_service.py:104-114`).
  - Divergence guard: If workflow state reports completed but file missing, regenerates (`src/content_creation/application/asset_generation_service.py:81-84`).
- **Conditional Branches & Failure Modes:**
  - Thumbnail is always generated regardless of recommended format.
  - Scripts, Carousels, and Newsletters generated conditionally based on `brief.recommended_formats`.
  - Idempotency skip logic: If artifact file exists and workflow state completed, generation is skipped.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/application/asset_generation_service.py:28-156`, `src/content_creation/generation/script.py:22-110`, `src/content_creation/generation/carousel.py:20-95`, `src/content_creation/generation/newsletter.py:18-90`, `src/content_creation/generation/thumbnail.py:18-80`
  - Supporting utilities & platform plumbing: `src/content_creation/prompts/registry.py:8-25`, `src/content_creation/shared/enums.py:8-15`

---

### Stage 7: Review
- **Entrypoints:**
  - CLI: `review-assets` (`src/content_creation/cli.py:145`, dispatch: `src/content_creation/cli.py:983-1116`), `batch-approve` (`src/content_creation/cli.py:93`, dispatch: `src/content_creation/cli.py:409-431`)
  - UI: `3_brief_viewer.py` (Brief decision), `4_storyboard.py` (Storyboard decision), `5_asset_workshop.py` (Asset decision)
  - Services:
    - `BriefReviewService.apply_decision` (`src/content_creation/application/brief_review_service.py:63` `def apply_decision(self, ctx: ApplicationContext, topic_id: str, decision: BriefDecision) -> BriefReviewResult:`)
    - `StoryboardReviewService.apply_decision` (`src/content_creation/application/storyboard_review_service.py:63` `def apply_decision(self, ctx: ApplicationContext, topic_id: str, decision: StoryboardDecision) -> StoryboardReviewResult:`)
    - `AssetReviewService.apply_decisions` (`src/content_creation/application/asset_review_service.py:109` `def apply_decisions(self, ctx: ApplicationContext, topic_id: str, decisions: List[AssetDecision]) -> ReviewResult:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `BriefDecision` (`src/content_creation/application/brief_review_service.py:25`), `StoryboardDecision` (`src/content_creation/application/storyboard_review_service.py:25`), `AssetDecision` (`src/content_creation/application/asset_review_service.py:24`)
  - Upstream disk artifact or SQLite source: Target asset JSON in `data/briefs/`, `data/storyboards/`, `data/scripts/`, `data/carousels/`, `data/newsletters/`, `data/thumbnails/`
  - Required fields & invariants: Target artifact must exist; `decision.status` must be a member of `ReviewStatus`.
- **Exact Output Contract:**
  - Returned Python type: `ReviewResult` (`src/content_creation/application/asset_review_service.py:33`), `BriefReviewResult`, `StoryboardReviewResult`
  - Written disk path or SQLite table: Updated asset JSON file with modified `review_status` / `review_notes`; audit history entry written to `data/review_history/<topic_id>.json` (`src/content_creation/storage/local.py:228`)
  - Emitted domain events: `review.submitted` via `create_review_event` (`src/content_creation/events/factory.py:45`)
- **Validation, Guard & Gate Checkpoints:**
  - State machine transition check: Validated by `ReviewTransitionEngine.validate_transition(from_status, to_status)` (`src/content_creation/workflow/review_transition_engine.py:133`).
  - Terminal state guard: If current state is `APPROVED` or `REJECTED`, transition is rejected (`src/content_creation/workflow/review_transition_engine.py:102-105`).
  - Rejection note invariant: Rejection requires explanatory notes.
- **Conditional Branches & Failure Modes:**
  - Auto-approve branch: CLI `--auto-approve` flag or `batch-approve` transitions all eligible `DRAFT` assets to `APPROVED` directly.
  - Partial batch failure: When processing multiple decisions, invalid transitions are rejected individually while valid transitions commit.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/workflow/review_transition_engine.py:112-165`, `src/content_creation/application/asset_review_service.py:42-195`
  - Supporting utilities & platform plumbing: `src/content_creation/models/review_history.py:12-38`, `src/content_creation/audit/service.py:18-65`

---

### Stage 8: Manifest
- **Entrypoints:**
  - CLI: `build-manifest` (`src/content_creation/cli.py:105`, dispatch: `src/content_creation/cli.py:622-644`) and `build-all-manifests` (`src/content_creation/cli.py:109`, dispatch: `src/content_creation/cli.py:646-665`)
  - UI: `5_asset_workshop.py` (`src/content_creation/ui/pages/5_asset_workshop.py:168`)
  - Service: `ManifestBuilder.build` (`src/content_creation/manifest.py:48` `def build(self, topic_id: str, topic_title: str, source_url: str) -> TopicManifest:`) and `build_all` (`src/content_creation/manifest.py:128` `def build_all(self) -> List[TopicManifest]:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `topic_id: str`, `topic_title: str`, `source_url: str`
  - Upstream disk artifact or SQLite source: `Brief` and asset files on disk (`data/briefs/`, `data/thumbnails/`, `data/scripts/`, `data/carousels/`, `data/newsletters/`)
  - Required fields & invariants: Brief must exist for `topic_id`.
- **Exact Output Contract:**
  - Returned Python type: `TopicManifest` (`src/content_creation/models/manifest.py:23` `class TopicManifest(BaseModel):`)
  - Written disk path or SQLite table: `data/manifests/<topic_id>.json` via `LocalStorage.save_manifest` (`src/content_creation/storage/local.py:180`)
  - Emitted domain events: `manifest.built` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Planner readiness gate: `ready_for_planner` computed boolean (`src/content_creation/manifest.py:92-108`). Requires:
    - Brief exists and `review_status == "approved"`
    - Thumbnail exists and `review_status == "approved"`
    - Every format in `recommended_formats` exists and has `review_status == "approved"`
    - No missing assets and `len(blocking_reasons) == 0`
  - Status classification: Categorized as `"complete"`, `"partial"`, or `"blocked"`.
- **Conditional Branches & Failure Modes:**
  - Missing asset handling: Asset marked with `status: "missing"`, reason appended to `blocking_reasons`.
  - Stale manifest rebuild: Rebuilds manifest cleanly from current filesystem state.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/manifest.py:22-215`
  - Supporting utilities & platform plumbing: `src/content_creation/models/manifest.py:10-31`, `src/content_creation/storage/local.py:177-188`

---

### Stage 9: Planning
- **Entrypoints:**
  - CLI: `plan-week` (`src/content_creation/cli.py:112`, dispatch: `src/content_creation/cli.py:667-748`)
  - UI: `2_topic_pipeline.py` (Schedule view)
  - Service: `PostingPlanner.plan_week` (`src/content_creation/planning/planner.py:45` `def plan_week(self, week_start: datetime.date) -> WeeklyCalendar:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `week_start: datetime.date`, `config/publishing.yaml` loaded at `src/content_creation/workflow/workflow_action_executor.py:680`
  - Upstream disk artifact or SQLite source: `TopicManifest` files from `data/manifests/*.json` where `ready_for_planner == True` via `LocalStorage.list_manifests` (`src/content_creation/storage/local.py:184`)
  - Required fields & invariants: `week_start` must represent a valid Monday; scheduling slots defined in `publishing.yaml`.
- **Exact Output Contract:**
  - Returned Python type: `WeeklyCalendar` (`src/content_creation/models/calendar.py:23` `class WeeklyCalendar(BaseModel):`)
  - Written disk path or SQLite table: `data/calendars/<week_start>.json` via `LocalStorage.save_calendar` (`src/content_creation/storage/local.py:195`)
  - Emitted domain events: `calendar.created` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Manifest completeness gate: Filters manifests strictly by `manifest.ready_for_planner is True` (`src/content_creation/planning/planner.py:64`).
  - Slot allocation rules: Disperses formats across target posting days according to `publishing.yaml` slots.
  - Unique topic per day: Ensures no topic is posted twice on the same day.
- **Conditional Branches & Failure Modes:**
  - Under-supply fallback: If fewer approved manifests exist than available schedule slots, fills available slots and logs a warning without crashing (`src/content_creation/planning/planner.py:82`).
  - Date normalization: If `week_start` is omitted in CLI, computes next upcoming Monday (`src/content_creation/cli.py:676-683`).
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/planning/planner.py:25-145`
  - Supporting utilities & platform plumbing: `src/content_creation/workflow/workflow_action_executor.py:678-685`, `src/content_creation/models/calendar.py:7-32`

---

### Stage 10: Dry Run
- **Entrypoints:**
  - CLI: `dry-run` (`src/content_creation/cli.py:120`, dispatch: `src/content_creation/cli.py:750-833`)
  - UI: `2_topic_pipeline.py` (Dry-run validation panel)
  - Service: `DryRunValidator.run` (`src/content_creation/planning/dryrun.py:21` `def run(self, calendar: WeeklyCalendar) -> DryRunReport:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `WeeklyCalendar` (`src/content_creation/models/calendar.py:23`)
  - Upstream disk artifact or SQLite source: `data/calendars/<week_start>.json` via `LocalStorage.get_calendar` (`src/content_creation/storage/local.py:191`)
  - Required fields & invariants: `WeeklyCalendar.posts` must contain scheduled entries.
- **Exact Output Contract:**
  - Returned Python type: `DryRunReport` (`src/content_creation/models/dryrun.py:18` `class DryRunReport(BaseModel):`)
  - Written disk path or SQLite table: `data/dryruns/<week_start>.json` via `LocalStorage.save_dryrun` (`src/content_creation/storage/local.py:210`), optional Markdown report export via `DryRunValidator.export_markdown` (`src/content_creation/planning/dryrun.py:137`)
  - Emitted domain events: `dryrun.completed` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Physical file existence check: Validates that `Path(post.asset_path).exists()` holds true on disk for every scheduled post (`src/content_creation/planning/dryrun.py:45`).
  - Approval verification check: Inspects actual asset JSON to ensure `review_status == "approved"`.
  - Blocked invariant: Any missing file immediately sets `is_ready = False` and increments `blocked_count` (`src/content_creation/planning/dryrun.py:58`).
- **Conditional Branches & Failure Modes:**
  - Warning assignment: If asset exists on disk but review status is `needs_review` or `draft`, sets `warning_count += 1` with an actionable recommendation.
  - Missing calendar handling: If calendar does not exist for `week_start`, CLI reports error and exits with non-zero code.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/planning/dryrun.py:18-150`
  - Supporting utilities & platform plumbing: `src/content_creation/models/dryrun.py:8-30`, `src/content_creation/storage/local.py:207-215`

---

### Stage 11: Analytics
- **Entrypoints:**
  - CLI: `init-analytics` (`src/content_creation/cli.py:128`, dispatch: `src/content_creation/cli.py:835-870`) and `update-analytics` (`src/content_creation/cli.py:136`, dispatch: `src/content_creation/cli.py:872-981`)
  - UI: `6_operations_dashboard.py` (`src/content_creation/ui/pages/6_operations_dashboard.py:220`)
  - Service: `WorkflowActionExecutor._dispatch_to_service` handling `init_analytics` (`src/content_creation/workflow/workflow_action_executor.py:699-724`) and `update_analytics` (`src/content_creation/workflow/workflow_action_executor.py:726-748`)
- **Exact Input Contract:**
  - Python / Pydantic types: `WeeklyCalendar` (`src/content_creation/models/calendar.py:23`), `PostAnalytics` (`src/content_creation/models/analytics.py:21`), `post_id: str`, `metrics: Dict[str, Any]`
  - Upstream disk artifact or SQLite source: `data/calendars/<week_start>.json` and `data/analytics/<post_id>.json`
  - Required fields & invariants: `post_id` format `<topic_id>_<format>_<week_start>`.
- **Exact Output Contract:**
  - Returned Python type: `PostAnalytics` (`src/content_creation/models/analytics.py:21` `class PostAnalytics(BaseModel):`)
  - Written disk path or SQLite table: `data/analytics/<post_id>.json` via `LocalStorage.save_analytics` (`src/content_creation/storage/local.py:225`)
  - Emitted domain events: `analytics.updated` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Record initialization check: Calendar must exist for `week_start`.
  - Update precondition: Target analytics record must exist in storage; raises `ValueError` if missing (`src/content_creation/workflow/workflow_action_executor.py:732`).
- **Conditional Branches & Failure Modes:**
  - Idempotency skip: During initialization, if `ctx.storage.get_analytics(post_id)` is not None, record creation is skipped (`src/content_creation/workflow/workflow_action_executor.py:710-711`).
  - Partial metrics update: Dynamically sets provided numeric performance metrics (`views_24h`, `reach_24h`, `saves`, `comments`, `cta_clicks`) without wiping unmentioned fields (`src/content_creation/workflow/workflow_action_executor.py:740-744`).
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/workflow/workflow_action_executor.py:699-748`
  - Supporting utilities & platform plumbing: `src/content_creation/models/analytics.py:7-35`, `src/content_creation/storage/local.py:218-226`

---

### Stage 12: Event Store
- **Entrypoints:**
  - CLI: `event-timeline` (`src/content_creation/cli.py:149`), `event-stats` (`src/content_creation/cli.py:157`), `event-replay` (`src/content_creation/cli.py:160`), `event-cleanup` (`src/content_creation/cli.py:169`)
  - UI: `6_operations_dashboard.py` (Timeline tab)
  - Service / Repository: `SQLiteEventRepository` (`src/content_creation/events/store/sqlite_repository.py:18` `class SQLiteEventRepository:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `EventEnvelope` (`src/content_creation/events/models.py:24`), `EventRecord` (`src/content_creation/events/store/models.py:18`)
  - Upstream disk artifact or SQLite source: In-flight domain events dispatched via `InMemoryEventBus` (`src/content_creation/events/bus.py:16`)
  - Required fields & invariants: `id: UUID`, `event_name: str`, `category: str`, `created_at: datetime`, `version: int`.
- **Exact Output Contract:**
  - Returned Python type: `EventRecord` (`src/content_creation/events/store/models.py:18`), `List[EventRecord]`
  - Written disk path or SQLite table: Table `events` in `data/events.db` initialized via `init_event_store_schema` (`src/content_creation/events/store/schema.py:9` `CREATE TABLE IF NOT EXISTS events`)
  - Emitted domain events: Replayed events re-emitted onto event bus during replay (`src/content_creation/events/store/replay.py:25`).
- **Validation, Guard & Gate Checkpoints:**
  - Database PRAGMA: Enforces `PRAGMA journal_mode=WAL` (`src/content_creation/events/store/schema.py:37`).
  - Primary key uniqueness: `INSERT OR IGNORE INTO events` ensures absolute idempotency on duplicate `id` (`src/content_creation/events/store/sqlite_repository.py:86`).
- **Conditional Branches & Failure Modes:**
  - Query filtering: Supports query by category, correlation ID, entity type, entity ID, time range, and pagination.
  - Replay dry-run: `event-replay --dry-run` inspects events without publishing to bus.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/events/store/sqlite_repository.py:18-235`, `src/content_creation/events/store/replay.py:15-80`
  - Supporting utilities & platform plumbing: `src/content_creation/events/store/schema.py:9-45`, `src/content_creation/events/bus.py:16-95`

---

### Stage 13: Metrics
- **Entrypoints:**
  - CLI: `metrics-kpi` (`src/content_creation/cli.py:174`), `metrics-summary` (`src/content_creation/cli.py:177`), `metrics-query` (`src/content_creation/cli.py:180`), `metrics-cleanup` (`src/content_creation/cli.py:185`), `metrics-rebuild` (`src/content_creation/cli.py:188`)
  - UI: `6_operations_dashboard.py` (Telemetry & KPIs tab)
  - Service / Repository: `SQLiteMetricRepository` (`src/content_creation/metrics/sqlite_repository.py:18` `class SQLiteMetricRepository:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `MetricRecord` (`src/content_creation/metrics/models.py:25`), `MetricType` (`counter`, `gauge`, `histogram`, `timer`)
  - Upstream disk artifact or SQLite source: Real-time telemetry emissions and event store records
  - Required fields & invariants: `metric_name: str`, `metric_type: MetricType`, `value: float`, `timestamp: datetime`.
- **Exact Output Contract:**
  - Returned Python type: `MetricRecord`, aggregated `Dict[str, float]`
  - Written disk path or SQLite table: Table `metrics` in `data/metrics.db` (`src/content_creation/metrics/schema.py:9` `CREATE TABLE IF NOT EXISTS metrics`)
  - Emitted domain events: None (leaf consumer of event bus telemetry).
- **Validation, Guard & Gate Checkpoints:**
  - Database PRAGMA: Enforces `PRAGMA journal_mode=WAL` (`src/content_creation/metrics/schema.py:36`).
  - Aggregation gates: Supported aggregations `sum`, `avg`, `min`, `max`, `count` (`src/content_creation/metrics/sqlite_repository.py:180-195`).
- **Conditional Branches & Failure Modes:**
  - Retention purging: `delete_expired(before: datetime)` deletes points past retention threshold.
  - Event rebuild: `rebuild_metrics_from_events` wipes metrics table and reconstructs all telemetry from event store.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/metrics/sqlite_repository.py:18-305`, `src/content_creation/metrics/kpi.py:15-95`
  - Supporting utilities & platform plumbing: `src/content_creation/metrics/schema.py:9-45`, `src/content_creation/metrics/models.py:10-45`

---

### Stage 14: Audit
- **Entrypoints:**
  - CLI: `audit-query` (`src/content_creation/cli.py:192`), `audit-entity` (`src/content_creation/cli.py:203`), `audit-actor` (`src/content_creation/cli.py:208`), `audit-report` (`src/content_creation/cli.py:212`), `audit-rebuild` (`src/content_creation/cli.py:215`)
  - UI: `6_operations_dashboard.py` (Audit Trail & Compliance tab)
  - Service / Repository: `SQLiteAuditRepository` (`src/content_creation/audit/sqlite_repository.py:18` `class SQLiteAuditRepository:`), `AuditComplianceService` (`src/content_creation/audit/compliance.py:20`)
- **Exact Input Contract:**
  - Python / Pydantic types: `AuditRecord` (`src/content_creation/audit/models.py:25` `class AuditRecord(BaseModel):`)
  - Upstream disk artifact or SQLite source: State mutation events and explicit audit entries
  - Required fields & invariants: `audit_id: UUID`, `action: str`, `actor_type: AuditActorType`, `actor_id: str`, `severity: AuditSeverity`, `timestamp: datetime`.
- **Exact Output Contract:**
  - Returned Python type: `AuditRecord`, `AuditComplianceReport` (`src/content_creation/audit/compliance.py:35`)
  - Written disk path or SQLite table: Table `audit` in `data/audit.db` (`src/content_creation/audit/schema.py:9` `CREATE TABLE IF NOT EXISTS audit`)
  - Emitted domain events: `audit.record_created` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Non-repudiation invariants: Actor ID, severity level (`INFO`, `WARNING`, `ERROR`, `CRITICAL`), and source category enforced.
  - WAL journal mode: Enforced on connection initialization (`src/content_creation/audit/schema.py:44`).
- **Conditional Branches & Failure Modes:**
  - Rebuild from events: Reconstructs audit history by scanning event records.
  - Report types: Generates compliance reports for `operator`, `decision`, `job`, `incident`, and `summary`.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/audit/sqlite_repository.py:18-285`, `src/content_creation/audit/compliance.py:20-140`
  - Supporting utilities & platform plumbing: `src/content_creation/audit/schema.py:9-50`, `src/content_creation/audit/models.py:10-55`

---

### Stage 15: Jobs & Locks
- **Entrypoints:**
  - CLI: Internal worker daemon / CLI status monitoring
  - UI: `6_operations_dashboard.py` (Background Jobs & Locks tab)
  - Service / Engines: `QueueEngine` (`src/content_creation/jobs/queue_engine.py:31` `class QueueEngine:`), `LockManager` (`src/content_creation/jobs/lock_manager.py:11` `class LockManager:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `Job` (`src/content_creation/jobs/models.py:25`), `ResourceLock` (`src/content_creation/jobs/lock_models.py:17`), `JobSubmissionResult` (`src/content_creation/jobs/queue_engine.py:15`)
  - Upstream disk artifact or SQLite source: Task payloads, SQLite tables `jobs` and `locks` in `data/jobs.db`
  - Required fields & invariants: Unique `job_id`, `job_type`, `priority`, target resource identifier, valid correlation ID.
- **Exact Output Contract:**
  - Returned Python type: `Job`, `ResourceLock`
  - Written disk path or SQLite table: Tables `jobs` and `locks` in `data/jobs.db` (`src/content_creation/jobs/schema.py:17, 89`)
  - Emitted domain events: `job.enqueued`, `job.started`, `job.completed`, `job.failed`, `lock.acquired`, `lock.released` (`src/content_creation/events/models.py:12`)
- **Validation, Guard & Gate Checkpoints:**
  - Exclusivity lock gate: Lock acquisition fails with `ResourceLockedException` if resource is already held by another active job (`src/content_creation/jobs/lock_manager.py:35`).
  - Heartbeat freshness check: Locks must be heartbeaten within timeout threshold; stale locks released by `release_stale_locks` (`src/content_creation/jobs/lock_manager.py:129`).
- **Conditional Branches & Failure Modes:**
  - Exponential backoff retry: When a job fails, `QueueEngine.schedule_retry` schedules next attempt with `delay = base_delay * (2 ** retry_count)` (`src/content_creation/jobs/queue_engine.py:134`).
  - Worker death recovery: Handled by `RecoverySupervisor` (`src/content_creation/jobs/recovery_supervisor.py:18`), recovering orphaned running jobs.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/jobs/queue_engine.py:31-295`, `src/content_creation/jobs/lock_manager.py:11-140`, `src/content_creation/jobs/recovery_supervisor.py:18-115`
  - Supporting utilities & platform plumbing: `src/content_creation/jobs/schema.py:9-115`, `src/content_creation/jobs/sqlite_repository.py:18-260`, `src/content_creation/jobs/sqlite_lock_repository.py:18-190`

---

### Stage 16: Notifications & SSE Streaming
- **Entrypoints:**
  - CLI: Internal streaming daemon
  - UI: `ui/components/notification_panel.py` (`src/content_creation/ui/components/notification_panel.py:10`)
  - Service / Server: `NotificationService` (`src/content_creation/notifications/service.py:28` `class NotificationService:`), `NotificationSSEServer` (`src/content_creation/notifications/streaming/server.py:254` `class NotificationSSEServer:`)
- **Exact Input Contract:**
  - Python / Pydantic types: `Notification` (`src/content_creation/notifications/models.py:23`), `NotificationFilter` (`src/content_creation/notifications/query.py:15`)
  - Upstream disk artifact or SQLite source: Table `notifications` in `data/notifications.db` (`src/content_creation/notifications/schema.py:16`), stream publisher (`src/content_creation/notifications/streaming/publisher.py:19`)
  - Required fields & invariants: `notification_id: UUID`, `title: str`, `category: NotificationCategory`, `status: NotificationStatus` (`unread`, `read`, `archived`).
- **Exact Output Contract:**
  - Returned Python type: `Notification`, `NotificationPage`, `NotificationSummary`
  - Written disk path or SQLite table: SQLite table `notifications` in `data/notifications.db`
  - Emitted network payload: SSE HTTP streaming data `event: <category>\ndata: <json>\n\n` on TCP socket (default port 18503).
- **Validation, Guard & Gate Checkpoints:**
  - Connection management: Handled via `SSEConnectionManager` (`src/content_creation/notifications/streaming/connection_manager.py:20`) enforcing client limits and keep-alive heartbeats (15s intervals).
  - WAL journal mode: Enforced on `data/notifications.db` (`src/content_creation/notifications/schema.py:11`).
- **Conditional Branches & Failure Modes:**
  - Client disconnection: Gracefully removes broken socket from connection set without server abort (`src/content_creation/notifications/streaming/connection_manager.py:65`).
  - Port fallback: Configurable port binding; fallback error handling if socket binding fails.
- **Core Logic vs. Supporting Utilities:**
  - Core domain / service code: `src/content_creation/notifications/service.py:28-230`, `src/content_creation/notifications/streaming/server.py:254-340`, `src/content_creation/notifications/streaming/connection_manager.py:20-145`
  - Supporting utilities & platform plumbing: `src/content_creation/notifications/schema.py:9-45`, `src/content_creation/notifications/sqlite_repository.py:18-240`
