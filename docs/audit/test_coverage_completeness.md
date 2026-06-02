# Test Coverage Completeness Audit

**Date:** 2026-06-02  
**Branch:** `feature/streamlit-control-center`  
**Production scope:** `src/content_creation/` (78 Python files)  
**Test scope:** `tests/` (22 test modules, **194 tests passing**)  
**Measured coverage:** **62%** line coverage (`pytest --cov=src/content_creation`)  
**Method:** Production file → test file mapping, import/call-path tracing, pytest coverage report, behavioral classification. No code changes.

---

## Executive summary

The suite is **broad and strong on domain generators and planning**, with recent additions (`test_inference_critical.py`, `test_brief_generation_critical.py`, `test_inference_fallback.py`) closing the largest historical gap in **inference orchestration**. Remaining holes cluster in three places:

1. **CLI surface area** — `cli.py` is **14%** covered; only `status`, `collect` (mocked), and E2E `collect` + `score-topics` are exercised.
2. **Workflow persistence** — `workflow/state.py` is **0%** covered despite use in `generate-assets` and `run-pipeline`.
3. **Infrastructure error paths** — provider HTTP bodies, cache corruption, `JsonRepository` load failures, and `PromptRegistry` missing-key paths lack direct tests.

**Generators** mock `InferenceManager` at the class boundary (appropriate for unit tests) but no test runs **real** `InferenceManager` inside `generate_brief` or asset generators end-to-end.

---

## Classification legend

| Status | Criteria |
|--------|------------|
| **Fully tested** | Public API exercised with success + primary failure/fallback paths; typically **≥85%** line coverage or equivalent behavioral coverage across main methods. |
| **Partially tested** | Some tests exist but gaps remain (CLI wiring, error paths, real I/O, indirect-only access, or heavy mocking of the module under test). |
| **Untested** | **0%** coverage on meaningful logic, or no test imports/calls the module’s behavior. |
| **N/A** | Empty package stub (`__init__.py` docstring only); no runtime logic. |

---

## Master map: production file → test file(s)

| Production file | Primary test file(s) | Also exercised via | Status |
|-----------------|----------------------|--------------------|--------|
| **CLI** | | | |
| `cli.py` | `test_cli.py`, `test_e2e_verification.py` | — | **Partial** (14%) |
| **Generation** | | | |
| `generation/brief.py` | `test_brief_generation_critical.py` | — | **Partial** (mocks `InferenceManager`) |
| `generation/script.py` | `test_generation_scaffold.py` | — | **Fully tested** (mocked inference) |
| `generation/carousel.py` | `test_generation_scaffold.py` | — | **Fully tested** |
| `generation/newsletter.py` | `test_generation_scaffold.py` | — | **Fully tested** |
| `generation/thumbnail.py` | `test_generation_scaffold.py`, `test_thumbnail_storyboard_integration.py` | — | **Fully tested** |
| `generation/__init__.py` | — | — | N/A |
| **Domains** | | | |
| `domains/content_intelligence/model.py` | `test_content_intelligence.py` | `test_storyboard.py` | **Fully tested** |
| `domains/content_intelligence/generator.py` | `test_content_intelligence.py` | — | **Fully tested** (mocked inference) |
| `domains/content_intelligence/repository.py` | `test_content_intelligence.py` | — | **Fully tested** |
| `domains/content_intelligence/quality.py` | `test_content_intelligence.py` | — | **Fully tested** |
| `domains/storyboard/model.py` | `test_storyboard.py`, `test_thumbnail_storyboard_integration.py` | — | **Fully tested** |
| `domains/storyboard/generator.py` | `test_storyboard.py` | — | **Fully tested** (mocked inference) |
| `domains/storyboard/repository.py` | `test_storyboard.py` | — | **Fully tested** |
| `domains/brief/repository.py` | — | `LocalStorage` in many tests | **Partial** (indirect only) |
| `domains/script/repository.py` | — | `LocalStorage` | **Partial** |
| `domains/carousel/repository.py` | — | `LocalStorage` | **Partial** |
| `domains/newsletter/repository.py` | — | `LocalStorage` | **Partial** |
| `domains/thumbnail/repository.py` | — | `LocalStorage` | **Partial** |
| `domains/*/__init__.py` (5 stubs) | — | — | N/A |
| `domains/__init__.py` | — | — | N/A |
| **Inference** | | | |
| `inference/manager.py` | `test_inference_critical.py`, `test_inference_fallback.py` | — | **Fully tested** (HTTP mocked at `generate_once`) |
| `inference/retry.py` | `test_inference_critical.py` | — | **Fully tested** |
| `inference/cache.py` | `test_inference_critical.py` | — | **Partial** (hit/write; corrupt JSON untested) |
| `inference/health.py` | `test_inference_critical.py` | — | **Partial** (cooldown tested; time-edge cases thin) |
| `inference/models.py` | `test_inference_critical.py` | — | **Fully tested** (via `ProviderError` / `ErrorCategory`) |
| `inference/providers/gemini.py` | `test_inference_critical.py` | — | **Partial** (48%; `generate_once` body mocked) |
| `inference/providers/openrouter.py` | `test_inference_critical.py`, `test_inference_fallback.py` | — | **Partial** (48%; HTTP/classify untested) |
| `inference/providers/base.py` | `test_inference_critical.py` + generator tests | — | **Fully tested** (dataclass usage) |
| `inference/providers/__init__.py` | — | — | N/A |
| `inference/__init__.py` | `test_inference_fallback.py` | — | N/A (re-export) |
| **Platform** | | | |
| `platform/storage/json_repository.py` | `test_content_intelligence.py`, `test_storyboard.py` | `LocalStorage` | **Partial** (84%; save/get error paths untested) |
| `platform/storage/local_backend.py` | `test_storage.py` | `LocalStorage` | **Partial** (92%; `save_raw` failure untested) |
| `platform/storage/__init__.py` | — | — | N/A |
| `platform/__init__.py` | — | — | N/A |
| **Storage** | | | |
| `storage/local.py` | `test_storage.py`, `test_manifest.py`, `test_review.py`, `test_planner.py`, `test_analytics.py`, `test_dryrun.py`, `test_integration.py`, `test_e2e_verification.py` | Many tests | **Partial** (66%) |
| **Workflow** | | | |
| `workflow/state.py` | — | — | **Untested** (0%) |
| `workflow/__init__.py` | — | — | **Untested** (0%) |
| **Collectors** | | | |
| `collectors/base.py` | — | — | **Partial** (53%; `collect()` never called) |
| `collectors/rss.py` | `test_ingestion.py`, `test_integration.py`, `test_e2e_verification.py` | — | **Partial** (93%; `parse()` not direct-tested) |
| `collectors/__init__.py` | — | — | N/A |
| **Ingestion** | | | |
| `ingestion.py` | `test_ingestion.py`, `test_integration.py`, `test_e2e_verification.py` | `test_cli.py` (mocked) | **Fully tested** |
| **Scoring** | | | |
| `scoring/engine.py` | `test_scoring_validation.py` | `test_e2e_verification.py` | **Partial** (86%; `get_config_summary` untested) |
| `scoring/validation.py` | `test_scoring_validation.py` | `test_e2e_verification.py` | **Fully tested** |
| `scoring/config.py` | `test_scoring_config.py`, `test_scoring_validation.py` | — | **Fully tested** |
| `scoring/base.py` | `test_scoring_validation.py`, `test_scoring_rules.py` | — | **Partial** (75%) |
| `scoring/rules.py` | `test_scoring_rules.py` | — | **Partial** (46%; only `KeywordRule`, `RecencyRule`; not used by engine) |
| `scoring/__init__.py` | — | — | N/A |
| **Planning** | | | |
| `planning/planner.py` | `test_planner.py` | — | **Fully tested** |
| `planning/dryrun.py` | `test_dryrun.py` | — | **Fully tested** |
| `planning/__init__.py` | — | — | N/A |
| **Manifest** | | | |
| `manifest.py` | `test_manifest.py`, `test_review.py` | — | **Partial** (82%) |
| **Prompts** | | | |
| `prompts/registry.py` | All generator/domain tests (fixtures) | — | **Partial** (94%; `KeyError` / `FileNotFoundError` untested) |
| `prompts/__init__.py` | — | — | N/A |
| **Models** | | | |
| `models/topic.py` | `test_models.py`, scoring/ingestion tests | Widespread | **Fully tested** |
| `models/brief.py` | `test_brief_generation_critical.py`, generator tests | — | **Fully tested** |
| `models/script.py` | `test_generation_scaffold.py` | — | **Fully tested** |
| `models/carousel.py` | `test_generation_scaffold.py` | — | **Fully tested** |
| `models/newsletter.py` | `test_generation_scaffold.py` | — | **Fully tested** |
| `models/thumbnail.py` | `test_generation_scaffold.py`, `test_thumbnail_storyboard_integration.py` | — | **Fully tested** |
| `models/manifest.py` | `test_manifest.py`, `test_planner.py` | — | **Fully tested** |
| `models/calendar.py` | `test_planner.py`, `test_dryrun.py` | — | **Fully tested** |
| `models/dryrun.py` | `test_dryrun.py` | — | **Fully tested** |
| `models/analytics.py` | `test_analytics.py` | — | **Fully tested** |
| `models/__init__.py` | — | — | N/A (barrel; unused in tests) |
| **Utils** | | | |
| `utils/logging.py` | `test_utils.py` | `test_cli.py` | **Partial** (60%; `PipelineLogger` untested) |
| `utils/config.py` | `test_utils.py` | — | **Partial** (70%; `get_config` untested) |
| `utils/__init__.py` | — | — | N/A |
| **Shared** | | | |
| `shared/enums.py` | Many tests | — | **Fully tested** |
| `shared/types.py` | Via models | — | **Fully tested** |
| `shared/__init__.py` | — | — | N/A |
| **Root** | | | |
| `__init__.py` | — | — | N/A |

### Test file index (what each file covers)

| Test file | Production modules primarily covered |
|-----------|-----------------------------------|
| `test_inference_critical.py` | `inference/manager`, `retry`, `cache`, `health`, providers (mocked HTTP) |
| `test_inference_fallback.py` | `InferenceManager.__init__` fallback wiring |
| `test_brief_generation_critical.py` | `generation/brief.generate_brief` |
| `test_generation_scaffold.py` | `generation/script`, `carousel`, `newsletter`, `thumbnail` |
| `test_content_intelligence.py` | CI domain (model, generator, repo, quality) |
| `test_storyboard.py` | Storyboard domain |
| `test_thumbnail_storyboard_integration.py` | Thumbnail + storyboard override |
| `test_manifest.py` | `manifest.ManifestBuilder`, `LocalStorage.list_briefs` |
| `test_review.py` | `ManifestBuilder`, `LocalStorage.update_asset_status` |
| `test_planner.py` | `PostingPlanner`, `LocalStorage` calendar I/O |
| `test_dryrun.py` | `DryRunValidator`, dry-run models |
| `test_analytics.py` | Analytics models + `LocalStorage` analytics I/O |
| `test_scoring_validation.py` | `ValidationEngine`, `ScoringEngine.score_items` |
| `test_scoring_rules.py` | `scoring/rules` (`KeywordRule`, `RecencyRule` only) |
| `test_scoring_config.py` | `scoring/config` |
| `test_ingestion.py` | `RSSCollector`, `IngestionEngine.get_collectors` |
| `test_integration.py` | `IngestionEngine.run`, deduplication race |
| `test_e2e_verification.py` | CLI `collect` + `score-topics` (real subprocess of `main`) |
| `test_storage.py` | `LocalStorage` staged I/O, writeability guard |
| `test_cli.py` | CLI flags, `status`, mocked `collect` |
| `test_utils.py` | `setup_logging`, `get_logger`, `get_env_var`, `load_env_file` |
| `test_models.py` | `TopicItem` / `ScoredTopicItem` |

---

## Module area summaries

### CLI (`cli.py`)

| Status | **Partial** — 14% line coverage (808 / 943 statements missed) |

**Tested commands**

| Command | Test |
|---------|------|
| `--version`, `--help` | `test_cli.py` |
| `status` | `test_cli.py` |
| `collect` (ingestion mocked) | `test_cli.py` |
| `collect --all` + `score-topics` | `test_e2e_verification.py` |

**Untested commands (no test invokes `main` with these argv)**

`list-topics`, `validate-items`, `review-scores`, `scoring-dashboard`, `generate-briefs`, `generate-assets`, `batch-approve`, `run-pipeline`, `build-manifest`, `build-all-manifests`, `plan-week`, `dry-run`, `init-analytics`, `update-analytics`, `review-assets`

**Untested CLI infrastructure:** `PipelineLogger` stages, `WorkflowStateManager` integration, `GEMINI_API_KEY` guard paths for generation commands, interactive `review-assets` loop.

---

### Generators (`generation/`)

| Module | Status | Notes |
|--------|--------|-------|
| `brief.py` | Partial | 12 tests; **`InferenceManager` always mocked** — no test uses real manager through `generate_brief` |
| `script.py` | Fully tested | Success, malformed JSON, retries, format validation |
| `carousel.py` | Fully tested | Slide parsing |
| `newsletter.py` | Fully tested | Section parsing |
| `thumbnail.py` | Fully tested | Storyboard override + fallback paths |

**Gap:** No cross-generator integration test; all share the same mock boundary pattern.

---

### Domains (`domains/`)

| Domain | Status | Notes |
|--------|--------|-------|
| `content_intelligence/` | Fully tested | Generator, repo, quality gate, timeliness |
| `storyboard/` | Fully tested | Generator, repo, style/metaphor/format helpers |
| `brief/`, `script/`, `carousel/`, `newsletter/`, `thumbnail/` repos | Partial | Only via `LocalStorage`; **no dedicated repository tests** |

**Production gap (not a test gap):** CI and Storyboard are **not called from `cli.py`**. Tests cover the modules; **CLI integration of these domains is untested** because it does not exist yet.

---

### Platform (`platform/storage/`)

| Module | Status | Gaps |
|--------|--------|------|
| `json_repository.py` | Partial | `list_all` / `get` on corrupt JSON; `save` `OSError` |
| `local_backend.py` | Partial | `save_raw` exception path; only writeability check in `test_storage` |

---

### Inference (`inference/`)

| Module | Status | Gaps |
|--------|--------|------|
| `manager.py` | Fully tested | Failover, cooldown, cache hit, no-fallback (mocked providers) |
| `retry.py` | Fully tested | Retry loop, backoff, non-retryable short-circuit |
| `cache.py` | Partial | **Corrupt cache file → silent miss** untested |
| `health.py` | Partial | Cooldown after 3 failures tested |
| `providers/gemini.py` | Partial | **`_classify_client_error` / real SDK paths** untested |
| `providers/openrouter.py` | Partial | **HTTP status classification / `requests` errors** untested |

**Note:** Prior audit (`test_coverage_gap_report.md`, 2026-06-01) listed inference as untested; **`test_inference_critical.py` (added since) addresses manager/retry/cache/health orchestration** with provider mocks.

---

### Collectors (`collectors/`)

| Module | Status | Gaps |
|--------|--------|------|
| `base.py` | Partial | **`collect()` never invoked** (0 call sites in repo + tests) |
| `rss.py` | Partial | `fetch` + `normalize` tested; **`parse()` not unit-tested directly** (covered indirectly in `test_integration` / E2E) |

---

### Workflow (`workflow/`)

| Module | Status | Gaps |
|--------|--------|------|
| `state.py` | **Untested** | **0%** — `WorkflowStateManager` used in CLI `generate-assets` / `run-pipeline` |
| All public methods | Untested | `load_state`, `save_state`, `mark_completed`, `mark_failed`, `stage_completed`, `get_pending_stages` |

**Risk:** Corrupt `data/workflow_state/*.json` → empty state → stages re-run; **no test verifies this.**

---

### Scoring (`scoring/`)

| Module | Status | Gaps |
|--------|--------|------|
| `engine.py` | Partial | `score_items` + rejection tested; **`get_config_summary` / `get_enabled_rules` untested** |
| `validation.py` | Fully tested | All three rules + engine integration |
| `config.py` | Fully tested | YAML load |
| `rules.py` | Partial | Only `KeywordRule`, `RecencyRule`; **`SourceQualityRule`, `QualityRule` untested**; engine uses **`SimpleRule`**, not `rules.py` |
| `base.py` | Partial | ABCs exercised indirectly |

---

### Storage (`storage/local.py`)

| Status | **Partial** — 66% coverage |

**Tested (directly or via feature tests):** `save_staged`, `get_staged`, `list_staged`, `exists`, `update_asset_status`, `list_briefs` (incl. corrupt JSON warning), calendar + analytics I/O, writeability guard.

**Weak / untested paths**

| Method / area | Coverage |
|---------------|----------|
| `save_scored`, `get_scored`, `list_scored` | E2E only via CLI `score-topics`; **no unit tests** |
| `save_raw` | Indirect via `test_integration` / E2E |
| `save_*` / `list_*` for scripts, carousels, newsletters, thumbnails | Via manifest/planner tests, not isolated |
| `list_dryruns`, `scored_exists` | **No callers in tests** |
| `save_manifest`, `list_manifests` | Manifest tests |

---

## Coverage snapshot (lowest production modules)

| Module | Line coverage | Classification |
|--------|---------------|----------------|
| `workflow/state.py` | **0%** | Untested |
| `workflow/__init__.py` | **0%** | Untested |
| `cli.py` | **14%** | Partial |
| `inference/providers/gemini.py` | **48%** | Partial |
| `inference/providers/openrouter.py` | **48%** | Partial |
| `scoring/rules.py` | **46%** | Partial |
| `collectors/base.py` | **53%** | Partial |
| `utils/logging.py` | **60%** | Partial |
| `storage/local.py` | **66%** | Partial |
| `utils/config.py` | **70%** | Partial |

**50 modules** reported at **100%** line coverage (mostly models, enums, small domain files).

---

## Top 20 highest-risk untested areas

Ranked by **risk score = Impact × Likelihood** (each 1–5, max 25).  
**Impact:** severity if broken in production. **Likelihood:** chance of regression reaching prod undetected.

| Rank | Area | Production location | Test gap | Impact | Likelihood | Score |
|------|------|---------------------|----------|--------|------------|-------|
| 1 | **Workflow stage persistence** | `workflow/state.py` — `WorkflowStateManager` | **0% coverage**; CLI `generate-assets` / `run-pipeline` depend on it | 5 | 5 | **25** |
| 2 | **`run-pipeline` command** | `cli.py` | Full multi-stage orchestration untested | 5 | 5 | **25** |
| 3 | **`generate-assets` + workflow skip logic** | `cli.py` + `WorkflowStateManager.stage_completed` | Asset loop + resumability untested | 5 | 5 | **25** |
| 4 | **Provider HTTP error classification** | `inference/providers/gemini.py`, `openrouter.py` — `generate_once` bodies | Tests mock `generate_once`; 429/401/500 mapping untested | 5 | 4 | **20** |
| 5 | **Multi-stage pipeline integration** | Brief → CI → Storyboard → Thumbnail | Stages tested in isolation only; **no chained test** | 5 | 4 | **20** |
| 6 | **CI / Storyboard CLI wiring** | Not in `cli.py` today | Modules tested; **production path missing** — future merge risk | 5 | 4 | **20** |
| 7 | **`generate-briefs` CLI command** | `cli.py` | `generate_brief` unit-tested; CLI wiring (API key, sleep, storage) not | 4 | 5 | **20** |
| 8 | **Corrupt workflow state JSON** | `WorkflowStateManager.load_state` | Silent empty state on decode error | 4 | 5 | **20** |
| 9 | **Corrupt inference cache JSON** | `inference/cache.py` `get()` | `JSONDecodeError` → `None` untested | 4 | 4 | **16** |
| 10 | **`JsonRepository` corrupt / missing entities** | `platform/storage/json_repository.py` | `ValidationError` on load; `OSError` on save | 4 | 4 | **16** |
| 11 | **`PromptRegistry` failure paths** | `prompts/registry.py` | `KeyError` (unknown key), `FileNotFoundError` (missing file) | 4 | 4 | **16** |
| 12 | **`review-assets` interactive CLI** | `cli.py` | Approve/reject loop untested | 4 | 4 | **16** |
| 13 | **`batch-approve` + manifest rebuild** | `cli.py` | Bulk approval untested | 4 | 4 | **16** |
| 14 | **`plan-week` / `dry-run` CLI** | `cli.py` | `PostingPlanner` / `DryRunValidator` well unit-tested; **CLI glue untested** | 4 | 4 | **16** |
| 15 | **`LocalStorage` scored-topic APIs** | `storage/local.py` — `save_scored`, `get_scored`, `list_scored` | Only E2E `score-topics`; edge cases not isolated | 4 | 3 | **12** |
| 16 | **`PipelineLogger` JSONL stages** | `utils/logging.py` | Used only in `run-pipeline`; untested | 4 | 3 | **12** |
| 17 | **`generate_brief` + real `InferenceManager`** | `generation/brief.py` | Unit tests mock manager; integration with retry/cache/failover untested | 4 | 3 | **12** |
| 18 | **`ManifestBuilder` format-mapping edge cases** | `manifest.py` — `FREETEXT_TO_FORMAT`, optional assets | Partial coverage (82%); free-text format branches | 4 | 3 | **12** |
| 19 | **`BaseCollector.collect()` orchestration** | `collectors/base.py` | Never called; `IngestionEngine` duplicates logic | 3 | 3 | **9** |
| 20 | **`init-analytics` / `update-analytics` CLI** | `cli.py` | Analytics storage unit-tested; CLI commands not | 3 | 3 | **9** |

### Honorable mentions (below top 20)

| Area | Score | Note |
|------|-------|------|
| `LocalBackend.save_raw` failure | 9 | Log-and-continue path |
| `RSSCollector.parse()` direct tests | 9 | Indirect coverage exists |
| `scoring/rules.py` unused in engine | 6 | Production uses `SimpleRule`; rules file is test-only |
| `get_config` / `get_config_summary` | 4–6 | Dead or debug APIs |
| `list_dryruns` / `scored_exists` | 4 | No production callers yet |

---

## CLI command coverage matrix

| Command | Tested? | Test reference |
|---------|---------|----------------|
| `--version` / `--help` | Yes | `test_cli.py` |
| `status` | Yes | `test_cli.py` |
| `collect` | Partial | Mocked in `test_cli.py`; real in `test_e2e_verification.py` |
| `score-topics` | Yes | `test_e2e_verification.py` |
| `list-topics` | No | — |
| `validate-items` | No | — |
| `review-scores` | No | — |
| `scoring-dashboard` | No | — |
| `generate-briefs` | No | `generate_brief` tested separately |
| `generate-assets` | No | — |
| `batch-approve` | No | — |
| `run-pipeline` | No | — |
| `build-manifest` | No | `ManifestBuilder` unit-tested |
| `build-all-manifests` | No | — |
| `plan-week` | No | `PostingPlanner` unit-tested |
| `dry-run` | No | `DryRunValidator` unit-tested |
| `init-analytics` | No | — |
| `update-analytics` | No | — |
| `review-assets` | No | — |

---

## What is well covered (strengths)

- **Domain generators** (CI, Storyboard, Script, Carousel, Newsletter, Thumbnail) with fallback and parse-failure paths.
- **Inference orchestration** (`InferenceManager`, `RetryManager`, failover, cooldown, cache hit) — `test_inference_critical.py`.
- **Brief generation function** — `test_brief_generation_critical.py` (12 cases).
- **Planning** — `PostingPlanner.plan_week` scheduling rules; `DryRunValidator.run`.
- **Scoring validation** — `ValidationEngine` and rejection via `ScoringEngine.score_items`.
- **Manifest builder** — complete / blocked / `ready_for_planner` semantics.
- **Ingestion** — deduplication, race on `FileExistsError`, full RSS loop integration.

---

## Recommended test priorities (audit only)

1. **`tests/test_workflow.py`** — `WorkflowStateManager` lifecycle + corrupt JSON (addresses ranks 1, 8).
2. **`tests/test_cli_pipeline.py`** — `run-pipeline` / `generate-assets` with mocked `InferenceManager` and `tmp_path` (ranks 2, 3, 7).
3. **`tests/test_inference_providers.py`** — classify errors without network (inject `ClientError` / mock `requests`) (rank 4).
4. **`tests/test_pipeline_integration.py`** — Brief → CI → Storyboard → Thumbnail chain with mocked inference (ranks 5, 6).
5. **`tests/test_prompt_registry.py`** — `KeyError` + `FileNotFoundError` (rank 11).
6. **`tests/test_json_repository.py`** — corrupt file + `ValidationError` (rank 10).

---

## Relation to prior audit

`docs/audit/test_coverage_gap_report.md` (2026-06-01, 165 tests) predates:

- `test_inference_critical.py` — closes the “inference layer never exercised” finding for **manager/retry/cache/health**.
- `test_brief_generation_critical.py` — closes “`generate_brief` has zero tests”.
- `test_inference_fallback.py` — covers fallback constructor wiring.

**Still accurate from that report:** workflow untested, CLI mostly untested, provider HTTP bodies untested, no full pipeline integration test.

---

*End of audit. No repository files were modified.*
