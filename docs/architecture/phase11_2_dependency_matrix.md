# Phase 11.2 — Dependency Matrix

**Date:** 2026-06-04
**Status:** COMPLETE
**Scope:** Authoritative workflow dependency specification for the Content Creation Factory

---

## 1. Artifact Inventory

| # | Artifact Type | Storage Path | Creation Service | Review Service | Lifecycle Source |
|---|--------------|-------------|-----------------|---------------|-----------------|
| A1 | **TopicItem** | `data/staged/{id}.json` | `CollectTopicsService` | None (operator via `review-scores`) | `TopicStatus` |
| A2 | **ScoredTopicItem** | `data/scored/{id}.json` | `ScoreTopicsService` | None | `TopicStatus` (auto-set to SCORED) |
| A3 | **Brief** | `data/briefs/{topic_id}.json` | `BriefGenerationService` → `generate_brief()` | `BriefReviewService` | `ReviewStatus` |
| A4 | **ContentIntelligence** | `data/content_intelligence/{topic_id}.json` | `ContentIntelligenceService` → `ContentIntelligenceGenerator` | None (manifest-level) | `ReviewStatus` |
| A5 | **Storyboard** | `data/storyboards/{topic_id}.json` | `StoryboardService` → `StoryboardGenerator` | `StoryboardReviewService` | `ReviewStatus` |
| A6 | **Script** | `data/scripts/{topic_id}.json` | `AssetGenerationService` → `ScriptGenerator` | `AssetReviewService` | `ReviewStatus` |
| A7 | **Carousel** | `data/carousels/{topic_id}.json` | `AssetGenerationService` → `CarouselGenerator` | `AssetReviewService` | `ReviewStatus` |
| A8 | **Newsletter** | `data/newsletters/{topic_id}.json` | `AssetGenerationService` → `NewsletterGenerator` | `AssetReviewService` | `ReviewStatus` |
| A9 | **Thumbnail** | `data/thumbnails/{topic_id}.json` | `AssetGenerationService` → `ThumbnailGenerator` | `AssetReviewService` | `ReviewStatus` |
| A10 | **Manifest** | `data/manifests/{topic_id}.json` | `ManifestBuilder` | None (derived) | `overall_status` Literal |

---

## 2. Dependency Graph

```
                        ┌─────────────────┐
                        │   Collectors    │
                        │  (RSS/arXiv)    │
                        └────────┬────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  ScoredTopicItem (A2)  │
                     │  status=SCORED         │
                     │  raw_text ≥ 100 chars  │
                     └───────────┬───────────┘
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │         Brief (A3)              │
                │  Hard dep: ScoredTopicItem      │
                │  Quality gate: raw_text ≥ 100   │
                │  Fallback: needs_review stub    │
                └───────┬────────────┬───────────┘
                        │            │
          ┌─────────────┘            └──────────────────┐
          ▼                                             ▼
┌──────────────────────┐               ┌────────────────────────────┐
│ ContentIntelligence   │               │   ManifestBuilder (A10)    │
│       (A4)            │               │   Reads brief for formats  │
│ Hard dep: Brief       │               │   Checks all asset files   │
│ Soft dep: ScoredItem  │               └────────────────────────────┘
│ Quality: READY/DEGRADED/BLOCKED
└───────────┬──────────┘
            │
            ▼
┌──────────────────────────┐
│    Storyboard (A5)       │
│  Hard dep: Brief         │
│  Hard dep: ContentIntel  │
│  Fallback: needs_review  │
└───────┬──────────┬───────┘
        │          │
        ▼          ▼
┌────────────────────────────────────────────────────┐
│              Assets (A6-A9)                         │
│  Hard dep: Storyboard (ValueError if missing)       │
│  Hard dep: Brief                                    │
│  NOTE: Does NOT check storyboard review_status      │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ Thumbnail │ │  Script  │ │ Carousel │ │Newslet.││
│  │ (always)  │ │(if short_│ │(if car.) │ │(if nl) ││
│  │           │ │  video)  │ │          │ │        ││
│  └──────────┘ └──────────┘ └──────────┘ └────────┘│
└────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Manifest (A10)  │
              │  Aggregates all  │
              │  asset statuses  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  PostingPlanner  │
              │  Gate: ready_    │
              │  for_planner     │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ DryRunValidator  │
              │ Gate: approved   │
              └────────┬─────────┘
                       │
                       ▼
                   Publishing
```

---

## 3. State Satisfaction Matrix

### 3.1 Brief → ContentIntelligence Dependency

| Brief `review_status` | Satisfies CI Dependency? | Lifecycle Mapping | Behavior |
|----------------------|------------------------|-------------------|----------|
| `DRAFT` | **Yes** (CI reads any brief in storage) | DRAFT | CI generates normally |
| `NEEDS_REVIEW` | **Yes** (no status filter on briefs) | NEEDS_REVIEW | CI generates normally |
| `REVIEWED` | **Yes** | REVIEWED | CI generates normally |
| `APPROVED` | **Yes** | APPROVED | CI generates normally |
| `REJECTED` | **Yes** (no status filter on briefs) | REJECTED | CI generates normally |

**Finding:** `ContentIntelligenceService` does NOT filter briefs by `review_status`. Any brief in storage is a candidate. The quality gate (`evaluate_brief_quality`) is a soft gate that degrades rather than blocks.

### 3.2 Brief + ContentIntelligence → Storyboard Dependency

| Brief | ContentIntelligence | Satisfies? | Behavior |
|-------|-------------------|------------|----------|
| Present | Present | **Yes** | Storyboard generates normally |
| Present | Missing | **No** | Skips topic, marks workflow failed |
| Missing | Any | **Hard fail** | `StoryboardFailure("Missing Brief dependency")`, marks workflow failed |
| Any | Present (any status) | **Yes** | No CI status filter |

**Finding:** `StoryboardService` has a hard dependency on Brief (raises `StoryboardFailure` if missing). It has no hard dependency on CI status — any CI artifact in storage is accepted.

### 3.3 Storyboard + Brief → Assets Dependency

| Storyboard | Brief | Satisfies? | Behavior |
|-----------|-------|------------|----------|
| Present (any status) | Present | **Yes** | Assets generate normally |
| Missing | Any | **Hard fail** | `ValueError` — aborts entire `AssetGenerationService.run()` |
| Present (REJECTED) | Present | **Yes** | Assets still generate (no status check) |
| Present (DRAFT) | Present | **Yes** | Assets still generate (no status check) |

**Finding:** `AssetGenerationService` raises `ValueError` on missing storyboard (unique among services — all others skip gracefully). It does NOT check `storyboard.review_status`.

### 3.4 Assets → Manifest Dependency

| Asset `review_status` | Manifest `status` | `overall_status` Impact | `ready_for_planner` Impact |
|----------------------|-------------------|------------------------|---------------------------|
| `approved` | `"approved"` | Contributes to `"complete"` | **Yes** |
| `draft` | `"draft"` | Prevents `"complete"` → `"partial"` | **No** |
| `needs_review` | `"needs_review"` | Prevents `"complete"` → `"partial"` | **No** |
| `reviewed` | `"reviewed"` | Prevents `"complete"` → `"partial"` | **No** |
| `rejected` | `"rejected"` | Triggers `"blocked"` | **No** |
| `missing` | `"missing"` | Triggers `"blocked"` | **No** |
| `skipped` | `"skipped"` | **Excluded** from calculation | **Excluded** |

**Manifest `overall_status` rules:**
1. Skip all `"skipped"` assets
2. If any remaining is `"missing"` or `"rejected"` → `"blocked"`
3. If all remaining are `"approved"` → `"complete"`
4. Otherwise → `"partial"`

**`ready_for_planner` rules:**
- `True` only if ALL non-skipped assets have `status == "approved"`

### 3.5 Manifest → PostingPlanner Dependency

| Manifest `ready_for_planner` | Satisfies? | Behavior |
|-----------------------------|------------|----------|
| `True` | **Yes** | Manifest is eligible for scheduling |
| `False` | **No** | Manifest excluded from scheduling |

**Additional gate:** The asset file must physically exist on disk at the path specified in the manifest (`_select_asset_path` checks `full_path.exists()`).

### 3.6 Calendar → DryRunValidator Dependency

| Post `asset_path` exists | `review_status` | `is_ready` | Behavior |
|-------------------------|----------------|------------|----------|
| Yes | `"approved"` | `True` | Ready for publishing |
| Yes | `"draft"` | `False` | Warning: not approved |
| Yes | `"needs_review"` | `False` | Warning: not approved |
| Yes | `"rejected"` | `False` | Warning: not approved |
| No | N/A | `False` | Blocked: missing file |

---

## 4. Hard Blocking Rules

Generation **must not start** when any of these conditions exist.

### 4.1 Brief Generation

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-01 | No `ScoredTopicItem` with `status=SCORED` exists | Hard | `BriefGenerationService` filters on `TopicStatus.SCORED` |
| HB-02 | `ScoredTopicItem.raw_text` < 100 characters | Hard | `generate_brief()` raises `ValueError` |

### 4.2 ContentIntelligence Generation

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-03 | No `Brief` exists in storage | Hard | `ContentIntelligenceService` returns empty if no briefs |
| HB-04 | Brief quality is `BLOCKED` (missing required fields) | **Soft** (see §5) | Generator returns stub CI with `NEEDS_REVIEW` — does NOT block |

### 4.3 Storyboard Generation

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-05 | No `Brief` exists for topic | Hard | `StoryboardService` appends `StoryboardFailure`, marks workflow failed |
| HB-06 | No `ContentIntelligence` exists in storage | Hard | `StoryboardService` returns empty if no CI artifacts |

### 4.4 Asset Generation

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-07 | No `Storyboard` exists for topic | Hard | `AssetGenerationService` raises `ValueError` (aborts entire run) |
| HB-08 | No `Brief` exists for topic | Hard | Asset generators require brief as input parameter |

### 4.5 Manifest Compilation

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-09 | Any non-skipped asset has `status="missing"` | Hard | `ManifestBuilder` sets `overall_status="blocked"` |
| HB-10 | Any non-skipped asset has `status="rejected"` | Hard | `ManifestBuilder` sets `overall_status="blocked"` |

### 4.6 Calendar Scheduling

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-11 | Manifest `ready_for_planner=False` | Hard | `PostingPlanner` filters manifests on `ready_for_planner` |
| HB-12 | Asset file does not exist on disk | Hard | `_select_asset_path()` returns `None`, slot skipped |

### 4.7 Dry-Run Validation

| Rule ID | Condition | Severity | Current Enforcement |
|---------|-----------|----------|-------------------|
| HB-13 | Asset file missing at scheduled path | Hard | `DryRunValidator` sets `is_ready=False`, counts as blocked |
| HB-14 | Asset `review_status != "approved"` | Hard | `DryRunValidator` sets `is_ready=False` |

---

## 5. Soft Blocking Rules

Generation **may start** but produces degraded output or requires operator acknowledgement.

| Rule ID | Condition | Severity | Artifact Affected | Current Behavior |
|---------|-----------|----------|-------------------|-----------------|
| SB-01 | Brief quality is `DEGRADED` (missing optional fields) | Soft | ContentIntelligence | CI generates with reduced quality |
| SB-02 | Brief quality is `BLOCKED` (missing required fields) | Soft* | ContentIntelligence | CI returns stub with all `needs_review` fields |
| SB-03 | `ScoredTopicItem` missing (fallback to `TopicItem`) | Soft | ContentIntelligence, Storyboard | Uses `priority_score=0.0` defaults |
| SB-04 | Storyboard missing (legacy mode) | Soft | All 4 asset generators | Generators accept `Optional[Storyboard]`, fallback to brief values |
| SB-05 | LLM inference fails | Soft | All generators | Return `needs_review` stub artifacts |
| SB-06 | Brief `recommended_formats` contains `"needs_review"` | Soft | Storyboard, ManifestBuilder | Normalized to `["short_video"]` in Storyboard; ManifestBuilder defaults to `"short_video"` |

*SB-02 is classified as soft because the system does NOT abort — it produces a degraded artifact that the operator must review.

### Soft Block Impact on Downstream

```
SB-02: CI stub (all needs_review)
  └─► Storyboard generates normally (no CI quality check at storyboard level)
       └─► Assets generate normally (no storyboard quality check)
            └─► Manifest: asset has review_status=needs_review
                 └─► overall_status="partial" (not blocked, not complete)
                      └─► ready_for_planner=False
                           └─► PostingPlanner excludes this topic
```

---

## 6. Generation Preconditions

### 6.1 Brief Generation

```
PRECONDITIONS:
  1. ScoredTopicItem exists with status=SCORED (HB-01)
  2. ScoredTopicItem.raw_text ≥ 100 chars (HB-02)
  3. Brief file does NOT already exist (skip if exists)

INPUTS:
  - ScoredTopicItem (topic_id, title, source, url, raw_text)
  - PromptRegistry (prompt template)
  - InferenceManager (Gemini API)

OUTPUT:
  - Brief with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "brief" (NOT tracked by WorkflowStateManager)
```

### 6.2 ContentIntelligence Generation

```
PRECONDITIONS:
  1. At least one Brief exists in storage (HB-03)
  2. Workflow stage "content_intelligence" not completed (or file missing)

INPUTS:
  - Brief (topic_id, all fields)
  - ScoredTopicItem (optional, for priority_score)
  - PromptRegistry
  - InferenceManager

QUALITY GATE (soft):
  - evaluate_brief_quality(brief) → READY | DEGRADED | BLOCKED
  - BLOCKED → stub CI (no LLM call)
  - DEGRADED → CI with reduced quality
  - READY → full CI generation

OUTPUT:
  - ContentIntelligence with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "content_intelligence"
```

### 6.3 Storyboard Generation

```
PRECONDITIONS:
  1. Brief exists for topic (HB-05) — HARD FAIL if missing
  2. At least one ContentIntelligence exists in storage (HB-06)
  3. Workflow stage "storyboard" not completed (or file missing)

INPUTS:
  - Brief (topic_id, recommended_formats, plain_english_summary, analogy)
  - ContentIntelligence (topic_type, hooks, curiosity_gap, story_angle, contrast_pair)
  - PromptRegistry
  - InferenceManager

OUTPUT:
  - Storyboard with deterministic fields (visual_style, visual_metaphor, formats_planned)
  - LLM-generated fields (thumbnail_hook, CTAs, claims)
  - review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "storyboard"
```

### 6.4 Thumbnail Generation

```
PRECONDITIONS:
  1. Storyboard exists for topic (HB-07) — ValueError if missing
  2. Brief exists for topic (HB-08)
  3. Workflow stage "thumbnail" not completed (or file missing)

INPUTS:
  - Storyboard (visual_metaphor, visual_style, thumbnail_hook)
  - Brief (analogy, topic_id)
  - PromptRegistry
  - InferenceManager

NOTE: Thumbnail is ALWAYS generated (not format-dependent)

OUTPUT:
  - ThumbnailPrompt with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "thumbnail"
```

### 6.5 Script Generation

```
PRECONDITIONS:
  1. Storyboard exists for topic (HB-07) — ValueError if missing
  2. Brief exists for topic (HB-08)
  3. Brief.recommended_formats maps to "short_video"
  4. Workflow stage "script" not completed (or file missing)

INPUTS:
  - Storyboard (script_hook, script_cta, script_claims, visual_metaphor)
  - Brief (all fields)
  - Format: "short_video"
  - PromptRegistry
  - InferenceManager

OUTPUT:
  - Script with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "script"
```

### 6.6 Carousel Generation

```
PRECONDITIONS:
  1. Storyboard exists for topic (HB-07)
  2. Brief exists for topic (HB-08)
  3. Brief.recommended_formats maps to "carousel"
  4. Workflow stage "carousel" not completed (or file missing)

INPUTS:
  - Storyboard (carousel_hook, carousel_cta, carousel_claims, visual_metaphor)
  - Brief (all fields)
  - PromptRegistry
  - InferenceManager

OUTPUT:
  - Carousel with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "carousel"
```

### 6.7 Newsletter Generation

```
PRECONDITIONS:
  1. Storyboard exists for topic (HB-07)
  2. Brief exists for topic (HB-08)
  3. Brief.recommended_formats maps to "newsletter"
  4. Workflow stage "newsletter" not completed (or file missing)

INPUTS:
  - Storyboard (newsletter_hook, newsletter_cta, newsletter_claims, visual_metaphor)
  - Brief (all fields, including recommended_formats for prompt)
  - PromptRegistry
  - InferenceManager

OUTPUT:
  - Newsletter with review_status=DRAFT (success) or NEEDS_REVIEW (fallback)

WORKFLOW STAGE: "newsletter"
```

---

## 7. Review Preconditions

### 7.1 Brief Review

```
PRECONDITIONS:
  1. Brief file exists in data/briefs/{topic_id}.json
  2. Brief has review_status field

ACTIONS AVAILABLE:
  - approve → review_status="approved"
  - reject  → review_status="rejected"
  - flag    → review_status="needs_review"

REVIEW SERVICE: BriefReviewService.apply_decision()
HISTORY: Records ReviewHistoryEntry
```

### 7.2 Storyboard Review

```
PRECONDITIONS:
  1. Storyboard file exists in data/storyboards/{topic_id}.json
  2. Storyboard has review_status field

ACTIONS AVAILABLE:
  - approve → review_status="approved"
  - reject  → review_status="rejected"
  - flag    → review_status="needs_review"

REVIEW SERVICE: StoryboardReviewService.apply_decision()
HISTORY: Records ReviewHistoryEntry
```

### 7.3 Asset Review (Multi-type)

```
PRECONDITIONS:
  1. At least one asset file exists (script, carousel, newsletter, thumbnail)
  2. Manifest file exists for topic

ACTIONS AVAILABLE (per asset):
  - approve → review_status="approved"
  - reject  → review_status="rejected"

REVIEW SERVICE: AssetReviewService.apply_decisions()
POST-ACTION: ManifestBuilder rebuilds manifest
HISTORY: Records ReviewHistoryEntry per asset
```

### 7.4 Batch Approve

```
PRECONDITIONS:
  1. At least one asset file exists with review_status NOT in ("approved", "rejected")

ACTIONS AVAILABLE:
  - approve all non-terminal assets to "approved"

NOTE: Bypasses service layer (direct file I/O)
      Does NOT record ReviewHistoryEntry (audit trail gap)
      Rebuilds all manifests after operation
```

---

## 8. Manifest Preconditions

### 8.1 Manifest Compilation

```
PRECONDITIONS:
  1. Brief file exists (for recommended_formats extraction)
  2. At least one asset file exists

COMPUTATION:
  1. Determine recommended asset types from brief.recommended_formats
  2. Always include: brief, thumbnail
  3. Conditionally include: script, carousel, newsletter
  4. For each asset type, check file existence and review_status
  5. Compute overall_status:
     - "blocked" if any non-skipped asset is "missing" or "rejected"
     - "complete" if all non-skipped assets are "approved"
     - "partial" otherwise
  6. Compute ready_for_planner:
     - True only if ALL non-skipped assets are "approved"
  7. Compute blocking_reasons:
     - Lists "missing", "rejected", and "needs_review" assets
```

### 8.2 Manifest → Planner Gate

```
GATE: ready_for_planner == True
EQUIVALENT TO: overall_status == "complete"
EQUIVALENT TO: ALL non-skipped assets have status == "approved"

PLANNER ADDITIONAL CHECKS:
  - Asset file must exist on disk at manifest path
  - Scheduling rules (max_same_topic, min_days_gap, no consecutive same format)
  - Maximum 7 posts per week
```

---

## 9. Approval Preconditions

### 9.1 Artifact Approval Pipeline

```
COMPLETE APPROVAL SEQUENCE:

1. TopicItem: SCORED → (operator review) → APPROVED
   Gate for: Brief generation

2. Brief: DRAFT → NEEDS_REVIEW → APPROVED
   Gate for: CI generation (soft — any status accepted)

3. ContentIntelligence: DRAFT → (no formal review)
   Gate for: Storyboard generation (existence check only)

4. Storyboard: DRAFT → NEEDS_REVIEW → APPROVED
   Gate for: Asset generation (existence check only, NOT status check)

5. Assets (×4): DRAFT → NEEDS_REVIEW → APPROVED
   Gate for: Manifest ready_for_planner

6. Manifest: overall_status = "complete"
   Gate for: PostingPlanner scheduling

7. DryRun: all assets review_status = "approved"
   Gate for: Publishing
```

### 9.2 Critical Gap: Storyboard Approval Not Enforced

**Current state:** `AssetGenerationService` checks storyboard existence but NOT `review_status`. A storyboard with `review_status=REJECTED` will still be used to generate assets.

**Impact:** Assets can be generated from a rejected storyboard, wasting LLM compute and producing content that may need to be regenerated.

**Recommendation (Phase 11.5):** Add storyboard approval check to asset generation preconditions.

---

## 10. Future Action Engine Integration Notes

### 10.1 Action Registry Mapping

The dependency matrix maps to a future `ActionRegistry` as follows:

| Current State | Available Actions | Blocked Actions |
|--------------|-------------------|-----------------|
| `ScoredTopicItem` exists, `Brief` missing | `generate_brief` | `generate_ci`, `generate_storyboard`, `generate_assets` |
| `Brief` exists, `CI` missing | `generate_ci`, `review_brief` | `generate_storyboard`, `generate_assets` |
| `CI` exists, `Storyboard` missing | `generate_storyboard` | `generate_assets` |
| `Storyboard` exists, assets missing | `generate_assets` | `build_manifest` |
| All assets exist, not all approved | `review_assets`, `batch_approve` | `plan_week` |
| All assets approved | `build_manifest`, `plan_week` | — |
| Manifest complete | `plan_week`, `dry_run` | `generate_*` (idempotent) |
| Calendar exists | `dry_run` | `plan_week` (overwrite) |

### 10.2 Lifecycle State → Action Mapping

Using `ArtifactLifecycleState` from Phase 11.1.2:

| Lifecycle State | Is Terminal? | Available Actions |
|----------------|-------------|-------------------|
| `PENDING` | No | Generate, review (if artifact exists) |
| `DRAFT` | No | Review, approve, reject |
| `NEEDS_REVIEW` | No | Review, approve, reject |
| `REVIEWED` | No | Approve, reject |
| `APPROVED` | Yes | None (consumed by downstream) |
| `REJECTED` | Yes | Regenerate (new artifact) |
| `MISSING` | Yes | Generate |
| `SKIPPED` | Yes | None |
| `FAILED` | No | Retry generation |

### 10.3 Dependency Rule Language (Future)

Future phases can express rules as:

```python
# Example: Storyboard generation requires APPROVED Brief + APPROVED CI
Rule(
    action="generate_storyboard",
    requires=[
        Dependency(artifact="brief", state=ArtifactLifecycleState.APPROVED),
        Dependency(artifact="content_intelligence", state=ArtifactLifecycleState.APPROVED),
    ],
    block_type="hard",
)
```

### 10.4 Known Inconsistencies to Resolve

| ID | Inconsistency | Phase | Recommendation |
|----|--------------|-------|---------------|
| INC-01 | Brief review_status not checked by CI service | 11.5 | Add optional review_status filter |
| INC-02 | Storyboard review_status not checked by asset service | 11.5 | Add storyboard approval gate |
| INC-03 | `needs_review` in blocking_reasons but not in overall_status | 11.5 | Decide: should needs_review block? |
| INC-04 | AssetGenerationService raises ValueError (unique) | 11.5 | Standardize to graceful skip |
| INC-05 | batch-approve bypasses service layer | 11.3 | Route through ActionRegistry |
| INC-06 | ContentIntelligence has no formal review step | 11.3 | Add CI review action or mark as auto-approved |

---

## Appendix A: Dependency Satisfaction Quick Reference

```
To generate Brief:         Need ScoredTopicItem (status=SCORED, raw_text≥100)
To generate CI:            Need Brief (any review_status)
To generate Storyboard:    Need Brief (HARD) + CI (any status)
To generate Assets:        Need Storyboard (HARD, any review_status) + Brief
To build Manifest:         Need asset files on disk
To schedule (plan_week):   Need manifest.ready_for_planner=True (all assets approved)
To dry-run:                Need calendar posts with approved assets
To publish:                Need dry-run pass with all assets approved
```

## Appendix B: Blocking Reason Truth Table

| Asset Status | In `blocking_reasons`? | Causes `blocked`? | Prevents `ready_for_planner`? |
|-------------|----------------------|-------------------|------------------------------|
| `approved` | No | No | No |
| `draft` | No | No | **Yes** |
| `needs_review` | **Yes** | No | **Yes** |
| `reviewed` | No | No | **Yes** |
| `rejected` | **Yes** | **Yes** | **Yes** |
| `missing` | **Yes** | **Yes** | **Yes** |
| `skipped` | No (excluded) | No (excluded) | No (excluded) |
| `unknown` | No | No | **Yes** |
