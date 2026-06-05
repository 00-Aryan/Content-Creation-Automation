# Phase 11.6.3 — Action Availability Adoption Audit

**Date:** 2026-06-04  
**Status:** COMPLETE  
**Author:** Principal Workflow Architect (Content Creation Automation Platform)

---

## SECTION 1 — EXECUTION PATH INVENTORY

The table below catalogs every operator action (A01–A23) and evaluates whether it is initiated through the Streamlit UI, the CLI, the Workflow Executor, and the Action Availability Engine.

| Action | UI Entrypoint | CLI Entrypoint | Executor Routing | Availability Engine | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A01: `collect`** | Yes (`1_topic_collection.py`) | Yes (`collect` command) | Yes | Yes (No custom rules) | **COMPLIANT** |
| **A02: `score_topics`** | Yes (`2_topic_pipeline.py`) | Yes (`score-topics` command) | Yes | Yes (No custom rules) | **COMPLIANT** |
| **A03: `generate_briefs`** | Yes (`3_brief_viewer.py`) | Yes (`generate-briefs` command) | Yes | Yes | **PARTIALLY COMPLIANT** (Internal filesystem bypass checks inside service layer) |
| **A04: `generate_ci`** | Yes (`4_storyboard.py`) | None | Yes (UI) / No (Pipeline) | Yes (UI) / No (Pipeline) | **NON-COMPLIANT** (Bypassed in end-to-end pipeline run) |
| **A05: `generate_storyboards`**| Yes (`4_storyboard.py`) | None | Yes (UI) / No (Pipeline) | Yes (UI) / No (Pipeline) | **NON-COMPLIANT** (Bypassed in end-to-end pipeline run; internal service check duplication) |
| **A06: `generate_assets`** | Yes (`5_asset_workshop.py`) | Yes (`generate-assets` command) | Yes (UI/CLI) / No (Pipeline)| Yes (UI/CLI) / No (Pipeline)| **NON-COMPLIANT** (Bypassed in end-to-end pipeline run; internal service check duplication) |
| **A07: `review_brief`** | Yes (`3_brief_viewer.py`) | None | No (Observation Action) | No | **COMPLIANT** (Read-only action) |
| **A08: `approve_brief`** | Yes (`3_brief_viewer.py`) | None | Yes | Yes | **COMPLIANT** (UI dropdown contains intermediate state bypasses) |
| **A09: `reject_brief`** | Yes (`3_brief_viewer.py`) | None | Yes | Yes | **COMPLIANT** |
| **A10: `review_storyboard`** | Yes (`4_storyboard.py`) | None | No (Observation Action) | No | **COMPLIANT** (Read-only action) |
| **A11: `approve_storyboard`**| Yes (`4_storyboard.py`) | None | Yes | Yes | **COMPLIANT** |
| **A12: `reject_storyboard`** | Yes (`4_storyboard.py`) | None | Yes | Yes | **COMPLIANT** |
| **A13: `review_assets`** | Yes (`5_asset_workshop.py`) | Yes (`review-assets` command) | No (Observation Action) | No | **COMPLIANT** (Read-only action) |
| **A14: `approve_asset`** | Yes (`5_asset_workshop.py`) | Yes (`review-assets` command) | Yes | Yes | **COMPLIANT** |
| **A15: `reject_asset`** | Yes (`5_asset_workshop.py`) | Yes (`review-assets` command) | Yes | Yes | **COMPLIANT** |
| **A16: `batch_approve`** | None | Yes (`batch-approve` command) | Yes | Yes (No custom rules) | **PARTIALLY COMPLIANT** (Bypassed in pipeline `--auto-approve` flag) |
| **A17: `build_manifest`** | None | Yes (`build-manifest` command) | Yes | Yes | **PARTIALLY COMPLIANT** (Bypassed in pipeline manifest build stage) |
| **A18: `build_all_manifests`**| None | Yes (`build-all-manifests` command)| Yes | Yes (No custom rules) | **COMPLIANT** |
| **A19: `plan_week`** | None | Yes (`plan-week` command) | Yes | Yes | **COMPLIANT** |
| **A20: `dry_run`** | None | Yes (`dry-run` command) | Yes | Yes | **COMPLIANT** |
| **A21: `init_analytics`** | None | Yes (`init-analytics` command) | Yes | Yes (No custom rules) | **COMPLIANT** |
| **A22: `update_analytics`** | None | Yes (`update-analytics` command)| Yes | Yes (No custom rules) | **COMPLIANT** |
| **A23: `run_pipeline`** | Yes (`app.py` / `2_topic_pipeline.py`) | Yes (`run-pipeline` command) | Yes | Yes (No custom rules) | **PARTIALLY COMPLIANT** (Outer orchestration routes through executor, but executes all sub-stages directly, bypassing gates) |

---

## SECTION 2 — BYPASS ANALYSIS

Despite the successful implementation of the `ActionAvailabilityEngine` and its adoption inside the `WorkflowActionExecutor` for primary entrypoints, several workflow execution bypasses remain:

1. **Pipeline Execution Bypass**:
   * The `PipelineRunService` (A23) directly instantiates and executes individual domain services (`BriefGenerationService`, `ContentIntelligenceService`, `StoryboardService`, `AssetGenerationService`) and helper builders (`ManifestBuilder`).
   * Because it calls these services directly instead of routing through `WorkflowActionExecutor.execute()`, the `ActionAvailabilityEngine` is completely bypassed during pipeline execution for stages 1 through 8.
2. **Auto-Approve Storage Mutation Bypass**:
   * When `run-pipeline` is run with `--auto-approve` enabled, `PipelineRunService` directly invokes `ctx.storage.update_asset_status` to mark pending assets as `approved`.
   * This bypasses the executor, availability checks, and review transitions, allowing unvalidated modifications to slide directly into storage.
3. **Filesystem Existence Bypass Checks in Services**:
   * `BriefGenerationService` directly inspects the filesystem (`brief_file.exists()`) to decide if a brief exists and should be skipped.
   * `StoryboardService` checks if `sb_file.exists()` and calls `ctx.storage.get_brief(topic_id)` directly, raising errors if missing.
   * `AssetGenerationService` checks if `thumbnail_file.exists()` and `asset_file.exists()` directly.
   * All these service-level existence gates duplicate logic that should be handled at the workflow evaluation level.
4. **UI Button Rendering Bypass**:
   * Streamlit buttons (e.g. `Collect Topics`, `Score Topics`, `Generate Briefs`, etc.) are always rendered in an enabled state. They do not consult the `ActionAvailabilityEngine` to check eligibility before rendering.
   * If a user clicks an invalid button, the error is caught at runtime by the `WorkflowActionExecutor` returning an failure state, but the UI itself is not dynamically disabled/greyed out with helpful tooltips.

---

## SECTION 3 — SINGLE SOURCE OF TRUTH ASSESSMENT

### Verdict: PARTIALLY COMPLIANT

The `ActionAvailabilityEngine` is the single source of truth for **individual human-initiated operator actions** triggered from CLI commands or individual UI clicks. However, it is **NOT** the single source of truth for automated pipeline runs (`run-pipeline`), auto-approvals, or service-level skip logic.

Until pipeline execution stages are refactored to route sub-actions through the executor, the backend will continue to duplicate validation and allow direct service bypasses.

---

## SECTION 4 — REMAINING GAPS

### Gap 1: Pipeline Orchestration Bypasses Executor
* **Severity**: High
* **Impact**: Sub-actions executed in `PipelineRunService` bypass all dependency checks, transition constraints, and availability rules.
* **Affected Actions**: A03, A04, A05, A06, A16, A17
* **Remediation Recommendation**: Refactor `PipelineRunService` to consume the `WorkflowActionExecutor` (or route stage execution through it) instead of directly calling service classes and builders.

### Gap 2: Auto-Approve Bypasses Review Transition Gates
* **Severity**: High
* **Impact**: Bypasses transition validations, allowing assets to move directly from missing/stale states to `APPROVED`.
* **Affected Actions**: A16
* **Remediation Recommendation**: In `PipelineRunService`, route auto-approval actions through `WorkflowActionExecutor.execute("approve_asset", ...)` or `WorkflowActionExecutor.execute("batch_approve", ...)`.

### Gap 3: Filesystem Existence Check Duplication in Services
* **Severity**: Medium
* **Impact**: Couples application services to raw file paths and duplicate validation logic.
* **Affected Actions**: A03, A05, A06
* **Remediation Recommendation**: Extract skip checks and dependency verifications from application service classes into the `ActionAvailabilityEngine` or the pre-execution checks inside the `WorkflowActionExecutor`.

### Gap 4: UI Buttons Not Dynamically Disabled
* **Severity**: Low
* **Impact**: Poor UX; buttons are clickable even when actions are blocked, requiring the user to run the action and encounter a failure toast.
* **Affected Actions**: All UI-facing actions (A01, A02, A03, A04, A05, A06, A08, A09, A11, A12, A14, A15)
* **Remediation Recommendation**: Update Streamlit pages to query the `ActionAvailabilityEngine` via the `ServiceClient` and toggle `disabled=True/False` on buttons.

---

## SECTION 5 — READINESS FOR 11.6.4

### Verdict: READY WITH REMEDIATION

The platform is ready to transition to **Phase 11.6.4 (Clean UI Adoption)**. However, the identified gaps in pipeline orchestration and service-level file gates must be scheduled for remediation to ensure complete enforcement of the workflow boundary architecture.
