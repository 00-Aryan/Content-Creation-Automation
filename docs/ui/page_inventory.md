# Page Inventory: Streamlit Content Creation MVP (v0.6)

**Author:** Product Designer  
**Document Status:** Approved (Remediated)  
**Target Path:** [page_inventory.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/page_inventory.md)  
**Constraints Met:** Exactly 6 pages, direct mappings to v0.6 application service layer.

---

## MVP Page Registry

To keep the application highly responsive and clean under Streamlit's routing constraints, the interface is organized into **exactly 6 pages** managed via the standard sidebar navigation array:

```
├── 1. Dashboard (Home)
├── 2. Topic Collection
├── 3. Topic Pipeline
├── 4. Brief Viewer
├── 5. Content Intelligence + Storyboard
└── 6. Asset Workshop (Generation & Review)
```

---

## Detailed Page Inventories

### Page 1: Dashboard
* **Route:** `/` or `Dashboard`
* **Purpose:** High-level status overview of active pipeline assets, workspace health, and end-to-end execution.
* **Components:**
  - **Metric Cards:** Stat counts for stage queues (Raw, Scored, Briefs, CI, Storyboards, Assets, Manifests).
  - **E2E Trigger Block:** A "Run End-to-End Pipeline" button that invokes [PipelineRunService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/pipeline_run_service.py).
  - **Live Console:** Scrollable box rendering live stream logs.
* **Backend Services Triggered:** `PipelineRunService`
* **Data Displayed:** Asset counts, API key health indicators, and run logs.

---

### Page 2: Topic Collection
* **Route:** `/collection` or `Topic Collection`
* **Purpose:** Ingestion workspace to scan feeds or input manual reference URLs.
* **Components:**
  - **RSS Configuration Grid:** Active configurations.
  - **Ingest Action Button:** Styled as "Collect Feeds".
* **Backend Services Triggered:** [CollectTopicsService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/collect_topics_service.py)
* **Data Displayed:** Normalized `TopicItem` metadata table.

---

### Page 3: Topic Pipeline
* **Route:** `/pipeline` or `Topic Pipeline`
* **Purpose:** Evaluation and ranking workspace to triage topics before brief generation.
* **Components:**
  - **Weight Adjustments:** Slider widgets.
  - **Score Action Button:** Styled as "Run Prioritization Scorer".
* **Backend Services Triggered:** [ScoreTopicsService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/score_topics_service.py)
* **Data Displayed:** Scores, categories, and validation warning flags.

---

### Page 4: Brief Viewer
* **Route:** `/briefs` or `Brief Viewer`
* **Purpose:** Synthesizes the core technical contribution of high-priority topics into briefs.
* **Components:**
  - **Topic Selector Dropdown:** Sorted by priority score.
  - **Brief Synthesis Button:** Styled as "Generate Brief Draft".
* **Backend Services Triggered:** [BriefGenerationService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/brief_generation_service.py)
* **Data Displayed:** plain English summaries, analogies, limitations, and recommendations.

---

### Page 5: Content Intelligence + Storyboard
* **Route:** `/storyboard` or `Content Intelligence + Storyboard`
* **Purpose:** Formulates editorial angles, psychological hooks, and visual formats mappings.
* **Components:**
  - **Dropdown Selector:** Selects an approved Brief.
  - **Generate CI Button:** Styled as "Build Content Intelligence".
  - **Generate Storyboard Button:** Styled as "Build Coordinated Storyboard" (requires CI to run first).
  - **Coordinated Grid:** Displays hooks, before/after pairs, format claims-split, visual metaphor concepts, and visual style notes.
* **Backend Services Triggered:**
  - [ContentIntelligenceService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/content_intelligence_service.py)
  - [StoryboardService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/storyboard_service.py)
* **Data Displayed:** Classifications, primary/secondary hooks, visual style selections, and claims matrices.

---

### Page 6: Asset Workshop (Generation & Review)
* **Route:** `/assets` or `Asset Workshop`
* **Purpose:** Coordinates asset generation (scripts, carousels, newsletters, thumbnails), manifest audits, and human-in-the-loop approvals.
* **Components:**
  - **Generate Assets Button:** Styled as "Generate Asset Suite". (Triggers `AssetGenerationService.run` which enforcesStoryboard existence; raises ValueError to user if missing).
  - **Manifest Status Header:** Displays `overall_status` and `ready_for_planner` badges.
  - **Assets Tabbed Editor:** Tabs for: Video Script, Carousel Slides, Newsletter Copy, and Thumbnail prompt text.
  - **Audit Toolbar:** Approve/Reject buttons per asset type.
* **Backend Services Triggered:**
  - [AssetGenerationService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/asset_generation_service.py)
  - [AssetReviewService.apply_decisions](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/asset_review_service.py)
* **Data Displayed:** Coordinated scripts, carousel cards, positive/negative prompts, review status, and compiled manifests.
