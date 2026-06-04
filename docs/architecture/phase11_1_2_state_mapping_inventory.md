# Phase 11.1.2 — Canonical Workflow State Mapping Inventory

**Date:** 2026-06-04
**Status:** COMPLETE
**Scope:** Complete inventory of all status enums, their values, usage locations, semantic meanings, and proposed mapping to `ArtifactLifecycleState`

---

## 1. Executive Summary

The content-creation system has **6 overlapping status systems** with no unified vocabulary. This inventory catalogs every status value, its meaning, where it is used, and how it maps to the new canonical `ArtifactLifecycleState`.

The canonical layer provides a **common language** for future dependency rules, action engines, and notifications without replacing any existing domain-specific enums.

---

## 2. Existing Status Systems

### 2.1 ReviewStatus

**File:** `src/content_creation/shared/enums.py`
**Type:** `str, Enum`
**Scope:** Content artifact review lifecycle (brief, storyboard, script, carousel, newsletter, thumbnail)

| Value | Semantic Meaning |
|-------|-----------------|
| `DRAFT` | Initial state from generator; not yet submitted for review |
| `NEEDS_REVIEW` | Flagged for operator review (fallback, operator flag, or quality gate) |
| `REVIEWED` | Operator has reviewed but not yet decided (intermediate state) |
| `APPROVED` | Operator approved; ready for downstream consumption |
| `REJECTED` | Operator rejected; requires regeneration |

**Usage locations:**
- `Brief.review_status` (models/brief.py)
- `Storyboard.review_status` (domains/storyboard/model.py)
- All asset models (script, carousel, newsletter, thumbnail) via `review_status` field
- `BriefReviewService.apply_decision()` (application/brief_review_service.py)
- `StoryboardReviewService.apply_decision()` (application/storyboard_review_service.py)
- `AssetReviewService.apply_decisions()` (application/asset_review_service.py)
- `batch-approve` CLI (cli.py)
- `ReviewHistoryEntry.new_status` (models/review_history.py)
- `ReviewTransitionEngine` (workflow/review_transition_engine.py)

---

### 2.2 TopicStatus

**File:** `src/content_creation/models/topic.py`
**Type:** `str, Enum`
**Scope:** TopicItem lifecycle from ingestion through approval

| Value | Semantic Meaning |
|-------|-----------------|
| `RAW` | Initial extraction from source; unvalidated |
| `STAGED` | Normalized and saved; ready for scoring |
| `SCORED` | Has priority score and scoring metadata |
| `APPROVED` | Operator-approved for content generation |
| `REJECTED` | Failed hard filters or low score |
| `REVIEW` | Pending human review (between SCORED and APPROVED/REJECTED) |

**Usage locations:**
- `TopicItem.status` (models/topic.py)
- `ScoredTopicItem.set_scored_status()` validator (models/topic.py)
- `CollectTopicsService` sets RAW→STAGED
- `ScoreTopicsService` sets STAGED→SCORED
- `BriefGenerationService` filters on `TopicStatus.SCORED`

---

### 2.3 AssetEntry.status (Manifest-level)

**File:** `src/content_creation/models/manifest.py`
**Type:** `Literal[...]` (not a formal enum)
**Scope:** Per-asset status within a topic manifest

| Value | Semantic Meaning |
|-------|-----------------|
| `"draft"` | Asset exists but not yet reviewed |
| `"needs_review"` | Asset flagged for operator review |
| `"reviewed"` | Asset reviewed but not decided |
| `"approved"` | Asset approved; counted toward manifest completeness |
| `"rejected"` | Asset rejected; blocks manifest completeness |
| `"missing"` | Asset file does not exist (system-computed) |
| `"skipped"` | Asset generation was skipped (system-computed) |

**Usage locations:**
- `TopicManifest.assets` dict values (models/manifest.py)
- `ManifestBuilder.build()` computes from file existence + `review_status`
- `AssetReviewService.get_review_queue()` reads this status
- `DryRunValidator` checks this status for scheduling readiness

---

### 2.4 ArtifactState.status (Workflow Resumability)

**File:** `src/content_creation/workflow/state.py`
**Type:** `str` (plain string field on dataclass)
**Scope:** Per-stage generation tracking for pipeline resumability

| Value | Semantic Meaning |
|-------|-----------------|
| `"pending"` | Stage not yet attempted |
| `"completed"` | Stage finished successfully; artifact saved |
| `"failed"` | Stage errored; may be retried |
| `"needs_review"` | Stage produced degraded output; needs operator review |

**Usage locations:**
- `ArtifactState.status` (workflow/state.py)
- `WorkflowStateManager.mark_completed()` sets `"completed"`
- `WorkflowStateManager.mark_failed()` sets `"failed"`
- `WorkflowStateManager.stage_completed()` checks for `"completed"`

---

### 2.5 TopicManifest.overall_status

**File:** `src/content_creation/models/manifest.py`
**Type:** `Literal[...]` (not a formal enum)
**Scope:** Aggregated manifest readiness status

| Value | Semantic Meaning |
|-------|-----------------|
| `"complete"` | All non-skipped assets are approved |
| `"partial"` | Mixed statuses; no missing/rejected assets |
| `"blocked"` | Missing or rejected assets exist |

**Usage locations:**
- `TopicManifest.overall_status` (models/manifest.py)
- `ManifestBuilder.build()` computes from asset statuses
- `PostingPlanner` filters on `ready_for_planner` (derived from overall_status)
- `DryRunValidator` checks overall_status

---

### 2.6 QualityStatus

**File:** `src/content_creation/domains/content_intelligence/quality.py`
**Type:** `str, Enum`
**Scope:** Brief quality assessment for Content Intelligence generation

| Value | Semantic Meaning |
|-------|-----------------|
| `READY` | All key fields present; full CI generation |
| `DEGRADED` | Some optional fields missing; CI proceeds with reduced quality |
| `BLOCKED` | Insufficient data; CI should not be generated |

**Usage locations:**
- `evaluate_brief_quality()` return value (domains/content_intelligence/quality.py)
- `ContentIntelligenceService` checks quality before generation

---

## 3. Cross-System State Overlap

### 3.1 Value Name Collisions

The same string value appears in multiple systems with different semantics:

| Value | ReviewStatus | TopicStatus | AssetEntry | ArtifactState | Overall |
|-------|-------------|-------------|------------|---------------|---------|
| `"draft"` | Initial review state | — | Asset not reviewed | — | Review |
| `"needs_review"` | Flagged for review | — | Flagged for review | Degraded output | Review |
| `"reviewed"` | Intermediate review | — | Intermediate review | — | Review |
| `"approved"` | Operator approved | Operator approved | Asset approved | — | Review |
| `"rejected"` | Operator rejected | Operator rejected | Asset rejected | — | Review |
| `"pending"` | — | — | — | Not yet attempted | Workflow |
| `"completed"` | — | — | — | Generation done | Workflow |
| `"failed"` | — | — | — | Generation error | Workflow |
| `"missing"` | — | — | File absent | — | Manifest |
| `"skipped"` | — | — | Generation skipped | — | Manifest |

### 3.2 Semantic Clusters

Despite different enum names, the states cluster into 6 semantic groups:

| Cluster | ReviewStatus | TopicStatus | AssetEntry | ArtifactState | Overall |
|---------|-------------|-------------|------------|---------------|---------|
| **Not started** | — | RAW, STAGED | — | PENDING | — |
| **In progress** | DRAFT | SCORED | "draft" | — | PARTIAL |
| **Needs review** | NEEDS_REVIEW | REVIEW | "needs_review" | "needs_review" | — |
| **Reviewed** | REVIEWED | — | "reviewed" | — | — |
| **Approved** | APPROVED | APPROVED | "approved" | COMPLETED | COMPLETE |
| **Rejected/Blocked** | REJECTED | REJECTED | "rejected" | FAILED | BLOCKED |
| **Absent** | — | — | "missing" | — | — |
| **Skipped** | — | — | "skipped" | — | — |

---

## 4. Proposed Canonical State: ArtifactLifecycleState

```python
class ArtifactLifecycleState(str, Enum):
    PENDING = "pending"            # Not yet started or in progress
    DRAFT = "draft"                # Initial artifact from generator
    NEEDS_REVIEW = "needs_review"  # Flagged for operator review
    REVIEWED = "reviewed"          # Reviewed but not decided
    APPROVED = "approved"          # Approved; ready for downstream
    REJECTED = "rejected"          # Rejected; requires regeneration
    MISSING = "missing"            # Artifact file does not exist
    SKIPPED = "skipped"            # Generation was skipped
    FAILED = "failed"              # Generation or processing failed
```

### 4.1 Semantics

| State | Meaning | Terminal? |
|-------|---------|-----------|
| `PENDING` | Artifact not yet started or still in progress; operator action may be needed | No |
| `DRAFT` | Initial artifact produced by generator; not yet submitted for review | No |
| `NEEDS_REVIEW` | Artifact flagged for operator review (fallback, quality gate, or explicit flag) | No |
| `REVIEWED` | Operator has reviewed the artifact but not yet approved/rejected | No |
| `APPROVED` | Operator approved; artifact is consumed by downstream services | Yes |
| `REJECTED` | Operator rejected; requires regeneration or archival | Yes |
| `MISSING` | Artifact file does not exist in storage (system-computed) | Yes |
| `SKIPPED` | Artifact generation was intentionally skipped (system-computed) | Yes |
| `FAILED` | Generation or processing failed with an error | No (retryable) |

---

## 5. Complete Mapping Tables

### 5.1 TopicStatus → ArtifactLifecycleState

| TopicStatus | ArtifactLifecycleState | Rationale |
|-------------|----------------------|-----------|
| `RAW` | `PENDING` | Initial extraction; nothing has happened yet |
| `STAGED` | `PENDING` | Normalized but not scored; still pending |
| `SCORED` | `PENDING` | Scored but not yet generating; still pending |
| `APPROVED` | `APPROVED` | Operator approved for generation |
| `REJECTED` | `REJECTED` | Topic rejected; no further processing |
| `REVIEW` | `NEEDS_REVIEW` | Flagged for human review |

### 5.2 ReviewStatus → ArtifactLifecycleState

| ReviewStatus | ArtifactLifecycleState | Rationale |
|-------------|----------------------|-----------|
| `DRAFT` | `DRAFT` | Direct 1:1 mapping |
| `NEEDS_REVIEW` | `NEEDS_REVIEW` | Direct 1:1 mapping |
| `REVIEWED` | `REVIEWED` | Direct 1:1 mapping |
| `APPROVED` | `APPROVED` | Direct 1:1 mapping |
| `REJECTED` | `REJECTED` | Direct 1:1 mapping |

### 5.3 AssetEntry.status → ArtifactLifecycleState

| AssetEntry.status | ArtifactLifecycleState | Rationale |
|------------------|----------------------|-----------|
| `"draft"` | `DRAFT` | Direct 1:1 mapping |
| `"needs_review"` | `NEEDS_REVIEW` | Direct 1:1 mapping |
| `"reviewed"` | `REVIEWED` | Direct 1:1 mapping |
| `"approved"` | `APPROVED` | Direct 1:1 mapping |
| `"rejected"` | `REJECTED` | Direct 1:1 mapping |
| `"missing"` | `MISSING` | Direct 1:1 mapping |
| `"skipped"` | `SKIPPED` | Direct 1:1 mapping |

### 5.4 ArtifactState.status → ArtifactLifecycleState

| ArtifactState.status | ArtifactLifecycleState | Rationale |
|---------------------|----------------------|-----------|
| `"pending"` | `PENDING` | Direct 1:1 mapping |
| `"completed"` | `APPROVED` | Completed generation = ready for review/approval pipeline |
| `"failed"` | `FAILED` | Generation error |
| `"needs_review"` | `NEEDS_REVIEW` | Degraded output needs review |

### 5.5 TopicManifest.overall_status → ArtifactLifecycleState

| overall_status | ArtifactLifecycleState | Rationale |
|---------------|----------------------|-----------|
| `"complete"` | `APPROVED` | All assets approved; manifest is complete |
| `"partial"` | `PENDING` | Mixed statuses; still in progress |
| `"blocked"` | `REJECTED` | Blocked by missing/rejected assets |

### 5.6 QualityStatus → ArtifactLifecycleState

| QualityStatus | ArtifactLifecycleState | Rationale |
|--------------|----------------------|-----------|
| `READY` | `APPROVED` | Brief quality is sufficient |
| `DEGRADED` | `NEEDS_REVIEW` | Partial quality; review recommended |
| `BLOCKED` | `REJECTED` | Insufficient data; cannot proceed |

---

## 6. Mapping Rationale Principles

1. **Preserve semantics:** Direct 1:1 mappings where the meaning is identical
2. **Cluster by intent:** States with the same operational intent map to the same lifecycle state
3. **Terminal preservation:** Terminal states in source enums remain terminal in lifecycle
4. **No information loss:** Every source value has exactly one lifecycle target
5. **Forward-looking:** Lifecycle states are designed for dependency rules, not just review

---

## 7. Future Usage

### Phase 11.2 — Dependency Matrix
- Use `ArtifactLifecycleState` to express "depends on APPROVED state"
- Replace scattered string comparisons with canonical state checks

### Phase 11.4 — Next Action Engine
- Query `ArtifactLifecycleState` to determine available actions
- Map lifecycle states to operator action recommendations

### Phase 11.5 — Action Availability Rules
- Define rules in terms of `ArtifactLifecycleState` transitions
- Use `ReviewTransitionEngine` for review-specific transitions

### Phase 11.8 — Notifications
- Emit events based on `ArtifactLifecycleState` changes
- Map lifecycle states to notification templates

---

## 8. Backward Compatibility

- **No existing enums are modified** — all 6 status systems remain intact
- **No persistence changes** — existing JSON files continue to work
- **No service changes** — mappers are pure functions, not integrated yet
- **No behavioral changes** — the canonical layer is additive only

The mapper layer is consumed by future phases when they need to reason about states across domain boundaries.
