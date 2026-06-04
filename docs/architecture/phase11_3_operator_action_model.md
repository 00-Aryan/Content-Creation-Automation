# Phase 11.3 — Operator Action Model

**Date:** 2026-06-04
**Status:** COMPLETE
**Scope:** Canonical operator action architecture for the Content Creation Factory

---

## 1. Executive Summary

This document defines every action an operator (human, UI, background job, or automation engine) can perform on the content-creation pipeline. It provides:

- Complete inventory of 18 operator-facing actions
- Canonical `OperatorAction` data model
- Preconditions, outcomes, and event mapping for each action
- Automation classification for future job system integration

---

## 2. Action Inventory

### 2.1 Primary Operator Actions

| # | action_id | Action Name | Category | CLI Command | Description |
|---|-----------|-------------|----------|-------------|-------------|
| A01 | `collect` | Collect Topics | GENERATION | `collect` | Ingest topics from configured feed sources |
| A02 | `score_topics` | Score Topics | GENERATION | `score-topics` | Score and validate staged topics |
| A03 | `generate_briefs` | Generate Briefs | GENERATION | `generate-briefs` | Generate educational briefs via Gemini |
| A04 | `generate_ci` | Generate Content Intelligence | GENERATION | (pipeline only) | Generate CI analysis via Gemini |
| A05 | `generate_storyboards` | Generate Storyboards | GENERATION | (pipeline only) | Generate storyboards via Gemini |
| A06 | `generate_assets` | Generate Assets | GENERATION | `generate-assets` | Generate thumbnails, scripts, carousels, newsletters |
| A07 | `review_brief` | Review Brief | REVIEW | (service only) | Load brief for operator review |
| A08 | `approve_brief` | Approve Brief | APPROVAL | (service only) | Set brief status to APPROVED |
| A09 | `reject_brief` | Reject Brief | APPROVAL | (service only) | Set brief status to REJECTED |
| A10 | `review_storyboard` | Review Storyboard | REVIEW | (service only) | Load storyboard for operator review |
| A11 | `approve_storyboard` | Approve Storyboard | APPROVAL | (service only) | Set storyboard status to APPROVED |
| A12 | `reject_storyboard` | Reject Storyboard | APPROVAL | (service only) | Set storyboard status to REJECTED |
| A13 | `review_assets` | Review Assets | REVIEW | `review-assets` | Load reviewable assets for a topic |
| A14 | `approve_asset` | Approve Asset | APPROVAL | `review-assets` | Set individual asset status to APPROVED |
| A15 | `reject_asset` | Reject Asset | APPROVAL | `review-assets` | Set individual asset status to REJECTED |
| A16 | `batch_approve` | Batch Approve | APPROVAL | `batch-approve` | Approve all pending assets across topics |
| A17 | `build_manifest` | Build Manifest | ORCHESTRATION | `build-manifest` | Compute manifest for a single topic |
| A18 | `build_all_manifests` | Build All Manifests | ORCHESTRATION | `build-all-manifests` | Compute manifests for all topics |
| A19 | `plan_week` | Plan Week | PLANNING | `plan-week` | Generate 7-day content calendar |
| A20 | `dry_run` | Dry Run | VALIDATION | `dry-run` | Validate planned calendar for publishing readiness |
| A21 | `init_analytics` | Initialize Analytics | SYSTEM | `init-analytics` | Create PostAnalytics records from calendar |
| A22 | `update_analytics` | Update Analytics | SYSTEM | `update-analytics` | Update performance metrics for a post |
| A23 | `run_pipeline` | Run Pipeline | ORCHESTRATION | `run-pipeline` | Execute full end-to-end pipeline |

### 2.2 Read-Only / Observation Actions

| # | action_id | Action Name | Category | CLI Command | Description |
|---|-----------|-------------|----------|-------------|-------------|
| R01 | `get_status` | Get Status | SYSTEM | `status` | Display system status |
| R02 | `list_topics` | List Topics | SYSTEM | `list-topics` | List staged topics |
| R03 | `validate_items` | Validate Items | VALIDATION | `validate-items` | Validate staged items against schema |
| R04 | `review_scores` | Review Scores | SYSTEM | `review-scores` | Display scored topics with flags |
| R05 | `scoring_dashboard` | Scoring Dashboard | SYSTEM | `scoring-dashboard` | Display aggregate scoring metrics |
| R06 | `get_review_history` | Get Review History | SYSTEM | (service only) | Retrieve audit trail for a topic |
| R07 | `get_all_history` | Get All History | SYSTEM | (service only) | Retrieve complete audit trail |

---

## 3. Action Categories

| Category | Count | Description | Typical Lifecycle |
|----------|-------|-------------|-------------------|
| **GENERATION** | 6 | Create new artifacts from upstream data + LLM | Seconds to minutes (LLM-dependent) |
| **REVIEW** | 3 | Load artifacts for operator inspection | Instant (read-only) |
| **APPROVAL** | 6 | Change artifact review_status (approve/reject) | Instant (file write) |
| **ORCHESTRATION** | 4 | Multi-step coordination (pipeline, manifests) | Seconds to minutes |
| **PLANNING** | 1 | Content calendar generation | Seconds |
| **VALIDATION** | 3 | Pre-publish checks and schema validation | Seconds |
| **SYSTEM** | 7 | Analytics, observation, status reporting | Instant |

---

## 4. OperatorAction Model

### 4.1 Schema Definition

```python
@dataclass(frozen=False)
class OperatorAction:
    """Canonical record of an operator action.

    Every action that mutates system state produces an OperatorAction
    record. Read-only actions (R01-R07) do NOT produce records.
    """

    action_id: str                    # Unique action identifier (e.g., "approve_brief")
    action_type: ActionType           # GENERATION | REVIEW | APPROVAL | ORCHESTRATION | PLANNING | VALIDATION | SYSTEM
    target_artifact_type: str         # Artifact type affected (e.g., "brief", "storyboard", "manifest")
    target_artifact_id: str           # Topic ID or post ID (e.g., "abc123", "abc123_short_video_2026-06-09")
    initiated_at: str                 # ISO-8601 UTC timestamp
    completed_at: Optional[str]       # ISO-8601 UTC timestamp, None if in progress
    result: ActionResult              # SUCCESS | FAILURE | SKIPPED | PARTIAL
    error_message: Optional[str]      # Error details if result=FAILURE
    notes: Optional[str]              # Operator notes (e.g., rejection reason)
    metadata: dict[str, str]          # Additional context (e.g., {"top_n": "5", "source": "arxiv"})
```

### 4.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action_id` | `str` | Yes | Unique identifier from §2.1 inventory (e.g., `"approve_brief"`) |
| `action_type` | `ActionType` | Yes | Category enum: `GENERATION`, `REVIEW`, `APPROVAL`, `ORCHESTRATION`, `PLANNING`, `VALIDATION`, `SYSTEM` |
| `target_artifact_type` | `str` | Yes | Primary artifact type affected: `"topic"`, `"brief"`, `"content_intelligence"`, `"storyboard"`, `"script"`, `"carousel"`, `"newsletter"`, `"thumbnail"`, `"manifest"`, `"calendar"`, `"dryrun"`, `"analytics"` |
| `target_artifact_id` | `str` | Yes | Topic ID (SHA256 hash) or post ID for analytics |
| `initiated_at` | `str` | Yes | ISO-8601 UTC timestamp when action started |
| `completed_at` | `str \| None` | No | ISO-8601 UTC timestamp when action finished; `None` if in progress |
| `result` | `ActionResult` | Yes | Outcome: `SUCCESS`, `FAILURE`, `SKIPPED`, `PARTIAL` |
| `error_message` | `str \| None` | No | Error details when `result=FAILURE` |
| `notes` | `str \| None` | No | Free-text operator notes (rejection reasons, observations) |
| `metadata` | `dict[str, str]` | No | Key-value pairs for context (CLI flags, counts, configuration) |

### 4.3 Supporting Enums

```python
class ActionType(str, Enum):
    GENERATION = "generation"
    REVIEW = "review"
    APPROVAL = "approval"
    ORCHESTRATION = "orchestration"
    PLANNING = "planning"
    VALIDATION = "validation"
    SYSTEM = "system"

class ActionResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    PARTIAL = "partial"      # Some items succeeded, some failed
```

---

## 5. Action Preconditions

For every action, the required lifecycle state (from `ArtifactLifecycleState`) and forbidden states are defined.

### 5.1 Generation Actions

#### A01 — collect

```
TYPE: GENERATION
TARGET: TopicItem

REQUIRED STATE: None (always available)
FORBIDDEN STATE: None
DEPENDENCY: config/feeds.yaml must exist and have enabled sources

PRECONDITIONS:
  - At least one feed source enabled in config/feeds.yaml

RESULT ON EXECUTION:
  - New TopicItem files created in data/staging/
  - Each TopicItem: status=RAW
```

#### A02 — score_topics

```
TYPE: GENERATION
TARGET: ScoredTopicItem

REQUIRED STATE: TopicItem with status=RAW or STAGED in data/staging/
FORBIDDEN STATE: None
DEPENDENCY: data/staging/*.json must exist, config/scoring.yaml must exist

PRECONDITIONS:
  - At least one staged TopicItem exists
  - Scoring config present

RESULT ON EXECUTION:
  - ScoredTopicItem files created in data/scored/
  - Topic status transitions: RAW/STAGED → SCORED or REJECTED
```

#### A03 — generate_briefs

```
TYPE: GENERATION
TARGET: Brief

REQUIRED STATE: ScoredTopicItem with status=SCORED
FORBIDDEN STATE: None (existing brief = skip, not block)
DEPENDENCY: data/scored/*.json, GEMINI_API_KEY, prompts/brief/*

PRECONDITIONS:
  - At least one ScoredTopicItem with status=SCORED exists
  - ScoredTopicItem.raw_text ≥ 100 chars
  - No existing Brief file for the topic (skip if exists)

RESULT ON EXECUTION:
  - Brief file created with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)
```

#### A04 — generate_ci

```
TYPE: GENERATION
TARGET: ContentIntelligence

REQUIRED STATE: Brief (any review_status)
FORBIDDEN STATE: None (no brief = skip)
DEPENDENCY: data/briefs/*.json, GEMINI_API_KEY, prompts/content_intelligence/*

PRECONDITIONS:
  - At least one Brief exists in storage
  - Workflow stage "content_intelligence" not completed (or artifact missing)

QUALITY GATE (soft):
  - evaluate_brief_quality(brief) → READY | DEGRADED | BLOCKED
  - BLOCKED → stub CI with all needs_review fields (no LLM call)
  - DEGRADED → CI with reduced quality
  - READY → full CI generation

RESULT ON EXECUTION:
  - ContentIntelligence file created with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)
```

#### A05 — generate_storyboards

```
TYPE: GENERATION
TARGET: Storyboard

REQUIRED STATE: Brief (HARD), ContentIntelligence (any status)
FORBIDDEN STATE: Brief missing = HARD FAIL (StoryboardFailure)
DEPENDENCY: data/briefs/*.json, data/content_intelligence/*.json, GEMINI_API_KEY

PRECONDITIONS:
  - Brief exists for topic (HARD dependency)
  - At least one ContentIntelligence exists in storage

RESULT ON EXECUTION:
  - Storyboard file created with deterministic + LLM fields
  - review_status=DRAFT (success) or NEEDS_REVIEW (fallback)
```

#### A06 — generate_assets

```
TYPE: GENERATION
TARGET: Thumbnail | Script | Carousel | Newsletter

REQUIRED STATE: Storyboard (HARD), Brief (HARD)
FORBIDDEN STATE: Storyboard missing = ValueError (aborts entire run)
DEPENDENCY: data/briefs/*.json, data/storyboards/*.json, GEMINI_API_KEY

PRECONDITIONS:
  - Storyboard exists for topic (HARD — raises ValueError if missing)
  - Brief exists for topic
  - Brief.recommended_formats determines which format-specific assets to generate
  - Thumbnail is always generated

RESULT ON EXECUTION:
  - Thumbnail always created
  - Script created if recommended_formats maps to "short_video"
  - Carousel created if recommended_formats maps to "carousel"
  - Newsletter created if recommended_formats maps to "newsletter"
  - Each: review_status=DRAFT (success) or NEEDS_REVIEW (fallback)
```

### 5.2 Review Actions

#### A07 — review_brief

```
TYPE: REVIEW
TARGET: Brief

REQUIRED STATE: Brief exists with review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: Brief missing (file not found)
DEPENDENCY: data/briefs/<topic_id>.json

PRECONDITIONS:
  - Brief file exists on disk

OUTPUT:
  - BriefReviewItem (topic_id, status, review_notes, why_it_matters, student_takeaway, summary)
```

#### A10 — review_storyboard

```
TYPE: REVIEW
TARGET: Storyboard

REQUIRED STATE: Storyboard exists with review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: Storyboard missing (file not found)
DEPENDENCY: data/storyboards/<topic_id>.json

PRECONDITIONS:
  - Storyboard file exists on disk

OUTPUT:
  - StoryboardReviewItem (topic_id, status, review_notes, visual_style, visual_metaphor, formats_planned)
```

#### A13 — review_assets

```
TYPE: REVIEW
TARGET: Multiple assets (script, carousel, newsletter, thumbnail)

REQUIRED STATE: Manifest exists, at least one asset file exists
FORBIDDEN STATE: Manifest missing
DEPENDENCY: data/manifests/<topic_id>.json, asset files

PRECONDITIONS:
  - Manifest file exists for topic
  - At least one asset file exists with status NOT in {skipped, missing}

OUTPUT:
  - List[AssetReviewItem] (asset_type, status, summary_text, content)
```

### 5.3 Approval Actions

#### A08 — approve_brief

```
TYPE: APPROVAL
TARGET: Brief

REQUIRED STATE: review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: APPROVED (already terminal), REJECTED (terminal)
DEPENDENCY: Brief file exists

STATE CHANGE:
  review_status → APPROVED
  review_notes → updated (if provided)

EVENTS: brief_approved
```

#### A09 — reject_brief

```
TYPE: APPROVAL
TARGET: Brief

REQUIRED STATE: review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: APPROVED (terminal), REJECTED (already terminal)
DEPENDENCY: Brief file exists

STATE CHANGE:
  review_status → REJECTED
  review_notes → updated (if provided)

EVENTS: brief_rejected
```

#### A11 — approve_storyboard

```
TYPE: APPROVAL
TARGET: Storyboard

REQUIRED STATE: review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: APPROVED, REJECTED
DEPENDENCY: Storyboard file exists

STATE CHANGE:
  review_status → APPROVED
  review_notes → updated (if provided)

EVENTS: storyboard_approved
```

#### A12 — reject_storyboard

```
TYPE: APPROVAL
TARGET: Storyboard

REQUIRED STATE: review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: APPROVED, REJECTED
DEPENDENCY: Storyboard file exists

STATE CHANGE:
  review_status → REJECTED
  review_notes → updated (if provided)

EVENTS: storyboard_rejected
```

#### A14 — approve_asset

```
TYPE: APPROVAL
TARGET: Individual asset (script, carousel, newsletter, thumbnail)

REQUIRED STATE: review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: APPROVED, REJECTED
DEPENDENCY: Asset file exists

STATE CHANGE:
  review_status → APPROVED

EVENTS: asset_approved (with asset_type in metadata)
POST-ACTION: ManifestBuilder rebuilds manifest for topic
```

#### A15 — reject_asset

```
TYPE: APPROVAL
TARGET: Individual asset (script, carousel, newsletter, thumbnail)

REQUIRED STATE: review_status ∈ {DRAFT, NEEDS_REVIEW, REVIEWED}
FORBIDDEN STATE: APPROVED, REJECTED
DEPENDENCY: Asset file exists

STATE CHANGE:
  review_status → REJECTED

EVENTS: asset_rejected (with asset_type in metadata)
POST-ACTION: ManifestBuilder rebuilds manifest for topic
```

#### A16 — batch_approve

```
TYPE: APPROVAL
TARGET: All non-terminal assets across all topics

REQUIRED STATE: At least one asset with review_status ∉ {APPROVED, REJECTED}
FORBIDDEN STATE: None (skips terminal assets)
DEPENDENCY: Asset files exist in data/briefs, data/scripts, data/carousels, data/newsletters, data/thumbnails

STATE CHANGE:
  All non-APPROVED/non-REJECTED assets: review_status → APPROVED
  All manifests rebuilt

EVENTS: batch_approved (with count in metadata)
NOTE: Does NOT record ReviewHistoryEntry (audit trail gap — INC-05)
```

### 5.4 Orchestration Actions

#### A17 — build_manifest

```
TYPE: ORCHESTRATION
TARGET: TopicManifest

REQUIRED STATE: Brief exists for topic
FORBIDDEN STATE: None (builds from current state regardless)
DEPENDENCY: All asset files for topic

PRECONDITIONS:
  - Brief file exists (for recommended_formats extraction)

RESULT ON EXECUTION:
  - Manifest file created/updated with:
    - overall_status: complete | partial | blocked
    - ready_for_planner: True only if ALL non-skipped assets approved
    - blocking_reasons: lists missing, rejected, needs_review assets
```

#### A18 — build_all_manifests

```
TYPE: ORCHESTRATION
TARGET: All TopicManifests

REQUIRED STATE: At least one Brief exists
FORBIDDEN STATE: None
DEPENDENCY: All briefs and asset files

RESULT ON EXECUTION:
  - One manifest per topic with a brief
  - Same computation as A17 for each
```

#### A23 — run_pipeline

```
TYPE: ORCHESTRATION
TARGET: Full pipeline (all artifacts)

REQUIRED STATE: None (pipeline manages its own prerequisites)
FORBIDDEN STATE: None
DEPENDENCY: All config files, GEMINI_API_KEY

STAGES (sequential, each requires prior success):
  1. collect → TopicItems
  2. score → ScoredTopicItems
  3. generate-briefs → Briefs
  4. generate-ci → ContentIntelligence
  5. generate-storyboards → Storyboards
  6. generate-assets → Assets
  7. build-manifests → Manifests
  8. batch-approve (conditional: --auto-approve) → Approved assets

POST-PIPELINE (inline in CLI):
  9. plan-week → Calendar
  10. dry-run → DryRunReport
  11. init-analytics → Analytics records

RESULT ON EXECUTION:
  - Pipeline log written to data/logs/
  - Calendar, dry-run report, analytics created
```

### 5.5 Planning Actions

#### A19 — plan_week

```
TYPE: PLANNING
TARGET: WeeklyCalendar

REQUIRED STATE: At least one manifest with ready_for_planner=True
FORBIDDEN STATE: No ready manifests (returns empty calendar)
DEPENDENCY: data/manifests/*.json, config/publishing.yaml

SCHEDULING RULES:
  - max_same_topic_per_week: 2
  - min_days_between_same_topic: 2
  - No same format on consecutive days
  - Maximum 7 posts per week
  - Asset file must exist on disk at manifest path

RESULT ON EXECUTION:
  - Calendar JSON and markdown written to data/calendars/
```

### 5.6 Validation Actions

#### A20 — dry_run

```
TYPE: VALIDATION
TARGET: DryRunReport

REQUIRED STATE: WeeklyCalendar exists with at least one post
FORBIDDEN STATE: Empty calendar
DEPENDENCY: Calendar JSON, all scheduled asset files

CHECKS PER POST:
  1. Asset file exists at scheduled path
  2. JSON parseable
  3. review_status == "approved"

CLASSIFICATION PER POST:
  - ready: file exists AND review_status=approved
  - warning: file exists AND review_status ∈ {draft, needs_review, reviewed}
  - blocked: file missing OR review_status ∈ {rejected, error, missing}

RECOMMENDED ACTIONS:
  - has_draft → "Run review-assets for topics with draft assets"
  - has_needs_review → "Review and approve needs_review assets"
  - has_rejected → "Regenerate rejected assets"
  - has_missing → "Run generation commands for missing assets"
  - none → "All assets ready — safe to publish"

RESULT ON EXECUTION:
  - DryRunReport JSON and markdown written to data/dryruns/
```

### 5.7 System Actions

#### A21 — init_analytics

```
TYPE: SYSTEM
TARGET: PostAnalytics

REQUIRED STATE: WeeklyCalendar exists with posts
FORBIDDEN STATE: None (skips existing records)
DEPENDENCY: data/calendars/<week_start>.json

RESULT ON EXECUTION:
  - PostAnalytics JSON files created for each post (skips existing)
  - post_id format: {topic_id}_{format}_{week_start}
```

#### A22 — update_analytics

```
TYPE: SYSTEM
TARGET: PostAnalytics

REQUIRED STATE: PostAnalytics record exists
FORBIDDEN STATE: None (interactive prompt)
DEPENDENCY: data/analytics/<post_id>.json

FIELDS UPDATED (interactive):
  - views_24h, views_7d, views_30d
  - reach_24h, reach_7d
  - saves, comments, cta_clicks
  - watch_time_pct (video only)
  - posted_at, notes

RESULT ON EXECUTION:
  - PerformanceSnapshot updated
  - last_updated timestamp refreshed
```

---

## 6. Action Outcomes

### 6.1 State Changes Summary

| Action | From State | To State | Artifact |
|--------|-----------|----------|----------|
| A01 collect | — | RAW | TopicItem |
| A02 score_topics | RAW/STAGED | SCORED or REJECTED | ScoredTopicItem |
| A03 generate_briefs | — | DRAFT or NEEDS_REVIEW | Brief |
| A04 generate_ci | — | DRAFT or NEEDS_REVIEW | ContentIntelligence |
| A05 generate_storyboards | — | DRAFT or NEEDS_REVIEW | Storyboard |
| A06 generate_assets | — | DRAFT or NEEDS_REVIEW | Thumbnail/Script/Carousel/Newsletter |
| A08 approve_brief | DRAFT/NEEDS_REVIEW/REVIEWED | APPROVED | Brief |
| A09 reject_brief | DRAFT/NEEDS_REVIEW/REVIEWED | REJECTED | Brief |
| A11 approve_storyboard | DRAFT/NEEDS_REVIEW/REVIEWED | APPROVED | Storyboard |
| A12 reject_storyboard | DRAFT/NEEDS_REVIEW/REVIEWED | REJECTED | Storyboard |
| A14 approve_asset | DRAFT/NEEDS_REVIEW/REVIEWED | APPROVED | Asset |
| A15 reject_asset | DRAFT/NEEDS_REVIEW/REVIEWED | REJECTED | Asset |
| A16 batch_approve | DRAFT/NEEDS_REVIEW/REVIEWED | APPROVED | All assets |
| A17 build_manifest | (computed) | complete/partial/blocked | Manifest |
| A18 build_all_manifests | (computed) | complete/partial/blocked | All Manifests |
| A19 plan_week | (computed) | (computed) | Calendar |
| A20 dry_run | (computed) | (computed) | DryRunReport |
| A21 init_analytics | — | initialized | PostAnalytics |
| A22 update_analytics | initialized | updated | PostAnalytics |

### 6.2 Artifacts Produced Per Action

| Action | Artifacts Created | Artifacts Modified |
|--------|------------------|-------------------|
| A01 collect | TopicItem | — |
| A02 score_topics | ScoredTopicItem | — |
| A03 generate_briefs | Brief | — |
| A04 generate_ci | ContentIntelligence | — |
| A05 generate_storyboards | Storyboard | — |
| A06 generate_assets | Thumbnail, Script, Carousel, Newsletter | — |
| A08 approve_brief | — | Brief (review_status) |
| A09 reject_brief | — | Brief (review_status) |
| A11 approve_storyboard | — | Storyboard (review_status) |
| A12 reject_storyboard | — | Storyboard (review_status) |
| A14 approve_asset | — | Asset (review_status) |
| A15 reject_asset | — | Asset (review_status) |
| A16 batch_approve | — | All assets (review_status) |
| A17 build_manifest | Manifest | — |
| A18 build_all_manifests | All Manifests | — |
| A19 plan_week | Calendar | — |
| A20 dry_run | DryRunReport | — |
| A21 init_analytics | PostAnalytics | — |
| A22 update_analytics | — | PostAnalytics (metrics) |

---

## 7. Event Mapping

Every mutating action should emit events for the future notification system (Phase 11.8).

### 7.1 Event Definitions

| Action | Event Name | Payload |
|--------|-----------|---------|
| A01 collect | `topics_collected` | `{count, source}` |
| A02 score_topics | `topics_scored` | `{count, scored_count, rejected_count}` |
| A03 generate_briefs | `briefs_generated` | `{count, skipped_count, failure_count}` |
| A04 generate_ci | `ci_generated` | `{count, skipped_count, failure_count}` |
| A05 generate_storyboards | `storyboards_generated` | `{count, skipped_count, failure_count}` |
| A06 generate_assets | `assets_generated` | `{count, thumbnail_count, script_count, carousel_count, newsletter_count}` |
| A08 approve_brief | `brief_approved` | `{topic_id, previous_status}` |
| A09 reject_brief | `brief_rejected` | `{topic_id, previous_status, reason}` |
| A11 approve_storyboard | `storyboard_approved` | `{topic_id, previous_status}` |
| A12 reject_storyboard | `storyboard_rejected` | `{topic_id, previous_status, reason}` |
| A14 approve_asset | `asset_approved` | `{topic_id, asset_type, previous_status}` |
| A15 reject_asset | `asset_rejected` | `{topic_id, asset_type, previous_status, reason}` |
| A16 batch_approve | `batch_approved` | `{approved_count, skipped_count}` |
| A17 build_manifest | `manifest_built` | `{topic_id, overall_status, ready_for_planner}` |
| A18 build_all_manifests | `manifests_built` | `{count, complete_count, partial_count, blocked_count}` |
| A19 plan_week | `week_planned` | `{week_start, post_count, format_counts}` |
| A20 dry_run | `dry_run_completed` | `{week_start, ready_count, warning_count, blocked_count}` |
| A21 init_analytics | `analytics_initialized` | `{week_start, post_count}` |
| A22 update_analytics | `analytics_updated` | `{post_id, fields_updated}` |
| A23 run_pipeline | `pipeline_completed` | `{stages_executed, success, duration_seconds}` |

### 7.2 Event Delivery Modes

| Mode | Description | Suitable Actions |
|------|-------------|-----------------|
| **Synchronous** | Emit immediately after action completes | A08, A09, A11, A12, A14, A15 |
| **Batch** | Emit after batch operation completes | A01, A02, A03, A04, A05, A06, A16, A18 |
| **Deferred** | Emit after pipeline stage completes | A23 (per-stage events) |
| **Observational** | No event (read-only) | R01-R07, A17, A19, A20 |

---

## 8. Automation Classification

### 8.1 Background-Job Suitable Actions

| Action | Can Queue? | Can Retry? | Idempotent? | Notes |
|--------|-----------|-----------|-------------|-------|
| A01 collect | Yes | Yes | Yes (skips duplicates) | Safe to run on schedule |
| A02 score_topics | Yes | Yes | Yes (overwrites) | Safe to run on schedule |
| A03 generate_briefs | Yes | Yes | Yes (skips existing) | LLM rate limits apply |
| A04 generate_ci | Yes | Yes | Yes (skips existing) | LLM rate limits apply |
| A05 generate_storyboards | Yes | Yes | Yes (skips existing) | LLM rate limits apply |
| A06 generate_assets | Yes | Yes | Yes (skips existing) | LLM rate limits apply |
| A16 batch_approve | Yes | No (state-dependent) | No (sets terminal) | One-shot operation |
| A17 build_manifest | Yes | Yes | Yes (overwrites) | Safe to rerun |
| A18 build_all_manifests | Yes | Yes | Yes (overwrites) | Safe to rerun |
| A19 plan_week | Yes | Yes | No (overwrites calendar) | Consider versioning |
| A20 dry_run | Yes | Yes | Yes (overwrites report) | Read-heavy but safe |
| A21 init_analytics | Yes | Yes | Yes (skips existing) | Safe to rerun |

### 8.2 Operator-Only Actions (Cannot Queue)

| Action | Reason |
|--------|--------|
| A08 approve_brief | Requires human judgment |
| A09 reject_brief | Requires human judgment |
| A11 approve_storyboard | Requires human judgment |
| A12 reject_storyboard | Requires human judgment |
| A14 approve_asset | Requires human judgment |
| A15 reject_asset | Requires human judgment |
| A22 update_analytics | Requires real-world data input |
| A23 run_pipeline | Complex orchestration with rate limits |

### 8.3 Retry Mechanisms

| Failure Type | Retry Strategy | Max Retries | Backoff |
|-------------|---------------|-------------|---------|
| LLM API error (429) | Exponential backoff | 3 | 5s, 15s, 45s |
| LLM API error (500) | Exponential backoff | 3 | 10s, 30s, 90s |
| LLM parse failure | Fallback artifact | 0 | None (immediate fallback) |
| File I/O error | No retry | 0 | None |
| Missing dependency | No retry | 0 | Skip topic |

---

## 9. Future Job System Integration

### 9.1 Job Model (Phase 11.7)

```python
@dataclass
class Job:
    job_id: str                      # UUID
    action: OperatorAction           # The action being executed
    status: JobStatus                # PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
    created_at: str                  # ISO-8601 UTC
    started_at: Optional[str]        # ISO-8601 UTC
    completed_at: Optional[str]      # ISO-8601 UTC
    progress: Optional[int]          # 0-100 percentage
    result: Optional[ActionResult]   # SUCCESS | FAILURE | SKIPPED | PARTIAL
    error_message: Optional[str]     # Error details
    retry_count: int                 # Current retry attempt
    max_retries: int                 # Maximum allowed retries

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 9.2 Job Queue Architecture

```
Operator CLI / UI
       │
       ▼
  ActionRegistry ──► validates preconditions
       │
       ▼
  JobQueue ──► persists Job record
       │
       ▼
  WorkerPool ──► executes action
       │
       ├──► Success → Job.status=COMPLETED → Event emitted
       │
       └──► Failure → Job.status=FAILED → Retry? → Event emitted
```

### 9.3 Integration Points

| Phase | Component | Consumes From This Phase |
|-------|-----------|------------------------|
| 11.4 | Action Registry | Action inventory (§2), preconditions (§5) |
| 11.5 | Action Availability Engine | Preconditions (§5), lifecycle states (§6) |
| 11.6 | UI Workflow Guidance | Action categories (§3), outcomes (§6) |
| 11.7 | Job Tracking | Job model (§9.1), automation classification (§8) |
| 11.8 | Notifications | Event mapping (§7), delivery modes (§7.2) |

---

## Appendix A: Complete Action Reference

| ID | Action | Category | Mutating? | Queueable? | Retryable? | Idempotent? |
|----|--------|----------|-----------|-----------|-----------|-------------|
| A01 | collect | GENERATION | Yes | Yes | Yes | Yes |
| A02 | score_topics | GENERATION | Yes | Yes | Yes | Yes |
| A03 | generate_briefs | GENERATION | Yes | Yes | Yes | Yes |
| A04 | generate_ci | GENERATION | Yes | Yes | Yes | Yes |
| A05 | generate_storyboards | GENERATION | Yes | Yes | Yes | Yes |
| A06 | generate_assets | GENERATION | Yes | Yes | Yes | Yes |
| A07 | review_brief | REVIEW | No | No | — | — |
| A08 | approve_brief | APPROVAL | Yes | No | No | No |
| A09 | reject_brief | APPROVAL | Yes | No | No | No |
| A10 | review_storyboard | REVIEW | No | No | — | — |
| A11 | approve_storyboard | APPROVAL | Yes | No | No | No |
| A12 | reject_storyboard | APPROVAL | Yes | No | No | No |
| A13 | review_assets | REVIEW | No | No | — | — |
| A14 | approve_asset | APPROVAL | Yes | No | No | No |
| A15 | reject_asset | APPROVAL | Yes | No | No | No |
| A16 | batch_approve | APPROVAL | Yes | Yes | No | No |
| A17 | build_manifest | ORCHESTRATION | Yes | Yes | Yes | Yes |
| A18 | build_all_manifests | ORCHESTRATION | Yes | Yes | Yes | Yes |
| A19 | plan_week | PLANNING | Yes | Yes | Yes | No |
| A20 | dry_run | VALIDATION | Yes | Yes | Yes | Yes |
| A21 | init_analytics | SYSTEM | Yes | Yes | Yes | Yes |
| A22 | update_analytics | SYSTEM | Yes | No | No | No |
| A23 | run_pipeline | ORCHESTRATION | Yes | No | Partial | No |
| R01 | get_status | SYSTEM | No | — | — | — |
| R02 | list_topics | SYSTEM | No | — | — | — |
| R03 | validate_items | VALIDATION | No | — | — | — |
| R04 | review_scores | SYSTEM | No | — | — | — |
| R05 | scoring_dashboard | SYSTEM | No | — | — | — |
| R06 | get_review_history | SYSTEM | No | — | — | — |
| R07 | get_all_history | SYSTEM | No | — | — | — |
