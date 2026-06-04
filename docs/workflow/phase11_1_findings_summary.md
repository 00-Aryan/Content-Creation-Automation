# Phase 11.1 — Findings Summary

**Date:** 2026-06-04
**Audit:** Workflow State Architecture Audit
**Status:** COMPLETE

---

## Findings

### F-01: Five Overlapping Status Systems

**Severity:** High

The codebase contains five distinct status/state enumerations with no unified state machine:

1. `ReviewStatus` (shared/enums.py) — 5 values: DRAFT, NEEDS_REVIEW, REVIEWED, APPROVED, REJECTED
2. `TopicStatus` (models/topic.py) — 6 values: RAW, STAGED, SCORED, APPROVED, REJECTED, REVIEW
3. `AssetEntry.status` (models/manifest.py) — 7 Literal values: draft, needs_review, reviewed, approved, rejected, missing, skipped
4. `ArtifactState.status` (workflow/state.py) — 4 string values: pending, completed, failed, needs_review
5. `TopicManifest.overall_status` (models/manifest.py) — 3 Literal values: complete, partial, blocked

**Impact:** No single source of truth for state transitions. Future phases (dependency matrix, action engine) cannot build reliable rules without a unified model.

### F-02: Review Transition Rules Scattered Across Four Locations

**Severity:** Medium

Review logic exists in:
- `BriefReviewService` (brief-specific)
- `StoryboardReviewService` (storyboard-specific)
- `AssetReviewService` (multi-asset)
- `batch-approve` CLI (direct file manipulation)

Each implements its own transition rules with no shared validation.

**Impact:** Inconsistent review semantics. `batch-approve` bypasses the service layer entirely.

### F-03: Batch Approve CLI Bypasses Service Layer

**Severity:** Medium

The `batch-approve` command in `cli.py` directly reads/writes JSON files and manipulates `review_status` fields. It does not go through `AssetReviewService` or record `ReviewHistoryEntry` entries.

**Impact:** Audit trail gap. Review history is incomplete for batch-approved assets.

### F-04: `needs_review` Meaning is Overloaded

**Severity:** Medium

The string `"needs_review"` appears in three distinct contexts:
1. **Generator fallback:** LLM parse failure → artifact created with `needs_review` placeholders
2. **Operator flagging:** Operator explicitly marks artifact for review
3. **CI quality gate:** Brief quality DEGRADED → CI produces `needs_review` artifact

**Impact:** Ambiguous semantics make it difficult to build action availability rules.

### F-05: ScoredTopicItem Auto-Status Transition

**Severity:** Medium

The `ScoredTopicItem.set_scored_status` validator silently changes `RAW`/`STAGED` → `SCORED` without an explicit transition event. This is a hidden state change.

**Impact:** State transitions are not fully observable. Action engines cannot reliably track when scoring occurred.

### F-06: Pipeline Orchestration Duplicated

**Severity:** Medium

Stage orchestration logic exists in both:
- `PipelineRunService.run()` (service layer)
- `cli.py` `run-pipeline` command (CLI layer with inline stage logic for stages 7–9)

**Impact:** Two code paths for the same workflow. Maintenance burden and potential divergence.

### F-07: Manifest `needs_review` Not Blocking

**Severity:** Low

`ManifestBuilder` adds `needs_review` to `blocking_reasons` but does not set `overall_status = "blocked"` for `needs_review` assets. Only `missing` and `rejected` trigger blocked status.

**Impact:** Manifests with `needs_review` assets show as `"partial"` rather than `"blocked"`, potentially allowing them to enter the planner queue.

### F-08: No Operator Identity in Review History

**Severity:** Low

`ReviewHistoryEntry` records `action`, `previous_status`, `new_status`, `notes`, `timestamp` — but no operator identity. All reviews appear anonymous.

**Impact:** Cannot attribute decisions to specific operators. Blocks future RBAC and multi-operator support.

### F-09: Storage Access Patterns Inconsistent

**Severity:** Low

Services use mixed patterns:
- `ctx.storage.get_brief(topic_id)` (single lookup)
- `ctx.storage.list_briefs()` + filter (full scan)
- Direct file reads in `DryRunValidator` and `batch-approve` CLI

**Impact:** Performance inconsistency. No guaranteed access pattern for repository abstraction.

### F-10: Format Mapping Duplication

**Severity:** Low

`FORMAT_TO_ASSET` and `FREETEXT_TO_FORMAT` are defined in `manifest.py` and imported into `asset_generation_service.py`. The mapping exists in two logical locations.

**Impact:** Changes to format mappings require updating multiple import sites.

---

## Risks

### R-01: Unified State Machine Required for Phase 11.2+

**Risk Level:** High

The dependency matrix (Phase 11.2) and action availability rules (Phase 11.5) require a single, authoritative state machine definition. The current five-system fragmentation makes this impossible without unification first.

**Mitigation:** Define a canonical `ArtifactState` enum in `shared/enums.py` that subsumes all current status systems. Map existing statuses to the canonical model.

### R-02: Audit Trail Gaps from CLI Bypass

**Risk Level:** Medium

The `batch-approve` CLI bypass creates incomplete review history. This undermines the append-only audit trail that Phase 11.7 (job tracking) and Phase 11.8 (notifications) depend on.

**Mitigation:** Route all approval actions through `AssetReviewService`. Add `ReviewHistoryEntry` recording to `batch-approve`.

### R-03: Action Engine Cannot Determine Available Actions

**Risk Level:** Medium

Without a unified state machine and explicit transition rules, the Next Action Engine (Phase 11.4) cannot reliably compute what actions are available for a given artifact.

**Mitigation:** Define `ActionAvailabilityRule` model with explicit preconditions based on artifact state.

### R-04: Multi-Operator Conflicts Unaddressed

**Risk Level:** Low (current) → High (future)

Single-operator assumption is valid now but creates architectural debt. When multi-operator support is needed, the lack of locking, identity, and conflict detection will require significant refactoring.

**Mitigation:** Design operator identity and action attribution into the state model now, even if enforcement is deferred.

---

## Architectural Recommendations

### R-01: Unify Status Enums

**Priority:** High

Create a single `ArtifactLifecycleState` enum that covers all artifact types:

```python
class ArtifactLifecycleState(str, Enum):
    PENDING = "pending"           # Not yet generated
    DRAFT = "draft"               # Generated, not reviewed
    NEEDS_REVIEW = "needs_review" # Flagged for review
    REVIEWED = "reviewed"         # Under review
    APPROVED = "approved"         # Approved for downstream
    REJECTED = "rejected"         # Rejected, needs regeneration
    MISSING = "missing"           # Expected but not found
    SKIPPED = "skipped"           # Explicitly skipped
    FAILED = "failed"             # Generation failed
```

Map existing `TopicStatus`, `ReviewStatus`, `ArtifactState.status`, and `AssetEntry.status` to this canonical model.

### R-02: Centralize Review Transition Rules

**Priority:** High

Create a `ReviewTransitionEngine` that:
- Defines valid transitions as a graph
- Validates all transitions against the graph
- Records `ReviewHistoryEntry` for every transition
- Enforces operator identity (future RBAC)

### R-03: Route All Approvals Through Service Layer

**Priority:** Medium

Refactor `batch-approve` CLI to use `AssetReviewService.apply_decisions()` instead of direct file manipulation. This ensures:
- Complete audit trail
- Consistent transition validation
- Manifest rebuild after every approval

### R-04: Define Operator Action Model

**Priority:** Medium

Create `OperatorAction` model for Phase 11.3:
- `action_id` (UUID)
- `operator_id` (string, anonymous for now)
- `action_type` (enum: collect, score, generate, review, approve, reject, plan, validate)
- `target_artifact_type` (string)
- `target_artifact_id` (string)
- `initiated_at` (ISO-8601)
- `completed_at` (ISO-8601, optional)
- `result` (enum: success, failure, skipped)

### R-05: Separate `needs_review` Semantics

**Priority:** Medium

Distinguish between:
- `NEEDS_REVIEW` — operator-initiated flag
- `FALLBACK` — generator produced degraded output
- `QUALITY_DEGRADED` — upstream quality issue

Or document that `needs_review` is an umbrella state with sub-categories tracked via `review_notes`.

### R-06: Eliminate Pipeline Orchestration Duplication

**Priority:** Low

Move stages 7–9 (plan-week, dry-run, init-analytics) from `cli.py` into `PipelineRunService`. The CLI should only invoke the service, not duplicate orchestration logic.

---

## Required Follow-Up Work

| Phase | Work | Depends On | Priority |
|-------|------|-----------|----------|
| Pre-11.2 | Unify status enums into canonical `ArtifactLifecycleState` | This audit | High |
| Pre-11.2 | Centralize review transition rules in `ReviewTransitionEngine` | This audit | High |
| 11.2 | Build dependency matrix from canonical state machine | Pre-11.2 | High |
| 11.3 | Define `OperatorAction` model with operator identity | This audit | Medium |
| 11.4 | Build `ActionRegistry` mapping artifact states to available actions | 11.2, Pre-11.2 | High |
| 11.5 | Define `ActionAvailabilityRule` model with preconditions | 11.4 | High |
| 11.6 | Refactor `batch-approve` to use service layer | Pre-11.2 | Medium |
| 11.7 | Define `Job` model wrapping operator actions | 11.3 | Medium |
| 11.8 | Define `WorkflowEvent` model for notification emission | 11.7 | Low |
| Future | RBAC model with operator identity + roles | 11.3 | Low |
| Future | Multi-operator locking + conflict detection | 11.7 | Low |

---

## Final Recommendation

**READY FOR PHASE 11.2**

The workflow architecture is well-structured with clear dependency chains, consistent patterns (generator retry, fail-fast, idempotent resumability), and solid foundational infrastructure (`WorkflowStateManager`, `ManifestBuilder`, review history).

The primary risk is status enum fragmentation, which must be resolved before the dependency matrix can be built reliably. Two pre-11.2 remediation items are required:

1. **Unify status enums** into a canonical `ArtifactLifecycleState`
2. **Centralize review transition rules** in a `ReviewTransitionEngine`

With these two items completed, Phase 11.2 (Dependency Matrix) can proceed with full confidence in the underlying state model.
