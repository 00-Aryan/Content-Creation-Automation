# Content Intelligence Service Design

## Overview
`ContentIntelligenceService` is an application service that orchestrates the generation of `ContentIntelligence` artifacts from generated educational `Briefs`. It serves as the bridge between the **Brief** stage and the **Storyboard** stage in the content pipeline.

## Architectural Design

### 1. Service Inputs
The service public entry point will accept:
* `ctx: ApplicationContext`: Provides dependencies like storage, workflow state manager, and prompt registry.
* `top_n: int` (default: `5`): Maximum number of briefs to process in a single batch.
* `api_key: Optional[str]` (default: `None`): Explicit LLM API key, falling back to the `GEMINI_API_KEY` environment variable.
* `rate_limit_delay: float` (default: `5.0`): The sleep delay (in seconds) between LLM calls to respect API limits.

### 2. Service Outputs
The service returns a `ContentIntelligenceGenerationResult` object:
```python
@dataclass(frozen=True)
class ContentIntelligenceFailure:
    topic_id: str
    error: str

@dataclass(frozen=True)
class ContentIntelligenceGenerationResult:
    generated_count: int
    skipped_count: int
    failures: list[ContentIntelligenceFailure]
    content_intelligences: list[ContentIntelligence]
```

### 3. Required Dependencies
* `ContentIntelligenceGenerator`: For generating content intelligence via LLM integration.
* `ApplicationContext`: To access underlying configurations and shared resources.
* `LocalStorage`: For reading Briefs and Scored Topic Items, and persisting Content Intelligence results.
* `WorkflowStateManager`: For verifying state eligibility and updating workflow progression.

### 4. Storage Interactions
* **Reads**:
  * Scored topics via `ctx.storage.list_scored()` to extract `priority_score` (for sorting), `category` (to resolve `TopicType`), and `published_at` (to resolve `timeliness_hook`).
  * Upstream `Brief` artifacts matching the targeted topic IDs via direct filesystem file path checks or `ctx.storage.list_briefs()`.
* **Writes**:
  * Saves the generated `ContentIntelligence` instance to disk using `ctx.storage.save_content_intelligence(ci)`.

### 5. Workflow Interactions
* **Stage Eligibility Check**: For each topic, the service queries `ctx.workflow.stage_completed(topic_id, "content_intelligence")`.
* **State Updates**:
  * **On Success**: Invokes `ctx.workflow.mark_completed(topic_id, "content_intelligence", provider, retries, artifact_path)`.
  * **On Failure**: Invokes `ctx.workflow.mark_failed(topic_id, "content_intelligence", retries)`.

### 6. Error Handling Strategy
* Errors during the processing of a single brief are caught at the per-topic boundary.
* A single topic failure will log the error, record a `ContentIntelligenceFailure` entry, mark the workflow stage as `failed` for that topic, and safely proceed to the next item in the queue (non-blocking batch execution).
* Global configuration errors (e.g. missing API keys) will raise an immediate exception before processing begins.

### 7. Resume/Skip Behavior
* A topic is skipped if:
  * The workflow stage is already marked as `completed`.
  * The file `data/content_intelligence/{topic_id}.json` already exists in storage.
* If a previous run marked a stage as `failed`, the service will attempt to re-process it on the next execution.

### 8. Batch Processing & Prioritization Behavior
* The service reads all scored topics with status `SCORED`.
* It sorts them descending by `priority_score`.
* It filters this list to include only topics that have a generated `Brief` on disk.
* It slices the sorted list to the `top_n` candidate topics.
* It processes each eligible candidate sequentially up to the `top_n` limit.

### 9. Rate Limiting Behavior
* To prevent API exhaustion, the service introduces a `time.sleep(rate_limit_delay)` after each generation attempt.
* The delay is skipped if it is the last item in the batch.

### 10. Testing Strategy
* **Unit Tests**:
  * Verify that input arguments (API key validation, `top_n` slice) are correctly applied.
  * Verify prioritization ordering by mock-ing multiple briefs with varying priority scores.
  * Mock `ContentIntelligenceGenerator` to verify both successful returns and parsing/inference fallback cases.
  * Verify that completed stages or pre-existing files are skipped.
  * Check that `WorkflowStateManager` is updated correctly for both successful and failed iterations.

---

## Specific Architectural Questions

### A. Should ContentIntelligenceService consume Brief objects directly?
Yes, Content Intelligence is functionally a transformation of a `Brief`. At the generator level, it requires a `Brief`. At the orchestration service level, it loads and consumes `Brief` models as the core source artifact.

### B. Should it load Briefs from storage or accept them as arguments?
It should load `Brief` objects from storage using `ApplicationContext` matching existing application service patterns (e.g., `BriefGenerationService` which dynamically queries scored topics from storage). This guarantees a completely decoupled API where downstream pipelines only need to pass the context.

### C. Should workflow checks live inside the service?
Yes. Workflow checks (`stage_completed`, `mark_completed`, `mark_failed`) are core responsibilities of application services. Placing them inside `ContentIntelligenceService` makes the stage self-contained and aligns with the structure of `AssetGenerationService`.

### D. Should the service mirror BriefGenerationService structure?
Yes. The structure should directly mirror `BriefGenerationService` to ensure high architectural consistency, using similar failure classes, results classes, and method naming.

### E. What should the public run() signature be?
```python
def run(
    self,
    ctx: ApplicationContext,
    top_n: int = 5,
    api_key: Optional[str] = None,
    rate_limit_delay: float = 5.0,
) -> ContentIntelligenceGenerationResult:
```

---

## Final Verdict
**READY FOR IMPLEMENTATION**
