# ADR 004: Unified LLM Cost Governance, Metered Gateway & Offline-First Evaluation Harness

- **Status:** PROPOSED
- **Date:** 2026-11-21
- **Deciders:** `spec-architect`, `prompt-eval-auditor`, `phase-orchestrator`
- **Target Phase:** Phase 3A / Cross-Phase Observability
- **Consulted:** `.agents/skills/security-and-cost-guard/SKILL.md`, `.agents/agents/prompt-eval-auditor.md`, `docs/refactor/adrs/001-native-fragments-and-ui-facades.md`, `docs/refactor/adrs/003-single-wal-sqlite-database.md`

---

## 1. Context & Problem Statement

The `Content-Creation-Automation` platform is evolving from template-driven generation and basic collectors toward agentic multi-stage synthesis (Phase 3A LangGraph state machines) and domain-specific rankers (Phase G1/G2 Gaming Clips Lore Rankers). These pipelines depend heavily on Large Language Models (LLMs) for topic ideation, evidence extraction, script authoring, hook generation, and quality grading.

However, operating agentic LLM loops without rigorous cost governance, token metering, and automated evaluation introduces severe operational, financial, and architectural liabilities:

1. **Strict Hardware & Budget Ceilings (Low-Config Host Constraints):**
   - The primary development and production host is constrained to:
     - **CPU:** AMD Ryzen 5 7600X (6 cores / 12 threads)
     - **RAM:** **8 GB DDR5** (strictly bounded resident memory budget)
     - **Disk:** 256 GB NVMe SSD
     - **OS:** Windows 11 (PowerShell / Windows-first Python runtime)
   - Traditional LLM observability stacks (e.g., self-hosted Langfuse servers, OpenTelemetry collectors, ClickHouse clusters, Prometheus, Grafana, or Docker daemons) require 4–8 GB RAM alone, which would immediately induce paging, disk thrashing, and memory crashes (`[WinError 1455]`).
   - **Zero Paid API Spend Mandate:** The project strictly operates under a **zero paid API spend** policy during development and validation. All development, testing, and continuous integration must utilize free API tiers (Google AI Studio Gemini Flash free tier, OpenRouter `:free` models, Groq free tier) or offline test doubles (`TestModel`, synthetic JSON/text fixtures).
2. **The "Shadow Cost" Visibility Blindspot:**
   - Free tiers provide zero monetary invoices. If token consumption is unmetered during free-tier operation, prompts and agent loops expand unchecked. When transitioning to production workloads or paid API tiers, token bloat converts directly into runaway API bills ("denial of wallet").
   - Without a *shadow costing* mechanism, engineers cannot calculate the true production cost per script, cost per topic, or evaluate whether prompt optimizations reduce financial overhead.
3. **Runaway Loops and Fragile Retry Cascades:**
   - Naive retry loops (e.g., retrying blindly on HTTP 429 quota exhaustion or retrying uncorrectable Pydantic validation errors) burn token quotas in seconds and trigger cascading rate-limit blocks across subsequent pipeline stages.
   - PydanticAI and LangGraph workflows require deterministic circuit breakers at both the per-call and per-artifact lifecycle boundaries.
4. **Offline Evaluation Deficit:**
   - Evaluating prompt revisions and model outputs manually or through live paid calls violates both reproducibility and budget mandates. The system requires an offline-first evaluation harness that leverages deterministic Python checks and calibrated rubric grading against static golden fixtures.

---

## 2. Decision Drivers

- **Local-First & Zero-Docker Architecture:** Observability, metering, and evaluation persistence must reside strictly within SQLite (`data/content_factory.db` in WAL mode per ADR-003) and render via Streamlit fragments (`@st.fragment` per ADR-001). No external background services, daemon containers, or heavy memory hogs.
- **Unified Metered Gateway & Shadow Cost Accounting:** Every outbound LLM interaction must flow through a centralized gateway that calculates actual cost ($0.00 for free tiers) and shadow cost (projected commercial pricing based on `config/model_prices.json`).
- **4-Layer Defense-in-Depth Circuit Breakers:** Protect the system from runaway generation via:
  1. Per-call `max_output_tokens` stage caps.
  2. Smart retry matrix (class-specific retry limits; zero retries on rate limits; max 1 reflection retry on schema error).
  3. Per-artifact `RunBudget` (enforcing PydanticAI `UsageLimits`).
  4. Global daily kill switch queried atomically from SQLite before execution.
- **Alignment with Repository Standards:** Strict adherence to `.agents/skills/security-and-cost-guard/SKILL.md` (secret scrubbing, budget caps, sanitized error mapping), `.agents/agents/prompt-eval-auditor.md` (two-pass evaluation: deterministic pre-audit + 5-dimension rubric), and `AGENTS.md` (no secret exposure).
- **Zero UI DDL & Clean Facade Routing:** All evaluation summaries and cost charts displayed in the Streamlit UI must query through `ServiceClient` with zero inline DDL in the rendering path.

---

## 3. Architecture Overview

```
                      +-------------------------------------------------------+
                      |                 Client Invocation                     |
                      |  (LangGraph Node / Stage 2 Generator / Lore Ranker)   |
                      +---------------------------+---------------------------+
                                                  |
                                                  v
                      +-------------------------------------------------------+
                      |         Layer 4: Global Daily Kill Switch             |
                      |   Check SUM(shadow_cost_usd) for UTC Day in SQLite    |
                      +---------------------------+---------------------------+
                                                  | [Budget OK]
                                                  v
                      +-------------------------------------------------------+
                      |           Layer 3: Artifact RunBudget Gate            |
                      |   Validate accumulated tokens/requests < RunBudget    |
                      +---------------------------+---------------------------+
                                                  | [Within Budget]
                                                  v
                      +-------------------------------------------------------+
                      |          Layer 1 & 2: Metered LLM Gateway             |
                      |  - Enforce per-stage max_output_tokens                |
                      |  - Execute request with Smart Retry Matrix            |
                      |  - Capture exact latency_ms, prompt & completion tok  |
                      +---------------------------+---------------------------+
                                                  |
                                                  v
                      +-------------------------------------------------------+
                      |               Shadow Costing Engine                   |
                      |  - Lookup rates from config/model_prices.json         |
                      |  - Calculate actual_cost_usd (0.0 for free tier)      |
                      |  - Calculate shadow_cost_usd (commercial equivalent)  |
                      +---------------------------+---------------------------+
                                                  |
                                                  v
                      +-------------------------------------------------------+
                      |       WAL-Mode SQLite (data/content_factory.db)       |
                      |       INSERT INTO llm_usage_ledger (...)              |
                      +---------------------------+---------------------------+
                                                  |
                         +------------------------+------------------------+
                         |                                                 |
                         v                                                 v
+-------------------------------------------------+     +-------------------------------------+
|        Streamlit Cost & Eval Dashboard          |     |     Offline-First Eval Harness      |
|  - Daily Budget Gauge                           |     |  - Golden Dataset Fixture Runs      |
|  - Cost-per-Script Stage Breakdown              |     |  - Pass 1: Deterministic Pre-Audit  |
|  - Retry Waste % KPI                            |     |  - Pass 2: 5-Dim Rubric (EvalRuns)  |
|  - Prompt Version A/B Comparison Table          |     |  - Writes to eval_runs in SQLite    |
|  (Streamlit @st.fragment via ServiceClient)     |     +-------------------------------------+
+-------------------------------------------------+
```

---

## 4. Decision 1 — Metered LLM Gateway & Shadow Costing

### 4.1 Model Pricing Catalog (`config/model_prices.json`)

To prevent hardcoding price assumptions across generators, all token costs and free-tier limits are declared in a versioned configuration file `config/model_prices.json`.

```json
{
  "version": "1.0.0",
  "updated_at": "2026-11-21T00:00:00Z",
  "models": {
    "gemini-2.0-flash": {
      "provider": "google",
      "tier": "free",
      "input_cost_per_million": 0.10,
      "output_cost_per_million": 0.40,
      "free_tier_rpm": 15,
      "free_tier_tpm": 1000000,
      "free_tier_rpd": 1500,
      "context_window": 1048576,
      "effective_date": "2026-01-01"
    },
    "gemini-1.5-flash": {
      "provider": "google",
      "tier": "free",
      "input_cost_per_million": 0.075,
      "output_cost_per_million": 0.30,
      "free_tier_rpm": 15,
      "free_tier_tpm": 1000000,
      "free_tier_rpd": 1500,
      "context_window": 1048576,
      "effective_date": "2026-01-01"
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
      "provider": "openrouter",
      "tier": "free",
      "input_cost_per_million": 0.35,
      "output_cost_per_million": 0.40,
      "free_tier_rpm": 20,
      "free_tier_tpm": 200000,
      "free_tier_rpd": 200,
      "context_window": 131072,
      "effective_date": "2026-01-01"
    },
    "groq/llama-3.1-8b-instant": {
      "provider": "groq",
      "tier": "free",
      "input_cost_per_million": 0.05,
      "output_cost_per_million": 0.08,
      "free_tier_rpm": 30,
      "free_tier_tpm": 30000,
      "free_tier_rpd": 14400,
      "context_window": 131072,
      "effective_date": "2026-01-01"
    }
  }
}
```

### 4.2 Unified `LLMUsageRecord` Pydantic v2 Schema

Every call executed through the gateway emits a validated `LLMUsageRecord`.

```python
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class LLMUsageRecord(BaseModel):
    """Immutable ledger record representing a single outbound LLM invocation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str = Field(description="Unique UUID4 string for this invocation")
    stage_name: str = Field(description="Pipeline stage identifier, e.g., stage_1_brief, stage_2_script, lore_ranker")
    provider: str = Field(description="LLM provider name, e.g., google, openrouter, groq, local")
    model_name: str = Field(description="Canonical model identifier")
    tier_type: Literal["free", "paid", "offline_mock"] = Field(
        default="free",
        description="Billing tier under which this call executed",
    )
    prompt_tokens: int = Field(ge=0, description="Tokens in input prompt")
    completion_tokens: int = Field(ge=0, description="Tokens generated in output response")
    total_tokens: int = Field(ge=0, description="Sum of prompt and completion tokens")
    actual_cost_usd: float = Field(
        ge=0.0,
        default=0.0,
        description="Actual dollars billed for this call (0.0 on free tiers)",
    )
    shadow_cost_usd: float = Field(
        ge=0.0,
        description="Calculated production cost if run under commercial API rates",
    )
    latency_ms: int = Field(ge=0, description="End-to-end execution latency in milliseconds")
    status: Literal["success", "retry_schema", "rate_limited", "timeout", "failed"] = Field(
        description="Final execution outcome",
    )
    attempt_number: int = Field(ge=1, default=1, description="Attempt number within retry policy")
    prompt_version: str = Field(default="v1.0.0", description="Git commit hash or semantic version of prompt")
    artifact_id: Optional[str] = Field(default=None, description="Target asset/script ID if applicable")
    topic_id: Optional[str] = Field(default=None, description="Source topic ID if applicable")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of invocation completion",
    )
```

### 4.3 SQLite DDL for `data/content_factory.db`

Per ADR-003, all operational tables reside in `data/content_factory.db`. The `llm_usage_ledger` and `eval_runs` schemas are defined below:

```sql
-- LLM Usage Ledger: Comprehensive append-only telemetry for cost & quota tracking
CREATE TABLE IF NOT EXISTS llm_usage_ledger (
    call_id TEXT PRIMARY KEY,
    stage_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    tier_type TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    actual_cost_usd REAL NOT NULL DEFAULT 0.0,
    shadow_cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    status TEXT NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    prompt_version TEXT NOT NULL DEFAULT 'v1.0.0',
    artifact_id TEXT,
    topic_id TEXT,
    created_at TEXT NOT NULL
);

-- Fast analytical indices for dashboard aggregations and daily kill switches
CREATE INDEX IF NOT EXISTS idx_llm_ledger_created_at ON llm_usage_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_ledger_stage_name ON llm_usage_ledger(stage_name);
CREATE INDEX IF NOT EXISTS idx_llm_ledger_model_name ON llm_usage_ledger(model_name);
CREATE INDEX IF NOT EXISTS idx_llm_ledger_artifact_id ON llm_usage_ledger(artifact_id);
CREATE INDEX IF NOT EXISTS idx_llm_ledger_topic_id ON llm_usage_ledger(topic_id);

-- Evaluation Runs: Stores offline-first evaluation harness outputs
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT PRIMARY KEY,
    stage_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    rubric_score REAL NOT NULL,
    hook_score REAL NOT NULL,
    grounding_score REAL NOT NULL,
    cliche_score REAL NOT NULL,
    pacing_score REAL NOT NULL,
    efficiency_score REAL NOT NULL,
    schema_passed INTEGER NOT NULL,
    retry_waste_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0.0,
    shadow_cost_usd REAL NOT NULL DEFAULT 0.0,
    audit_report_path TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_stage_version ON eval_runs(stage_name, prompt_version);
CREATE INDEX IF NOT EXISTS idx_eval_runs_created_at ON eval_runs(created_at);
```

---

## 5. Decision 2 — 4-Layer Circuit Breakers (Hard Stopping Points)

To guarantee that runaway LLM execution cannot exhaust free quotas, hang system threads, or leak costs, the system introduces a 4-layer defense-in-depth circuit breaker architecture:

```
+-----------------------------------------------------------------------------------+
|                           LAYER 4: GLOBAL DAILY KILL SWITCH                       |
|   Query SQLite: If SUM(shadow_cost_usd) > $5.00/day OR tokens > 1M/day -> HALT    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        LAYER 3: PER-ARTIFACT RUN BUDGET                           |
|   Enforce PydanticAI UsageLimits: max_total_tokens <= 12,000, max_requests <= 6   |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         LAYER 2: SMART RETRY MATRIX                               |
|   Schema error: max 1 retry | 429 Rate Limit: 0 retry (fallback) | 5xx: max 2 exp  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       LAYER 1: PER-CALL OUTPUT TOKEN CAPS                         |
|   Hard max_output_tokens per stage: Hook (512), Script (1200), Carousel (1500)   |
+-----------------------------------------------------------------------------------+
```

### 5.1 Layer 1: Per-Call `max_output_tokens` Caps by Pipeline Stage

Generators must never request unbounded token completions. Every call enforces an explicit upper bound based on task characteristics:

| Pipeline Stage / Node | Output Contract | `max_output_tokens` Cap | Rationale |
| :--- | :--- | :---: | :--- |
| **Stage 1: Topic Normalizer** | `TopicItem` metadata | **512** | Topic metadata extraction requires concise JSON. |
| **Stage 1.5: Evidence Briefing** | `EvidenceBundle` summary | **1,024** | Grounding synthesis with key technical claims and numbers. |
| **Stage 2: Short Script Generator** | Spoken script + visual cues | **1,200** | Standard 50-60s Short (140-160 words) + visual cues. |
| **Stage 2: Carousel Generator** | 5–8 slides structure | **1,500** | Up to 8 slides with slide text, visual layout, and caption. |
| **Phase 3A: LangGraph Synthesis Node** | Agent domain step | **1,024** | Focused task execution per sub-agent state transition. |
| **Phase G1/G2: Gaming Clips Lore Ranker** | Hook score + lore rank | **512** | Structured rating JSON with 1-sentence reasoning. |

### 5.2 Layer 2: Smart Retry Matrix

Blind retries violate `.agents/skills/security-and-cost-guard/SKILL.md` Rule 5. The gateway dispatches errors according to strict failure classes:

| Error Category | HTTP / Exception Code | Max Retries | Backoff Strategy | Action / Mitigation |
| :--- | :--- | :---: | :--- | :--- |
| **Pydantic Validation** | `ValidationError` | **1** | Immediate reflection | Feed exact validation error diff back to LLM in single repair attempt; abort if second attempt fails. |
| **Rate Limit / Quota** | HTTP `429` / ResourceExhausted | **0** | No retry on same model | Instantly route to fallback free provider (e.g., Gemini -> Groq Llama 3) if configured; otherwise fail fast with `RateLimitExceededError`. |
| **Server Timeout / Error**| HTTP `500`, `502`, `503`, `504` | **2** | Bounded exponential backoff + jitter (1s, 3s) | Network or transient provider outage; fail fast if unresolved after 2 attempts. |
| **Permanent / Auth / Gate** | HTTP `401`, `403`, Safety Filter | **0** | No retry | Abort immediately; record security failure in telemetry; checkpoint current state. |

### 5.3 Layer 3: Per-Artifact `RunBudget` (PydanticAI `UsageLimits` Alignment)

In multi-agent synthesis loops (Phase 3A), a rogue agent loop could repeatedly invoke models. Each artifact generation task is bounded by an explicit `RunBudget` that aligns with PydanticAI's native `UsageLimits`:

```python
from dataclasses import dataclass
from content_creation.core.exceptions import BudgetExceededError


@dataclass(frozen=True)
class RunBudget:
    """Resource budget allocated to a single artifact generation workflow."""

    max_requests: int = 6
    max_total_tokens: int = 12000
    max_shadow_cost_usd: float = 0.05
    max_revisions: int = 2

    def check_limits(self, requests: int, total_tokens: int, shadow_cost: float) -> None:
        if requests > self.max_requests:
            raise BudgetExceededError(f"Request count {requests} exceeded budget {self.max_requests}")
        if total_tokens > self.max_total_tokens:
            raise BudgetExceededError(f"Total tokens {total_tokens} exceeded budget {self.max_total_tokens}")
        if shadow_cost > self.max_shadow_cost_usd:
            raise BudgetExceededError(f"Shadow cost ${shadow_cost:.4f} exceeded budget ${self.max_shadow_cost_usd:.4f}")
```

### 5.4 Layer 4: Daily Global Kill Switch

Before executing *any* outbound LLM call, the gateway executes an atomic read query against `data/content_factory.db`:

```sql
SELECT
    COALESCE(SUM(shadow_cost_usd), 0.0) as daily_shadow_cost,
    COALESCE(SUM(total_tokens), 0) as daily_tokens
FROM llm_usage_ledger
WHERE created_at >= strftime('%Y-%m-%dT00:00:00Z', 'now');
```

- **Default Ceilings:**
  - `DAILY_MAX_SHADOW_COST_USD` = **$5.00**
  - `DAILY_MAX_TOKENS` = **1,000,000 tokens**
- If the current sum exceeds either ceiling, the call is blocked immediately with `DailyBudgetCapExceededError`, and an alert notification is emitted to `notifications.db`.

---

## 6. Decision 3 — Offline-First Evaluation Harness & Cost Dashboard

### 6.1 Golden Fixture Evaluation Workflow

Aligning with `.agents/agents/prompt-eval-auditor.md`, the evaluation harness runs offline against static golden datasets stored in `tests/fixtures/eval/`:
- `golden_topics.json`: Pre-ingested, normalized ML/AI research topics.
- `golden_evidence_bundles.json`: Source-grounded quotes, benchmarks, and claims.
- `golden_scripts.json`: Reference baseline scripts with human review ratings.

The harness executes the standard **Two-Pass Audit**:

```
[Golden Test Fixture] ---> [Pass 1: Deterministic Python Pre-Audit]
                                  │
                                  ├─ WPM & Duration Math (140-160 WPM, <58s)
                                  ├─ AI Cliché & Slop Regex Scan (zero banned phrases)
                                  ├─ Prompt Token Footprint & Rule Count
                                  └─ Concrete Claim Extraction
                                  │
                                  v
                             [Pass 2: 5-Dimension Monetization Rubric]
                                  │
                                  ├─ Dim 1: 0-3s Hook & Retention (25%)
                                  ├─ Dim 2: Evidence Grounding (25% HARD GATE)
                                  ├─ Dim 3: Natural Spoken Voice (20%)
                                  ├─ Dim 4: Director Cut Density (20%)
                                  └─ Dim 5: Token & Prompt Efficiency (10%)
                                  │
                                  v
                             [eval_runs record written to content_factory.db]
```

### 6.2 Key Operational Metrics

The evaluation harness computes and tracks 4 core KPIs across prompt iterations and model upgrades:

1. **`schema_pass_rate`:**
   $$\text{Schema Pass Rate} = \frac{\text{Runs with 0 Pydantic Validation Retries}}{\text{Total Runs}} \times 100\%$$
   *Threshold:* $\ge 95\%$.
2. **`avg_rubric_score`:**
   Weighted aggregate score out of 10.0 across all 5 dimensions.
   *Threshold:* $\ge 8.0 / 10.0$ (with 0 grounding gate failures).
3. **`avg_tokens_per_item`:**
   Mean total tokens consumed per completed artifact.
   *Target:* $\le 3,500$ tokens for short-form video scripts.
4. **`retry_waste_pct`:**
   $$\text{Retry Waste \%} = \frac{\text{Tokens burned on retries and failed calls}}{\text{Total Tokens consumed}} \times 100\%$$
   *Threshold:* $\le 5.0\%$.

### 6.3 Streamlit Cost & Evaluation Dashboard Specification

Adhering strictly to ADR-001 (`ServiceClient` facade + `@st.fragment`), the Cost & Evaluation Dashboard provides real-time operational visibility without executing DDL or opening raw database connections inside render loops:

```
+--------------------------------------------------------------------------------------------------+
| Streamlit Operations Hub: Cost & Evaluation Governance (Fragment)                                 |
+--------------------------------------------------------------------------------------------------+
| [Daily Shadow Spend: $1.24 / $5.00]  [Tokens Today: 248k / 1.0M]  [Retry Waste: 2.1% (Healthy)]  |
| [====================================>                                     ] 24.8% of daily cap  |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
| Stage Cost Breakdown (Stacked Bar)                     Prompt A/B Version Comparison             |
| +-------------------------------------------------+    +---------------------------------------+ |
| | Stage 1 (Briefing):       $0.0024               |    | Ver   Model      Score  Tokens  Waste | |
| | Stage 2 (Script Hook):    $0.0082               |    | v1.0  Gemini-2.0 8.6    3,100   1.8%  | |
| | Stage 2 (Visual Beats):   $0.0041               |    | v1.1  Llama-3.3  8.2    3,850   4.2%  | |
| | Eval Runs (Pass 1 & 2):   $0.0010               |    | v0.9  Gemini-1.5 7.4    4,200   7.6%  | |
| +-------------------------------------------------+    +---------------------------------------+ |
+--------------------------------------------------------------------------------------------------+
```

- **UI Facade Methods on `ServiceClient`:**
  - `get_daily_budget_summary() -> DailyBudgetSummary`
  - `get_stage_cost_breakdown(start_date, end_date) -> list[StageCostSummary]`
  - `get_prompt_evaluation_matrix() -> list[PromptVersionMatrix]`
- **Render Hygiene:** Decorated with `@st.fragment(run_every="30s")` for partial refresh, avoiding full Streamlit page reruns.

---

## 7. Consequences & Trade-Offs

### Positive Consequences
- **Financial Protection:** Eliminates the risk of surprise billing when switching from free tiers to commercial API keys.
- **Hardware Compatibility:** Operates 100% within the 8 GB RAM / Windows host ceiling with zero Docker or memory-heavy external services.
- **Early Drift Detection:** Catches prompt degradation, cliché accumulation, and token bloat before code merges via the offline evaluation harness.
- **Auditability:** Complete, immutable lineage in `llm_usage_ledger` correlating prompt versions, tokens, latency, and cost to specific generated scripts.

### Negative Consequences & Mitigations
- **Database File Growth:** High-volume batch runs append records to `content_factory.db`.
  - *Mitigation:* SQLite indexes are scoped to analytical fields; historical usage data older than 90 days can be rolled up into daily aggregate summaries if needed.
- **Latency Overhead:** Running pre-flight daily budget checks and post-call ledger inserts adds ~2–5 ms per LLM call.
  - *Mitigation:* Negligible compared to network LLM inference latencies (500–2,000 ms). SQLite WAL mode ensures non-blocking concurrent writes.

---

## 8. Phased Implementation Hooks

| Phase | Module / Target | Implementation Hook |
| :--- | :--- | :--- |
| **Phase 2C** | `src/content_creation/core/db/` | Add `create_llm_governance_schema(conn)` to consolidated SQLite migration in `data/content_factory.db` per ADR-003. |
| **Phase 3A** | `src/content_creation/synthesis/gateway.py` | Implement `MeteredLLMGateway` wrapping PydanticAI / LangGraph nodes with `LLMUsageRecord` telemetry, `RunBudget`, and 4-layer breakers. |
| **Phase 3A** | `src/content_creation/synthesis/eval_harness.py`| Implement the offline two-pass evaluation harness against `tests/fixtures/eval/`. |
| **Phase G1/G2**| `src/content_creation/gaming_clips/ranker.py` | Bind the Gaming Clips Lore Ranker to `MeteredLLMGateway` using the 512-token cap and free tier fallback. |
| **UI Integration** | `src/content_creation/ui/views/cost_governance.py` | Render the Streamlit Cost & Eval Dashboard via `ServiceClient` using `@st.fragment`. |

---

## 9. Compliance & Verification Checklist

Before completing tasks implementing this ADR, verify:
- [ ] **Secret Hygiene (`AGENTS.md` §6.2):** Zero API keys logged, printed, or persisted in `llm_usage_ledger`.
- [ ] **Hardware Ceiling:** Peak process RAM remains $\le 2\text{ GB}$ (host total $\le 8\text{ GB}$); zero external Docker containers.
- [ ] **Zero UI DDL:** Streamlit cost dashboard runs read queries only; zero schema checks in UI render loops.
- [ ] **Offline Testing:** Unit tests in `tests/test_llm_governance.py` run 100% offline using `tmp_path` and `TestModel`.
