# Storage Repository Plan

> Architecture Blueprint — Phase C.1 (Documentation Only)
> Created: 2026-05-29
> Status: PLANNING — No code changes permitted in this phase.

---

## 1. Executive Summary

### Current Storage Architecture

All persistence lives in a single class: `storage/local.py` → `LocalStorage` (446 lines).

It manages 13 directories, imports 10 domain models, and provides 26 public methods covering save, list, get, exists, and update operations for every domain in the system.

### Problems Identified

1. **God object:** One class owns persistence for all domains.
2. **10 domain model imports at module level** — platform depends on all domains (inverted dependency).
3. **Structural duplication:** 8 save methods and 8 list methods are byte-for-byte identical in pattern.
4. **Mixed concerns:** `save_staged` contains atomic dedup logic (domain), while `save_raw` contains timestamp naming (infrastructure).
5. **Cross-domain dispatch:** `update_asset_status` uses a string-keyed dispatch table across 5 domains.
6. **Backend lock-in:** Every method hardcodes `Path` + `open()` — no abstraction for alternative backends.

### Recommended Direction

- Extract a generic `JsonRepository[T]` base in `platform/storage/` that owns file I/O mechanics.
- Each domain gets a thin repository that knows its model class and ID strategy.
- `LocalStorage` becomes a facade during migration, delegating to domain repositories.

---

## 2. LocalStorage Responsibility Audit

| Method | Category | Evidence |
|--------|----------|----------|
| `__init__` (directory setup) | Infrastructure | Creates 13 `Path` objects, calls `_ensure_dirs` |
| `_verify_writeable` | Infrastructure | Filesystem write test, no domain knowledge |
| `_ensure_dirs` | Infrastructure | `mkdir` for all directories, no domain knowledge |
| `save_raw` | Infrastructure | Timestamp-based naming, raw payload dump, no model |
| `save_staged` | **Mixed** | Uses `item.id` (domain) + mode `'x'` atomic dedup (domain logic) + file I/O (infra) |
| `save_scored` | Infrastructure pattern | `item.id` → `model_dump_json` → write. Generic. |
| `save_brief` | Infrastructure pattern | `brief.topic_id` → `model_dump_json` → write. Generic. |
| `save_script` | Infrastructure pattern | Identical to save_brief |
| `save_carousel` | Infrastructure pattern | Identical to save_brief |
| `save_newsletter` | Infrastructure pattern | Identical to save_brief |
| `save_thumbnail` | Infrastructure pattern | Identical to save_brief |
| `save_manifest` | Infrastructure pattern | Identical to save_brief |
| `save_calendar` | Infrastructure pattern | Uses `week_start` as key (domain knowledge of ID strategy) |
| `save_dryrun` | Infrastructure pattern | Uses `week_start` as key |
| `save_analytics` | Infrastructure pattern | Uses `post_id` as key |
| `list_staged` | Infrastructure pattern | glob → json.load → Model(**data) |
| `list_scored` | Infrastructure pattern | Identical to list_staged |
| `list_briefs` | Infrastructure pattern | Identical to list_staged |
| `list_scripts` | Infrastructure pattern | Identical to list_briefs |
| `list_carousels` | Infrastructure pattern | Identical to list_briefs |
| `list_newsletters` | Infrastructure pattern | Identical to list_briefs |
| `list_thumbnails` | Infrastructure pattern | Identical to list_briefs |
| `list_manifests` | Infrastructure pattern | Identical to list_briefs |
| `list_calendars` | Infrastructure pattern | Identical to list_briefs |
| `list_dryruns` | Infrastructure pattern | Identical to list_briefs |
| `list_analytics` | Infrastructure pattern | Identical to list_briefs |
| `get_staged` | Infrastructure pattern | ID → file path → json.load → Model |
| `get_scored` | Infrastructure pattern | Identical to get_staged |
| `get_analytics` | Infrastructure pattern | Identical to get_staged (uses `post_id`) |
| `exists` | Infrastructure | Path existence check |
| `scored_exists` | Infrastructure | Path existence check |
| `update_asset_status` | **Domain Logic** | Cross-domain dispatch table, JSON field mutation, ReviewStatus knowledge |

---

## 3. Duplication Analysis

### Save Pattern (repeated 8 times)

```python
def save_<type>(self, obj: Model) -> Path:
    file_path = self.<type>s_dir / f"{obj.<id_field>}.json"
    try:
        with open(file_path, "w") as f:
            f.write(obj.model_dump_json(indent=2))
        return file_path
    except Exception as e:
        logger.error(f"Failed to save <type> to {file_path}: {e}")
        raise
```

**Instances:** save_brief, save_script, save_carousel, save_newsletter, save_thumbnail, save_manifest, save_calendar, save_dryrun, save_analytics

**Only variation:** The ID field accessor:
- `topic_id` → brief, script, carousel, newsletter, thumbnail, manifest
- `week_start` → calendar, dryrun
- `post_id` → analytics

### List Pattern (repeated 10 times)

```python
def list_<type>(self) -> List[Model]:
    items = []
    for file_path in self.<type>s_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                items.append(Model(**data))
        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning("Failed to load <type> %s: %s", file_path.name, e)
    return items
```

**Instances:** list_staged, list_scored, list_briefs, list_scripts, list_carousels, list_newsletters, list_thumbnails, list_manifests, list_calendars, list_dryruns, list_analytics

**Only variation:** The Model class used for deserialization.

### Get Pattern (repeated 3 times)

```python
def get_<type>(self, id: str) -> Optional[Model]:
    file_path = self.<dir> / f"{id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            return Model(**data)
    except Exception as e:
        logger.error(...)
        return None
```

**Instances:** get_staged, get_scored, get_analytics

### Unique Methods (not duplicated)

| Method | Why Unique |
|--------|-----------|
| `save_raw` | Timestamp-based naming, raw payload (not Pydantic model) |
| `save_staged` | Uses file mode `'x'` for atomic dedup, re-raises `FileExistsError` |
| `update_asset_status` | Cross-domain dispatch, JSON field mutation without full model load |

---

## 4. Infrastructure vs Domain Ownership

### Platform Storage Responsibilities (`platform/storage/`)

| Responsibility | Description |
|---------------|-------------|
| File I/O | `open()`, `read()`, `write()`, `Path` operations |
| JSON serialization | `json.dump()`, `json.load()`, `model_dump_json()` |
| Directory management | `mkdir`, path construction, existence checks |
| Error handling | Logging on I/O failure, exception wrapping |
| Backend abstraction | Future: S3, SQLite, etc. |
| Writeability verification | `_verify_writeable()` |

### Domain Repository Responsibilities (`domains/*/repository.py`)

| Responsibility | Description |
|---------------|-------------|
| Model class knowledge | Knows which Pydantic model to deserialize into |
| ID strategy | Knows whether key is `topic_id`, `week_start`, or `post_id` |
| ID extraction | Knows how to get the key from a model instance |
| Domain-specific queries | Future: "list briefs needing review", "get latest calendar" |
| Atomic dedup logic | `save_staged` mode `'x'` behavior |
| Cross-domain status update | `update_asset_status` dispatch |

---

## 5. Proposed Repository Architecture

### Platform Layer

```
platform/storage/
    __init__.py
    json_repository.py    # Generic JsonRepository[T] base class
    local_backend.py      # LocalFileBackend (path construction, file I/O)
```

`JsonRepository[T]` provides:
- `save(entity: T) -> Path`
- `list_all() -> List[T]`
- `get(id: str) -> Optional[T]`
- `exists(id: str) -> bool`

Parameterized by:
- `model_class: Type[T]`
- `directory: Path`
- `id_field: str` (default: `"topic_id"`)

### Domain Repositories

```
domains/brief/repository.py       # BriefRepository — id_field="topic_id"
domains/script/repository.py      # ScriptRepository — id_field="topic_id"
domains/carousel/repository.py    # CarouselRepository — id_field="topic_id"
domains/newsletter/repository.py  # NewsletterRepository — id_field="topic_id"
domains/thumbnail/repository.py   # ThumbnailRepository — id_field="topic_id"
```

### Orchestration Repositories (non-domain, cross-cutting)

```
platform/storage/
    topic_repository.py       # TopicRepository — save_staged (atomic), save_scored, exists
    manifest_repository.py    # ManifestRepository — id_field="topic_id"
    calendar_repository.py    # CalendarRepository — id_field="week_start"
    dryrun_repository.py      # DryRunRepository — id_field="week_start"
    analytics_repository.py   # AnalyticsRepository — id_field="post_id"
```

### Special Cases

| Method | Proposed Owner | Reason |
|--------|---------------|--------|
| `save_raw` | `platform/storage/local_backend.py` | Pure infrastructure, no model |
| `save_staged` | `platform/storage/topic_repository.py` | Atomic dedup is ingestion-domain logic |
| `update_asset_status` | `orchestration/` or stays in facade | Cross-domain dispatch, not owned by any single domain |

---

## 6. Dependency Rules

### Allowed

```
domains/script/repository.py
    → platform/storage/json_repository.py
    → shared/types.py (TopicId)
    → domains/script/model.py (Script)

platform/storage/json_repository.py
    → shared/ (types only)
    → pydantic (BaseModel generic)

orchestration/manifest.py
    → domains/*/repository.py (reads from multiple)
```

### Forbidden

```
platform/storage/json_repository.py
    ✗→ domains/script/model.py     (must not know specific models)
    ✗→ domains/brief/model.py      (must not know specific models)

domains/script/repository.py
    ✗→ domains/carousel/repository.py  (no lateral domain deps)

domains/script/repository.py
    ✗→ storage/local.py            (must not depend on god object)
```

### Key Principle

`JsonRepository[T]` accepts `Type[T]` as a constructor parameter, not as an import. This keeps the platform layer model-agnostic.

---

## 7. Migration Sequence

### Phase C.2: Storage Infrastructure Extraction

**Goal:** Create `platform/storage/json_repository.py` with the generic save/list/get/exists pattern.

**Scope:**
- Create `JsonRepository[T]` generic base class
- Parameterized by: model class, directory path, ID field name
- Does NOT replace LocalStorage yet — coexists

**Risk:** LOW — New code only, no existing code modified.

**Validation:** Unit tests for JsonRepository in isolation.

---

### Phase C.3: First Domain Repository (Brief)

**Goal:** Create `BriefRepository` using `JsonRepository[Brief]`, wire it into LocalStorage as delegate.

**Scope:**
- Create `domains/brief/repository.py`
- `LocalStorage.save_brief` delegates to `BriefRepository.save`
- `LocalStorage.list_briefs` delegates to `BriefRepository.list_all`

**Risk:** LOW — Facade pattern preserves all existing call sites.

**Validation:** All 125 tests pass. Brief save/list behavior unchanged.

---

### Phase C.4: Content Domain Repositories (Script, Carousel, Newsletter, Thumbnail)

**Goal:** Create repositories for remaining content domains.

**Scope:**
- `ScriptRepository`, `CarouselRepository`, `NewsletterRepository`, `ThumbnailRepository`
- LocalStorage delegates to each

**Risk:** LOW — Same pattern as C.3, repeated 4 times.

**Validation:** All tests pass. Each domain's persistence independently testable.

---

### Phase C.5: Orchestration Repositories (Manifest, Calendar, DryRun, Analytics)

**Goal:** Extract non-content-domain repositories.

**Scope:**
- `ManifestRepository` (topic_id key)
- `CalendarRepository` (week_start key)
- `DryRunRepository` (week_start key)
- `AnalyticsRepository` (post_id key)

**Risk:** LOW — Same pattern, different ID strategies already parameterized.

**Validation:** All tests pass. Planner and dry-run behavior unchanged.

---

### Phase C.6: Topic Repository (Special Case)

**Goal:** Extract `save_staged` (atomic dedup) and `save_scored` into a dedicated repository.

**Scope:**
- `TopicRepository` with `save_staged` (mode `'x'`), `save_scored`, `get_staged`, `get_scored`, `exists`, `scored_exists`
- Preserves `FileExistsError` re-raise behavior

**Risk:** MEDIUM — `save_staged` has unique atomic semantics that must be preserved exactly.

**Validation:** Ingestion tests pass. Dedup behavior verified. `FileExistsError` propagation confirmed.

---

### Phase C.7: Facade Removal (Optional, Future)

**Goal:** Remove `LocalStorage` facade once all consumers use repositories directly.

**Scope:**
- Update CLI, manifest builder, planner, generators to inject repositories
- Remove `storage/local.py`

**Risk:** HIGH — Broad consumer update. Only after all domains are packaged.

**Validation:** Full test suite. End-to-end pipeline run.

---

## 8. Testing Strategy

### Repository Unit Tests (per domain)

```
domains/brief/tests/test_repository.py
    - test_save_creates_file
    - test_list_all_returns_models
    - test_get_by_id
    - test_get_nonexistent_returns_none
    - test_exists
```

**Ownership:** Domain author.
**Isolation:** Uses `tmp_path` fixture, no external dependencies.

### Platform Storage Tests

```
tests/test_json_repository.py
    - test_generic_save_list_cycle
    - test_generic_get_by_id
    - test_handles_corrupt_json
    - test_handles_validation_error
    - test_directory_creation
```

**Ownership:** Platform maintainer.
**Isolation:** Uses a test Pydantic model, not real domain models.

### Integration Tests (existing, unchanged)

```
tests/test_storage.py          # Existing — validates LocalStorage facade
tests/test_manifest.py         # Reads from storage directories
tests/test_planner.py          # Reads manifests from storage
tests/test_dryrun.py           # Reads calendars from storage
```

**Ownership:** Orchestration maintainer.
**Purpose:** Verify facade delegation works correctly during migration.

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Circular imports (repository → model → shared → ?) | LOW | HIGH | shared/ has zero internal imports; repositories import only their own model |
| Serialization regression (model_dump_json behavior) | NONE | — | Same Pydantic serialization, same method calls |
| File path regression (wrong directory) | LOW | HIGH | Repositories receive directory as constructor param; tests verify paths |
| Workflow state impact | NONE | — | WorkflowStateManager is independent of LocalStorage |
| Manifest builder impact | LOW | LOW | ManifestBuilder reads JSON files directly, not through LocalStorage.list_* |
| Planner impact | LOW | LOW | Planner uses manifests, not raw storage |
| save_staged atomic semantics lost | MEDIUM | HIGH | TopicRepository must preserve mode 'x' exactly; dedicated test |
| update_asset_status breaks | LOW | MEDIUM | Stays in facade until orchestration layer owns it |
| Test discovery breaks with domain test dirs | LOW | LOW | pytest discovers recursively by default |

---

## 10. Architecture Governance Rules

### Rule 1: Domains Own Repositories

Each content domain owns its repository. The repository knows the domain model and ID strategy. No other domain's repository may be imported.

### Rule 2: Storage Backends Do Not Know Domain Models

`JsonRepository[T]` is generic. It receives `Type[T]` as a parameter. It never imports a specific domain model at module level.

### Rule 3: Repositories Own Domain Queries

Any domain-specific query (e.g., "list briefs with status=NEEDS_REVIEW") belongs in the domain's repository, not in platform storage.

### Rule 4: Infrastructure Owns Persistence Mechanics

File I/O, JSON encoding, directory creation, error handling patterns — these belong in `platform/storage/`. Domains do not implement their own file operations.

### Rule 5: ID Strategy Is Domain Knowledge

Whether a model is keyed by `topic_id`, `week_start`, or `post_id` is domain knowledge. The repository declares its ID field; the platform storage uses it generically.

### Rule 6: LocalStorage Facade Persists During Migration

`LocalStorage` remains functional throughout migration. It delegates to repositories internally. Consumers are updated to use repositories directly only in later phases.

### Rule 7: Atomic Semantics Must Be Explicit

`save_staged` uses mode `'x'` for atomic dedup. This is documented, tested, and preserved in `TopicRepository`. No other repository uses this pattern unless explicitly required.

### Rule 8: Cross-Domain Operations Stay in Orchestration

`update_asset_status` dispatches across 5 domains. This is an orchestration concern, not a domain concern. It stays in the facade or moves to orchestration — never into a single domain's repository.
