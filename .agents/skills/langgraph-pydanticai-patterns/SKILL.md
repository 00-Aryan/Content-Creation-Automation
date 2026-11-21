---
name: langgraph-pydanticai-patterns
description: Enforce current LangGraph (SqliteSaver, interrupt/Command, Send fan-out, typed reducers) and PydanticAI (output_type, UsageLimits, Ollama-hybrid fallback, TestModel, Langfuse OTel) patterns. Load whenever building, refactoring, verifying, or testing Phase 3 synthesis workflows, LLM agents, or observability hooks.
---

# LangGraph & PydanticAI Patterns

Modern architectural standards for Phase 3 synthesis workflows, stateful graph execution, human-in-the-loop gates, model tiering, and zero-leak observability.

## Mandatory Architecture Rules

### Rule 1 — Single-DB Checkpointing & Typed State (`SqliteSaver`)
*Rationale: In-memory checkpointers lose review state on restart; unvalidated state dictionaries cause runtime key errors and corrupt merges across parallel nodes.*
- **Do**: Back `SqliteSaver` with the single WAL-mode SQLite file (`data/content_factory.db`) using stable `config={"configurable": {"thread_id": topic_id}}`.
- **Do**: Define graph state with strict `TypedDict` or Pydantic v2 models and explicit reducers (`Annotated[list[AssetOutput], operator.add]`) for parallel fan-out branches.
- **Don't**: Mutate state dicts in place or pass unvalidated `dict[str, Any]` across graph nodes.

```python
# Pattern: Typed state with parallel fan-out reducer
class SynthesisState(TypedDict):
    topic_id: str
    active_formats: list[str]
    assets: Annotated[list[AssetOutput], operator.add]
    revision_count: int
```

### Rule 2 — Safe Human-in-the-Loop Steering (`interrupt()` + `Command(resume=...)`)
*Rationale: Resuming via `Command(resume=...)` re-executes the interrupted node from line 1; executing side effects before `interrupt()` triggers duplicate runs.*
- **Do**: Use `from langgraph.types import Command, interrupt` with JSON-serializable payloads for human review or steering overrides.
- **Do**: Isolate `interrupt()` inside dedicated gate nodes with zero side effects so resumption from line 1 does not re-invoke LLMs, writes, or DB updates.
- **Don't**: Place LLM calls, filesystem writes, or database mutations before `interrupt()` inside the same node.

```python
# Pattern: Isolated review gate node
def review_gate_node(state: SynthesisState) -> Command[Literal["synthesize", "reject"]]:
    decision = interrupt({"topic_id": state["topic_id"], "review_data": state["summary"]})
    return Command(goto="synthesize" if decision.get("approved") else "reject")
```

### Rule 3 — Parallel Channel Fan-Out (`Send()`) & Bounded Critic Loops
*Rationale: Monolithic synthesis serializes independent formats; unbounded review cycles lead to infinite graph loops and wallet exhaustion.*
- **Do**: Use `from langgraph.types import Send` in conditional edges to dispatch active formats (`youtube_short`, `instagram_reel`, `instagram_carousel`, `facebook_reel`) while skipping `in_progress` formats (`linkedin_post`, `newsletter`).
- **Do**: Track an explicit `revision_count: int` in state and enforce a hard conditional exit at `revision_count >= 2`.
- **Don't**: Allow recursive Critic or refinement edges without decrementing/incrementing a hard bounded loop counter.

```python
# Pattern: Parallel Send fan-out and bounded Critic exit
def fan_out_channels(state: SynthesisState) -> list[Send]:
    return [Send("synthesize_asset", {"format": fmt}) for fmt in state["active_formats"]]

def route_critic_result(state: SynthesisState) -> str:
    if state["revision_count"] >= 2 or state.get("passed_critic", False):
        return "format_outputs"
    return "revise_asset"
```

### Rule 4 — Current PydanticAI Contracts, `UsageLimits` & Hybrid Tiering
*Rationale: Deprecated APIs (`result_type`, `result.data`) break in modern PydanticAI; unbudgeted LLM calls risk runaway token burn.*
- **Do**: Use modern `Agent(..., output_type=MyModel, defer_model_check=True, retries=2)` and access typed output via `result.output` (never deprecated `result_type` or `result.data`).
- **Do**: Pass `usage_limits=UsageLimits(...)` on every invocation to enforce request and token ceilings.
- **Do**: Restrict local Ollama (`OllamaModel` at `http://127.0.0.1:11434/v1`) with `NativeOutput(Schema)` strictly to Tier-0 basic triage (spam/dedup/tag only — never final scripts or Critic scoring), paired with `FallbackModel` to cloud models (`google:...`, `openrouter:...`) when offline.
- **Do**: In `pytest`, always mock LLM interactions via `agent.override(model=TestModel())` or `FunctionModel` — zero live network or Ollama calls in tests.
- **Don't**: Use deprecated `result_type`, access `result.data`, or use local Ollama models for final educational scripts or Critic scoring.

```python
# Pattern: Modern agent contract with usage limits
agent = Agent("google-gla:gemini-2.5-flash", output_type=ScriptSchema, retries=2)
result = await agent.run(prompt, usage_limits=UsageLimits(request_limit=3, total_tokens_limit=4000))
script = result.output  # Strictly result.output
```

### Rule 5 — Env-Gated Langfuse OpenTelemetry Observability
*Rationale: Ungated instrumentation causes unauthenticated network errors, slow test suites, and noisy log warnings in offline and CI environments.*
- **Do**: Wire tracing through `langfuse.get_client()` + `Agent.instrument_all()` (or `instrument=True` per agent) so PydanticAI emits standard OTel spans automatically.
- **Do**: Gate initialization strictly behind `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` being present in environment, and disable completely if `PYTEST_CURRENT_TEST` is detected.
- **Don't**: Initialize Langfuse clients or emit telemetry when credentials are missing or during test execution.

```python
# Pattern: Env-gated Langfuse initialization
if os.getenv("LANGFUSE_PUBLIC_KEY") and not os.getenv("PYTEST_CURRENT_TEST"):
    Agent.instrument_all()
```

## Quick Verification Checklist

Before finishing any Phase 3 task, `refactor-executor`, `contract-verifier`, and `qa-test-engineer` must scan:
1. **[ ] SqliteSaver WAL**: Checkpointing uses `SqliteSaver` on `data/content_factory.db` with `thread_id` in config.
2. **[ ] Isolated `interrupt()`**: Review nodes contain only `interrupt()` with zero prior side effects (safe idempotency).
3. **[ ] Bounded Fan-Out**: Active channels fan out via `Send()`; Critic loops hard-exit when `revision_count >= 2`.
4. **[ ] Modern PydanticAI**: Uses `output_type`, `result.output`, `UsageLimits`, and `TestModel` in tests (zero live calls).
5. **[ ] Env-Gated Langfuse**: Observability is active only when credentials exist and suppressed during pytest runs.
