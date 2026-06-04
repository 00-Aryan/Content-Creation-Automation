# Phase 11.1 — Workflow State Architecture Audit

**Date:** 2026-06-04
**Status:** COMPLETE
**Scope:** Authoritative workflow architecture contract for the Content Ingestion & Synthesis Factory

---

## 1. Executive Summary

### Purpose of Workflow Architecture

This audit defines the authoritative workflow architecture contract for the Content-Creation factory. It establishes artifact lifecycle states, operator and service responsibilities, dependency contracts, action ownership, workflow constraints, approval gates, and future extensibility boundaries.

The resulting document becomes the foundation for Phase 11.2–11.8 (dependency matrix, operator state model, next action engine, action availability rules, job tracking, notifications).

### Current System Maturity

The system has completed Weeks 1–4 of the roadmap:

- **Ingestion:** RSS/arXiv collectors → `TopicItem` normalization → staged storage
- **Scoring:** `ScoringEngine` + `ValidationEngine` → `ScoredTopicItem`
- **Brief Generation:** Gemini-backed `generate_brief()` → `Brief` artifacts
- **Content Intelligence:** `ContentIntelligenceGenerator` → `ContentIntelligence` artifacts
- **Storyboard:** `StoryboardGenerator` → `Storyboard` artifacts
- **Asset Generation:** Script, Carousel, Newsletter, Thumbnail generators → content assets
- **Manifest System:** `ManifestBuilder` → per-topic asset readiness tracking
- **Posting Planner:** `PostingPlanner` → 7-day calendar from approved manifests
- **Dry-Run Validation:** `DryRunValidator` → pre-publish readiness reports
- **Analytics:** `PostAnalytics` → post-level performance placeholders
- **Workflow Resumability:** `WorkflowStateManager` → file-based stage tracking

125 tests pass. All generators follow the shared retry/LLM pattern. Review history is append-only.

### Operator-Console Scope

The operator console (Phase 11+) will be a CLI-first interface for single operators. It provides:

- Artifact review workflows (approve/reject/skip)
- Pipeline orchestration with visibility into stage status
- Calendar planning and dry-run validation
- Analytics initialization and updates

### Single-Operator Assumptions

- One operator runs the pipeline at a time
- No concurrent review conflicts
- No role-based access control (RBAC)
- No multi-tenant isolation
- Operator actions are synchronous (CLI-driven)
- Future multi-operator support requires locking, RBAC, and conflict resolution

---

## 2. Workflow Ownership Model

### Topic Collection

| Role | Owner |
|------|-------|
| **Producer** | `Collectors` (RSS, arXiv, Manual) |
| **Consumer** | `ScoringEngine` |
| **Owner** | System |
| **Reviewer** | None |

### Topic Scoring

| Role | Owner |
|------|-------|
| **Producer** | `ScoringEngine` + `ValidationEngine` |
| **Consumer** | `BriefGenerationService` |
| **Owner** | System |
| **Reviewer** | Operator (via `review-scores` CLI) |

### Brief

| Role | Owner |
|------|-------|
| **Producer** | `BriefGenerationService` (via `generate_brief()`) |
| **Consumer** | `ContentIntelligenceService`, `StoryboardService`, `AssetGenerationService`, `ManifestBuilder` |
| **Owner** | System (generation) / Operator (approval) |
| **Reviewer** | Operator (via `review-assets` CLI or `BriefReviewService`) |

### Content Intelligence

| Role | Owner |
|------|-------|
| **Producer** | `ContentIntelligenceService` (via `ContentIntelligenceGenerator`) |
| **Consumer** | `StoryboardService` |
| **Owner** | System (generation) / Operator (approval) |
| **Reviewer** | Operator (via `review-assets` CLI) |

### Storyboard

| Role | Owner |
|------|-------|
| **Producer** | `StoryboardService` (via `StoryboardGenerator`) |
| **Consumer** | `AssetGenerationService` (all 4 generators) |
| **Owner** | System (generation) / Operator (approval) |
| **Reviewer** | Operator (via `review-assets` CLI or `StoryboardReviewService`) |

### Assets (Script, Carousel, Newsletter, Thumbnail)

| Role | Owner |
|------|-------|
| **Producer** | `AssetGenerationService` (ScriptGenerator, CarouselGenerator, NewsletterGenerator, ThumbnailGenerator) |
| **Consumer** | `ManifestBuilder`, `PostingPlanner` |
| **Owner** | System (generation) / Operator (approval) |
| **Reviewer** | Operator (via `review-assets` CLI or `AssetReviewService`) |

### Manifest

| Role | Owner |
|------|-------|
| **Producer** | `ManifestBuilder` |
| **Consumer** | `PostingPlanner`, `DryRunValidator` |
| **Owner** | System |
| **Reviewer** | None (derived from asset statuses) |

### Weekly Calendar

| Role | Owner |
|------|-------|
| **Producer** | `PostingPlanner` |
| **Consumer** | `DryRunValidator`, Analytics initialization |
| **Owner** | System |
| **Reviewer** | Operator (via `plan-week` CLI output) |

### Dry-Run Report

| Role | Owner |
|------|-------|
| **Producer** | `DryRunValidator` |
| **Consumer** | Operator (CLI output) |
| **Owner** | System |
| **Reviewer** | Operator (reads report) |

### Post Analytics

| Role | Owner |
|------|-------|
| **Producer** | Analytics initialization (from calendar) |
| **Consumer** | Operator (manual updates) |
| **Owner** | Operator |
| **Reviewer** | None |

---

## 3. Artifact Lifecycle Definitions

### 3.1 TopicItem

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **RAW** | Initial extraction from source, unvalidated | Collected from RSS/arXiv/manual | Passes schema validation |
| **STAGED** | Normalized, saved to `data/staged/` | Passes `TopicItem` Pydantic validation | Submitted to scoring engine |
| **SCORED** | Has `priority_score` and scoring metadata | `ScoredTopicItem` created by `ScoringEngine` | Operator review or brief generation |
| **APPROVED** | Operator-approved for content generation | Operator sets status via review | Brief generation initiated |
| **REJECTED** | Failed hard filters or low score | Hard filter triggered or operator rejection | Archived (no further processing) |
| **REVIEW** | Pending human review | Operator flags for review | Operator approves or rejects |

### 3.2 Brief

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **DRAFT** | Initial state from generator | `generate_brief()` succeeds | Operator reviews |
| **NEEDS_REVIEW** | Flagged for operator review | Generator fallback or operator flag | Operator approves or rejects |
| **REVIEWED** | Intermediate review state | Operator marks as reviewed | Operator approves or rejects |
| **APPROVED** | Ready for CI/storyboard generation | Operator approves | Downstream services consume |
| **REJECTED** | Needs regeneration | Operator rejects | Re-generation or archival |

### 3.3 Content Intelligence

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **DRAFT** | Initial state from generator | `ContentIntelligenceGenerator` succeeds | Operator reviews |
| **NEEDS_REVIEW** | Quality-degraded or flagged | Brief quality is DEGRADED or BLOCKED | Operator approves or rejects |
| **REVIEWED** | Intermediate review state | Operator marks as reviewed | Operator approves or rejects |
| **APPROVED** | Ready for storyboard generation | Operator approves | `StoryboardService` consumes |
| **REJECTED** | Needs regeneration | Operator rejects | Re-generation or archival |

**Quality Gates (QualityStatus):**
- `READY`: All brief fields present → full CI generation
- `DEGRADED`: Some optional brief fields missing → CI proceeds with reduced quality
- `BLOCKED`: Insufficient brief data → CI produces placeholder `needs_review` artifact

### 3.4 Storyboard

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **DRAFT** | Initial state from generator | `StoryboardGenerator` succeeds | Operator reviews |
| **NEEDS_REVIEW** | Flagged for review | Generation fallback or operator flag | Operator approves or rejects |
| **REVIEWED** | Intermediate review state | Operator marks as reviewed | Operator approves or rejects |
| **APPROVED** | Ready for asset generation | Operator approves | All 4 asset generators consume |
| **REJECTED** | Needs regeneration | Operator rejects | Re-generation or archival |

### 3.5 Content Assets (Script, Carousel, Newsletter, Thumbnail)

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **DRAFT** | Initial state from generator | Generator succeeds | Operator reviews |
| **NEEDS_REVIEW** | Fallback or flagged | LLM parse failure → fallback artifact | Operator approves or rejects |
| **REVIEWED** | Intermediate review state | Operator marks as reviewed | Operator approves or rejects |
| **APPROVED** | Ready for manifest inclusion | Operator approves | `ManifestBuilder` includes in manifest |
| **REJECTED** | Needs regeneration | Operator rejects | Re-generation or archival |

### 3.6 TopicManifest

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **complete** | All non-skipped assets approved | All `AssetEntry.status == "approved"` (non-skipped) | `PostingPlanner` consumes |
| **partial** | Some assets not yet approved | Mixed statuses, no missing/rejected | Operator reviews remaining assets |
| **blocked** | Missing or rejected assets exist | Any `AssetEntry.status == "missing"` or `"rejected"` | Operator resolves blockers |

### 3.7 WeeklyCalendar

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **generated** | Calendar created by planner | At least one manifest with `ready_for_planner == True` | Dry-run validation |

### 3.8 DryRunReport

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **generated** | Validation complete | Calendar exists | Operator reads report |

### 3.9 PostAnalytics

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **initialized** | Record created from calendar | Calendar exists | Operator updates with real metrics |
| **updated** | Real metrics populated | Operator provides data | Ongoing tracking |

### 3.10 WorkflowState (Resumability)

| State | Purpose | Entry Criteria | Exit Criteria |
|-------|---------|----------------|---------------|
| **pending** | Stage not yet attempted | Topic enters pipeline | Generation attempted |
| **completed** | Stage finished successfully | Artifact saved to disk | N/A (terminal) |
| **failed** | Stage errored | Exception during generation | Re-attempt on next run |
| **needs_review** | Stage produced degraded output | Fallback artifact created | Operator review |

---

## 4. Workflow Dependency Architecture

### 4.1 Primary Dependency Chain

```
Collectors (RSS/arXiv/Manual)
    │
    ▼
TopicItem (RAW → STAGED)
    │
    ▼
ScoringEngine + ValidationEngine
    │
    ▼
ScoredTopicItem (SCORED/REJECTED)
    │
    ▼
BriefGenerationService
    │
    ▼
Brief (DRAFT → APPROVED)
    │
    ▼
ContentIntelligenceService
    │
    ▼
ContentIntelligence (DRAFT → APPROVED)
    │
    ▼
StoryboardService
    │
    ▼
Storyboard (DRAFT → APPROVED)
    │
    ├──▶ ThumbnailGenerator ──▶ ThumbnailPrompt
    ├──▶ ScriptGenerator ──▶ Script
    ├──▶ CarouselGenerator ──▶ Carousel
    └──▶ NewsletterGenerator ──▶ Newsletter
              │
              ▼
         ManifestBuilder
              │
              ▼
         TopicManifest (complete/partial/blocked)
              │
              ▼
         PostingPlanner
              │
              ▼
         WeeklyCalendar
              │
              ▼
         DryRunValidator
              │
              ▼
         DryRunReport
              │
              ▼
         PostAnalytics (initialized → updated)
```

### 4.2 Hard Dependencies

| Artifact | Required Before | Dependency Type |
|----------|----------------|-----------------|
| ScoredTopicItem | Brief generation | **Hard** — brief generation fails without scored item |
| Brief | Content Intelligence generation | **Hard** — CI generator requires brief fields |
| Brief | Storyboard generation | **Hard** — storyboard generator requires brief |
| Content Intelligence | Storyboard generation | **Hard** — storyboard generator requires CI hooks |
| Storyboard | All asset generation | **Hard** — `AssetGenerationService` raises `ValueError` if storyboard missing |
| Approved assets | Manifest `ready_for_planner` | **Hard** — manifest logic requires `status == "approved"` |
| Manifest (complete) | Calendar planning | **Hard** — `PostingPlanner` filters on `ready_for_planner == True` |

### 4.3 Soft Dependencies

| Artifact | Optional Before | Dependency Type |
|----------|----------------|-----------------|
| Storyboard | Thumbnail generation | **Soft** — generators accept `Optional[Storyboard]`; fallback to Brief values |
| Storyboard | Script/Carousel/Newsletter generation | **Soft** — generators accept `Optional[Storyboard]`; fallback to Brief values |
| Brief `recommended_formats` | Asset type selection | **Soft** — defaults to `short_video` if unknown format |

### 4.4 Future Dependencies

| Artifact | Future Consumer | Dependency Type |
|----------|----------------|-----------------|
| Approved Calendar | Platform connectors (Twitter, LinkedIn) | **Future** — posting requires approved calendar + assets |
| Post Analytics | Dashboard / reporting | **Future** — analytics aggregation requires populated metrics |
| Storyboard | Multi-format parallel generation | **Future** — may enable concurrent asset generation |
| Content Intelligence | A/B testing hooks | **Future** — CI hooks enable variant testing |

---

## 5. Action Ownership Matrix

### 5.1 Collect Topics

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `collect` CLI) |
| **Validator** | `IngestionEngine` (schema validation) |
| **Executor** | `CollectTopicsService` |

### 5.2 Score Topics

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `score-topics` CLI) |
| **Validator** | `ValidationEngine` (post-scoring checks) |
| **Executor** | `ScoreTopicsService` |

### 5.3 Review Scores

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `review-scores` CLI) |
| **Validator** | System (display only) |
| **Executor** | Operator (mental review) |

### 5.4 Generate Brief

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `generate-briefs` CLI) or `PipelineRunService` |
| **Validator** | Pydantic model validation + Gemini API |
| **Executor** | `BriefGenerationService` → `generate_brief()` |

### 5.5 Generate Content Intelligence

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via pipeline) or `PipelineRunService` |
| **Validator** | `evaluate_brief_quality()` + Pydantic model |
| **Executor** | `ContentIntelligenceService` → `ContentIntelligenceGenerator` |

### 5.6 Generate Storyboard

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via pipeline) or `PipelineRunService` |
| **Validator** | Pydantic model + dependency check (brief + CI required) |
| **Executor** | `StoryboardService` → `StoryboardGenerator` |

### 5.7 Generate Assets

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `generate-assets` CLI) or `PipelineRunService` |
| **Validator** | Pydantic model + dependency check (storyboard required) |
| **Executor** | `AssetGenerationService` → individual generators |

### 5.8 Review Brief

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `review-assets` CLI or `BriefReviewService`) |
| **Validator** | `BriefReviewService` (transition rules) |
| **Executor** | `BriefReviewService.apply_decision()` |

### 5.9 Review Storyboard

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `review-assets` CLI or `StoryboardReviewService`) |
| **Validator** | `StoryboardReviewService` (transition rules) |
| **Executor** | `StoryboardReviewService.apply_decision()` |

### 5.10 Review Assets (Multi-type)

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `review-assets` CLI) |
| **Validator** | `AssetReviewService` (transition rules) |
| **Executor** | `AssetReviewService.apply_decisions()` |

### 5.11 Batch Approve

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `batch-approve` CLI) or `PipelineRunService` |
| **Validator** | System (checks existing status) |
| **Executor** | CLI direct file manipulation + `ManifestBuilder` rebuild |

### 5.12 Build Manifest

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `build-manifest` CLI) or automatic after review |
| **Validator** | `ManifestBuilder` (asset existence + status checks) |
| **Executor** | `ManifestBuilder.build()` |

### 5.13 Plan Week

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `plan-week` CLI) |
| **Validator** | `PostingPlanner` (diversity + scheduling rules) |
| **Executor** | `PostingPlanner.plan_week()` |

### 5.14 Dry Run

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `dry-run` CLI) |
| **Validator** | `DryRunValidator` (approval status checks) |
| **Executor** | `DryRunValidator.run()` |

### 5.15 Initialize Analytics

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `init-analytics` CLI) |
| **Validator** | System (deduplication check) |
| **Executor** | CLI direct `PostAnalytics` creation |

### 5.16 Update Analytics

| Role | Owner |
|------|-------|
| **Initiator** | Operator (via `update-analytics` CLI) |
| **Validator** | System (interactive prompts) |
| **Executor** | CLI direct `PostAnalytics` update |

---

## 6. Workflow Constraints

### 6.1 Current Constraints

| ID | Constraint | Enforced By | Severity |
|----|-----------|-------------|----------|
| C-01 | Brief generation requires `ScoredTopicItem` with status `SCORED` | `BriefGenerationService` filters on `TopicStatus.SCORED` | Hard |
| C-02 | Content Intelligence generation requires a valid `Brief` | `ContentIntelligenceService` loads brief from storage | Hard |
| C-03 | Storyboard generation requires a valid `Brief` + `ContentIntelligence` | `StoryboardService` loads both from storage | Hard |
| C-04 | Asset generation requires a valid `Storyboard` | `AssetGenerationService` raises `ValueError` if missing | Hard |
| C-05 | Manifest `ready_for_planner` requires all non-skipped assets `approved` | `ManifestBuilder` logic | Hard |
| C-06 | Calendar planning requires manifests with `ready_for_planner == True` | `PostingPlanner` filters manifests | Hard |
| C-07 | Dry-run validation checks `review_status == "approved"` for each scheduled asset | `DryRunValidator` | Hard |
| C-08 | Review transitions are recorded in `ReviewHistoryEntry` append-only log | All review services | Hard |
| C-09 | `WorkflowStateManager` tracks 7 fixed stages per topic | `WorkflowState.__post_init__` | Hard |
| C-10 | Topic ID is deterministic SHA256 of URL | `TopicItem.generate_id()` | Hard |
| C-11 | `plain_english_summary` must have exactly 3 items | `Brief` Pydantic validator | Hard |
| C-12 | All timestamps use UTC timezone | `datetime.now(timezone.utc)` convention | Soft |
| C-13 | Missing/unknown fields must be set to `"unknown"` | Schema convention | Soft |
| C-14 | Storyboard hooks override LLM-generated hooks in assets | Generator `model_copy(update={...})` pattern | Hard |

### 6.2 Future Constraints

| ID | Constraint | Phase | Severity |
|----|-----------|-------|----------|
| F-01 | Multi-operator review requires conflict detection | Phase 11+ | Hard |
| F-02 | Platform posting requires approved calendar + all assets | Phase 12+ | Hard |
| F-03 | RBAC enforcement for operator actions | Phase 11+ | Hard |
| F-04 | Concurrent pipeline runs require locking | Phase 11+ | Hard |
| F-05 | Notification delivery requires job tracking | Phase 11.8 | Soft |
| F-06 | Next Action Engine requires dependency graph | Phase 11.4 | Hard |

---

## 7. State Transition Matrix

### 7.1 TopicItem Transitions

```
RAW ──────────▶ STAGED ──────────▶ SCORED ──────────▶ APPROVED
                  │                   │                   │
                  │                   ▼                   │
                  │               REJECTED                │
                  │                                       │
                  └─────────────────▶ REVIEW ◀────────────┘
                                       │
                                  ┌────┴────┐
                                  ▼         ▼
                              APPROVED   REJECTED
```

| From | To | Trigger | Valid |
|------|----|---------|-------|
| RAW | STAGED | Schema validation passes | Yes |
| STAGED | SCORED | `ScoringEngine.score_items()` | Yes |
| STAGED | REJECTED | Hard filter triggered | Yes |
| SCORED | APPROVED | Operator approval | Yes |
| SCORED | REVIEW | Operator flags for review | Yes |
| SCORED | REJECTED | Low score + operator decision | Yes |
| REVIEW | APPROVED | Operator approves | Yes |
| REVIEW | REJECTED | Operator rejects | Yes |
| APPROVED | * | Terminal (brief generation proceeds) | Yes |
| REJECTED | * | Terminal (no further processing) | Yes |

**Invalid Transitions:**
- REJECTED →任何 state (no re-entry)
- RAW → SCORED (must pass through STAGED)
- STAGED → APPROVED (must score first)

### 7.2 Content Artifact Transitions (Brief, CI, Storyboard, Assets)

```
DRAFT ────────▶ NEEDS_REVIEW ────▶ REVIEWED ────▶ APPROVED
                                  │
                                  ▼
                               REJECTED
```

| From | To | Trigger | Valid |
|------|----|---------|-------|
| DRAFT | NEEDS_REVIEW | Generator fallback or operator flag | Yes |
| DRAFT | APPROVED | Operator skips review (auto-approve) | Yes |
| NEEDS_REVIEW | REVIEWED | Operator marks reviewed | Yes |
| NEEDS_REVIEW | APPROVED | Operator approves directly | Yes |
| NEEDS_REVIEW | REJECTED | Operator rejects | Yes |
| REVIEWED | APPROVED | Operator approves | Yes |
| REVIEWED | REJECTED | Operator rejects | Yes |
| APPROVED | * | Terminal (ready for downstream) | Yes |
| REJECTED | * | Terminal (regeneration required) | Yes |

**Invalid Transitions:**
- APPROVED → DRAFT (no reverse)
- REJECTED →任何 state (no re-entry without regeneration)

### 7.3 Manifest Status Transitions

```
partial ◀───▶ complete
  │
  ▼
blocked
```

| From | To | Trigger | Valid |
|------|----|---------|-------|
| partial | complete | All non-skipped assets approved | Yes |
| partial | blocked | Any asset becomes missing/rejected | Yes |
| blocked | partial | Blocker resolved (asset regenerated) | Yes |
| complete | partial | Asset revoked (rejected) | Yes |

### 7.4 WorkflowState Transitions

```
pending ──────▶ completed
  │
  ▼
failed ───────▶ pending (retry)
```

| From | To | Trigger | Valid |
|------|----|---------|-------|
| pending | completed | Artifact saved successfully | Yes |
| pending | failed | Exception during generation | Yes |
| failed | pending | Next pipeline run retries | Yes |
| completed | * | Terminal (skip on re-run) | Yes |

---

## 8. Operator Responsibility Model

### 8.1 Operators ARE Responsible For

| Responsibility | Mechanism |
|---------------|-----------|
| Initiating pipeline stages | CLI commands (`collect`, `score-topics`, `generate-briefs`, etc.) |
| Reviewing artifacts | `review-assets` CLI, `review-scores` CLI |
| Approving content | `batch-approve` CLI, `review-assets` decisions |
| Rejecting content | `review-assets` decisions with reasons |
| Scheduling content | `plan-week` CLI |
| Validating readiness | `dry-run` CLI |
| Updating analytics | `update-analytics` CLI |
| Monitoring pipeline status | `status` CLI, `scoring-dashboard` CLI |

### 8.2 Operators are NOT Responsible For

| Non-Responsibility | Owner |
|-------------------|-------|
| Editing storage directly | System (LocalStorage) |
| Managing filesystem structure | System (LocalStorage) |
| Managing credentials | System (env vars, .env) |
| Orchestrating dependencies manually | System (service layer) |
| Enforcing workflow constraints | System (validation logic) |
| Recording review history | System (append-only log) |
| Persisting workflow state | System (WorkflowStateManager) |
| Rate limiting LLM calls | System (RetryManager) |
| Handling API failures | System (InferenceManager failover) |
| Rebuilding manifests after review | System (ManifestBuilder) |

---

## 9. System Responsibility Model

### 9.1 System IS Responsible For

| Responsibility | Component |
|---------------|-----------|
| Dependency enforcement | Service layer (pre-generation checks) |
| Schema validation | Pydantic models |
| Idempotency | `WorkflowStateManager` skip logic |
| Artifact persistence | `LocalStorage` + `JsonRepository[T]` |
| Execution tracking | `WorkflowStateManager` stage status |
| Rate limiting | `RetryManager` + `time.sleep()` |
| Failover | `InferenceManager` (Gemini → OpenRouter) |
| Review audit trail | `ReviewHistoryEntry` append-only log |
| Manifest computation | `ManifestBuilder` (asset status aggregation) |
| Calendar scheduling | `PostingPlanner` (diversity rules) |
| Pre-publish validation | `DryRunValidator` |
| Divergence detection | Stage completed but file missing → regenerate |
| LLM response caching | `InferenceCache` |
| Prompt template management | `PromptRegistry` |

### 9.2 System is NOT Responsible For

| Non-Responsibility | Owner |
|-------------------|-------|
| Making approval decisions | Operator |
| Overriding reviews | Operator |
| Choosing which topics to process | Operator (via `--top` flag) |
| Deciding publishing schedule | Operator (via config + planner) |
| Interpreting analytics metrics | Operator |
| Content quality judgment | Operator |

---

## 10. Code Smell & Architecture Risk Audit

### 10.1 Duplicated Workflow Rules

| Risk | Severity | Description |
|------|----------|-------------|
| Status enum fragmentation | **High** | `ReviewStatus` (shared/enums.py), `TopicStatus` (models/topic.py), `AssetEntry.status` (Literal), `ArtifactState.status` (string), `TopicManifest.overall_status` (Literal) — five overlapping status systems with no unified state machine |
| Asset status mapping duplication | **Medium** | `FORMAT_TO_ASSET` defined in both `manifest.py` and `asset_generation_service.py` (imported but logically duplicated) |
| Format mapping duplication | **Medium** | `FREETEXT_TO_FORMAT` and `FORMAT_TO_ASSET` duplicated between `manifest.py` and `asset_generation_service.py` |
| Review transition rules scattered | **Medium** | Review logic in `BriefReviewService`, `StoryboardReviewService`, `AssetReviewService`, and `batch-approve` CLI — no single transition rule engine |

### 10.2 UI-Owned Validation

| Risk | Severity | Description |
|------|----------|-------------|
| Batch approve CLI directly manipulates files | **Medium** | `batch-approve` in `cli.py` reads/writes JSON files directly instead of going through a service layer |
| Dry-run reads asset files directly | **Low** | `DryRunValidator` opens asset JSON files directly instead of using `LocalStorage` repository pattern |
| Analytics initialization in CLI | **Low** | `init-analytics` creates `PostAnalytics` objects directly in CLI code |

### 10.3 Hidden State Transitions

| Risk | Severity | Description |
|------|----------|-------------|
| `ScoredTopicItem` auto-sets status | **Medium** | `set_scored_status` validator silently changes RAW/STAGED → SCORED without explicit transition |
| WorkflowState divergence handling | **Low** | Services detect "completed but file missing" and regenerate — this is a hidden recovery path |
| Manifest `needs_review` in blocking_reasons but not in overall_status logic | **Low** | `needs_review` assets contribute to `blocking_reasons` but don't trigger `"blocked"` overall_status |

### 10.4 Inconsistent Review Semantics

| Risk | Severity | Description |
|------|----------|-------------|
| `REVIEWED` status unused in some paths | **Medium** | `batch-approve` skips directly from any status to `approved`, bypassing `REVIEWED` |
| `needs_review` meaning overloaded | **Medium** | Means "generator failed" in fallback path, "operator flagged" in review path, and "quality degraded" in CI quality gate |
| No `REVIEWED` → `DRAFT` transition | **Low** | Once reviewed, cannot revert to draft for re-editing |

### 10.5 Dependency Leakage

| Risk | Severity | Description |
|------|----------|-------------|
| `AssetGenerationService` imports from `manifest.py` | **Low** | `FORMAT_TO_ASSET` and `FREETEXT_TO_FORMAT` imported from manifest module into generation service |
| CLI directly imports domain services | **Low** | `cli.py` imports `PostingPlanner`, `DryRunValidator` directly instead of through application services |
| Storage access patterns inconsistent | **Medium** | Some services use `ctx.storage.get_brief()`, others use `ctx.storage.list_briefs()` + filter |

### 10.6 Service Responsibility Overlap

| Risk | Severity | Description |
|------|----------|-------------|
| `AssetReviewService` vs `batch-approve` CLI | **Medium** | Two paths to approve assets — service-based and CLI-direct — with different behaviors |
| `BriefReviewService` vs `AssetReviewService` | **Low** | Brief has its own review service separate from the general asset review service |
| `StoryboardReviewService` vs `AssetReviewService` | **Low** | Storyboard has its own review service separate from the general asset review service |
| Pipeline orchestration in CLI vs `PipelineRunService` | **Medium** | `run-pipeline` CLI duplicates stage orchestration logic that also exists in `PipelineRunService` |

---

## 11. Future Compatibility Assessment

### 11.1 Phase 11.2 — Dependency Matrix

**Compatibility:** ✅ **READY**

The dependency chain is well-defined and documented in this audit. The `ManifestBuilder` already computes dependency satisfaction via `ready_for_planner`. The `WorkflowStateManager` tracks per-stage completion.

**Required follow-up:** Unify status enums into a single state machine definition.

### 11.2 Phase 11.3 — Operator State Model

**Compatibility:** ⚠️ **NEEDS REMEDIATION**

Current state: Operator responsibilities are implicit in CLI commands. No formal operator state model exists.

**Gaps:**
- No operator session tracking
- No action history per operator
- No ownership assignment for reviews
- Single-operator assumption prevents multi-operator readiness

**Required follow-up:** Define `OperatorAction` model, add operator identity to review history.

### 11.3 Phase 11.4 — Next Action Engine

**Compatibility:** ⚠️ **NEEDS REMEDIATION**

Current state: Next actions are implicit in CLI help text and pipeline stage ordering.

**Gaps:**
- No formal "available actions" computation
- No dependency-aware action recommendation
- No artifact state → action mapping

**Required follow-up:** Build `ActionRegistry` that maps artifact states to available operator actions.

### 11.4 Phase 11.5 — Action Availability Rules

**Compatibility:** ⚠️ **NEEDS REMEDIATION**

Current state: Action availability is hardcoded in CLI argument parsing and service `if` conditions.

**Gaps:**
- No declarative action availability rules
- No rules engine for complex conditions
- Actions like `batch-approve` bypass normal state checks

**Required follow-up:** Define `ActionAvailabilityRule` model with dependency/state/precondition checks.

### 11.5 Phase 11.7 — Job Tracking

**Compatibility:** ⚠️ **NEEDS REMEDIATION**

Current state: `WorkflowStateManager` tracks generation stages but not operator-initiated jobs.

**Gaps:**
- No job ID for operator actions
- No start/end timestamps for CLI commands
- No progress tracking for multi-step operations
- `PipelineRunService` has JSONL logging but no formal job model

**Required follow-up:** Define `Job` model, wrap CLI commands in job lifecycle.

### 11.6 Phase 11.8 — Notifications

**Compatibility:** ⚠️ **NEEDS REMEDIATION**

Current state: All output is CLI stdout. No notification infrastructure.

**Gaps:**
- No event emission from services
- No subscriber model
- No notification channels

**Required follow-up:** Define `WorkflowEvent` model, add event emission to services.

### 11.7 Future RBAC

**Compatibility:** ❌ **NOT READY**

Current state: No operator identity, no roles, no permissions.

**Gaps:**
- No operator authentication
- No role definitions
- No permission checks on actions
- `batch-approve` has no access control

**Required follow-up:** Define RBAC model before multi-operator support.

### 11.8 Future Multi-Operator Support

**Compatibility:** ❌ **NOT READY**

Current state: Single-operator CLI with no concurrency controls.

**Gaps:**
- No file locking for concurrent access
- No conflict detection for simultaneous reviews
- No operator assignment for artifacts
- No work queue for distributed processing

**Required follow-up:** Define concurrency model, add locking, implement operator assignment.

---

## Appendix A: Artifact Storage Map

| Artifact | Storage Path | Repository |
|----------|-------------|------------|
| TopicItem (staged) | `data/staged/{id}.json` | `LocalStorage` |
| ScoredTopicItem | `data/scored/{id}.json` | `LocalStorage` |
| Brief | `data/briefs/{topic_id}.json` | `BriefRepository` |
| Content Intelligence | `data/content_intelligence/{topic_id}.json` | `ContentIntelligenceRepository` |
| Storyboard | `data/storyboards/{topic_id}.json` | `StoryboardRepository` |
| Script | `data/scripts/{topic_id}.json` | `ScriptRepository` |
| Carousel | `data/carousels/{topic_id}.json` | `CarouselRepository` |
| Newsletter | `data/newsletters/{topic_id}.json` | `NewsletterRepository` |
| Thumbnail | `data/thumbnails/{topic_id}.json` | `ThumbnailRepository` |
| Manifest | `data/manifests/{topic_id}.json` | `LocalStorage` |
| Calendar | `data/calendars/{week_start}.json` | `LocalStorage` |
| Dry-Run Report | `data/dryruns/{week_start}.json` | `LocalStorage` |
| Analytics | `data/analytics/{post_id}.json` | `LocalStorage` |
| Workflow State | `data/workflow_state/{topic_id}.json` | `WorkflowStateManager` |
| Review History | `data/review_history/{topic_id}.json` | `LocalStorage` |

## Appendix B: Service Registry

| Service | Module | Dependencies |
|---------|--------|-------------|
| `CollectTopicsService` | `application.collect_topics_service` | `ApplicationContext`, `IngestionEngine` |
| `ScoreTopicsService` | `application.score_topics_service` | `ApplicationContext`, `ScoringEngine`, `ValidationEngine` |
| `BriefGenerationService` | `application.brief_generation_service` | `ApplicationContext`, `generate_brief()` |
| `ContentIntelligenceService` | `application.content_intelligence_service` | `ApplicationContext`, `ContentIntelligenceGenerator` |
| `StoryboardService` | `application.storyboard_service` | `ApplicationContext`, `StoryboardGenerator` |
| `AssetGenerationService` | `application.asset_generation_service` | `ApplicationContext`, all 4 generators |
| `BriefReviewService` | `application.brief_review_service` | `ApplicationContext` |
| `StoryboardReviewService` | `application.storyboard_review_service` | `ApplicationContext` |
| `AssetReviewService` | `application.asset_review_service` | `ApplicationContext`, `ManifestBuilder` |
| `PipelineRunService` | `application.pipeline_run_service` | `ApplicationContext`, all generation + planning services |

## Appendix C: Shared Enum Reference

### ReviewStatus (shared/enums.py)
```
DRAFT = "draft"
NEEDS_REVIEW = "needs_review"
REVIEWED = "reviewed"
APPROVED = "approved"
REJECTED = "rejected"
```

### TopicStatus (models/topic.py)
```
RAW = "raw"
STAGED = "staged"
SCORED = "scored"
APPROVED = "approved"
REJECTED = "rejected"
REVIEW = "review"
```

### ArtifactState.status (workflow/state.py)
```
"pending" | "completed" | "failed" | "needs_review"
```

### AssetEntry.status (models/manifest.py)
```
"draft" | "needs_review" | "reviewed" | "approved" | "rejected" | "missing" | "skipped"
```

### TopicManifest.overall_status (models/manifest.py)
```
"complete" | "partial" | "blocked"
```

### QualityStatus (domains/content_intelligence/quality.py)
```
READY = "ready"
DEGRADED = "degraded"
BLOCKED = "blocked"
```
