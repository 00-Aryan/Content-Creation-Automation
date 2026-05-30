# Domain Migration Plan

> Architecture Blueprint v1.0 — Phase A (Documentation Only)
> Created: 2026-05-29
> Status: PLANNING — No code changes permitted in this phase.

---

## 1. Executive Summary

### Current Architecture

The codebase is a **flat modular monolith** organized by technical layer:

```
src/content_creation/
    models/          # All Pydantic schemas (10 files)
    generation/      # All generators (5 files)
    storage/         # Single LocalStorage god-object (1 file, 460+ lines)
    planning/        # Planner + DryRun
    scoring/         # Rules engine
    collectors/      # RSS ingestion
    inference/       # LLM provider abstraction
    workflow/        # Stage-state persistence
    utils/           # Logging + config
    manifest.py      # Cross-cutting manifest builder
    ingestion.py     # Ingestion orchestrator
    cli.py           # 60KB monolithic CLI
```

### Target Architecture

A **domain-oriented modular monolith** organized by business capability:

```
src/content_creation/
    shared/          # Cross-cutting types and enums
    platform/        # Infrastructure (storage, inference, workflow, utils)
    domains/
        brief/       # Model, generator, repository, prompts, tests
        script/      # Model, generator, repository, prompts, tests
        carousel/    # Model, generator, repository, prompts, tests
        newsletter/  # Model, generator, repository, prompts, tests
        thumbnail/   # Model, generator, repository, prompts, tests
        storyboard/  # (future) Model, generator, repository, prompts, tests
    orchestration/   # CLI, manifest builder, planner, dry-run
```

### Why Migration Is Needed

1. **False coupling:** `ReviewStatus` lives in `models/brief.py` but is imported by 13 files — every domain appears to depend on Brief.
2. **God object:** `storage/local.py` (460+ lines) owns persistence for all domains with identical repeated patterns.
3. **No domain isolation:** Adding Storyboard requires touching 11 files across 6 directories.
4. **Unclear ownership:** No single developer can reason about "the Script domain" without reading 5 scattered files.
5. **Test monolith:** `test_generation_scaffold.py` (23KB) tests all generators in one file.

---

## 2. Current Domain Inventory

### Brief Domain

| Aspect | Current Location |
|--------|-----------------|
| Model | `models/brief.py` — `Brief`, `ReviewStatus` |
| Generator | `generation/brief.py` — `generate_brief()` (function, not class) |
| Storage | `storage/local.py` — `save_brief()`, `list_briefs()` |
| Prompt | `prompts/summarize.md` |
| Tests | `tests/test_generation_scaffold.py` (partial) |

- **Inputs:** `ScoredTopicItem`, prompt template, API key
- **Outputs:** `Brief` (JSON to `data/briefs/`)
- **Dependencies:** `inference.InferenceManager`, `models.topic.ScoredTopicItem`
- **Consumers:** All 4 asset generators, `ManifestBuilder`, `PostingPlanner`

### Script Domain

| Aspect | Current Location |
|--------|-----------------|
| Model | `models/script.py` — `Script` |
| Generator | `generation/script.py` — `ScriptGenerator` class |
| Storage | `storage/local.py` — `save_script()`, `list_scripts()` |
| Prompt | `prompts/short_video.md` |
| Tests | `tests/test_generation_scaffold.py` (partial) |

- **Inputs:** `Brief`, format string (`"short_video"`)
- **Outputs:** `Script` (JSON to `data/scripts/`)
- **Dependencies:** `inference.InferenceManager`, `models.brief.Brief`, `models.brief.ReviewStatus`
- **Consumers:** `ManifestBuilder` (reads `review_status`, `generated_at`), `PostingPlanner` (path reference)

### Carousel Domain

| Aspect | Current Location |
|--------|-----------------|
| Model | `models/carousel.py` — `Carousel`, `CarouselSlide` |
| Generator | `generation/carousel.py` — `CarouselGenerator` class |
| Storage | `storage/local.py` — `save_carousel()`, `list_carousels()` |
| Prompt | `prompts/carousel.md` |
| Tests | `tests/test_generation_scaffold.py` (partial) |

- **Inputs:** `Brief`
- **Outputs:** `Carousel` (JSON to `data/carousels/`)
- **Dependencies:** `inference.InferenceManager`, `models.brief.Brief`, `models.brief.ReviewStatus`
- **Consumers:** `ManifestBuilder`, `PostingPlanner`

### Newsletter Domain

| Aspect | Current Location |
|--------|-----------------|
| Model | `models/newsletter.py` — `Newsletter`, `NewsletterSection` |
| Generator | `generation/newsletter.py` — `NewsletterGenerator` class |
| Storage | `storage/local.py` — `save_newsletter()`, `list_newsletters()` |
| Prompt | `prompts/newsletter.md` |
| Tests | `tests/test_generation_scaffold.py` (partial) |

- **Inputs:** `Brief`
- **Outputs:** `Newsletter` (JSON to `data/newsletters/`)
- **Dependencies:** `inference.InferenceManager`, `models.brief.Brief`, `models.brief.ReviewStatus`
- **Consumers:** `ManifestBuilder`, `PostingPlanner`

### Thumbnail Domain

| Aspect | Current Location |
|--------|-----------------|
| Model | `models/thumbnail.py` — `ThumbnailPrompt` |
| Generator | `generation/thumbnail.py` — `ThumbnailGenerator` class |
| Storage | `storage/local.py` — `save_thumbnail()`, `list_thumbnails()` |
| Prompt | `prompts/thumbnail.md` |
| Tests | `tests/test_generation_scaffold.py` (partial) |

- **Inputs:** `Brief`
- **Outputs:** `ThumbnailPrompt` (JSON to `data/thumbnails/`)
- **Dependencies:** `inference.InferenceManager`, `models.brief.Brief`, `models.brief.ReviewStatus`
- **Consumers:** `ManifestBuilder`, `PostingPlanner`

---

## 3. Shared Concerns Analysis

### Concepts That Belong in `shared/`

| Concept | Current Location | Import Count | Rationale |
|---------|-----------------|-------------|-----------|
| `ReviewStatus` | `models/brief.py` | 13 files | Used by all 5 content models + all generators + storage + CLI. Has nothing to do with Brief semantically. |
| `topic_id: str` | Raw `str` in 9 models | 9 models | Universal foreign key. Should be a typed alias for traceability. |
| `generated_at: str` | Raw `str` in 8 models | 8 models | Universal timestamp. Should be a typed alias or validated type. |
| `source_links: List[str]` | Repeated in Script, Carousel, Newsletter | 3 models | Shared provenance pattern. |
| `claims_used: List[str]` | Repeated in Script, Carousel, Newsletter | 3 models | Shared grounding pattern. |

### Proposed `shared/` Structure

```
src/content_creation/shared/
    __init__.py
    types.py          # TopicId = NewType("TopicId", str)
                      # ArtifactId = NewType("ArtifactId", str)
                      # GeneratedAt = str (with docstring)
    enums.py          # ReviewStatus enum
    protocols.py      # ContentArtifact protocol (topic_id, review_status, generated_at)
```

### Evidence

Current false dependency chain:
```
models/script.py → from .brief import ReviewStatus
models/carousel.py → from .brief import ReviewStatus
models/newsletter.py → from .brief import ReviewStatus
models/thumbnail.py → from .brief import ReviewStatus
generation/script.py → from content_creation.models.script import Script, ReviewStatus
generation/carousel.py → from content_creation.models.brief import Brief, ReviewStatus
generation/newsletter.py → from content_creation.models.brief import Brief, ReviewStatus
generation/thumbnail.py → from content_creation.models.brief import Brief, ReviewStatus
storage/local.py → from content_creation.models.brief import ReviewStatus (deferred)
cli.py → from content_creation.models.brief import ReviewStatus (3 locations)
```

After extraction, all these become `from content_creation.shared.enums import ReviewStatus`.

---

## 4. Platform Layer Analysis

### Components That Belong in `platform/`

| Component | Current Location | Responsibility | Dependencies |
|-----------|-----------------|----------------|--------------|
| **Inference** | `inference/` | LLM provider abstraction, retry, caching, health | None (leaf) |
| **Storage** | `storage/local.py` | File I/O, JSON serialization, directory management | All models (for deserialization) |
| **Workflow** | `workflow/` | Stage-state persistence, resumability | None (leaf) |
| **Utils** | `utils/` | Logging setup, YAML config loading | None (leaf) |
| **Scoring** | `scoring/` | Rules engine, validation, config | `models.topic` |
| **Collectors** | `collectors/` | RSS/feed fetching | `models.topic` |
| **Ingestion** | `ingestion.py` | Orchestrates collect → normalize → store | `collectors`, `storage`, `models.topic` |

### Proposed `platform/` Structure

```
src/content_creation/platform/
    __init__.py
    inference/        # Unchanged — already well-isolated
        manager.py
        retry.py
        cache.py
        health.py
        providers/
    storage/
        base.py       # Generic JsonRepository[T] base class
        local.py      # LocalFileBackend (directory management)
    workflow/          # Unchanged — already well-isolated
        state.py
    scoring/          # Unchanged — operates on TopicItem only
        engine.py
        config.py
        validation.py
        rules.py
        base.py
    collectors/       # Unchanged — operates on TopicItem only
        rss.py
        base.py
    ingestion.py      # Orchestrates collection
    utils/
        logging.py
        config.py
```

### Ownership Rules

- **Platform owns infrastructure.** It provides services to domains.
- **Platform does NOT own domain models.** It provides generic persistence.
- **Platform does NOT know about specific content types.** It knows about `JsonRepository[T]` where T is any Pydantic model.

---

## 5. Target Architecture

### Full Proposed Structure

```
src/content_creation/
    __init__.py                    # Package version, setup_logging, get_config
    shared/
        __init__.py
        types.py                   # TopicId, ArtifactId, GeneratedAt
        enums.py                   # ReviewStatus
        protocols.py               # ContentArtifact protocol
    platform/
        __init__.py
        inference/                 # LLM abstraction (unchanged internals)
        storage/
            base.py                # JsonRepository[T] generic base
            local.py               # LocalFileBackend
        workflow/
            state.py               # WorkflowStateManager
        scoring/                   # Rules engine (unchanged)
        collectors/                # RSS fetchers (unchanged)
        ingestion.py               # IngestionEngine
        utils/
            logging.py
            config.py
    domains/
        brief/
            __init__.py
            model.py               # Brief model
            generator.py           # generate_brief()
            repository.py          # BriefRepository(JsonRepository[Brief])
            prompts/
                summarize.md
        script/
            __init__.py
            model.py               # Script model
            generator.py           # ScriptGenerator class
            repository.py          # ScriptRepository(JsonRepository[Script])
            prompts/
                short_video.md
        carousel/
            __init__.py
            model.py               # Carousel, CarouselSlide models
            generator.py           # CarouselGenerator class
            repository.py          # CarouselRepository
            prompts/
                carousel.md
        newsletter/
            __init__.py
            model.py               # Newsletter, NewsletterSection models
            generator.py           # NewsletterGenerator class
            repository.py          # NewsletterRepository
            prompts/
                newsletter.md
        thumbnail/
            __init__.py
            model.py               # ThumbnailPrompt model
            generator.py           # ThumbnailGenerator class
            repository.py          # ThumbnailRepository
            prompts/
                thumbnail.md
        storyboard/                # Future — empty until Phase G
            __init__.py
    orchestration/
        __init__.py
        cli.py                     # Main CLI entry point
        manifest.py                # ManifestBuilder (reads all domains)
        planning/
            planner.py             # PostingPlanner
            dryrun.py              # DryRunValidator
    models/                        # COMPATIBILITY SHIM (temporary)
        __init__.py                # Re-exports from domains for backward compat
    generation/                    # COMPATIBILITY SHIM (temporary)
        __init__.py                # Re-exports from domains for backward compat
```

### Ownership Rules

| Layer | Owns | Does NOT Own |
|-------|------|-------------|
| `shared/` | Types, enums, protocols | Business logic, persistence, generation |
| `platform/` | Infrastructure services | Domain models, domain logic |
| `domains/<name>/` | Model, generator, repository, prompts | Other domains, orchestration |
| `orchestration/` | CLI, manifest, planning | Domain internals |

---

## 6. Dependency Rules

### Allowed Dependencies

```
shared/        → (nothing — leaf layer)
platform/      → shared/
domains/X/     → shared/, platform/
orchestration/ → shared/, platform/, domains/
```

### Prohibited Dependencies

| From | Cannot Import | Reason |
|------|--------------|--------|
| `domains/script/` | `domains/carousel/` | No lateral domain coupling |
| `domains/script/` | `domains/brief/model` | Brief is an input via interface, not a hard import |
| `platform/` | `domains/` | Infrastructure must not know about specific domains |
| `shared/` | `platform/`, `domains/` | Shared is the innermost layer |

### Domain Input Contract

Domains receive `Brief` as a **parameter** to their generator, not as an import dependency on the Brief domain. The `Brief` model class is importable because it's a data contract, but no domain imports another domain's generator or repository.

```python
# ALLOWED: importing a model for type annotation
from content_creation.domains.brief.model import Brief

# PROHIBITED: importing another domain's generator
from content_creation.domains.brief.generator import generate_brief
```

### Orchestration Privilege

Only `orchestration/` may import from multiple domains simultaneously. This is where cross-domain coordination happens (manifest building, CLI routing, planning).

---

## 7. Migration Sequence

### Phase B: Shared Concept Extraction

**Goal:** Extract `ReviewStatus` and shared types into `shared/` to eliminate the false Brief dependency.

**Scope:**
- Create `src/content_creation/shared/__init__.py`
- Create `src/content_creation/shared/enums.py` with `ReviewStatus`
- Create `src/content_creation/shared/types.py` with `TopicId`, `GeneratedAt`
- Update all 13 import sites to use `shared.enums.ReviewStatus`
- Keep `models/brief.py` re-exporting `ReviewStatus` for backward compatibility

**Risk:** LOW — Pure import path change. No runtime behavior change.

**Validation:**
- All 125 tests pass
- `grep -r "from.*brief import.*ReviewStatus"` returns only the compat shim
- No circular imports introduced

---

### Phase C: Storage Repository Extraction

**Goal:** Extract the generic persistence pattern from `LocalStorage` into a base class, then create domain-specific repositories.

**Scope:**
- Create `src/content_creation/platform/storage/base.py` with `JsonRepository[T]`
- Create per-domain repository files (e.g., `domains/script/repository.py`)
- `LocalStorage` becomes a thin facade delegating to repositories
- No file path changes for `data/` directories

**Risk:** MEDIUM — Storage is consumed by CLI, manifest builder, and tests. Facade pattern preserves backward compatibility.

**Validation:**
- All 125 tests pass without modification
- `LocalStorage` still works as before (delegates internally)
- Each repository is independently testable

---

### Phase D: Prompt Ownership Consolidation

**Goal:** Move prompt files to live alongside their domain's generator.

**Scope:**
- Move `prompts/short_video.md` → `domains/script/prompts/short_video.md`
- Move `prompts/carousel.md` → `domains/carousel/prompts/carousel.md`
- Move `prompts/newsletter.md` → `domains/newsletter/prompts/newsletter.md`
- Move `prompts/thumbnail.md` → `domains/thumbnail/prompts/thumbnail.md`
- Move `prompts/summarize.md` → `domains/brief/prompts/summarize.md`
- Update `prompt_dir` references in generators and CLI

**Risk:** LOW — File moves only. Generators already receive `prompt_dir` as constructor parameter.

**Validation:**
- All generation tests pass
- End-to-end `run-pipeline` produces valid output
- No hardcoded paths remain in generators

---

### Phase E: Domain Packaging

**Goal:** Create the `domains/` package structure with model + generator + repository co-located.

**Scope:**
- Create `domains/brief/`, `domains/script/`, `domains/carousel/`, `domains/newsletter/`, `domains/thumbnail/`
- Move models from `models/<name>.py` → `domains/<name>/model.py`
- Move generators from `generation/<name>.py` → `domains/<name>/generator.py`
- Create compatibility shims in `models/__init__.py` and `generation/__init__.py`
- Move repositories from Phase C into domain packages

**Risk:** MEDIUM — Many import paths change. Compatibility shims mitigate breakage.

**Validation:**
- All 125 tests pass (via compatibility shims)
- `python -c "from content_creation.models import Script"` still works
- No circular imports (verified with `importlib` check)

---

### Phase F: Test Migration

**Goal:** Split monolithic test files into domain-owned test modules.

**Scope:**
- Split `test_generation_scaffold.py` into:
  - `domains/script/tests/test_generator.py`
  - `domains/carousel/tests/test_generator.py`
  - `domains/newsletter/tests/test_generator.py`
  - `domains/thumbnail/tests/test_generator.py`
- Move shared fixtures to `tests/conftest.py`
- Keep cross-cutting tests (`test_manifest.py`, `test_planner.py`, `test_dryrun.py`) in top-level `tests/`

**Risk:** LOW — Test reorganization only. No production code changes.

**Validation:**
- `pytest` discovers and runs all tests
- Coverage unchanged
- Each domain's tests runnable in isolation: `pytest domains/script/tests/`

---

### Phase G: Storyboard Domain Introduction

**Goal:** Add the Storyboard domain using the established pattern, validating the architecture supports new domains cleanly.

**Scope:**
- Create `domains/storyboard/model.py` — Pydantic model
- Create `domains/storyboard/generator.py` — `StoryboardGenerator` class
- Create `domains/storyboard/repository.py` — `StoryboardRepository`
- Create `domains/storyboard/prompts/storyboard.md`
- Register in `orchestration/manifest.py` (`FORMAT_TO_ASSET`)
- Register in `orchestration/cli.py` (generate-assets loop)
- Register in `orchestration/planning/planner.py` (`FORMAT_TO_DIR`)
- Add `domains/storyboard/tests/`

**Risk:** LOW — If architecture is correct, this touches only:
1. New domain package (self-contained)
2. Registration points in orchestration (3 files)

**Validation:**
- Storyboard generates from Brief without importing other domains
- Manifest builder discovers storyboard assets
- Planner can schedule storyboard posts
- All existing 125+ tests still pass

---

## 8. Testing Strategy

### Domain Tests (owned by each domain)

```
domains/<name>/tests/
    test_model.py        # Schema validation, edge cases
    test_generator.py    # Generation logic, fallbacks, retry behavior
    test_repository.py   # Save/load/list operations
    conftest.py          # Domain-specific fixtures
```

**Ownership:** Domain author maintains these tests.
**Isolation:** Each domain's tests must pass independently with mocked platform services.

### Platform Tests (owned by platform team)

```
tests/
    test_storage.py      # Generic repository behavior
    test_inference.py    # Provider abstraction, retry, caching
    test_workflow.py     # State persistence
    test_scoring.py      # Rules engine
    test_ingestion.py    # Collection pipeline
```

**Ownership:** Platform/infrastructure maintainer.
**Isolation:** No domain-specific knowledge required.

### Integration Tests (owned by orchestration)

```
tests/
    test_manifest.py     # Cross-domain manifest building
    test_planner.py      # Calendar generation from manifests
    test_dryrun.py       # Validation of calendars
    test_cli.py          # End-to-end CLI commands
    test_e2e.py          # Full pipeline integration
```

**Ownership:** Orchestration maintainer.
**Purpose:** Verify domains work together correctly through orchestration layer.

---

## 9. Risk Assessment

### Import Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Circular import between shared/ and domains/ | LOW | HIGH | shared/ has zero imports from other layers |
| Broken imports during Phase E | MEDIUM | MEDIUM | Compatibility shims in old locations |
| CLI deferred imports break | LOW | LOW | CLI already uses deferred imports for generators |

### Circular Dependency Risks

**Current state:** No circular imports exist. The CLI uses deferred imports (`from content_creation.generation.script import ScriptGenerator` inside function bodies) which prevents import-time cycles.

**Future risk:** If `shared/` accidentally imports from `domains/`, a cycle forms. Prevented by governance rule: shared/ imports nothing from this package.

### Test Breakage Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `test_generation_scaffold.py` breaks during split | MEDIUM | LOW | Split is mechanical — same assertions, different files |
| `test_manifest.py` breaks if asset types change | LOW | MEDIUM | Manifest tests use fixture data, not live generation |
| Import path changes break test imports | MEDIUM | LOW | Compatibility shims active during transition |

### Workflow Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `data/` directory structure changes | NONE | — | Data paths are NOT changing |
| Existing generated artifacts become unreadable | NONE | — | JSON schema is NOT changing |
| `WorkflowStateManager` state files invalidated | NONE | — | State format is NOT changing |

### Storage Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `LocalStorage` facade breaks | LOW | HIGH | Facade delegates to same underlying logic |
| File path construction changes | NONE | — | Paths remain `data/<type>/{topic_id}.json` |
| Concurrent access issues | NONE | — | Single-process local-first design unchanged |

---

## 10. Architecture Governance Rules

### Rule 1: Domains Cannot Import Other Domains

```python
# PROHIBITED
from content_creation.domains.script.generator import ScriptGenerator  # in carousel domain

# ALLOWED
from content_creation.domains.brief.model import Brief  # model-as-contract is OK
```

**Exception:** Importing another domain's **model** for type annotation is permitted. Importing another domain's **generator, repository, or internal logic** is prohibited.

### Rule 2: Prompts Stay With Domains

Every domain owns its prompt templates. Prompts are never shared across domains. If two domains need similar prompting patterns, extract the pattern into `shared/protocols.py` as a structural contract, not a shared prompt file.

### Rule 3: Shared Concepts Stay in `shared/`

If a type, enum, or protocol is used by 3+ domains, it belongs in `shared/`. Domain-specific types stay in their domain.

**Current candidates for shared/:**
- `ReviewStatus` (5 domains)
- `TopicId` type (9 models)
- `GeneratedAt` type (8 models)

### Rule 4: Infrastructure Stays in `platform/`

Storage backends, inference providers, retry logic, caching, health tracking, workflow state — these are platform concerns. Domains consume them via dependency injection, never by reaching into platform internals.

### Rule 5: New Domains Follow the Template

Every new domain must contain:
```
domains/<name>/
    __init__.py        # Public exports
    model.py           # Pydantic model(s)
    generator.py       # Generator class with generate(brief) -> Model
    repository.py      # Repository extending JsonRepository[Model]
    prompts/           # Domain-owned prompt templates
    tests/
        test_generator.py
        test_model.py
```

### Rule 6: Orchestration Is the Only Cross-Domain Coordinator

Only code in `orchestration/` may import from multiple domains. If you find yourself importing two domains in a single file outside orchestration, you're violating domain isolation.

### Rule 7: Backward Compatibility During Migration

During the migration period, compatibility shims in `models/__init__.py` and `generation/__init__.py` must re-export symbols from their new locations. These shims are removed only after all consumers are updated.

### Rule 8: No Schema Changes Without Coordination

Per existing project rules (`TASK_SPEC.md`): "Never change `docs/schema.md` without updating all dependent Pydantic models and tests." This extends to domain models — changing a domain's model requires updating its tests, repository, and any orchestration code that reads its JSON.

### Rule 9: Data Directory Structure Is Frozen

The `data/` directory layout (`data/scripts/`, `data/carousels/`, etc.) does NOT change during migration. File naming (`{topic_id}.json`) does NOT change. This ensures zero data migration risk.

### Rule 10: Tests Must Pass at Every Phase Boundary

No phase is complete until all existing tests pass. Each phase boundary is a valid commit point where the system is fully functional.

---

## Appendix: Storyboard Insertion Points

When Phase G introduces the Storyboard domain, these are the exact registration points in orchestration:

| File | What to Add |
|------|------------|
| `orchestration/manifest.py` → `FORMAT_TO_ASSET` | `"storyboard": "storyboard"` |
| `orchestration/manifest.py` → `ASSET_PATH_PREFIX` | `"storyboard": "data/storyboards"` |
| `orchestration/manifest.py` → asset loop | Include `"storyboard"` in iteration |
| `orchestration/planning/planner.py` → `FORMAT_TO_DIR` | `"storyboard": "data/storyboards"` |
| `orchestration/cli.py` → generate-assets | Add storyboard generation branch |
| `orchestration/cli.py` → batch-approve | Include `"storyboard"` in asset_types list |
| `platform/storage/local.py` | Add `storyboards_dir` path (or auto-discover from repository) |

No existing domain code needs modification.
