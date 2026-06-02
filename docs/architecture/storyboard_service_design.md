# Storyboard Service Design

## Overview
`StoryboardService` is an application service that orchestrates the generation of `Storyboard` artifacts. It consumes both the upstream `Brief` and `ContentIntelligence` artifacts to lay out format-specific hooks, claims, call-to-actions (CTAs), and visual guidelines for final asset production.

## Architectural Design

### 1. Service Inputs
The public service `run()` entry point will accept:
* `ctx: ApplicationContext`: Provides dependencies like storage, workflow state manager, and prompt registry.
* `top_n: int` (default: `5`): Maximum number of storyboards to generate in a batch.
* `api_key: Optional[str]` (default: `None`): API key for LLM generation, falling back to the `GEMINI_API_KEY` environment variable.
* `rate_limit_delay: float` (default: `5.0`): The sleep delay (in seconds) between LLM calls to respect API limits.

### 2. Service Outputs
The service returns a `StoryboardGenerationResult` object:
```python
@dataclass(frozen=True)
class StoryboardFailure:
    topic_id: str
    error: str

@dataclass(frozen=True)
class StoryboardGenerationResult:
    generated_count: int
    skipped_count: int
    failures: list[StoryboardFailure]
    storyboards: list[Storyboard]
```

### 3. Required Dependencies
* `StoryboardGenerator`: For constructing storyboard content via LLM and rules.
* `ApplicationContext`: To access underlying configurations and shared resources.
* `LocalStorage`: For reading Briefs, Content Intelligence, and Scored Topic Items, and persisting Storyboards.
* `WorkflowStateManager`: For verifying state eligibility and updating workflow progression.

### 4. Storage Interactions
* **Reads**:
  * Generated Content Intelligence artifacts via `ctx.storage.list_content_intelligence()`.
  * Generated `Brief` artifacts matching the targeted topic IDs via `ctx.storage.get_brief()`.
  * Scored topics via `ctx.storage.get_scored()` or `ctx.storage.get_staged()` to retrieve `priority_score` (for sorting and batch slicing).
* **Writes**:
  * Saves the generated `Storyboard` instance to disk using `ctx.storage.save_storyboard(sb)`.

### 5. Workflow Interactions
* **Stage Eligibility Check**: For each topic, the service queries `ctx.workflow.stage_completed(topic_id, "storyboard")`.
* **State Updates**:
  * **On Success**: Invokes `ctx.workflow.mark_completed(topic_id, "storyboard", provider, retries, artifact_path)`.
  * **On Failure**: Invokes `ctx.workflow.mark_failed(topic_id, "storyboard", retries)`.

### 6. Skip/Resume Behavior
* A topic is skipped if:
  * The workflow state reports that the `"storyboard"` stage is `completed` for the given topic.
  * The file `data/storyboards/{topic_id}.json` already exists in storage.
* If a previous execution marked the stage as `failed`, the service will attempt to re-process it in the next run.

### 7. Batch & Prioritization Behavior
* The service reads all generated `ContentIntelligence` items.
* It filters candidate topics to those that have both a generated `Brief` and a generated `ContentIntelligence` on disk.
* It resolves the corresponding `ScoredTopicItem` to extract the `priority_score`.
* It sorts candidate items descending by `priority_score`.
* It slices the candidates to the `top_n` limit and processes them sequentially.

### 8. Error Handling Strategy
* Errors during the processing of a single storyboard are caught at the per-topic boundary.
* A single topic failure will log the error, record a `StoryboardFailure` entry, mark the workflow stage as `failed` for that topic, and safely proceed to the next candidate in the queue (non-blocking batch execution).
* Global configuration errors (e.g. missing API keys) will raise an immediate exception before processing begins.

### 9. Relationship Between Brief and Content Intelligence
* A `Brief` contains the high-level educational content structure, takeaways, analogy, and format suggestions.
* A `ContentIntelligence` contains the derived emotional register, timeliness hooks, curiosity gap, and classification tags.
* The `Storyboard` sits downstream from both and acts as their synthesiser. It combines hooks and registers from `ContentIntelligence` with the educational concepts and format recommendations from the `Brief` to design format-specific hooks, claims, call-to-actions (CTAs), and visual guidelines.

### 10. Storyboard Ownership Boundaries
* **Orchestration**: Managed by `StoryboardService`. It owns loading inputs, resolving priorities, managing limits, skipping, rate limiting, and updating workflow states.
* **Composition/Generation**: Managed by `StoryboardGenerator`. It owns template management, prompt replacements, deterministic mapping, visual style rules, visual metaphor extraction, and invoking inference boundaries.
* **Persistence**: Managed by `StoryboardRepository` via `LocalStorage`. It owns directories, file mapping, and serialization formats.
* **Resumability Logs**: Managed by `WorkflowStateManager`. It owns status logs on disk.

---

## Specific Architectural Questions

### A. Should StoryboardService consume both Brief and Content Intelligence?
Yes. The domain generator `StoryboardGenerator.generate(brief, ci)` requires both models as arguments to perform deterministic allocations (like visual style mapping) and LLM prompt template renders. Therefore, the orchestration service must fetch and supply both.

### B. Should StoryboardService load dependencies from storage?
Yes. It should load both `Brief` and `ContentIntelligence` models from storage using the `ApplicationContext` container, matching the decoupled pattern of existing services.

### C. Should workflow checks live inside the service?
Yes. Workflow state eligibility validation and logging (`stage_completed`, `mark_completed`, `mark_failed`) are core orchestration responsibilities and should reside directly inside the `StoryboardService`.

### D. Should StoryboardService mirror ContentIntelligenceService patterns?
Yes. Mirroring these patterns guarantees a highly consistent application service layer across all completion pipeline stages.

### E. What should the public run() signature be?
```python
def run(
    self,
    ctx: ApplicationContext,
    top_n: int = 5,
    api_key: Optional[str] = None,
    rate_limit_delay: float = 5.0,
) -> StoryboardGenerationResult:
```

### F. What data contract should AssetGenerationService eventually consume?
`AssetGenerationService` will consume the `Storyboard` model instead of the `Brief` model. The `Storyboard` specifies the exact allocation of claims, hooks, CTAs, visual styles, and visual metaphors to individual formats, making it the canonical plan for assets generation.

---

## Final Verdict
**READY FOR IMPLEMENTATION**
