# Mutation Testing Readiness Audit

**Date:** 2026-06-02  
**Role:** Test Quality Specialist  
**Baseline:** 194 tests passing, **62%** line coverage ([test_coverage_completeness.md](./test_coverage_completeness.md))  
**Tools referenced:** [mutmut](https://mutmut.readthedocs.io/), [cosmic-ray](https://cosmic-ray.readthedocs.io/) (not installed in project today)  
**Scope:** Review assertions, mocks, fixtures; estimate ability to kill realistic mutants. **No code or config changes.**

---

## 1. Executive summary

| Dimension | Assessment |
|-----------|------------|
| **Mutation readiness** | **Moderate** — suite is strong for domain logic and inference orchestration, weak for CLI/workflow and anything behind class-level `InferenceManager` mocks. |
| **Estimated mutation score (first run)** | **42–55%** on `src/content_creation` (proportion of mutants killed) |
| **Estimated survival hotspots** | `cli.py`, `workflow/state.py`, provider HTTP bodies, `JsonRepository` error branches, generator→manager wiring |
| **Recommended before mutmut CI gate** | Refactor mock boundaries; add workflow + CLI E2E tests ([e2e_test_strategy.md](./e2e_test_strategy.md)); exclude stubs from mutation scope |

**Bottom line:** Running mutation testing today would **produce actionable signal** in scoring, manifest, planner, dry-run, and `RetryManager` / `InferenceManager` (unit tests), but would **not** validate production CLI paths or generator integration with real inference wiring. Many surviving mutants would reflect **test design gaps**, not acceptable production behavior.

---

## 2. Methodology

### What “realistic mutations” means here

Mutants considered representative of production bugs:

| Operator class | Example bug |
|----------------|-------------|
| **Conditionals** | Invert `if result.success`, skip cooldown check, wrong comparison on `len(raw_text)` |
| **Arithmetic / constants** | Wrong backoff delay, off-by-one retry index |
| **Return values** | Return early without save; wrong `overall_status` |
| **Strings** | Change `"needs_review"` fallback constant |
| **Dead code removal** | Delete `mark_failed`, delete deduplication `continue` |
| **Boundary** | Change `15000` truncation to `1500` |

Not in scope for first pass: cosmetic comment/docstring mutants, `__repr__` changes.

### How readiness was judged

1. **Assertion audit** — strength, specificity, behavioral vs existence-only.  
2. **Mock audit** — boundary (network vs class vs function) and whether mutants in the mocked layer are invisible to tests.  
3. **Fixture audit** — reuse, duplication, shared helpers (`_make_result`).  
4. **Duplicate detection** — structural similarity across files.  
5. **Coverage cross-check** — 0% modules imply ~100% mutant survival.

---

## 3. Suite inventory

| Metric | Value |
|--------|-------|
| Test modules | 22 |
| Test functions (approx.) | **194** |
| `assert` statements (approx.) | **430+** |
| `patch` / `MagicMock` usages (files with mocks) | **11 files**, ~**90+** patch contexts |
| `@pytest.fixture` definitions | **~35** (no `conftest.py`; per-file fixtures) |
| `@pytest.mark.parametrize` | **0** — duplication is copy-paste, not parametrized |
| Class-level `InferenceManager` patches | **~45** test methods across **6** files |
| Real `InferenceManager` exercised | `test_inference_critical.py`, `test_inference_fallback.py` (constructor/failover only) |

---

## 4. Assertions review

### 4.1 Strength tiers

| Tier | Pattern | Mutation detection | Examples |
|------|---------|-------------------|----------|
| **A — Strong** | Exact values, collections, call args, side effects on disk | High | `test_inference_critical` sleep `call(15.0), call(30.0)`; `test_manifest` `build` status; `test_planner` scheduling constraints |
| **B — Adequate** | Enum/status + multiple field checks | Medium–high | Generator success paths with 5+ field asserts; CI quality gate tests |
| **C — Weak** | `is not None`, `.called` only, import smoke | Low | `test_cli_imports`; `test_generate_brief_boundary` (`assert mock_inference_manager.generate.called`); `test_utils` logger existence |
| **D — Coupled to constant** | Only `== "needs_review"` | Medium (constant-specific) | Fallback tests across generators — **miss** mutants that still return `needs_review` but wrong shape/count |

### 4.2 Assertion strengths by area

| Area | Tier | Notes |
|------|------|-------|
| `test_inference_critical.py` | **A** | Call counts, `mock_sleep` args, failover provider identity, cache second call not invoking provider |
| `test_brief_generation_critical.py` | **A–B** | Truncation length 15000 verified on prompt; fallback fields; `pytest.raises` for short text |
| `test_manifest.py` / `test_review.py` | **A** | Filesystem + `overall_status` / `ready_for_planner` / `blocking_reasons` |
| `test_planner.py` / `test_dryrun.py` | **A–B** | Scheduling invariants, `blocked_count`, warning text |
| `test_scoring_validation.py` | **A** | Rule messages and flag content |
| `test_generation_scaffold.py` | **B** | Good on success JSON fields; retry test is **misleading** (see weak tests) |
| `test_cli.py` | **C–B** | Exit codes + substring on stdout; collect path mocks engine |
| `test_e2e_verification.py` | **B** | JSON keys on scored item; no brief/generation |
| `test_analytics.py` | **B–C** | Mix of field asserts and `is not None` |

### 4.3 Assertion gaps that mutants would exploit

| Gap | Surviving mutant example |
|-----|--------------------------|
| No assertion on **prompt template placeholders** in most generator tests | Remove `{{ brief.topic_id }}` substitution — tests still pass if mock ignores prompt |
| **CLI** generation commands untested | Delete entire `generate-assets` loop |
| **Workflow** untested | `mark_failed` never writes file; `stage_completed` always returns False |
| **Provider** bodies untested | Wrong HTTP status → wrong `retryable` flag |
| **Duplicate collect tests** only assert exit 0 | `engine.run` never called (already patched) |

---

## 5. Mocks review

### 5.1 Mock boundary map

```text
                    ┌─────────────────────────────────────┐
  feedparser.parse  │  RSSCollector / IngestionEngine   │  ← E2E + integration test REAL
        (mocked)    └─────────────────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────┐
  InferenceManager  │  generate_brief, *Generator, CI, SB  │  ← CLASS-LEVEL MOCK (blind)
  (class patch)     └─────────────────────────────────────┘
                                    │
        generate_once (mocked)      │  InferenceManager.generate  ← REAL in test_inference_critical
                    ┌───────────────▼─────────────────────┐
                    │  RetryManager, Cache, HealthTracker   │  ← REAL
                    └─────────────────────────────────────┘
```

### 5.2 Over-mocked tests (high mutant survival behind mock)

| File / pattern | Mock target | What mutants survive |
|----------------|-------------|----------------------|
| `test_generation_scaffold.py` (17 tests) | `patch("...InferenceManager")` whole class | `InferenceManager(api_key=...)` never constructed; wrong `task_type`; manager not passed prompt |
| `test_brief_generation_critical.py` | `autouse` `patch("...brief.InferenceManager")` | Entire `generate_brief` inference wiring (lines 43–44); only post-mock logic tested |
| `test_content_intelligence.py` (9 patches) | CI generator `InferenceManager` | Same; quality gate that runs **before** LLM is still tested |
| `test_storyboard.py` (6 patches) | Storyboard `InferenceManager` | Deterministic branches (**good**); LLM path wiring blind |
| `test_thumbnail_storyboard_integration.py` | Thumbnail `InferenceManager` | Storyboard override logic **is** tested (no mock on `model_copy`) |
| `test_cli.py` `collect` | `IngestionEngine.run` → `[]` | Any mutation inside `run()` except via E2E/integration |

**Verdict:** Generator tests are **over-mocked at the class boundary**. They are valid **unit** tests for JSON parse + fallback constants, but mutation testing would **over-report survival** on `generation/*.py` lines that instantiate or call `InferenceManager`.

### 5.3 Appropriately mocked tests

| File | Mock | Why appropriate |
|------|------|-----------------|
| `test_inference_critical.py` | `GeminiProvider.generate_once`, `OpenRouterProvider.generate_once` | Exercises real `InferenceManager`, `RetryManager`, cache, health |
| `test_e2e_verification.py` | `feedparser.parse` | Avoids network; still runs real ingestion + CLI score path |
| `test_integration.py` | Collector methods on mock collector | Tests `IngestionEngine.run` control flow (race / dedup) |

### 5.4 Under-mocked areas (no tests = 100% survival)

| Module | Coverage | Mutation survival |
|--------|----------|-------------------|
| `workflow/state.py` | **0%** | **~100%** |
| `cli.py` (most commands) | **14%** | **~85–90%** |
| `inference/providers/gemini.py` HTTP paths | **48%** | **~65–75%** |
| `utils/logging.py` `PipelineLogger` | partial | **~70%** |

---

## 6. Fixtures review

### 6.1 Structure

- **No root `conftest.py`** — fixtures duplicated per file (`sample_brief` appears in ≥4 files with near-identical `Brief` payloads).
- **Shared helpers** — `_make_inference_result` / `_make_result` duplicated in 5+ files (good consistency, bad DRY).
- **`tmp_path`** — used well for repos and storage; mutation-friendly for `JsonRepository`.

### 6.2 Fixture quality

| Quality | Fixtures |
|---------|----------|
| **Good** | `valid_*_response` JSON strings; `mock_env` in E2E; `ci_registry` / `sb_registry` with real prompt files |
| **Adequate** | `scored_topic` in brief tests (fixed 500-char text) |
| **Weak** | `prompt_dir` with `"Test prompt"` only — would not catch missing placeholder keys in template |

### 6.3 Fixture-related mutation blind spots

| Issue | Effect |
|-------|--------|
| Identical `sample_brief` across files | Mutations to `Brief` validation rarely tested inconsistently |
| Registry fixtures only write one prompt file | `PromptRegistry.get_path` KeyError path untested |
| No frozen “golden” corrupt files on disk | `JsonRepository` corrupt-load mutants survive |

---

## 7. Weak tests (explicit list)

| ID | Test | Weakness | Mutants likely to survive |
|----|------|----------|---------------------------|
| W1 | `test_cli.test_cli_imports` | `assert cli is not None` | Any change to `cli.py` except import errors |
| W2 | `test_generate_brief_boundary_100` | Only `generate.called` | Wrong truncation, wrong prompt, wrong `task_type` |
| W3 | `test_generate_script_429_retry` | Name implies retry; asserts `call_count == 1` on **mock** manager | All `RetryManager` behavior in script path |
| W4 | `test_collect_command_real` / `_all` | Duplicate; `IngestionEngine.run` patched | Identical survival profile |
| W5 | Fallback tests asserting only `review_status == NEEDS_REVIEW` | Single field | Wrong fallback list length, wrong `topic_id` |
| W6 | `test_inference_fallback` `test_explicit_fallback...` | Asserts `_fallback._client is not None` | Implementation-coupled; survives behavior-equivalent refactors |
| W7 | `test_utils` logger tests | Existence only | Logging config regressions |
| W8 | `test_analytics` several `assert result is not None` | No field-level check on update path | Wrong metric values persisted |

---

## 8. Duplicate tests

### 8.1 Structural duplicates (copy-paste)

| Cluster | Files | Overlap | Recommendation (future) |
|---------|-------|---------|-------------------------|
| **Generator scaffold quartet** | `test_generation_scaffold.py` | Script / carousel / newsletter / thumbnail share identical 4-test pattern (success, malformed, “retry”, format) | Single `@pytest.mark.parametrize("generator,model,...", [...])` — **same mutation coverage, less maintenance** |
| **Collect CLI** | `test_cli.py` | `test_collect_command_real` vs `_all` differ only by argv | One parametrized test |
| **Repository CRUD** | `test_content_intelligence.py`, `test_storyboard.py` | `save` / `get` / `list_all` / `exists` identical structure | Shared mixin or `conftest` helper |
| **Thumbnail storyboard vs scaffold** | `test_thumbnail_storyboard_integration.py`, `test_generation_scaffold.py` | Overlapping thumbnail + mock pattern | Keep integration file for override asserts only |

**Mutation impact of duplicates:** Duplicates do **not** improve mutation score — they kill the **same mutants** multiple times, inflating confidence without new detection power.

### 8.2 Conceptual overlap (different layer, acceptable)

| Tests | Relationship |
|-------|--------------|
| `test_manifest.TestTopicManifest` vs `test_review.TestManifestBuilderComplete` | Model vs builder+storage — **complementary**, not pure duplicate |
| `test_inference_critical` vs `test_inference_fallback` | Execution vs constructor wiring — **complementary** |

---

## 9. Mutation score readiness by module

Estimated **mutant kill rate** if mutmut were run today (ranges from static analysis, not measured).

| Module | Line cov. | Assertion strength | Mock penalty | Est. kill rate |
|--------|-----------|-------------------|--------------|---------------|
| `inference/retry.py` | 91% | A | None | **80–90%** |
| `inference/manager.py` | 97% | A | Low (provider mock) | **75–85%** |
| `inference/cache.py` | 91% | B | Low | **60–70%** (corrupt-file gap) |
| `inference/health.py` | high | B | Low | **70–80%** |
| `inference/providers/*.py` | 48% | C | High | **25–40%** |
| `generation/brief.py` | high* | B | **Class mock** | **45–60%** on file; **0%** on manager lines |
| `generation/script|carousel|newsletter|thumbnail.py` | ~93% | B | **Class mock** | **50–65%** |
| `domains/content_intelligence/*` | ~96% | B–A | Class mock on generator | **55–70%** |
| `domains/storyboard/generator.py` | 93% | A on deterministic | Class mock on LLM | **65–75%** |
| `scoring/validation.py` | 93% | A | None | **80–88%** |
| `scoring/engine.py` | 86% | B | None | **70–80%** |
| `scoring/rules.py` | 46% | B (partial) | None | **35–45%** (only 2/4 rules tested) |
| `manifest.py` | 82% | A | None | **72–82%** |
| `planning/planner.py` | 96% | A | None | **78–88%** |
| `planning/dryrun.py` | 90% | A–B | None | **75–85%** |
| `ingestion.py` | 92% | B | E2E real path | **70–80%** |
| `collectors/rss.py` | 93% | B | feedparser mock | **65–75%** |
| `storage/local.py` | 66% | B | Partial | **55–65%** |
| `workflow/state.py` | **0%** | — | — | **0–5%** |
| `cli.py` | **14%** | C | Heavy | **15–25%** |
| `utils/logging.py` | 60% | C | — | **30–40%** |

\*High line coverage on generators because tests execute generator bodies while mocking the manager class.

### 9.1 Project-level mutation score estimate

| Scenario | Estimated mutation score |
|----------|-------------------------|
| **Full `src/content_creation`** (first run, no config) | **42–55%** |
| **Excluding `cli.py` + `workflow/`** | **58–68%** |
| **After E2E Phase A** ([e2e_test_strategy.md](./e2e_test_strategy.md)) | **55–65%** full tree |
| **After mock refactor** (provider-level only) | **+5–8 pts** on generation modules |
| **Target for CI gate** (recommended) | **≥65%** global, **≥80%** on `inference/` + `planning/` + `manifest.py` |

**Interpretation:** A **50% mutation score** with current tests does **not** mean production is broken — it means **half of artificial bugs in untested or over-mocked code would go unnoticed**, especially CLI and workflow.

---

## 10. Realistic mutants: would tests catch them?

| Mutation | Likely killed? | Why |
|----------|----------------|-----|
| `RetryManager`: remove final sleep on exhaustion | **Yes** | `test_inference_critical` |
| `InferenceManager`: skip failover when primary fails | **Yes** | `test_inference_manager_failover` |
| `generate_brief`: raise threshold 100 → 200 | **Yes** | `test_generate_brief_too_short` / boundary |
| `generate_brief`: truncate 15000 → 500 | **Yes** | `test_generate_brief_with_truncation` |
| `ManifestBuilder`: mark `complete` when any `needs_review` | **Yes** | manifest + review tests |
| `PostingPlanner`: allow same topic consecutive days | **Yes** | planner tests |
| `ScoringEngine`: stop rejecting short text | **Partial** | validation tests may not cover |
| `ScriptGenerator`: wrong fallback hook string (not `needs_review`) | **Yes** | exact assert `== "needs_review"` |
| `ScriptGenerator`: omit `InferenceManager` construction | **No** | class-level mock |
| `cli generate-assets`: delete `wf.mark_completed` | **No** | no workflow tests |
| `WorkflowStateManager.load_state`: raise on corrupt JSON | **No** | 0% coverage |
| `GeminiProvider`: 429 → non-retryable | **No** | `generate_once` mocked |
| `JsonRepository.list_all`: skip corrupt files | **No** | no corrupt fixture |
| `FREETEXT_TO_FORMAT`: wrong mapping | **Partial** | `test_build_skips_non_recommended_formats` etc. |
| `IngestionEngine`: disable deduplication | **Partial** | integration race test only |
| `OPENROUTER` auto-fallback disabled | **Yes** | `test_inference_fallback` |

---

## 11. Readiness checklist for running mutmut

### 11.1 Prerequisites

| Item | Status | Action |
|------|--------|--------|
| mutmut / cosmic-ray in `dev` deps | **Missing** | Add when implementing |
| `conftest.py` with shared fixtures | **Missing** | Reduces duplicate-equivalent runs |
| CI time budget (+10–30 min) | Unknown | Run on `inference`, `planning`, `manifest` first |
| Mutation config (`pyproject.toml` or `setup.cfg`) | **Missing** | Define paths to test / exclude |

### 11.2 Suggested mutmut scope (documentation only)

```ini
# Illustrative — not added to repo
[tool.mutmut]
paths_to_mutate = src/content_creation/
do_not_mutate =
    */__init__.py
    */models/*
```

**Phase 1 mutate targets:** `inference/`, `scoring/`, `manifest.py`, `planning/`  
**Phase 2:** `generation/`, `domains/` (expect survival until mock refactor)  
**Phase 3:** `cli.py`, `workflow/` (after E2E tests)

### 11.3 Test improvements ranked by mutation ROI

| Priority | Change | Expected Δ mutation score |
|----------|--------|---------------------------|
| P0 | Add `test_workflow.py` for `WorkflowStateManager` | **+2–3%** global; **+80%** on workflow module |
| P0 | E2E CLI tests without patching `IngestionEngine.run` | **+4–6%** global |
| P1 | Replace class `InferenceManager` patch with `generate_once` patch in `test_brief_generation_critical` | **+3–5%** on `generation/brief.py` |
| P1 | Provider error classification tests (inject `ClientError` / mock `requests`) | **+2–3%** on providers |
| P2 | Corrupt JSON fixtures for cache + `JsonRepository` | **+1–2%** |
| P2 | Parametrize generator scaffold (maintenance; **+0%** mutation unless new asserts) | — |
| P3 | Remove W1–W4 weak tests or strengthen | Quality hygiene |

---

## 12. Duplicate vs weak vs over-mocked — summary matrix

| Category | Count (approx.) | Mutation testing effect |
|----------|-----------------|-------------------------|
| **Weak tests** | 8 identified (W1–W8) | Inflate pass rate; do not kill mutants |
| **Over-mocked tests** | ~45 methods | High survival behind `InferenceManager` class patch |
| **Duplicate tests** | 4 clusters | Redundant kill count; no extra detection |
| **Strong tests** | ~60–80 methods | Core mutation detection power |

---

## 13. Conclusion

The test suite would detect **many realistic bugs** in:

- Retry / failover / cache orchestration  
- Manifest and publishing planner logic  
- Scoring validation rules  
- Pydantic parsing and `"needs_review"` fallback **content** in generators  

It would **miss** most bugs in:

- CLI command handlers and `run-pipeline`  
- Workflow resumability  
- Live provider error mapping  
- Wiring between generators and `InferenceManager`  

**Mutation testing readiness: 6/10** — safe to pilot on `inference/` and `planning/` modules; **not ready** for repo-wide mutation gates until CLI/workflow coverage and mock boundaries are addressed.

---

## 14. Related documents

| Document | Relevance |
|----------|-----------|
| [test_coverage_completeness.md](./test_coverage_completeness.md) | Line coverage gaps |
| [e2e_test_strategy.md](./e2e_test_strategy.md) | Planned tests that improve mutation score |
| [high_value_test_design.md](./high_value_test_design.md) | Provider-level mock guidance |

---

*End of audit. No tests or tooling were added to the repository.*
