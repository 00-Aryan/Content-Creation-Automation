# User Flows: Streamlit Content Creation Pipeline UI

**Author:** UX Architect  
**Document Status:** Approved (Draft)  
**Target Path:** [user_flows.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/user_flows.md)  
**Context:** Detailed Step-by-Step UI Page State Definitions  

---

## Operational Flow Overview

The Streamlit application coordinates the execution of the content creation pipeline in a step-by-step linear workflow, matching the underlying backend architecture. Users traverse from raw topic ingestion to final multi-format asset approval through the following sequential path:

```
[1. Dashboard] ──► [2. Collect Topics] ──► [3. Score Topics] ──► [4. Generate Briefs]
                                                                        │
[8. Review Outputs] ◄── [7. Generate Assets] ◄── [6. Storyboards] ◄─────┘
```

Each page in the application manages its data lifecycle directly through the underlying repository patterns, persisting changes to local JSON storage files on completion of each step.

---

## Detailed Page Flow Specifications

### Page 1: Dashboard
* **Purpose:** Provides a centralized control center displaying overall system status, total assets in each stage of the lifecycle, API connection statuses, and pipeline throughput metrics.
* **Inputs:** Read-only aggregate counts calculated from `data/` subdirectories (`data/raw`, `data/briefs`, `data/content_intelligence`, `data/storyboards`, `data/thumbnails`, `data/workflow_state`).
* **Actions:**
  - **Refresh Dashboard:** Re-scan the filesystem and update counts.
  - **Credentials Check:** Validate connectivity to primary Gemini API and OpenRouter fallback endpoints.
* **Outputs:** 
  - Summary metric cards showing: *Collected Raw Feeds*, *Scored Topics*, *Active Drafts*, *Needs Review*, *Approved Content Suites*.
  - A visual timeline/progress pipeline chart showing current pipeline backlog distribution.
  - Health checks indicators for the Gemini and OpenRouter API keys.
* **Empty States:** Renders an informational banner: *"No database directory detected. Initialize the directory structure to get started."*
* **Error States:** Renders a warning message if API keys are missing from `.env` or return validation failures (e.g. *OpenRouter: 401 Unauthorized*).
* **Success States:** Green status badges confirming: *System fully operational. All API configurations healthy.*

---

### Page 2: Collect Topics
* **Purpose:** Initiates the ingestion phase, scanning configured RSS feeds or sources to download and store raw paper/article metadata.
* **Inputs:** Confired RSS URLs or manual URL entries in a text field.
* **Actions:**
  - **Run Collector:** Triggers the RSS parser and ingestion runner scripts.
  - **Clear Raw Queue:** Delete staging raw files.
* **Outputs:** A data table of raw topics (Topic ID, Title, Source Link, Ingested Timestamp) ready for scoring.
* **Empty States:** Renders a table card: *"Raw queue empty. Click 'Run Collector' to scan configured feeds."*
* **Error States:** Renders an error box: *"Failed to connect to RSS Feed: Network Timeout."*
* **Success States:** A banner displaying: *"Successfully collected 24 new raw topics."*

---

### Page 3: Score Topics
* **Purpose:** Evaluates raw topics using the platform's prioritization rules, applying configurable weights to rank research materials.
* **Inputs:** 
  - Sliders to temporarily adjust weights for topic rules (e.g., novelty, utility, student value).
  - Selected topics checkboxes from the raw queue.
* **Actions:**
  - **Run Prioritization Scorer:** Feeds selection to `ScoringEngine` and writes `ScoredTopicItem` JSONs.
* **Outputs:** A prioritized list of topics sorted by total score, showing triggered warning flags (e.g., lack of source URL or duplicate entries).
* **Empty States:** Renders: *"No unscored raw topics available. Collect topics first."*
* **Error States:** Displays: *"Configuration error: scoring.yaml weight mismatch."*
* **Success States:** Renders: *"Scoring complete. 12 topics prioritized. Proceed to Brief Generation."*

---

### Page 4: Generate Briefs
* **Purpose:** Synthesizes the core technical contribution of selected high-scoring papers into clear educational briefs.
* **Inputs:** 
  - Topic selection dropdown from the scored queue.
  - Text inputs for optional manual brief overrides (e.g., student takeaways or analogies).
* **Actions:**
  - **Generate Brief:** Triggers the LLM to write the Brief.
  - **Mark Brief Approved:** Direct state persistence to storage.
* **Outputs:** Renders the text blocks of the generated Brief: plain English summaries, analogies, limitations, and target audiences.
* **Empty States:** Renders: *"Select a scored topic from the dropdown to generate its Brief."*
* **Error States:** Displays: *"Brief generation failed: Rate limit (429) hit. Gemini model currently unavailable. Fallback provider triggered."*
* **Success States:** Displays: *"Brief generated successfully. Quality: READY. Analogy and limitations fully populated."*

---

### Page 5: Generate Content Intelligence
* **Purpose:** Extracts hooks, emotional registers, contrast pairs, and curiosity gaps from approved briefs.
* **Inputs:** Selection of an approved Brief.
* **Actions:**
  - **Extract Hooks & Angles:** Runs the Content Intelligence LLM generator.
* **Outputs:** Display cards showing primary hook (statistic/quote), secondary hook (question/bold claim), before/after contrast pairs, and topic classification (e.g. "paper").
* **Empty States:** Displays: *"No brief selected. Please select a brief to analyze."*
* **Error States:** Displays: *"Content Intelligence failed: JSON format validation error. Delimiter expected."*
* **Success States:** Displays: *"Content Intelligence successfully drafted. Register: EXCITEMENT. Hooks extracted."*

---

### Page 6: Generate Storyboards
* **Purpose:** Coordinates the claims distribution, visual metaphors, layout styles, and CTAs across formats.
* **Inputs:** Select topic with active Content Intelligence.
* **Actions:**
  - **Build Storyboard:** Executes the storyboard mapping generator.
* **Outputs:** Grid displaying layout formatting options (Carousel, Short Video, Newsletter) with their assigned hooks, CTA details, and the shared visual metaphor concept.
* **Empty States:** Displays: *"Select a topic with content intelligence to construct a storyboard layout."*
* **Error States:** Displays: *"Storyboard generation failed. Reason: Insufficient Content Intelligence data."*
* **Success States:** Displays: *"Storyboard generated. 3 format tracks coordinated. Visual metaphor resolved."*

---

### Page 7: Generate Assets
* **Purpose:** Generates the specific copy and scripting formats based on the storyboard allocations.
* **Inputs:** Dropdown to select a storyboard. Checkboxes to toggle format generation (Carousel, Newsletter, Script, Thumbnail).
* **Actions:**
  - **Generate Content Suite:** Simultaneously spawns generator jobs.
* **Outputs:** Tabbed viewer presenting the final scripts, visual slides, and markdown emails side-by-side with copy buttons.
* **Empty States:** Displays: *"No storyboard selected. Choose a storyboard to generate assets."*
* **Error States:** Renders: *"Inference failed on script generation. Retrying..."*
* **Success States:** Displays: *"All assets successfully generated as Drafts."*

---

### Page 8: Review Outputs
* **Purpose:** The final quality check dashboard where authors can manually review, override, and approve the complete suite before publishing.
* **Inputs:** Dropdown containing topics in `needs_review` or `draft` status. Text boxes to edit generated text inline.
* **Actions:**
  - **Approve Entire Suite:** Saves `review_status="approved"` to files on disk.
  - **Regenerate Section:** Re-runs the LLM prompt for a single specific section.
  - **Download ZIP Bundle:** Compiles all approved assets for download.
* **Outputs:** Summary evaluation cards representing the expert roles (Strategist, Creator, Editor, Auditor) and inline editing inputs.
* **Empty States:** Displays: *"All generated assets have been approved and published. No items remaining in review queue."*
* **Error States:** Displays: *"Cannot approve suite: Thumbnail prompt has 'needs_review' placeholders. Edit or regenerate before approval."*
* **Success States:** Displays: *"Suite APPROVED. Bundle created. Ready for upload."*
