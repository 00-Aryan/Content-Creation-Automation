# UI & Backend Architecture Alignment Review (v0.5)

This document evaluates the alignment between the approved Streamlit UI design documents and the core backend service layer delivered in v0.5.

---

## 1. Mismatch Inventory

### 1.1 The Content Intelligence & Storyboard Pipeline Gap
*   **Description:** The UI designs ([user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md) and [page_inventory.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/page_inventory.md)) assume a two-step generation phase where a user generates "Content Intelligence" (hooks, registers, angles) and "Storyboards" (CTA placement, format mapping) before asset generation.
*   **Architectural Drift:** In the shipped v0.5 service layer, [AssetGenerationService](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/asset_generation_service.py) generates assets directly from a [Brief](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models/brief.py) object. Chained generators (`ContentIntelligenceGenerator` and `StoryboardGenerator`) are currently orphaned (implemented but not integrated into the production pipeline).
*   **Severity:** **High (Blocker)**
*   **Affected Documents:** [page_inventory.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/page_inventory.md) (Page 5), [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md) (Page 5 & 6), [backend_integration_plan.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/backend_integration_plan.md) (Section 6.4).
*   **Recommended Correction:** Consolidate the UI generation step. The user should generate a Brief, and then immediately proceed to Asset Generation. Merge the Content Intelligence and Storyboard screens into read-only layout preview panels or mock visualizations, rather than requiring active backend execution loops for them in the MVP.

---

### 1.2 Page Count & Sidebar Registry Discrepancy
*   **Description:** There is an inconsistent page count across the UI documents:
    *   [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md) specifies **8 pages**.
    *   [page_inventory.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/page_inventory.md) specifies **exactly 6 pages**.
    *   [backend_integration_plan.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/backend_integration_plan.md) references a separate "Page 7 / Generate Assets" and "Page 6 — Asset Review".
*   **Severity:** **Medium**
*   **Affected Documents:** [page_inventory.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/page_inventory.md), [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md), [backend_integration_plan.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/backend_integration_plan.md).
*   **Recommended Correction:** Re-align the specs around a single **5-page structure** to keep sidebar navigation clean and map directly to the five core application use-cases:
    ```
    ├── 1. Dashboard (Pipeline status & E2E Run trigger)
    ├── 2. Topic Ingestion (Feed collection & Manual entry)
    ├── 3. Prioritization Triage (Topic scoring grid & config)
    ├── 4. Brief Creator (Brief synthesis & manual overrides)
    └── 5. Asset Workshop (Multi-format generation & Asset Review panel)
    ```

---

### 1.3 Missing End-to-End Pipeline Action in UI
*   **Description:** The UI user flows do not list an action to trigger the end-to-end `PipelineRunService` (e.g., from the Dashboard), despite "Run Pipeline" being flagged as a "Must Have" feature in the MVP scope of the [product_definition.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/product_definition.md).
*   **Severity:** **Medium**
*   **Affected Documents:** [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md) (Page 1 Actions).
*   **Recommended Correction:** Explicitly add a "Run End-to-End Pipeline" trigger widget on Page 1 (Dashboard). This widget should invoke [PipelineRunService](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/pipeline_run_service.py) in the background and print real-time stdout logs to a Streamlit console block.

---

### 1.4 Non-Existent Directory Scans
*   **Description:** The Dashboard flow in [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md) assumes directories `data/content_intelligence` and `data/storyboards` are scanned for dashboard status metrics. These folders do not exist in the [LocalStorage](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) adapter.
*   **Severity:** **Low**
*   **Affected Documents:** [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md) (Page 1 Inputs).
*   **Recommended Correction:** Remove these directory paths from the Dashboard count calculations to prevent file system scan errors.

---

## 2. Verdict

**VERDICT: ALIGNED WITH CHANGES REQUIRED**

The core backend service endpoints (`Collect`, `Score`, `Brief`, `Asset`, `Review`, `PipelineRun`) align with the user intent of Triaging and Generating educational assets. However, the UI flows must be updated to remove active references to the unimplemented intermediate storyboard pipeline steps, and the page navigation counts must be harmonized.
