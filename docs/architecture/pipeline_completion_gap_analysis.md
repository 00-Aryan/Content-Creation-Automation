# Pipeline Completion Gap Analysis: Content Intelligence & Storyboard Integration

This document outlines the architectural gap analysis to transition **Content Intelligence** and **Storyboards** from isolated domain structures into first-class production stages inside the `content-creation` pipeline.

---

## 1. Current vs. Target Pipeline Flow

### Current Execution Flow (v0.5)
```mermaid
graph LR
    Collect[1. Ingestion / Collect] --> Score[2. Prioritization / Score]
    Score --> Brief[3. Synthesis / Brief]
    Brief --> Assets[4. Asset Generation]
    Assets --> Review[5. Review & Approval]
```

### Target Execution Flow (Unified Pipeline)
```mermaid
graph LR
    Collect[1. Collect] --> Score[2. Score]
    Score --> Brief[3. Brief]
    Brief --> CI[4. Content Intelligence]
    CI --> Storyboard[5. Storyboard]
    Storyboard --> Assets[6. Asset Generation]
    Assets --> Review[7. Review & Approval]
```

---

## 2. Component Readiness Matrix

| Pipeline Component | Shipped Status | Classification | Location / Details |
| :--- | :--- | :--- | :--- |
| **Content Intelligence Model** | Fully Implemented | **Already exists** | [model.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/content_intelligence/model.py) |
| **Content Intelligence Generator** | Fully Implemented | **Already exists** | [generator.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/content_intelligence/generator.py) (includes quality-check fallback) |
| **Content Intelligence Repository** | Fully Implemented | **Already exists** | [repository.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/content_intelligence/repository.py) |
| **Storyboard Model** | Fully Implemented | **Already exists** | [model.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard/model.py) |
| **Storyboard Generator** | Fully Implemented | **Already exists** | [generator.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard/generator.py) (maps claim split & styles) |
| **Storyboard Repository** | Fully Implemented | **Already exists** | [repository.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard/repository.py) |
| **LocalStorage Integration** | Missing Properties | **Missing** | No properties or methods in [LocalStorage](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) wrap these repos. |
| **ApplicationContext Mapping** | Missing Properties | **Missing** | [ApplicationContext](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/context.py) does not expose references. |
| **ContentIntelligenceService** | Not Created | **Missing** | Needs to be created under `src/content_creation/application/`. |
| **StoryboardService** | Not Created | **Missing** | Needs to be created under `src/content_creation/application/`. |
| **Workflow State Tracking** | Lacks CI / Storyboard stages | **Partially exists** | [WorkflowStateManager](file:///home/aryan/May-2026/Content-Creation/src/content_creation/workflow/state.py) does not monitor CI/Storyboard. |
| **AssetGenerationService** | Consumes Brief directly | **Partially exists** | [AssetGenerationService](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/asset_generation_service.py) must be updated to consume Storyboard. |
| **PipelineRunService** | Skips CI / Storyboard | **Partially exists** | [PipelineRunService](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/pipeline_run_service.py) must orchestrate new stages. |

---

## 3. Core Architectural Questions Answered

### 3.1 Is `ContentIntelligenceService` needed?
> [!IMPORTANT]
> **YES.**
An independent service wrapper (`ContentIntelligenceService`) is necessary to isolate presentation layers (CLI/Streamlit) from raw model orchestration. The service will:
*   Retrieve scored topics from local storage.
*   Filter out degraded briefs using the quality engine (`evaluate_brief_quality`).
*   Query `ContentIntelligenceGenerator` to generate hooks and angles.
*   Persist the results through the repository.

### 3.2 Is `StoryboardService` needed?
> [!IMPORTANT]
> **YES.**
A dedicated orchestration service (`StoryboardService`) is required to bridge the Brief and Content Intelligence models. It will load the generated `Brief` and `ContentIntelligence` structures, invoke `StoryboardGenerator` to determine claim allocations and layout style rules, and persist the storyboard JSON.

### 3.3 Should `AssetGenerationService` consume Storyboard instead of Brief?
> [!TIP]
> **YES.**
In the current setup, `AssetGenerationService` receives a `Brief` and queries generators using only the brief data. Once storyboards are integrated:
*   Generators (especially `ThumbnailGenerator`) should consume the `Storyboard` to utilize the resolved visual metaphor and visual styles (`diagram_overlay`, `bold_typographic`).
*   Format generators (scripts, carousels, newsletters) will generate content from the claims and hooks allocated specifically to their formats by the storyboard, resulting in improved visual and textual cohesion.

### 3.4 Should `PipelineRunService` orchestrate CI and Storyboard stages?
> [!YES]
> **YES.**
[PipelineRunService](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/pipeline_run_service.py) must be updated to include two new sequential execution block stages between `BriefGeneration` (Stage 3) and `AssetGeneration` (Stage 4). This guarantees that pipeline logs are written to the JSONL log file and can be triaged correctly in the GUI.

### 3.5 What workflow-state changes are required?
Two new stage identifiers must be added to the workflow state machine registry:
1.  `content_intelligence` — tracks hook extraction completion.
2.  `storyboard` — tracks claims-split and metaphor allocation completion.

The [WorkflowStateManager](file:///home/aryan/May-2026/Content-Creation/src/content_creation/workflow/state.py) will check and write these states in the database (`data/workflow_state/`), ensuring resume-safety across UI and CLI.

### 3.6 What storage changes are required?
The storage layer must be updated to manage the new assets:
1.  Extend [LocalStorage](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) to declare `content_intelligence_dir` (`data/content_intelligence/`) and `storyboards_dir` (`data/storyboards/`).
2.  Implement retrieval and serialization wrappers:
    *   `save_content_intelligence(ci)` / `get_content_intelligence(topic_id)`
    *   `save_storyboard(sb)` / `get_storyboard(topic_id)`
3.  Inject these directory references into the dependency container [ApplicationContext](file:///home/aryan/May-2026/Content-Creation/src/content_creation/application/context.py).

### 3.7 What test additions are required?
To ensure release readiness, we must implement:
1.  **Unit Tests:** Verify `ContentIntelligenceService` and `StoryboardService` mock orchestrations.
2.  **Integration Tests:** Assert that `PipelineRunService` runs the new pipeline stages in the correct order, writes metadata logs, and handles fallback exceptions.
3.  **Generator Assertions:** Update asset generator tests (such as thumbnail/script tests) to verify they parse input from the `Storyboard` model instead of the `Brief` model.

---

## 4. Estimation & Verdict

### Required Tasks
1.  **LocalStorage Update:** Add directories and saving methods (15 lines of code).
2.  **Service Implementations:** Add `ContentIntelligenceService` and `StoryboardService` classes (approx. 120 lines of code).
3.  **Asset Generators Update:** Refactor generator classes to consume `Storyboard` (approx. 80 lines of code).
4.  **Pipeline Integration:** Add execution blocks to `PipelineRunService` and `WorkflowStateManager` (approx. 40 lines of code).
5.  **Test Suite Coverage:** Add mock tests and E2E integration validations (approx. 150 lines of test code).

**FINAL VERDICT: MEDIUM EFFORT**

The core generative logic, prompts, and JSON mapping parameters for both Content Intelligence and Storyboards already exist and are thoroughly tested. Integrating them into the production pipeline only requires linking the components through the service and storage layers.
