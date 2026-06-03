# Backend Integration Plan — Streamlit × Shared Service Layer (v0.6)

**Author:** Senior Staff Engineer  
**Document Status:** Approved (Remediated)  
**Target Path:** [backend_integration_plan.md](file:///home/aryan/May-2026/Content-Creation/docs/ui/backend_integration_plan.md)  

---

## 1. Executive Summary

Introduce a thin **`application/` use-case layer** that owns pipeline orchestration. Both the CLI parser and Streamlit views function as **presentation adapters** that independently call the **same services** and the **same** `WorkflowStateManager` + `LocalStorage` instances.

| Layer | Responsibility |
|---|---|
| **`streamlit_app/`** | UI Widgets $\rightarrow$ calls `application/` |
| **`cli.py`** | Argument parsing $\rightarrow$ calls `application/` |
| **`application/`** | Use-case execution logic & workflow states |
| **`storage/`** | Persistence & directory management |

---

## 2. Core Service Contracts (v0.6 Authoritative)

Streamlit views must call these services via the shared `ApplicationContext` dependency container:

### 2.1 Context Container
```python
# context.py
class ApplicationContext:
    base_dir: Path
    storage: LocalStorage
    workflow: WorkflowStateManager
    prompt_registry: PromptRegistry
```

### 2.2 Ingestion & Prioritization Services
* **Collect:** `CollectTopicsService.run(self, ctx: ApplicationContext, source_filter: Optional[str] = None) -> CollectResult`
* **Score:** `ScoreTopicsService.run(self, ctx: ApplicationContext) -> ScoreResult`

### 2.3 Synthesis Services
* **Brief:** `BriefGenerationService.run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> BriefGenerationResult`
* **Content Intelligence:** `ContentIntelligenceService.run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> ContentIntelligenceGenerationResult`
* **Storyboard:** `StoryboardService.run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> StoryboardGenerationResult`

### 2.4 Asset Generation & Audit Services
* **Asset Generation:** `AssetGenerationService.run(self, ctx: ApplicationContext, top_n: int = 5, api_key: Optional[str] = None, rate_limit_delay: float = 5.0) -> AssetGenerationResult`
  * *Constraint:* Requires `Storyboard` to exist on disk. Throws `ValueError` if missing. Bypassing Storyboards is prohibited.
* **Asset Review:** 
  * `AssetReviewService.get_review_queue(self, ctx: ApplicationContext, topic_id: str) -> List[AssetReviewItem]`
  * `AssetReviewService.apply_decisions(self, ctx: ApplicationContext, topic_id: str, decisions: List[AssetDecision]) -> ReviewResult`

---

## 3. Strict Storyboard Ownership Enforcements

All generators expect a mandatory `Storyboard` parameter, falling back to brief configurations ONLY if `storyboard` is explicitly `None` in standalone tests:
* `ThumbnailGenerator.generate(storyboard: Optional[Storyboard], brief: Brief)`
* `ScriptGenerator.generate(storyboard: Optional[Storyboard], brief: Brief, format: str)`
* `CarouselGenerator.generate(storyboard: Optional[Storyboard], brief: Brief)`
* `NewsletterGenerator.generate(storyboard: Optional[Storyboard], brief: Brief)`

In the runtime production pipeline, asset generation **never runs without a storyboard**.

---

## 4. UI Streamlit Integration Rules

1. **No direct generator calls:** Streamlit must never import or call `ThumbnailGenerator`, `ScriptGenerator`, or other generator instances directly. All generation calls must route through `AssetGenerationService.run(...)`.
2. **No raw writes:** All directory writes must use service boundaries.
3. **Workflow Integration:** `WorkflowStateManager` completed states are automatically checked and populated by the services. UI actions must not modify state files directly.
4. **Caching:** `@st.cache_resource` is used to load `ApplicationContext` once per session. Clear cache on mutations.
5. **Logs Piping:** Use `PipelineRunService` execution logs block to visualize running processes in real-time.
