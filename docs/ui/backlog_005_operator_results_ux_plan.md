# UX Implementation Plan: Operator Pipeline Results UX (BACKLOG-005)

This document details the plan to improve the operator experience upon completion of an end-to-end pipeline execution. The changes are restricted purely to the presentation layer in the Streamlit interface.

---

## 1. Current State

Currently, when the end-to-end pipeline runs via the Editorial Content Pipeline Dashboard in [app.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/app.py), the output screen exposes developer-oriented debug details. 

* **Duration:** Rendered as raw seconds (e.g., `Duration: 226.44s`).
* **Path Information:** Exposes absolute server-side filesystem paths (e.g., `Log path: /opt/render/project/src/data/logs/pipeline_20260604_120000.jsonl`).
* **Execution Details:** Outputs raw stage structures via list formatting (e.g., `Stages executed: collect, score, generate-briefs, ...`).
* **Pipeline Results:** Renders the full `stage_summaries` payload as raw JSON via `st.json(res.stage_summaries)` directly in the main view.
* **Asset Summaries:** No aggregated checkbox summary of business outcomes (like which assets were completed or skipped) is displayed.

---

## 2. Proposed State

The proposed state prioritizes business outcomes and readability for operators, relegating technical logs and paths to a collapsible section.

1. **Human-Readable Duration:** Duration seconds are converted to a clean format (e.g., `3m 46s`).
2. **Path Sanitization:** The absolute filesystem paths are hidden from the operator-facing layout. Only the log file's name (e.g., `pipeline_20260604_120000.jsonl`) is shown as metadata.
3. **Pipeline Summary Metrics:** Instead of raw JSON, key metrics are parsed and displayed using standard UI list formats or column metric cards:
   * **Topics Collected:** Extracted from the `collect` stage count.
   * **Topics Scored:** Extracted from the `score` stage count.
   * **Briefs Generated:** Extracted from the `generate-briefs` stage count.
   * **Content Intelligence Generated:** Extracted from the `generate-content-intelligence` stage count.
   * **Storyboards Generated:** Extracted from the `generate-storyboards` stage count.
   * **Assets Generated:** Extracted as a summation of all asset categories generated in the `generate-assets` stage.
   * **Manifests Built:** Extracted from the `build-manifests` stage count.
4. **Generated Asset Outcomes:** Individual asset statuses (Script, Thumbnail, Carousel, Newsletter) are displayed clearly using checkmarks (`✓`) or status badges based on whether they were created successfully.
5. **Technical Diagnostics Section:** Raw JSON is moved inside a collapsed disclosure box (`st.expander`) titled **Technical Diagnostics & Logs**, accessible only if technical troubleshooting is required.

---

## 3. Proposed Screen Layout

The following Streamlit layout mockup illustrates the completed pipeline view on [app.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/app.py):

```
+-----------------------------------------------------------------------------+
| 🟢 Pipeline completed successfully.                                         |
+-----------------------------------------------------------------------------+
|                                                                             |
|  ⏱️ Run Duration: 3m 46s                                                    |
|                                                                             |
|  📋 Pipeline Run Summary                                                     |
|  -----------------------------------------------------------------          |
|  • Topics Collected: 15                                                     |
|  • Topics Scored: 12                                                        |
|  • Briefs Generated: 5                                                      |
|  • Content Intelligence Generated: 5                                        |
|  • Storyboards Generated: 5                                                 |
|  • Assets Generated: 20                                                     |
|  • Manifests Built: 5                                                       |
|                                                                             |
|  📦 Generated Asset Outcomes                                                |
|  -----------------------------------------------------------------          |
|  ✓ Script (5 generated)                                                     |
|  ✓ Thumbnail (5 generated)                                                  |
|  ✓ Carousel (5 generated)                                                   |
|  ✓ Newsletter (5 generated)                                                 |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  | ▶ Technical Diagnostics & Logs                                         |  |
|  +-----------------------------------------------------------------------+  |
|                                                                             |
+-----------------------------------------------------------------------------+
```

When the operator expands **Technical Diagnostics & Logs**:

```
+-----------------------------------------------------------------------------+
|  ▼ Technical Diagnostics & Logs                                             |
|  -----------------------------------------------------------------          |
|  Log File: pipeline_20260604_120000.jsonl                                   |
|  Full Log Path: /opt/render/project/src/data/logs/...                       |
|                                                                             |
|  Raw Summaries:                                                             |
|  {                                                                          |
|    "collect": {"count": 15, "success": true},                               |
|    "score": {"scored_count": 12, "rejected_count": 3, "success": true},     |
|    "generate-briefs": {"generated_count": 5, "skipped_count": 0, ...},      |
|    ...                                                                      |
|  }                                                                          |
+-----------------------------------------------------------------------------+
```

---

## 4. Acceptance Criteria

| ID | Criterion | Verification Method |
| :--- | :--- | :--- |
| **AC-1** | Replace raw default JSON with parsed metrics. | Verify that no JSON payload is rendered by default on successful/failed pipeline runs. |
| **AC-2** | Format execution duration to human-readable strings. | Verify durations $\ge 60$s format as `Xm Ys` and durations $< 60$s format as `Ys` or `0m Ys`. |
| **AC-3** | Hide absolute filesystem paths. | Check default views to confirm that absolute paths (e.g., `/opt/render/...`) are absent. |
| **AC-4** | Concise pipeline outcome metrics. | Confirm the counts for Collected, Scored, Briefs, CI, Storyboards, Assets, and Manifests match the backend return values. |
| **AC-5** | Clear individual asset outcomes. | Verify checkmark outputs (`✓`) are shown for Script, Thumbnail, Carousel, and Newsletter when they are successfully built. |
| **AC-6** | Technical diagnostics containment. | Confirm raw JSON summaries and absolute log path are only shown inside a collapsed `st.expander` box. |
| **AC-7** | Zero backend or core logic drift. | Confirm that no modifications are made to [pipeline_run_service.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/pipeline_run_service.py) or backend endpoints. |

---

## 5. Validation Strategy

Validation will follow a strict Plan-Act-Validate cycle on the presentation layer.

### Presentation Unit Verification
A formatting utility module will be introduced (or added to existing UI utility functions) to test:
```python
def format_duration(seconds: float) -> str:
    """Converts raw seconds to an operator-friendly format like '3m 46s'."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"
```
A unit test suite in `tests/` will validate this function with values like:
* `226.44` $\rightarrow$ `"3m 46s"`
* `45.2` $\rightarrow$ `"45s"`
* `3600.0` $\rightarrow$ `"60m 0s"`

### Defensive Summary Ingestion
To prevent crashes if backend summaries change, a parsing helper will extract counts safely using fallback defaults:
```python
def parse_pipeline_summary(stage_summaries: dict) -> dict:
    return {
        "collected": stage_summaries.get("collect", {}).get("count", 0),
        "scored": stage_summaries.get("score", {}).get("scored_count", 0),
        "briefs": stage_summaries.get("generate-briefs", {}).get("generated_count", 0),
        "ci": stage_summaries.get("generate-content-intelligence", {}).get("generated_count", 0),
        "storyboards": stage_summaries.get("generate-storyboards", {}).get("generated_count", 0),
        "manifests": stage_summaries.get("build-manifests", {}).get("count", 0),
        "assets": stage_summaries.get("generate-assets", {}).get("counts", {}),
    }
```

### Manual Verification
1. Run the Streamlit application using `streamlit run src/content_creation/ui/app.py`.
2. Trigger a pipeline run with a sample limit (e.g. 1 or 2 items).
3. Validate that the UI matches the mockup, showing clean formatting, checklist outcomes, and that absolute log path/JSON info is hidden under the diagnostics expander.

---

## 6. Risk Assessment

* **Risk R-001 (Backend Contract Changes):** If stage names or result keys inside `stage_summaries` change in a future release, the UI parser might fail to find the metrics.
  * *Mitigation:* Implement defensive dictionary parsing with `.get()` fallbacks. If any stage parsing throws an exception, catch the error and present a graceful warning alert while still allowing access to the diagnostics expander.
* **Risk R-002 (Incomplete Runs):** In case of early failure, later stages (like `generate-assets`) will not exist in the JSON summaries.
  * *Mitigation:* The UI parser must treat missing stage results as `0` counts rather than failing or raising a `KeyError`.
* **Risk R-003 (Streamlit Rerenders):** State loss upon toggle of the diagnostics expander.
  * *Mitigation:* Ensure pipeline results are stored in Streamlit's `st.session_state` so the results persist correctly during interactive expander toggling.

---

## 7. Impact Assessment

* **Operator Usability:** High. Operators get a clear picture of the pipeline's execution and generated artifacts at a glance without reading raw JSON payloads.
* **Security & Privacy:** High. Hiding server-side absolute paths (e.g., `/opt/render/...`) prevents local deployment directory structures from leaking through the web UI.
* **Performance:** Negligible. All formatting, rendering, and parsing happen inside memory in Streamlit in a fraction of a millisecond.
* **Maintainability:** High. Restricting modifications entirely to the UI script in [app.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/ui/app.py) ensures backend decoupled services remain untouched.
