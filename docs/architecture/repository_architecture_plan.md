# Repository Architecture Plan

> Architecture Blueprint — Phase C.3 (Documentation Only)
> Created: 2026-05-29
> Status: PLANNING — No code changes permitted in this phase.

---

## 1. Executive Summary

### Current State

`LocalStorage` contains 9 save methods, 10 list methods, 3 get methods, 2 exists checks, and 1 cross-domain update method. After Phase C.2, infrastructure (filesystem verification, directory creation, raw saves, existence checks) is delegated to `LocalBackend`. The remaining methods are structurally identical, differing only in:

1. The Pydantic model class used for (de)serialization
2. The ID field accessor (`topic_id`, `week_start`, `post_id`, or `id`)

### Problems Identified

1. **LocalStorage still imports 10 domain models** — platform depends on all domains.
2. **Every save/list/get is copy-paste** with only model class and ID field varying.
3. **No domain can own its persistence** — all persistence logic lives in one shared file.
4. **Adding a new domain (Storyboard) requires modifying LocalStorage** — violates Open/Closed.

### Recommended Direction

A **generic `JsonRepository[T]`** parameterized by model class and ID field is appropriate. Evidence:

- 8 of 9 save methods are byte-for-byte identical in structure
- 10 of 10 list methods are byte-for-byte identical in structure
- 3 of 3 get methods are byte-for-byte identical in structure
- The only variations are: `Type[T]` and `id_field: str`

This is not a speculative abstraction — it is a direct extraction of proven, repeated code.

---

## 2. Repository Responsibility Audit

| Responsibility | Category | Evidence |
|---------------|----------|----------|
| Serialize model to JSON file | Platform | `model.model_dump_json(indent=2)` — same call in all 9 save methods |
| Deserialize JSON to model | Platform | `Model(**data)` — same pattern in all 10 list methods |
| Construct file path from ID | Platform | `dir / f"{id}.json"` — same in all methods |
| Glob directory for all files | Platform | `dir.glob("*.json")` — same in all list methods |
| Check file existence | Platform | `file_path.exists()` — same in all get methods |
| Handle ValidationError/JSONDecodeError | Platform | Same try/except in all list/get methods |
| Know which model class to use | Repository | Each method knows its specific `Model` |
| Know which ID field to extract | Repository | `topic_id` vs `week_start` vs `post_id` vs `id` |
| Atomic dedup on save (mode 'x') | Repository (Topic) | Only `save_staged` uses this |
| Cross-domain status dispatch | Orchestration | `update_asset_status` dispatches across 5 domains |
| Know directory path | Repository | Each repo knows its data subdirectory |

---

## 3. Common Operations Analysis

### Operations That Are Truly Common

| Operation | Signature | Variation Points | Count |
|-----------|-----------|-----------------|-------|
| **save** | `save(entity: T) -> Path` | model class, id_field | 8 identical + 1 special (save_staged) |
| **list_all** | `list_all() -> List[T]` | model class | 10 identical |
| **get** | `get(id: str) -> Optional[T]` | model class, directory | 3 identical |
| **exists** | `exists(id: str) -> bool` | directory | Already in LocalBackend |

### Operations That Are NOT Common

| Operation | Why Unique | Owner |
|-----------|-----------|-------|
| `save_staged` | Uses mode `'x'`, re-raises `FileExistsError` | TopicRepository |
| `update_asset_status` | Dispatches across 5 domains, mutates JSON field | Orchestration |
| `save_raw` | Timestamp naming, no model | LocalBackend (already extracted) |

### Conclusion

**4 operations are generic. 3 are special cases.** The generic operations cover 21 of 24 remaining domain methods (87.5%).

---

## 4. ID Strategy Analysis

| Strategy | Used By | Field Accessor | Example Value |
|----------|---------|---------------|---------------|
| `topic_id` | Brief, Script, Carousel, Newsletter, Thumbnail, Manifest | `entity.topic_id` | `"5d2862b7a56a..."` (SHA-256) |
| `id` | TopicItem, ScoredTopicItem | `entity.id` | `"5d2862b7a56a..."` (SHA-256) |
| `week_start` | WeeklyCalendar, DryRunReport | `entity.week_start` | `"2026-06-01"` |
| `post_id` | PostAnalytics | `entity.post_id` | `"{topic_id}_{format}_{week_start}"` |

### Can One Abstraction Support All?

**Yes.** The ID field name is the only variation. A repository parameterized by `id_field: str` handles all cases:

```python
# Conceptual — not implementation
def _get_id(self, entity: T) -> str:
    return getattr(entity, self._id_field)
```

### Design Constraint

The `id_field` must be a string attribute name that exists on the model. This is a constructor parameter, not a runtime discovery. Each repository declares its ID field at instantiation.

---

## 5. Generic Repository Evaluation

### Proposal: `JsonRepository[T]`

A generic class parameterized by:
- `model_class: Type[T]` — the Pydantic model for deserialization
- `directory: Path` — where files are stored
- `id_field: str` — attribute name for the entity's unique key

Provides:
- `save(entity: T) -> Path`
- `list_all() -> List[T]`
- `get(id: str) -> Optional[T]`
- `exists(id: str) -> bool`

### Benefits

| Benefit | Evidence |
|---------|----------|
| Eliminates 21 copy-paste methods | 8 save + 10 list + 3 get currently duplicated |
| Adding Storyboard requires zero platform changes | Just instantiate `JsonRepository[Storyboard]` |
| Each domain can own its repository | `ScriptRepository = JsonRepository[Script]` with `id_field="topic_id"` |
| Backend swappable | Replace file I/O in one place for S3/SQLite |
| Testable in isolation | `tmp_path` + any Pydantic model |

### Drawbacks

| Drawback | Mitigation |
|----------|-----------|
| Generic type may confuse IDE tooling | Type alias per domain provides concrete types |
| `getattr` for ID extraction is implicit | Documented, tested, fails fast on typo |
| Cannot handle `save_staged` atomic semantics | TopicRepository overrides/extends save |

### Alternatives Considered

| Alternative | Verdict | Reason |
|-------------|---------|--------|
| No generic — keep copy-paste | **Rejected** | 21 identical methods is unmaintainable |
| ABC/Protocol-based interface | **Rejected** | Adds abstraction without reducing duplication |
| Per-domain full implementation | **Rejected** | Each would re-implement the same 4 methods |
| Mixin-based approach | **Rejected** | More complex than simple generic class |

### Recommendation

**`JsonRepository[T]` is appropriate.** It is not speculative — it is a direct extraction of 21 proven, identical methods into a single parameterized implementation.

---

## 6. Domain Repository Design

### Brief Repository

```
Owner: domains/brief/
Model: Brief
ID field: topic_id
Directory: data/briefs/
Operations: save, list_all, get (future), exists (future)
Special logic: None
```

### Script Repository

```
Owner: domains/script/
Model: Script
ID field: topic_id
Directory: data/scripts/
Operations: save, list_all, get (future)
Special logic: None
```

### Carousel Repository

```
Owner: domains/carousel/
Model: Carousel
ID field: topic_id
Directory: data/carousels/
Operations: save, list_all
Special logic: None
```

### Newsletter Repository

```
Owner: domains/newsletter/
Model: Newsletter
ID field: topic_id
Directory: data/newsletters/
Operations: save, list_all
Special logic: None
```

### Thumbnail Repository

```
Owner: domains/thumbnail/
Model: ThumbnailPrompt
ID field: topic_id
Directory: data/thumbnails/
Operations: save, list_all
Special logic: None
```

### Future Domain Queries

As domains mature, repositories may gain domain-specific queries:

- `BriefRepository.list_needing_review() -> List[Brief]`
- `ScriptRepository.get_by_format(format: str) -> List[Script]`

These are domain-owned extensions, not platform concerns.

---

## 7. Special Case Analysis

### `save_staged()` — Atomic Dedup

**Current behavior:**
```python
with open(file_path, "x") as f:  # fails if exists
    f.write(item.model_dump_json(indent=2))
# FileExistsError re-raised to caller
```

**Where it belongs:** `TopicRepository` (extends or overrides the generic save).

**Rationale:** Atomic dedup is ingestion-domain logic. No other domain needs this. The generic `save` uses mode `'w'` (overwrite). TopicRepository overrides with mode `'x'`.

**Implementation approach:** TopicRepository can either:
1. Subclass `JsonRepository[TopicItem]` and override `save` with mode `'x'`
2. Add a `save_new(entity)` method alongside the generic `save`

Option 2 is preferred — it preserves the ability to update scored items (which use mode `'w'`).

### `update_asset_status()` — Cross-Domain Dispatch

**Current behavior:**
```python
asset_dirs = {"brief": ..., "script": ..., "carousel": ..., "newsletter": ..., "thumbnail": ...}
# reads JSON, mutates review_status field, writes back
```

**Where it belongs:** Orchestration layer (CLI or a dedicated service).

**Rationale:**
- It dispatches across 5 domains — no single domain owns it.
- It mutates a JSON field without loading the full model — this is a deliberate optimization.
- It uses `ReviewStatus` from shared — correct dependency direction.

**Migration path:** Stays in `LocalStorage` facade until orchestration layer is established. Then moves to `orchestration/review.py` or similar.

---

## 8. Future Backend Considerations

### Filesystem (Current)

- `Path` + `open()` + `json.dump/load`
- `glob("*.json")` for listing
- Mode `'x'` for atomic creation
- Zero infrastructure cost

### S3-Compatible Storage (Future)

- Replace `open()` with `put_object()`/`get_object()`
- Replace `glob()` with `list_objects(prefix=...)`
- Replace mode `'x'` with conditional put (if-none-match)
- `JsonRepository[T]` abstracts this — domain repos unchanged

### SQLite (Future)

- Replace file-per-entity with table-per-domain
- Replace `glob()` with `SELECT * FROM ...`
- Replace `get()` with `SELECT WHERE id = ?`
- `JsonRepository[T]` abstracts this — domain repos unchanged

### How Repository Architecture Supports Evolution

The key insight: **domain repositories don't do file I/O directly.** They delegate to `JsonRepository[T]`, which delegates to `LocalBackend`. Swapping the backend means:

1. Create `S3Backend` implementing the same interface as `LocalBackend`
2. Pass it to `JsonRepository[T]` instead of the local backend
3. Zero domain code changes

---

## 9. Migration Sequence

### Phase C.4: JsonRepository Implementation

**Goal:** Create the generic `JsonRepository[T]` in `platform/storage/`.

**Scope:**
- `platform/storage/json_repository.py`
- Parameterized by: `model_class`, `directory`, `id_field`
- Provides: `save`, `list_all`, `get`, `exists`
- Unit tested independently with a test model

**Risk:** LOW — New code only, no existing code modified.

**Validation:** Dedicated unit tests pass. No integration impact.

---

### Phase C.5: Brief Repository

**Goal:** Create `BriefRepository` using `JsonRepository[Brief]`, delegate from LocalStorage.

**Scope:**
- Create repository (thin: just instantiation with correct params)
- `LocalStorage.save_brief` → delegates to `BriefRepository.save`
- `LocalStorage.list_briefs` → delegates to `BriefRepository.list_all`

**Risk:** LOW — Facade preserves all call sites.

**Validation:** All 125 tests pass unchanged.

---

### Phase C.6: Script Repository

**Goal:** Same pattern as C.5 for Script.

**Scope:** `ScriptRepository`, delegate save_script/list_scripts.

**Risk:** LOW.

**Validation:** All tests pass.

---

### Phase C.7: Carousel Repository

**Goal:** Same pattern for Carousel.

**Risk:** LOW.

---

### Phase C.8: Newsletter Repository

**Goal:** Same pattern for Newsletter.

**Risk:** LOW.

---

### Phase C.9: Thumbnail Repository

**Goal:** Same pattern for Thumbnail.

**Risk:** LOW.

---

### Phase C.10: Orchestration Repositories (Manifest, Calendar, DryRun, Analytics)

**Goal:** Extract remaining non-content-domain repositories.

**Scope:**
- ManifestRepository (topic_id)
- CalendarRepository (week_start)
- DryRunRepository (week_start)
- AnalyticsRepository (post_id, includes get)

**Risk:** LOW — Same pattern, different ID fields.

---

### Phase C.11: Topic Repository (Special Case)

**Goal:** Extract save_staged/save_scored/get_staged/get_scored/list_staged/list_scored.

**Scope:**
- TopicRepository extends or wraps JsonRepository
- Preserves mode `'x'` atomic semantics for save_staged
- save_scored uses standard mode `'w'`

**Risk:** MEDIUM — Atomic semantics must be preserved exactly.

**Validation:** Ingestion tests pass. FileExistsError propagation confirmed.

---

## 10. Testing Strategy

### Repository Unit Tests

Each repository gets tests verifying:
- `save` creates correct file at correct path
- `list_all` returns all valid entities, skips corrupt files
- `get` returns entity by ID, returns None if missing
- `exists` returns correct boolean

**Fixture:** `tmp_path` — no mocking needed.

### JsonRepository Generic Tests

Test the base class with a synthetic model:
```python
class _TestModel(BaseModel):
    topic_id: str
    value: str
```

Verifies generic behavior independent of any real domain.

### Integration Tests (Unchanged)

Existing tests (`test_storage.py`, `test_manifest.py`, `test_planner.py`) continue to exercise the `LocalStorage` facade. They validate that delegation works correctly.

### Ownership

| Test Category | Owner |
|--------------|-------|
| `JsonRepository` generic tests | Platform |
| `BriefRepository` tests | Brief domain |
| `ScriptRepository` tests | Script domain |
| Integration tests | Orchestration |

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Import cycle: repo → model → shared → repo | NONE | — | shared/ has zero imports; repos import only own model |
| Serialization regression | NONE | — | Same `model_dump_json` / `Model(**data)` calls |
| Workflow state impact | NONE | — | WorkflowStateManager is independent |
| Manifest builder impact | LOW | LOW | ManifestBuilder reads files directly, not through list_* |
| Planner impact | NONE | — | Planner reads manifests, not domain repos |
| save_staged atomics lost | MEDIUM | HIGH | TopicRepository preserves mode 'x'; dedicated test |
| update_asset_status breaks | NONE | — | Stays in facade until orchestration owns it |
| Rollback strategy | — | — | Each phase is independently revertible; facade always works |

---

## 12. Repository Governance Rules

### Rule 1: Repositories Own Domain Persistence Logic

Each domain's repository knows its model class, ID field, and directory. No other component should contain this knowledge.

### Rule 2: Backends Own Filesystem Mechanics

File I/O, path construction, glob operations, error handling — these live in `platform/storage/`. Repositories do not call `open()` directly.

### Rule 3: Repositories Cannot Depend on Other Repositories

`ScriptRepository` cannot import `BriefRepository`. Cross-domain reads go through orchestration.

### Rule 4: Repositories Cannot Depend on Other Domains

`ScriptRepository` imports only `Script` model + `shared/`. Never imports from `domains/brief/`.

### Rule 5: Generic Repository Is Infrastructure

`JsonRepository[T]` lives in `platform/storage/`. It is not a domain concept. Domains instantiate it with their specific parameters.

### Rule 6: Domain-Specific Queries Extend the Repository

If a domain needs `list_by_status(status)`, it adds that method to its repository. The generic base provides only save/list_all/get/exists.

### Rule 7: Cross-Domain Operations Are Orchestration Concerns

`update_asset_status` and any future cross-domain queries belong in orchestration, not in any single domain's repository.

### Rule 8: New Domains Get a Repository by Default

Adding Storyboard means creating `StoryboardRepository = JsonRepository[Storyboard]` with `id_field="topic_id"`. Zero platform changes required.
