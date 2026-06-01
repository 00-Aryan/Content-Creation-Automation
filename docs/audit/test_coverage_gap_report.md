# Test Coverage Gap Report

**Project:** Content Creation Automation  
**Date:** 2026-06-01  
**Status:** Reliability Sprint Day 1  
**Tests passing:** 165  
**Auditor role:** Principal Test Architect / Senior Python QA Engineer

---

## Executive Summary

The test suite is wide but shallow in the infrastructure layer. Domain logic (CI, Storyboard, generation scaffolds) is well-covered at the unit level with proper fallback testing. The critical gap is the **inference layer**: `InferenceManager`, `RetryManager`, `HealthTracker`, and `InferenceCache` are never exercised directly — every test mocks the entire `InferenceManager` class at import time. This means the retry loop, failover logic, cooldown enforcement, and cache read/write have zero test coverage. A single bug in `RetryManager.execute()` or `HealthTracker.record_failure()` would be invisible until production.

Secondary gaps: `WorkflowStateManager`, `PromptRegistry`, `JsonRepository` error paths, `LocalBackend`, `BaseCollector.collect()`, and `generation/brief.py` are untested or only partially tested. There is no integration test for the full Topic → Brief → CI → Storyboard → Thumbnail pipeline.

**What would most likely fail in production:**
1. Retry loop silently exhausting retries without sleeping (wrong `attempt` index off-by-one in `RetryManager.execute`)
2. Failover never triggering because `HealthTracker.in_cooldown` is never validated against real time
3. Cache returning stale/corrupt data silently (JSON decode error swallowed)
4. `PromptRegistry.get()` raising `FileNotFoundError` in production when a prompt file is missing — no test covers this path
5. `WorkflowStateManager` corrupt-JSON path returning empty state silently, causing stages to re-run

---

## 1. Public API Inventory

### inference/

| Class / Function | Public Methods | File |
|---|---|---|
| `InferenceManager` | `__init__`, `generate`, `health` (property), `_build_provider` (static) | `manager.py` |
| `RetryManager` | `__init__`, `execute`, `is_retryable`, `calculate_delay`, `create_state`, `record_attempt`, `policy` (property) | `retry.py` |
| `InferenceCache` | `__init__`, `get`, `put` | `cache.py` |
| `HealthTracker` | `__init__`, `get`, `record_success`, `record_failure` | `health.py` |
| `ProviderHealth` | `in_cooldown` (property) | `health.py` |
| `GeminiProvider` | `generate`, `generate_once`, `provider_name`, `model_name` | `providers/gemini.py` |
| `OpenRouterProvider` | `generate`, `generate_once`, `provider_name`, `model_name` | `providers/openrouter.py` |
| `BaseProvider` | `generate` (abstract), `provider_name`, `model_name` | `providers/base.py` |
| `InferenceResult` | dataclass fields | `providers/base.py` |
| `ProviderError` | dataclass fields | `models.py` |
| `RetryPolicy` | dataclass fields | `retry.py` |

### domains/

| Class / Function | Public Methods | File |
|---|---|---|
| `ContentIntelligenceGenerator` | `__init__`, `generate` | `content_intelligence/generator.py` |
| `ContentIntelligenceRepository` | `save`, `get`, `list_all`, `exists` | `content_intelligence/repository.py` |
| `evaluate_brief_quality` | function | `content_intelligence/quality.py` |
| `StoryboardGenerator` | `__init__`, `generate` | `storyboard/generator.py` |
| `StoryboardRepository` | `save`, `get`, `list_all`, `exists` | `storyboard/repository.py` |
| Domain repositories (brief, carousel, newsletter, thumbnail, script) | `save`, `get`, `list_all`, `exists` | `domains/*/repository.py` |

### generation/

| Class / Function | Public Methods | File |
|---|---|---|
| `ScriptGenerator` | `__init__`, `generate` | `script.py` |
| `CarouselGenerator` | `__init__`, `generate` | `carousel.py` |
| `NewsletterGenerator` | `__init__`, `generate` | `newsletter.py` |
| `ThumbnailGenerator` | `__init__`, `generate` | `thumbnail.py` |
| `generate_brief` | function | `brief.py` |

### storage/

| Class / Function | Public Methods | File |
|---|---|---|
| `LocalStorage` | `__init__`, `save_staged`, `get_staged`, `list_staged`, `exists`, `save_scored`, `get_scored`, `list_scored`, `update_asset_status`, `save_raw` | `local.py` |

### platform/storage/

| Class / Function | Public Methods | File |
|---|---|---|
| `JsonRepository` | `__init__`, `save`, `get`, `list_all`, `exists` | `json_repository.py` |
| `LocalBackend` | `__init__`, `save_raw`, `exists` | `local_backend.py` |

### workflow/

| Class / Function | Public Methods | File |
|---|---|---|
| `WorkflowStateManager` | `__init__`, `load_state`, `save_state`, `mark_completed`, `mark_failed`, `stage_completed`, `get_pending_stages` | `state.py` |

### planning/

| Class / Function | Public Methods | File |
|---|---|---|
| `PostingPlanner` | `__init__`, `plan_week` | `planner.py` |
| `DryRunValidator` | `__init__`, `validate` | `dryrun.py` |

### prompts/

| Class / Function | Public Methods | File |
|---|---|---|
| `PromptRegistry` | `__init__`, `get_path`, `get` | `registry.py` |

### collectors/

| Class / Function | Public Methods | File |
|---|---|---|
| `BaseCollector` | `__init__`, `fetch`, `parse`, `normalize`, `collect` | `base.py` |
| `RSSCollector` | `fetch`, `parse`, `normalize` (inherits `collect`) | `rss.py` |

### scoring/

| Class / Function | Public Methods | File |
|---|---|---|
| `ScoringEngine` | `__init__`, `score_items` | `engine.py` |
| `ValidationEngine` | `__init__`, `validate_item` | `validation.py` |
| `ScoreConsistencyRule`, `SuspiciousScoreRule`, `MetadataCompletenessRule` | `validate` | `validation.py` |
| `load_scoring_config` | function | `config.py` |

### Top-level

| Class / Function | Public Methods | File |
|---|---|---|
| `ManifestBuilder` | `__init__`, `build` | `manifest.py` |
| `IngestionEngine` | `__init__`, `run`, `get_collectors` | `ingestion.py` |
| `main` | function | `cli.py` |

---

## 2. Coverage Matrix

| Component | Class / Symbol | Status | Reason |
|---|---|---|---|
| **inference** | `InferenceManager.__init__` | Partially tested | Constructed inside mocked patch; constructor logic (provider registry, fallback wiring) never runs in tests |
| **inference** | `InferenceManager.generate` | **Untested** | Every test patches `InferenceManager` at class level — `generate()` body never executes |
| **inference** | `InferenceManager._execute_with` | **Untested** | Private but core; failover path never exercised |
| **inference** | `RetryManager.execute` | **Untested** | No test calls it with a real callable; retry loop, sleep, exhaustion path all uncovered |
| **inference** | `RetryManager.is_retryable` | **Untested** | Never called in any test |
| **inference** | `RetryManager.calculate_delay` | **Untested** | Backoff math never verified |
| **inference** | `InferenceCache.get` | **Untested** | No test exercises cache read path |
| **inference** | `InferenceCache.put` | **Untested** | No test exercises cache write path |
| **inference** | `HealthTracker.record_success` | **Untested** | Never called directly |
| **inference** | `HealthTracker.record_failure` | **Untested** | Cooldown trigger (3 consecutive failures) never tested |
| **inference** | `HealthTracker.in_cooldown` | **Untested** | Time-based property never validated |
| **inference** | `GeminiProvider.generate_once` | Partially tested | Error classification (`_classify_client_error`) tested indirectly via mock; actual HTTP path never runs |
| **inference** | `OpenRouterProvider.generate_once` | Partially tested | Same as Gemini — HTTP path mocked away |
| **domains/CI** | `ContentIntelligenceGenerator.generate` | Fully tested | Success, fallback on failure, fallback on malformed JSON, quality gate (BLOCKED/DEGRADED/READY), timeliness hook |
| **domains/CI** | `ContentIntelligenceRepository` | Fully tested | save, get, list_all, exists |
| **domains/CI** | `evaluate_brief_quality` | Fully tested | All QualityStatus branches covered |
| **domains/storyboard** | `StoryboardGenerator.generate` | Fully tested | Success, fallback, visual style mapping, metaphor resolution, format normalization |
| **domains/storyboard** | `StoryboardRepository` | Fully tested | save, get, list_all, exists |
| **domains/brief** | `BriefRepository` | **Untested** | No test file for brief domain repository |
| **domains/carousel,newsletter,thumbnail,script** | Repositories | **Untested** | Domain repositories for these four types have no direct tests |
| **generation** | `ScriptGenerator.generate` | Fully tested | Success, malformed JSON fallback, retry passthrough, format field, source URL |
| **generation** | `CarouselGenerator.generate` | Fully tested | Success, malformed JSON fallback, retry passthrough, slide parsing |
| **generation** | `NewsletterGenerator.generate` | Fully tested | Success, malformed JSON fallback, retry passthrough, section parsing |
| **generation** | `ThumbnailGenerator.generate` | Fully tested | Success, malformed JSON fallback, retry passthrough, storyboard override, storyboard fallback |
| **generation** | `generate_brief` | **Untested** | No test for brief generation function; short-text rejection, fallback, PromptRegistry path all uncovered |
| **storage** | `LocalStorage` | Partially tested | save/load/list/exists covered; `save_scored`, `get_scored`, `list_scored` not directly tested; `save_raw` not tested |
| **storage** | `LocalStorage.update_asset_status` | Fully tested | Success, missing file, unknown type |
| **platform/storage** | `JsonRepository` | Partially tested | Used indirectly via domain repositories; error paths (ValidationError on load, OSError on save) not tested |
| **platform/storage** | `LocalBackend` | **Untested** | No test for `save_raw`, `exists`, or `_verify_writeable` failure |
| **workflow** | `WorkflowStateManager` | **Untested** | `load_state`, `save_state`, `mark_completed`, `mark_failed`, `stage_completed`, `get_pending_stages` all untested |
| **planning** | `PostingPlanner.plan_week` | Partially tested | Model validation tested; planner logic with real manifests not integration-tested |
| **planning** | `DryRunValidator.validate` | Partially tested | Model validation tested; validator with real calendar not integration-tested |
| **prompts** | `PromptRegistry.get` | Partially tested | Used as fixture in CI/Storyboard tests with tmp_path; `FileNotFoundError` path and unknown-key `KeyError` path not tested |
| **prompts** | `PromptRegistry.get_path` | Partially tested | Same as above |
| **collectors** | `BaseCollector.collect` | **Untested** | Orchestration method (fetch → parse → normalize with per-record error handling) never tested directly |
| **collectors** | `RSSCollector` | Partially tested | fetch errors, normalize edge cases tested; `parse()` method not directly tested |
| **scoring** | `ScoringEngine.score_items` | Fully tested | Rejection rules (short text, low score, missing source), scoring config load |
| **scoring** | `ValidationEngine` + rules | Fully tested | All three rules, integration, edge cases |
| **manifest** | `ManifestBuilder.build` | Fully tested | complete, blocked, blocking_reasons, ready_for_planner |
| **ingestion** | `IngestionEngine.run` | Fully tested | Full loop, deduplication race condition |
| **ingestion** | `IngestionEngine.get_collectors` | Fully tested | Source filter, ID filter, enabled filter |
| **cli** | `main` | Partially tested | collect + score-topics E2E tested; generate-briefs, generate-assets, review, plan-week, dry-run CLI paths not tested |

---

## 3. Error Path Coverage Audit

| Component | Error Scenario | Covered? | Notes |
|---|---|---|---|
| `InferenceManager.generate` | Provider returns `success=False` | **No** | `generate()` body never runs in tests |
| `InferenceManager.generate` | Primary in cooldown → failover | **No** | `_execute_with` + `HealthTracker.in_cooldown` path untested |
| `InferenceManager.generate` | Primary fails → fallback provider | **No** | Fallback wiring never exercised |
| `RetryManager.execute` | Retryable error → sleep → retry | **No** | `time.sleep` never called in tests |
| `RetryManager.execute` | Max retries exhausted | **No** | Exhaustion return path untested |
| `RetryManager.execute` | Non-retryable error → immediate return | **No** | `is_retryable=False` path untested |
| `InferenceCache.get` | Malformed JSON in cache file | **No** | `json.JSONDecodeError` swallowed silently — untested |
| `InferenceCache.get` | Cache miss | **No** | Miss path untested |
| `InferenceCache.put` | `result.success=False` → skip write | **No** | Guard clause untested |
| `GeminiProvider.generate_once` | `ClientError` 429 → retryable ProviderError | **No** | Real SDK never called; classification logic untested |
| `GeminiProvider.generate_once` | `ClientError` 401/403 → non-retryable | **No** | Same |
| `GeminiProvider.generate_once` | Generic exception → NETWORK category | **No** | Same |
| `OpenRouterProvider.generate_once` | HTTP 429 → retryable | **No** | Real HTTP never called |
| `OpenRouterProvider.generate_once` | HTTP 500 → retryable | **No** | Same |
| `OpenRouterProvider.generate_once` | `requests.RequestException` | **No** | Same |
| `JsonRepository.save` | `OSError` on write | **No** | Exception re-raised but never tested |
| `JsonRepository.list_all` | `ValidationError` on corrupt file | **No** | Warning logged, item skipped — untested |
| `JsonRepository.get` | `ValidationError` on corrupt file | **No** | Returns `None` silently — untested |
| `LocalBackend._verify_writeable` | Directory not writeable | **No** | `OSError` path untested |
| `LocalBackend.save_raw` | `Exception` on write | **No** | Error logged but untested |
| `WorkflowStateManager.load_state` | Corrupt JSON file | **No** | Returns empty state silently — untested |
| `PromptRegistry.get` | File not found | **No** | `FileNotFoundError` untested |
| `PromptRegistry.get_path` | Unknown domain/name | **No** | `KeyError` untested |
| `generate_brief` | `raw_text` too short | **No** | `ValueError` path untested |
| `generate_brief` | Inference failure → fallback | **No** | Fallback Brief untested |
| `generate_brief` | Malformed JSON response | **No** | Parse exception path untested |
| `BaseCollector.collect` | `fetch()` raises exception | **No** | Returns `[]` silently — untested |
| `BaseCollector.collect` | `normalize()` raises per-record | **No** | Per-record error handling untested |
| `LocalStorage.save_staged` | `FileExistsError` | Tested | Race condition test in `test_integration.py` |
| `LocalStorage` | Not writeable | Tested | `test_storage.py` |
| `RSSCollector.fetch` | HTTP 404 | Tested | `test_ingestion.py` |
| `RSSCollector.fetch` | Bozo with no entries | Tested | `test_ingestion.py` |
| `ContentIntelligenceGenerator.generate` | Inference failure | Tested | `test_content_intelligence.py` |
| `ContentIntelligenceGenerator.generate` | Malformed JSON | Tested | `test_content_intelligence.py` |
| `ContentIntelligenceGenerator.generate` | BLOCKED brief | Tested | `test_content_intelligence.py` |
| `StoryboardGenerator.generate` | Inference failure | Tested | `test_storyboard.py` |
| `ThumbnailGenerator.generate` | Inference failure + storyboard | Tested | `test_thumbnail_storyboard_integration.py` |

---

## 4. Fallback Coverage Audit

| Fallback Scenario | Status | Notes |
|---|---|---|
| Inference retry (RetryManager loop) | **Untested** | `RetryManager.execute` never called with a real callable |
| Inference failover (primary → fallback provider) | **Untested** | `InferenceManager._execute_with` fallback branch never exercised |
| Cache miss → live inference | **Untested** | Cache layer bypassed entirely in all tests |
| Cache hit → return cached result | **Untested** | Cache hit path never exercised |
| Storyboard fallback (LLM failure → `needs_review`) | Tested | `test_storyboard.py::test_generate_fallback_on_failure` |
| Storyboard fallback preserves deterministic fields | Tested | Visual style, hooks still populated on failure |
| Thumbnail fallback without storyboard | Tested | `test_generation_scaffold.py` |
| Thumbnail fallback with storyboard | Tested | `test_thumbnail_storyboard_integration.py::test_storyboard_fallback_uses_storyboard_values` |
| CI fallback on LLM failure | Tested | `test_content_intelligence.py::test_generate_fallback_on_failure` |
| CI fallback on malformed JSON | Tested | `test_content_intelligence.py::test_generate_fallback_on_malformed_json` |
| CI blocked brief → no LLM call | Tested | `test_content_intelligence.py::TestGeneratorQualityGate` |
| Brief generation fallback | **Untested** | `generate_brief` fallback path never tested |
| Script/Carousel/Newsletter fallback | Tested | All three have malformed JSON fallback tests |
| WorkflowStateManager corrupt JSON → empty state | **Untested** | Silent fallback never verified |

---

## 5. Integration Coverage Audit

### Current pipeline: Topic → Brief → CI → Storyboard → Thumbnail

| Stage Boundary | Test Type | Covered? |
|---|---|---|
| Topic → Brief (full `generate_brief` call) | Unit | **No** — `generate_brief` has zero tests |
| Brief → CI (`ContentIntelligenceGenerator.generate`) | Unit | Yes — mocked InferenceManager |
| CI → Storyboard (`StoryboardGenerator.generate`) | Unit | Yes — mocked InferenceManager |
| Storyboard → Thumbnail (`ThumbnailGenerator.generate` with storyboard) | Unit | Yes — mocked InferenceManager |
| Topic → Brief → CI (two-stage) | Integration | **No** |
| Brief → CI → Storyboard (two-stage) | Integration | **No** |
| CI → Storyboard → Thumbnail (two-stage) | Integration | **No** |
| Full Topic → Brief → CI → Storyboard → Thumbnail | End-to-end | **No** |
| Collect → Score (CLI) | E2E | Yes — `test_e2e_verification.py` |
| Ingestion loop (fetch → normalize → persist) | Integration | Yes — `test_integration.py` |
| ManifestBuilder with real storage | Integration | Yes — `test_review.py` |
| PostingPlanner with real manifests | Integration | **No** — only model validation tested |
| DryRunValidator with real calendar | Integration | **No** — only model validation tested |

**Summary:** Everything from Brief generation onward is unit-tested only, with `InferenceManager` mocked at the class level. There is no test that chains two or more pipeline stages together using real objects. The `generate_brief` function — the entry point to the entire generation pipeline — has no tests at all.

---

## 6. Risk Ranking

| Rank | Component | Risk Level | Likelihood | Impact | Reason |
|---|---|---|---|---|---|
| 1 | `RetryManager.execute` — retry loop correctness | **Critical** | High | High | Off-by-one in attempt index, wrong sleep timing, or exhaustion logic would silently drop retries. Every generation call goes through this. |
| 2 | `InferenceManager.generate` — failover path | **Critical** | Medium | High | If primary fails and fallback is configured, the failover branch is completely untested. Silent failure in production. |
| 3 | `generate_brief` — entire function | **Critical** | High | High | Entry point to the generation pipeline. Short-text guard, fallback Brief, PromptRegistry path — all untested. Any regression here breaks the whole pipeline. |
| 4 | `HealthTracker` — cooldown enforcement | **High** | Medium | High | `in_cooldown` uses `time.time()` comparison. If the cooldown logic is wrong, the provider could be permanently locked out or never locked out. |
| 5 | `InferenceCache` — get/put correctness | **High** | Medium | Medium | Corrupt cache file silently returns `None` (miss). A bug in `put` could write bad data that poisons future requests. |
| 6 | `WorkflowStateManager` — corrupt JSON fallback | **High** | Low | High | Returns empty state on corrupt file, causing all stages to re-run. No test verifies this is safe. |
| 7 | `PromptRegistry.get` — missing file | **High** | Medium | High | `FileNotFoundError` in production if a prompt file is missing or misnamed. No test covers this path. |
| 8 | `JsonRepository` — error paths | **Medium** | Low | Medium | `ValidationError` on corrupt stored files silently skips items in `list_all`. Could cause silent data loss. |
| 9 | `BaseCollector.collect` — per-record error handling | **Medium** | Medium | Medium | A bad record silently drops and logs a warning. No test verifies the orchestration continues correctly. |
| 10 | `LocalBackend` — write failure | **Medium** | Low | Medium | `save_raw` swallows exceptions with a log. No test verifies the error is surfaced or handled. |
| 11 | `PostingPlanner` / `DryRunValidator` — integration | **Medium** | Low | Medium | Only model validation tested. Real planner logic with manifests and diversity rules untested. |
| 12 | Domain repositories (brief, carousel, etc.) | **Low** | Low | Low | Thin wrappers over `JsonRepository`. Low risk but zero direct coverage. |

---

## 7. Top 10 Recommended Test Backlog

### T-01 — `RetryManager.execute`: retry loop with retryable error
**Risk addressed:** Critical — retry loop correctness  
**Estimated effort:** Small (1–2 hours)  
**Expected confidence gain:** High — verifies sleep timing, attempt counting, exhaustion return, and non-retryable early exit without any real network calls. Use a mock callable that fails N times then succeeds.

---

### T-02 — `InferenceManager.generate`: failover when primary fails
**Risk addressed:** Critical — failover path  
**Estimated effort:** Small (1–2 hours)  
**Expected confidence gain:** High — mock both `GeminiProvider` and `OpenRouterProvider` at the provider level (not the manager level). Verify that when primary returns `success=False`, the fallback provider is called.

---

### T-03 — `generate_brief`: success, fallback, and short-text rejection
**Risk addressed:** Critical — brief generation entry point  
**Estimated effort:** Small (2 hours)  
**Expected confidence gain:** High — three tests: (1) valid JSON response → correct `Brief`, (2) inference failure → fallback `Brief` with `needs_review`, (3) `raw_text` < 100 chars → `ValueError`.

---

### T-04 — `InferenceCache`: get (hit, miss, corrupt), put (success, skip on failure)
**Risk addressed:** High — cache correctness  
**Estimated effort:** Small (1–2 hours)  
**Expected confidence gain:** High — use `tmp_path`. Verify cache miss returns `None`, cache hit returns correct `InferenceResult`, corrupt JSON returns `None`, and `put` with `success=False` writes nothing.

---

### T-05 — `HealthTracker`: cooldown trigger and `in_cooldown` property
**Risk addressed:** High — provider health enforcement  
**Estimated effort:** Small (1 hour)  
**Expected confidence gain:** High — call `record_failure` three times, assert `in_cooldown=True`. Call `record_success`, assert `in_cooldown=False`. Use `freezegun` or `unittest.mock.patch("time.time")` to control clock.

---

### T-06 — `InferenceManager.generate`: cache hit skips provider call
**Risk addressed:** High — cache integration with manager  
**Estimated effort:** Small (1 hour)  
**Expected confidence gain:** Medium — construct a real `InferenceManager` with a `tmp_path` cache dir. Pre-populate the cache. Assert provider is never called on second `generate()` call.

---

### T-07 — `WorkflowStateManager`: full lifecycle + corrupt JSON fallback
**Risk addressed:** High — workflow state persistence  
**Estimated effort:** Small (1–2 hours)  
**Expected confidence gain:** High — use `tmp_path`. Test `mark_completed`, `mark_failed`, `stage_completed`, `get_pending_stages`. Write a corrupt JSON file and verify `load_state` returns empty `WorkflowState` without raising.

---

### T-08 — `PromptRegistry`: unknown key raises `KeyError`, missing file raises `FileNotFoundError`
**Risk addressed:** High — prompt resolution failures  
**Estimated effort:** Small (30 min)  
**Expected confidence gain:** Medium — two tests: (1) `registry.get("unknown", "prompt")` raises `KeyError`, (2) registry with valid key but missing file raises `FileNotFoundError`.

---

### T-09 — `generate_brief` + `ContentIntelligenceGenerator`: two-stage integration
**Risk addressed:** Medium — pipeline stage chaining  
**Estimated effort:** Medium (2–3 hours)  
**Expected confidence gain:** Medium — mock `InferenceManager` at the provider level. Run `generate_brief` to produce a `Brief`, feed it directly into `ContentIntelligenceGenerator.generate`. Assert the `ContentIntelligence` output has correct `topic_id` and `quality_status`.

---

### T-10 — `BaseCollector.collect`: fetch failure returns `[]`, per-record normalize error is skipped
**Risk addressed:** Medium — collector error handling  
**Estimated effort:** Small (1 hour)  
**Expected confidence gain:** Medium — subclass `BaseCollector` in the test. Verify that when `fetch()` raises, `collect()` returns `[]`. Verify that when one `normalize()` call raises, the other records are still returned.

---

## 8. Summary Table

| Question | Answer |
|---|---|
| What is not tested? | `InferenceManager.generate`, `RetryManager.execute`, `InferenceCache`, `HealthTracker`, `WorkflowStateManager`, `generate_brief`, `LocalBackend`, `BaseCollector.collect`, `PromptRegistry` error paths, all domain repositories except CI and Storyboard |
| What is only partially tested? | `GeminiProvider`/`OpenRouterProvider` (error classification logic), `LocalStorage` (scored paths, save_raw), `JsonRepository` (error paths), `PostingPlanner`/`DryRunValidator` (model only, no integration), `PromptRegistry` (happy path only), `RSSCollector` (parse not tested) |
| What would most likely fail in production? | (1) Retry loop bug in `RetryManager.execute`, (2) Failover never triggering, (3) `generate_brief` regression, (4) Missing prompt file crashing generation, (5) Corrupt cache file causing silent miss |
| Which 10 tests increase confidence most? | T-01 through T-10 above, in priority order |
