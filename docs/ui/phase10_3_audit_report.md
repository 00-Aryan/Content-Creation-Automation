# Phase 10.3 Audit Report: Execution Controls Review

**Date:** 2026-06-03  
**Auditor:** Kiro (automated architecture audit)  
**Status:** COMPLETE  
**Backend Contract Reference:** [v0.6_backend_signoff.md](../release/v0.6_backend_signoff.md)  
**Implementation Reference:** [phase10_3_implementation_report.md](./phase10_3_implementation_report.md)

---

## Audit Scope

Files reviewed:

- `src/content_creation/ui/services/client.py`
- `src/content_creation/ui/components/status.py`
- `src/content_creation/ui/app.py`
- `src/content_creation/ui/pages/1_topic_collection.py`
- `src/content_creation/ui/pages/2_topic_pipeline.py`
- `src/content_creation/ui/pages/3_brief_viewer.py`
- `src/content_creation/ui/pages/4_storyboard.py`
- `src/content_creation/ui/pages/5_asset_workshop.py`
- `src/content_creation/ui/state/session.py` (supporting)

---

## Findings

### Check 1 — Service Routing Validation: PASS

All 7 approved service mappings are correctly implemented end-to-end.

| UI Control | Expected Service | Actual Route | Result |
|---|---|---|---|
| Collect Topics | CollectTopicsService | `client.collect_topics()` → `CollectTopicsService.run` | ✅ Pass |
| Score Topics | ScoreTopicsService | `client.score_topics()` → `ScoreTopicsService.run` | ✅ Pass |
| Generate Briefs | BriefGenerationService | `client.generate_briefs()` → `BriefGenerationService.run` | ✅ Pass |
| Generate Content Intelligence | ContentIntelligenceService | `client.generate_content_intelligence()` → `ContentIntelligenceService.run` | ✅ Pass |
| Generate Storyboards | StoryboardService | `client.generate_storyboards()` → `StoryboardService.run` | ✅ Pass |
| Generate Asset Suite | AssetGenerationService | `client.generate_asset_suite()` → `AssetGenerationService.run` | ✅ Pass |
| Run Full Pipeline | PipelineRunService | `client.run_full_pipeline()` → `PipelineRunService.run` | ✅ Pass |

No page imports or directly invokes storage, generators, or backend services. All generation calls are routed through `ServiceClient` methods, which are the designated adapter boundary.

---

### Check 2 — Separation of Concerns: PASS

The three-layer contract (UI → client adapter → application service) is respected throughout.

- Pages contain only widget layout, user input collection, and result display logic.
- No business rules, scoring logic, or pipeline orchestration exists in any page file.
- `ServiceClient` owns all `ApplicationContext` access; pages never reference `client.ctx` directly.
- Read-only artifact helpers (`list_briefs`, `get_brief`, `get_storyboard`, `get_topic_assets`, etc.) are all encapsulated in `ServiceClient`, keeping storage access out of pages.

The implementation follows the approved layered architecture with no violations.

---

### Check 3 — Storyboard-First Enforcement: PASS with WARNING

**PASS:** The authoritative enforcement point remains `AssetGenerationService`. Page 5 (`5_asset_workshop.py`) calls `client.generate_asset_suite()`, which delegates to `AssetGenerationService.run`. The backend `ValueError` on missing storyboard is surfaced directly to the operator via a dedicated `except ValueError` handler and `st.error()`. No brief-only fallback path exists in the UI.

**WARNING — W-001: UI-level CI prerequisite gate duplicates backend ordering logic.**

In `4_storyboard.py`, the "Generate Storyboards" button is conditionally rendered only when `ci` (Content Intelligence) is truthy:

```python
with col_actions2:
    if ci:
        if not storyboard:
            gen_sb_btn = st.button("📋 Generate Storyboards", ...)
```

This gate is a UI convenience, not a security boundary — `StoryboardService` enforces its own prerequisite independently. However, it means the UI is encoding ordering knowledge that belongs solely to the application service layer. If the backend prerequisite rule changes, the UI gate will silently diverge.

This is not a violation of the storyboard-first rule (no fallback path exists), but it is an architectural duplication risk.

---

### Check 4 — Session State Hygiene: PASS

`session.py` initializes and manages exactly three keys:

```python
"selected_topic_id": None
"selected_brief_id":  None
"filters":            {"status": "all", "category": "all"}
```

No workflow state, pipeline execution state, or artifact lifecycle state is stored in `st.session_state`. The session layer is strictly UI-scoped.

---

### Check 5 — Execution UX: PASS

All 7 execution controls use `st.status(...)` with all three required states:

| State | Implementation |
|---|---|
| Running | `st.status("...", expanded=True)` — active while service executes |
| Success | `status.update(label="...", state="complete")` + `st.success(...)` |
| Failure | `status.update(label="...", state="error")` + `st.error(...)` |

Exceptions are caught at two levels: service-level failures (`ValueError` for storyboard blocking in page 5; generic `Exception` for all other services) and outer try/except for unexpected failures. Error messages are surfaced directly from backend exception text without suppression.

Duration display (`timed.duration_seconds`) is present on all execution paths.

---

### Check 6 — Full Pipeline Control: PASS

`app.py` delegates the "Run Full Pipeline" action to `client.run_full_pipeline()`, which calls `PipelineRunService.run(ctx, top_n=..., source_filter=..., auto_approve=False, api_key=...)`.

The dashboard contains no manual stage chaining. There is no sequence of `collect → score → brief → CI → storyboard → assets` invocations in any page or in `app.py`.

---

### Additional Finding — W-002: Weight sliders in Topic Pipeline are display-only

In `2_topic_pipeline.py`, five slider widgets are rendered for weight adjustments (Usefulness, Novelty, Credibility, Explainability, Hook Potential). However, these values are not passed to `client.score_topics()`, which calls `ScoreTopicsService.run(ctx)` with no weight parameters:

```python
# Sliders rendered but not used:
usefulness_w = st.slider("Usefulness", ...)
# ...
timed = client.score_topics()  # weights not forwarded
```

The scoring engine reads weights from `config/scoring.yaml`. The UI display implies the operator can adjust weights at runtime, but the sliders have no effect on actual scoring output. This is a UX accuracy issue — operators may be misled into believing they are affecting scoring behavior.

This finding does not violate the audit's architectural checks (scoring still routes correctly through `ScoreTopicsService`), but it represents a misleading UI element.

---

### Additional Observation — Client-layer storage access: ACCEPTABLE

`ServiceClient.get_metric_counts()` and `ServiceClient.list_workflow_states()` access `self.ctx.storage` and `self.ctx.workflow` directly. This is within the permitted adapter boundary (`client.py` is the adapter layer) and no page accesses `ctx` directly. This pattern is consistent with the backend integration plan's adapter model and is not a concern.

---

## Architecture Compliance

The implementation correctly respects the three-layer boundary defined in the backend integration plan:

```
Streamlit pages
      ↓
ServiceClient (adapter)
      ↓
Application services (CollectTopicsService, ScoreTopicsService, etc.)
      ↓
ApplicationContext (storage + workflow)
```

No page crosses the adapter boundary. No generator is imported or instantiated in any page or in `app.py`. `WorkflowStateManager` is not modified from the UI. `@st.cache_resource` is used correctly on `get_context()` to load `ApplicationContext` once per session.

The storyboard-first enforcement point remains exclusively in `AssetGenerationService`. The UI has no fallback asset generation path.

---

## Risks

**R-001 (Low) — W-001: Diverging CI prerequisite gate.**  
If `StoryboardService` relaxes its CI prerequisite, the UI gate will remain, hiding the storyboard button from operators even when generation would succeed. Conversely, if a new prerequisite is added at the service layer, the UI will not reflect it. The single source of truth for pipeline ordering should be the service layer, not the UI.

**R-002 (Low) — W-002: Misleading weight sliders.**  
Operators interacting with the Topic Pipeline page may adjust sliders and expect them to influence scoring results. Since they do not, repeated "why didn't my weight change work?" confusion is the likely operational outcome. The risk is limited to UX friction, not data integrity.

**R-003 (Low) — Dashboard workflow state table uses direct `ctx.workflow` traversal.**  
`list_workflow_states()` in `client.py` calls `self.ctx.workflow._dir.glob("*.json")`, accessing a private attribute of `WorkflowStateManager`. This couples `ServiceClient` to the internal directory layout of the workflow manager. If `WorkflowStateManager` changes its storage convention, this method will silently break. The risk is within the adapter layer and does not affect pages, but it is a fragile pattern.

---

## Recommendation

> **READY FOR PHASE 10.4**

All 6 required checks pass. The two warnings (W-001, W-002) and one fragility note (R-003) are low-severity and do not affect correctness, data integrity, or architectural compliance. No violations were found. No remediation is required before proceeding to Phase 10.4.

The warnings are recorded here for the Phase 10.4 backlog:

- W-001: Remove the UI-level CI prerequisite gate from `4_storyboard.py` and let `StoryboardService` surface the prerequisite failure as a user-facing error.
- W-002: Either wire the weight sliders to a config mutation path (if runtime weight overrides are desired) or replace them with a read-only display of the current `config/scoring.yaml` weights to eliminate the misleading implication.
- R-003: Replace `self.ctx.workflow._dir.glob(...)` in `list_workflow_states()` with a public `WorkflowStateManager` list API to remove the private-attribute dependency.
