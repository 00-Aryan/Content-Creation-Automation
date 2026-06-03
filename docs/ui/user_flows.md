# User Flows: Streamlit Content Creation Pipeline UI (v0.6)

**Author:** UX Architect  
**Document Status:** Approved (Remediated)  
**Target Path:** [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md)  
**Context:** Step-by-Step UI Page State and Action Mappings to v0.6 Services  

---

## Operational Flow Overview

The Streamlit application coordinates the execution of the content creation pipeline in a step-by-step linear workflow, matching the underlying backend service architecture. Users traverse from raw topic ingestion to final multi-format asset approval through the following sequential path:

```
[1. Dashboard] ──► [2. Collect Topics] ──► [3. Score Topics] ──► [4. Generate Briefs]
                                                                        │
[8. Review Outputs] ◄── [7. Generate Assets] ◄── [6. Storyboards] ◄─────┘
```

Each page in the application manages its data lifecycle directly through the underlying Application Services, persisting changes to local storage via the `ApplicationContext` container.

---

## Detailed Page Flow Specifications

### Page 1: Dashboard
* **Purpose:** Centralized control center displaying overall system status, total assets in each stage of the lifecycle, API connection statuses, and pipeline run executions.
* **Inputs:** Read-only aggregate counts calculated from `LocalStorage` directories (`data/raw`, `data/briefs`, `data/content_intelligence`, `data/storyboards`, `data/thumbnails`, `data/scripts`, `data/carousels`, `data/newsletters`, `data/manifests`).
* **Actions:**
  - **Run End-to-End Pipeline:** Triggers [PipelineRunService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/pipeline_run_service.py) in the background. Streams logs live to a Streamlit console.
  - **Credentials Check:** Validate connectivity to primary Gemini API and OpenRouter fallback endpoints.
* **Outputs:** 
  - Summary metric cards showing: *Collected Raw Feeds*, *Scored Topics*, *Active Briefs*, *Storyboards*, *Needs Review*, *Approved Content Suites*.
  - Live console stream showing background execution logs.
* **Empty/Error States:** Warns if API keys are missing from `.env` or validation fails.

---

### Page 2: Collect Topics
* **Purpose:** Initiates the ingestion phase, scanning configured RSS feeds or sources to download and store raw paper/article metadata.
* **Inputs:** Optional source id filter.
* **Actions:**
  - **Run Collector:** Triggers [CollectTopicsService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/collect_topics_service.py).
* **Outputs:** A data table of raw topics (Topic ID, Title, Source Link, Ingested Timestamp).

---

### Page 3: Score Topics
* **Purpose:** Evaluates raw topics using the platform's prioritization rules, applying configured weights to rank research materials.
* **Inputs:** Weight adjustments for scoring criteria ( novelty, utility, student value).
* **Actions:**
  - **Run Prioritization Scorer:** Triggers [ScoreTopicsService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/score_topics_service.py).
* **Outputs:** A prioritized list of topics sorted by total score, showing warning flags.

---

### Page 4: Generate Briefs
* **Purpose:** Synthesizes the core technical contribution of selected high-scoring papers into clear educational briefs.
* **Inputs:** Topic selection dropdown from the scored queue.
* **Actions:**
  - **Generate Brief:** Triggers [BriefGenerationService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/brief_generation_service.py) for the selected topic.
* **Outputs:** Renders plain English summaries, analogies, limitations, and recommended formats.

---

### Page 5: Generate Content Intelligence
* **Purpose:** Extracts hooks, emotional registers, contrast pairs, and curiosity gaps from approved briefs.
* **Inputs:** Selection of an approved Brief.
* **Actions:**
  - **Extract Hooks & Angles:** Runs [ContentIntelligenceService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/content_intelligence_service.py) for the selected topic.
* **Outputs:** Displays primary hooks, secondary hooks, before/after contrast pairs, and topic classifications.

---

### Page 6: Generate Storyboards
* **Purpose:** Coordinates the claims distribution, visual metaphors, layout styles, and CTAs across formats.
* **Inputs:** Select topic with active Content Intelligence.
* **Actions:**
  - **Build Storyboard:** Runs [StoryboardService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/storyboard_service.py) for the selected topic.
* **Outputs:** Grid displaying format layouts (Carousel, Short Video, Newsletter) with their assigned hooks, CTA details, and the shared visual metaphor concept.

---

### Page 7: Generate Assets
* **Purpose:** Generates the specific copy and scripting formats based on the storyboard allocations.
* **Inputs:** Dropdown to select a topic with completed Storyboard. (Storyboard is a mandatory gate; fails validation if missing).
* **Actions:**
  - **Generate Assets:** Runs [AssetGenerationService.run](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/asset_generation_service.py) for the selected topic.
* **Outputs:** Displays generation counts and updates workflow state to completed.
* **Error States:** Explicitly fails if Storyboard is missing, prompting the user to generate a Storyboard first.

---

### Page 8: Review Outputs
* **Purpose:** Final preview workspace to review generated copy (newsletters, video scripts, carousels, thumbnails) and export files.
* **Inputs:** Dropdown containing topics with completed drafts. Manifest data loaded for review visibility.
* **Actions:**
  - **Approve/Reject Asset Type:** Calls [AssetReviewService.apply_decisions](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/asset_review_service.py) with structured `AssetDecision` payloads.
  - **Download ZIP Bundle:** Compiles all approved assets for download.
* **Outputs:** Tabbed viewer presenting scripts, carousels, newsletters, and thumbnail prompts beside the manifest status tags.
