# Phase 11.1.1 — Review Transition Inventory

**Date:** 2026-06-04
**Status:** COMPLETE
**Scope:** Audit of all review-state transition logic across the codebase

---

## 1. Executive Summary

This inventory audits every location that performs or influences review-state transitions for content artifacts. It produces a canonical transition table that becomes the single source of truth for `ReviewTransitionEngine`.

### Key Finding

**No transition validation exists.** Any `ReviewStatus` can transition to any other with no guards. The audit identified 4 independent locations that implement review logic, each with no shared validation.

---

## 2. State Definitions

### 2.1 Canonical ReviewStatus (shared/enums.py)

```python
class ReviewStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
```

### 2.2 Manifest-level AssetEntry.status (models/manifest.py)

```python
Literal["draft", "needs_review", "reviewed", "approved", "rejected", "missing", "skipped"]
```

Adds `missing` and `skipped` beyond `ReviewStatus`. These are manifest-computed states, not operator-reviewable states.

---

## 3. Transition Locations Audited

### 3.1 BriefReviewService

**File:** `src/content_creation/application/brief_review_service.py`

| Method | Transition Performed | Validation |
|--------|---------------------|------------|
| `apply_decision()` | `previous_status → decision.status` | **None** — any status can become any other |

**Observed behavior:**
- Reads current `review_status` from storage
- Directly writes `decision.status` to storage
- Records `ReviewHistoryEntry` with `previous_status` and `new_status`
- No checks on whether the transition is legal

### 3.2 StoryboardReviewService

**File:** `src/content_creation/application/storyboard_review_service.py`

| Method | Transition Performed | Validation |
|--------|---------------------|------------|
| `apply_decision()` | `previous_status → decision.status` | **None** — identical pattern to BriefReviewService |

### 3.3 AssetReviewService

**File:** `src/content_creation/application/asset_review_service.py`

| Method | Transition Performed | Validation |
|--------|---------------------|------------|
| `apply_decisions()` | `previous_status → decision.status` per asset | **None** — but reads `previous_status` from file before updating |

**Note:** Uses `update_asset_status()` (no notes) instead of `update_asset_status_with_notes()`. Inconsistent with brief/storyboard services.

### 3.4 batch-approve CLI

**File:** `src/content_creation/cli.py` (lines 344-407)

| Method | Transition Performed | Validation |
|--------|---------------------|------------|
| Direct file I/O | `any non-terminal status → APPROVED` | **Skips** assets already `approved` or `rejected` |

**Behavior:**
- Reads JSON files directly (bypasses service layer)
- Skips `approved` and `rejected` (implicit terminal-state guard)
- Sets `ReviewStatus.APPROVED` on all remaining assets
- Does NOT record `ReviewHistoryEntry` (audit trail gap)
- Rebuilds all manifests after batch operation

### 3.5 PipelineRunService batch-approve stage

**File:** `src/content_creation/application/pipeline_run_service.py` (lines 219-265)

| Method | Transition Performed | Validation |
|--------|---------------------|------------|
| Direct file I/O | `any non-terminal status → APPROVED` | **Same** as CLI batch-approve |

**Behavior:** Identical to CLI `batch-approve` — reads files directly, skips `approved`/`rejected`, does NOT record `ReviewHistoryEntry`.

---

## 4. Canonical Transition Table

### 4.1 Content Artifact Transitions (Brief, Storyboard, Script, Carousel, Newsletter, Thumbnail)

These are the **valid** transitions based on the architecture audit (Section 7.2) and observed system behavior:

| From | To | Trigger | Currently Validated |
|------|----|---------|-------------------|
| DRAFT | NEEDS_REVIEW | Generator fallback or operator flag | No |
| DRAFT | APPROVED | Auto-approve (batch or pipeline) | No |
| NEEDS_REVIEW | REVIEWED | Operator marks reviewed | No |
| NEEDS_REVIEW | APPROVED | Operator approves directly | No |
| NEEDS_REVIEW | REJECTED | Operator rejects | No |
| REVIEWED | APPROVED | Operator approves | No |
| REVIEWED | REJECTED | Operator rejects | No |

**Terminal states (no outgoing transitions):**
- `APPROVED` — ready for downstream consumption
- `REJECTED` — requires regeneration

**Explicitly invalid transitions:**
| From | To | Reason |
|------|----|--------|
| APPROVED | DRAFT | No reverse transition |
| APPROVED | NEEDS_REVIEW | No downgrade from approved |
| APPROVED | REVIEWED | No downgrade from approved |
| APPROVED | REJECTED | No downgrade from approved |
| REJECTED | * | Terminal — requires new artifact generation |
| DRAFT | REVIEWED | Must go through NEEDS_REVIEW first |
| DRAFT | REJECTED | Must go through NEEDS_REVIEW first |
| REVIEWED | DRAFT | No reverse transition |
| REVIEWED | NEEDS_REVIEW | No re-flagging after review |

### 4.2 Manifest-level Status (AssetEntry.status)

The manifest adds `missing` and `skipped` states that are computed, not operator-driven:

| Status | Meaning | Operator Actionable |
|--------|---------|-------------------|
| `missing` | Asset file does not exist | No (system-computed) |
| `skipped` | Asset generation was skipped | No (system-computed) |
| `draft` | Initial state | Yes |
| `needs_review` | Flagged for review | Yes |
| `reviewed` | Intermediate review | Yes |
| `approved` | Ready for planning | Yes |
| `rejected` | Needs regeneration | Yes |

---

## 5. Transition Graph

```
                    ┌──────────────────────────────────────────────────┐
                    │                                                  │
                    ▼                                                  │
                ┌────────┐     needs_review     ┌──────────────┐      │
                │ DRAFT  │ ──────────────────▶  │ NEEDS_REVIEW │      │
                └────────┘                      └──────────────┘      │
                    │                                │   │   │        │
                    │ approved                       │   │   │        │
                    │ (auto-approve)                 │   │   │        │
                    ▼                                │   │   │        │
                ┌──────────┐                         │   │   │        │
                │ APPROVED │ ◀───────────────────────┘   │   │        │
                └──────────┘   approved (direct)         │   │        │
                    ▲                                    │   │        │
                    │                                    │   │        │
                    │            ┌──────────┐            │   │        │
                    └────────────│ REVIEWED │◀───────────┘   │        │
                                 └──────────┘  reviewed      │        │
                                     │   │                   │        │
                                     │   │ rejected          │        │
                                     │   ▼                   │        │
                                     │ ┌──────────┐          │        │
                                     │ │ REJECTED │◀─────────┘        │
                                     │ └──────────┘  rejected         │
                                     │                                │
                                     └────────────────────────────────┘
                                          (APPROVED ← REVIEWED ← NEEDS_REVIEW)
```

### Terminal States

- **APPROVED**: No outgoing transitions. Asset is consumed by downstream services.
- **REJECTED**: No outgoing transitions. Requires new artifact generation.

---

## 6. Inconsistencies Found

| ID | Inconsistency | Severity | Location |
|----|---------------|----------|----------|
| I-01 | No transition validation in any service | High | All review services |
| I-02 | batch-approve bypasses service layer | Medium | cli.py, pipeline_run_service.py |
| I-03 | batch-approve does not record ReviewHistoryEntry | Medium | cli.py, pipeline_run_service.py |
| I-04 | AssetReviewService uses update_asset_status (no notes) while brief/storyboard use update_asset_status_with_notes | Low | asset_review_service.py |
| I-05 | REVIEWED state is optional — operators can skip directly from NEEDS_REVIEW to APPROVED | Low | All review services |

---

## 7. Recommendations for ReviewTransitionEngine

1. **Single graph**: One canonical transition graph shared by all review paths
2. **API surface**: `can_transition(from_status, to_status)`, `validate_transition(from_status, to_status)`, `get_available_transitions(from_status)`
3. **No side effects**: Engine validates transitions only — does not touch storage, UI, or services
4. **Asset-type agnostic**: Same graph for brief, storyboard, script, carousel, newsletter, thumbnail
5. **Future-proof**: Extensible for additional states without breaking existing consumers

---

## 8. Phase 11.1.2 Readiness

This inventory provides the complete specification for `ReviewTransitionEngine`:

- **Transition graph**: Fully defined in Section 4.1
- **Terminal states**: APPROVED, REJECTED
- **Entry states**: DRAFT (generator-created)
- **API methods**: can_transition, validate_transition, get_available_transitions
- **Test cases**: Every valid and invalid transition from the table

**Ready for implementation.**
