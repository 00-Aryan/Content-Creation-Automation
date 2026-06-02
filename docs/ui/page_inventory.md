# Page Inventory: Streamlit Content Creation MVP

**Author:** Product Designer  
**Document Status:** Approved (Draft)  
**Target Path:** [page_inventory.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/page_inventory.md)  
**Constraints Met:** Exactly 6 pages, minimal architectural complexity, strict backend coordination.

---

## MVP Page Registry

To keep the application highly responsive and clean under Streamlit's routing constraints, the interface is organized into **exactly 6 pages** managed via the standard sidebar navigation array.

```
├── 1. Dashboard (Home)
├── 2. Topic Collection
├── 3. Topic Pipeline
├── 4. Brief Viewer
├── 5. Content Intelligence + Storyboard
└── 6. Asset Review
```

---

## Detailed Page Inventories

### Page 1: Dashboard
* **Route:** `/` or `Dashboard`
* **Purpose:** High-level status overview of active pipeline assets, model provider latencies, and workspace health.
* **Components:**
  - **Metric Cards:** Large stat callouts for pipeline queues (Collected, Scored, Drafts, Needs Review, Approved).
  - **Pipeline Progress Bar:** Horizontal stage indicator.
  - **API Health Panel:** Green/Red status lights checking environment variables and credential response statuses.
* **Backend Operations Triggered:**
  - Standard directory list scans (counting files inside `data/raw`, `data/briefs`, etc.).
  - `InferenceManager` mock ping (verifying API connectivity for `gemini` and `openrouter`).
* **Data Displayed:** Asset counts per directory, API connectivity status logs, recent pipeline history log statements.

---

### Page 2: Topic Collection
* **Route:** `/collection` or `Topic Collection`
* **Purpose:** Ingestion workspace to scan feeds or input manual reference URLs.
* **Components:**
  - **RSS Sources Config Grid:** List of configured RSS URLs.
  - **Manual Entry Form:** A simple form containing: *Title*, *Source URL*, *Publish Date*, *Category* (AI research, ML engineering, developer tools).
  - **Trigger Action Button:** A button styled as "Collect Feeds".
  - **Raw Ingested Data Table:** Interactive spreadsheet showing recently downloaded items.
* **Backend Operations Triggered:**
  - `RSSCollector.collect()` execution scanning feeds.
  - File saving operations writing raw topic JSONs to `data/raw/` or `data/staged/`.
* **Data Displayed:** List of raw topics containing Title, Category, Source URL, and ingestion status.

---

### Page 3: Topic Pipeline
* **Route:** `/pipeline` or `Topic Pipeline`
* **Purpose:** Evaluation and ranking workspace to triage topics before brief generation.
* **Components:**
  - **Scoring Weight Sliders:** Real-time sliders adjusting rule categories (e.g., novelty weight, utility weight, takeaway weight).
  - **Score Action Button:** Styled as "Re-evaluate Scores".
  - **Scored Topics Grid:** Table sorted by score, supporting multi-select checkboxes for queue routing.
* **Backend Operations Triggered:**
  - `load_scoring_config()` parsing YAML settings.
  - `ScoringEngine(config).score_all()` parsing raw JSON inputs.
  - Saving `ScoredTopicItem` objects to `data/scored/`.
* **Data Displayed:** Total scores, prioritized titles, categories, publication dates, and fired warning tags (e.g. "missing_source").

---

### Page 4: Brief Viewer
* **Route:** `/briefs` or `Brief Viewer`
* **Purpose:** Synthesis step that turns highly-ranked papers into peer-reviewed educational briefs.
* **Components:**
  - **Scored Queue Dropdown:** Selects which scored topic to generate or view.
  - **Generation Trigger Button:** Styled as "Generate Brief Draft".
  - **Editor Workspace:** Editable text cards for Brief fields (Takeaways, Analogy, Limitations).
  - **Save State Control:** Buttons styled as "Approve Brief" and "Flag for Review".
* **Backend Operations Triggered:**
  - `generate_brief()` LLM orchestration call.
  - Files saving/updating inside `data/briefs/` (using [BriefRepository](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/brief/repository.py)).
* **Data Displayed:** Summary fields, Analogies, Technical Limitations, recommended distribution formats, and source URLs.

---

### Page 5: Content Intelligence + Storyboard
* **Route:** `/storyboard` or `Content Intelligence + Storyboard`
* **Purpose:** Consolidates hooks formulation, angles analysis, and Claims/CTA mapping into a unified presentation step.
* **Components:**
  - **Brief Selector:** Dropdown displaying approved Briefs.
  - **Build Hooks & Storyboard Button:** Unified trigger button that runs the CI and Storyboard generator chain.
  - **Story Angles Grid:** Side-by-side cards showing hook text, register styles, and curiosity gaps.
  - **Claims Allocation Matrix:** Table mapping technical statements to specific formats (Carousel, Video Script, Newsletter).
  - **Visual Metaphor Panel:** Visual prompt mockup guidelines.
* **Backend Operations Triggered:**
  - `ContentIntelligenceGenerator.generate()` to draft hooks.
  - `StoryboardGenerator.generate()` to map claims and visual styles.
  - Persistence calls saving models to `data/content_intelligence/` and `data/storyboards/`.
* **Data Displayed:** Statistic/Bold claim hooks, curiosity gap text, emotional register settings ("excitement"), format claims mapping arrays, layout style selections ("diagram_overlay"), and resolved visual metaphors.

---

### Page 6: Asset Review
* **Route:** `/review` or `Asset Review`
* **Purpose:** Final preview workspace to review generated copy (newsletters, video scripts, carousels, thumbnails) and export files.
* **Components:**
  - **Draft Selector:** Dropdown displaying completed drafts.
  - **Assets Tabbed Interface:** Four clean panels:
    1. *Video Script* (spoken voice column, slide indicator column)
    2. *Carousel Deck* (slide cards, graphic design instructions)
    3. *Newsletter Editor* (markdown formatted body)
    4. *Thumbnail Studio* (positive titles, negative prompts, contrast guidelines)
  - **Inline Override Fields:** Simple text inputs to tweak hooks or headlines directly.
  - **Approval Toolbar:** Buttons for "Approve Asset Suite" and "Export ZIP Package".
* **Backend Operations Triggered:**
  - `WorkflowStateManager.mark_completed()` or `WorkflowStateManager.mark_failed()`.
  - Zip bundler compilation of JSON/Markdown directories for the topic.
* **Data Displayed:** Script narrative text, Carousel slides bodies, Newsletter sections, Thumbnail titles, style notes, and overall workflow badges (`APPROVED`, `NEEDS_REVIEW`).
