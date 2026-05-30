# Prompt Ownership Migration Blueprint

> Phase: D.4a — Architecture & Discovery  
> Status: Design Only — No Implementation  
> Date: 2026-05-30  
> Depends on: D.1 Audit, D.2 CI Blueprint, D.3 Storyboard Blueprint

---

## 1. Executive Summary

All 5 prompts currently live in a flat shared directory (`prompts/`). No abstraction layer exists — generators use raw `open(path, "r")`. The CLI hardcodes `base_dir / "prompts"` in 3 locations. Tests use `tmp_path` fixtures and have zero dependency on real prompt locations.

This creates a migration-friendly situation: prompts can be relocated with minimal code changes (3 CLI sites + 5 generator constructors), and tests require no changes at all.

**Recommended approach:** Introduce a thin `PromptRegistry` that maps `(domain, prompt_name)` → file path. Generators request prompts by domain key. The registry resolves paths, enabling gradual migration from flat directory to domain-owned directories without changing generator logic.

---

## 2. Current Prompt Inventory

| # | File | Size | Domain Owner | Current Consumer |
|---|------|------|-------------|-----------------|
| 1 | `prompts/summarize.md` | ~30 lines | Brief | `generate_brief()` |
| 2 | `prompts/short_video.md` | ~40 lines | Script | `ScriptGenerator` |
| 3 | `prompts/carousel.md` | ~42 lines | Carousel | `CarouselGenerator`, `ScriptGenerator` (loaded but unused) |
| 4 | `prompts/newsletter.md` | ~40 lines | Newsletter | `NewsletterGenerator`, `ScriptGenerator` (loaded but unused) |
| 5 | `prompts/thumbnail.md` | ~50 lines | Thumbnail | `ThumbnailGenerator` |

**Future prompts (not yet created):**

| # | File | Domain Owner | Consumer |
|---|------|-------------|----------|
| 6 | `content_intelligence.md` | Content Intelligence | CI Generator |
| 7 | `storyboard.md` | Storyboard | Storyboard Generator |

---

## 3. Prompt Ownership Audit

| Prompt | Owner Domain | Rationale |
|--------|-------------|-----------|
| `summarize.md` | `brief` | Produces Brief schema; only consumed by brief generator |
| `short_video.md` | `script` | Produces Script schema; only consumed by script generator |
| `carousel.md` | `carousel` | Produces Carousel schema; only consumed by carousel generator |
| `newsletter.md` | `newsletter` | Produces Newsletter schema; only consumed by newsletter generator |
| `thumbnail.md` | `thumbnail` | Produces ThumbnailPrompt schema; only consumed by thumbnail generator |
| `content_intelligence.md` (future) | `content_intelligence` | Will produce CI schema |
| `storyboard.md` (future) | `storyboard` | Will produce Storyboard schema |

**Ownership rule:** A prompt belongs to the domain whose schema it produces.

---

## 4. Prompt Consumer Analysis

| Prompt | Primary Consumer | Secondary Consumer | Notes |
|--------|-----------------|-------------------|-------|
| `summarize.md` | `brief.py::generate_brief()` | None | Loaded via explicit `prompt_path` parameter |
| `short_video.md` | `script.py::ScriptGenerator.generate()` | None | Loaded in `__init__`, used when `format="short_video"` |
| `carousel.md` | `carousel.py::CarouselGenerator.generate()` | `script.py::ScriptGenerator.__init__()` | ScriptGenerator loads it but never uses it for carousel generation |
| `newsletter.md` | `newsletter.py::NewsletterGenerator.generate()` | `script.py::ScriptGenerator.__init__()` | Same: loaded but unused by ScriptGenerator |
| `thumbnail.md` | `thumbnail.py::ThumbnailGenerator.generate()` | None | Single consumer |

**Anomaly:** `ScriptGenerator` loads `carousel.md` and `newsletter.md` in its `__init__` but only ever uses `short_video.md`. This is dead code from an earlier design where ScriptGenerator handled all formats. It creates a false dependency that should be removed during migration.

---

## 5. Prompt Path Dependency Analysis

### Hardcoded Path Assumptions

| Location | Line | Assumption | Pattern |
|----------|:---:|-----------|---------|
| `cli.py` | 329 | `base_dir / "prompts" / "summarize.md"` | Direct path construction |
| `cli.py` | 372 | `base_dir / "prompts"` | Flat directory assumption |
| `cli.py` | 600 | `base_dir / "prompts"` | Duplicated in run-pipeline |
| `brief.py` | 14 | Receives `prompt_path: Path` | No assumption — caller decides |
| `script.py` | 23-25 | `prompt_dir / "short_video.md"` etc. | Filename hardcoded |
| `carousel.py` | 20 | `prompt_dir / "carousel.md"` | Filename hardcoded |
| `newsletter.py` | 20 | `prompt_dir / "newsletter.md"` | Filename hardcoded |
| `thumbnail.py` | 20 | `prompt_dir / "thumbnail.md"` | Filename hardcoded |

### Dependency Graph

```
cli.py ──────────────────────────────────────────────────────────────┐
  │                                                                   │
  ├─ generate-briefs: base_dir/"prompts"/"summarize.md" ──▶ brief.py │
  │                                                                   │
  ├─ generate-assets: base_dir/"prompts" ──▶ ScriptGenerator         │
  │                                         ──▶ CarouselGenerator     │
  │                                         ──▶ NewsletterGenerator   │
  │                                         ──▶ ThumbnailGenerator    │
  │                                                                   │
  └─ run-pipeline: (duplicates both above)                            │
                                                                      │
tests/test_generation_scaffold.py ────────────────────────────────────┘
  │                                                                    
  └─ tmp_path fixtures: create stub .md files (no real path dependency)
```

### Key Insight

The **only** place that knows prompts live in `prompts/` is `cli.py` (3 sites). Generators don't know the directory — they receive it as a parameter. This means the CLI is the single point of change for path migration.

---

## 6. Prompt Loading Architecture Review

### Current Loading Mechanisms

| Pattern | Used By | Mechanism |
|---------|---------|-----------|
| **Pattern A:** Caller passes `prompt_path: Path` | `brief.py` | Generator receives full path; `open(prompt_path, "r")` |
| **Pattern B:** Caller passes `prompt_dir: Path`, generator constructs filename | `script.py`, `carousel.py`, `newsletter.py`, `thumbnail.py` | Generator hardcodes filename; `open(self.prompt_dir / "name.md", "r")` |

### Problems with Current Approach

1. **No abstraction** — Raw `open()` calls; no caching, no validation, no versioning
2. **Inconsistent API** — Brief uses Pattern A; others use Pattern B
3. **Dead loading** — ScriptGenerator loads 3 files, uses 1
4. **No discovery** — No way to list available prompts or validate completeness
5. **Flat assumption** — All prompts must be siblings in one directory

### Recommended Future Architecture: PromptRegistry

```python
# Conceptual — NOT implementation
class PromptRegistry:
    def get(self, domain: str, prompt_name: str) -> str:
        """Return prompt content by domain and name."""
        
    def path_for(self, domain: str, prompt_name: str) -> Path:
        """Return resolved path for a domain prompt."""
        
    def list_domain(self, domain: str) -> List[str]:
        """List all prompts owned by a domain."""
```

**Why PromptRegistry over direct loading:**

| Concern | Direct Loading | PromptRegistry |
|---------|---------------|----------------|
| Path resolution | Hardcoded per generator | Centralized mapping |
| Migration | Change every generator | Change registry config |
| Future domains | New hardcoded paths | Register new domain |
| Testing | Create stub files | Mock registry |
| Caching | None | Optional read-once cache |
| Validation | None | Can verify all prompts exist at startup |

**Why NOT PromptLoader (simple function):**
A loader function solves path resolution but doesn't provide discovery, validation, or domain awareness. The registry pattern scales to 7+ domains without growing complexity.

---

## 7. Future Domain Prompt Requirements

### Content Intelligence Domain

| Prompt | Purpose | Input | Output |
|--------|---------|-------|--------|
| `content_intelligence.md` | Transform Brief into creator strategy | Brief fields | CI schema (hooks, angles, visuals, audience) |

### Storyboard Domain

| Prompt | Purpose | Input | Output |
|--------|---------|-------|--------|
| `storyboard.md` | Coordinate CI resources across formats | Brief + CI fields | Storyboard schema (assignments, palette, differentiation) |

### Potential Future Prompts (per domain)

| Domain | Additional Prompts | Rationale |
|--------|-------------------|-----------|
| Brief | `summarize_v2.md` | Version iteration without breaking v1 |
| Script | `long_video.md` | Format expansion |
| Content Intelligence | `ci_refinement.md` | Human-feedback-driven CI improvement |
| Storyboard | `storyboard_single_format.md` | Simplified storyboard for single-format topics |

---

## 8. Prompt Ownership Target Architecture

### Target Directory Structure

```
prompts/                          # Legacy location (symlinks during migration)
│
src/content_creation/
├── domains/
│   ├── brief/
│   │   └── prompts/
│   │       └── summarize.md
│   ├── script/
│   │   └── prompts/
│   │       └── short_video.md
│   ├── carousel/
│   │   └── prompts/
│   │       └── carousel.md
│   ├── newsletter/
│   │   └── prompts/
│   │       └── newsletter.md
│   ├── thumbnail/
│   │   └── prompts/
│   │       └── thumbnail.md
│   ├── content_intelligence/
│   │   └── prompts/
│   │       └── content_intelligence.md
│   └── storyboard/
│       └── prompts/
│           └── storyboard.md
└── prompt_registry.py            # Central resolution
```

### Alternative: Config-Driven (Lower Risk)

```yaml
# config/prompts.yaml
domains:
  brief:
    summarize: "prompts/brief/summarize.md"
  script:
    short_video: "prompts/script/short_video.md"
  carousel:
    carousel: "prompts/carousel/carousel.md"
  newsletter:
    newsletter: "prompts/newsletter/newsletter.md"
  thumbnail:
    thumbnail: "prompts/thumbnail/thumbnail.md"
  content_intelligence:
    content_intelligence: "prompts/content_intelligence/content_intelligence.md"
  storyboard:
    storyboard: "prompts/storyboard/storyboard.md"
```

**Recommendation:** Config-driven approach. Lower risk, no code-level coupling to directory structure, easy to change paths without code changes.

---

## 9. Migration Sequence

### Step 1: Introduce PromptRegistry (no file moves)

- Create `prompt_registry.py` with hardcoded paths pointing to current `prompts/` location
- All generators continue working unchanged
- **Risk:** Zero — additive only

### Step 2: Wire generators through registry (no file moves)

- Update `brief.py` to use registry instead of `prompt_path` parameter
- Update `script.py`, `carousel.py`, `newsletter.py`, `thumbnail.py` to use registry
- Remove dead loading in `ScriptGenerator.__init__` (carousel.md, newsletter.md)
- Update CLI to pass registry instead of `prompt_dir`
- **Risk:** Low — behavior unchanged, only path resolution changes

### Step 3: Create domain directories (no deletions)

- Create `prompts/brief/`, `prompts/script/`, etc.
- **Copy** (not move) prompts into domain directories
- Update registry config to point to new locations
- Verify all tests pass
- **Risk:** Low — originals still exist as fallback

### Step 4: Remove legacy flat directory

- Delete `prompts/summarize.md`, `prompts/short_video.md`, etc.
- Verify all tests pass
- **Risk:** Low — registry already points to new locations

### Step 5: Add future domain prompts

- Create `prompts/content_intelligence/content_intelligence.md`
- Create `prompts/storyboard/storyboard.md`
- Register in registry
- **Risk:** Zero — additive only

---

## 10. Testing Impact Assessment

### Current Test Behavior

| Test File | Prompt Dependency | Impact of Migration |
|-----------|------------------|-------------------|
| `test_generation_scaffold.py` | Uses `tmp_path` fixtures creating stub `.md` files | **Zero impact** — tests don't reference real prompt paths |
| `test_manifest.py` | Single reference to "prompt" (likely in a string) | **Zero impact** |

### Why Tests Are Safe

1. All test fixtures create their own prompt files in `tmp_path`
2. No test reads from the real `prompts/` directory
3. No test asserts on prompt file content
4. Generator tests mock `InferenceManager` — prompt content is irrelevant to test assertions

### New Tests Needed (Post-Migration)

| Test | Purpose |
|------|---------|
| `test_prompt_registry_resolves_all_domains` | Verify registry returns valid paths for all registered prompts |
| `test_prompt_registry_missing_prompt_raises` | Verify clear error on missing prompt |
| `test_all_registered_prompts_exist_on_disk` | Integration test: all configured paths are real files |

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| Generator behavior changes during migration | Very Low | High | Registry returns identical file content; no prompt rewrites |
| Tests break | Very Low | Medium | Tests use tmp_path; no real path dependency |
| ScriptGenerator dead-load removal causes regression | Low | Low | ScriptGenerator never calls carousel/newsletter prompts; removal is safe |
| Future domain prompts conflict with existing names | Low | Low | Domain namespacing prevents collision |
| Registry adds unnecessary complexity | Medium | Low | Keep registry minimal (~30 lines); config-driven |
| Migration stalls mid-way (half flat, half domain) | Medium | Medium | Registry supports both layouts simultaneously during transition |

### Migration Complexity Per Prompt

| Prompt | Complexity | Risk | Reason |
|--------|:---:|:---:|--------|
| `summarize.md` | Low | Low | Single consumer, explicit path parameter |
| `short_video.md` | Low | Low | Single consumer (ScriptGenerator for short_video) |
| `carousel.md` | Low | Low | Primary consumer clear; dead-load in ScriptGenerator removable |
| `newsletter.md` | Low | Low | Same as carousel |
| `thumbnail.md` | Low | Low | Single consumer, clean pattern |

---

## 12. Governance Rules

### Prompt Ownership Principle

> A prompt belongs to the domain whose **output schema** it produces.

| If prompt produces... | It belongs to domain... |
|----------------------|------------------------|
| Brief schema | `brief` |
| Script schema | `script` |
| Carousel schema | `carousel` |
| Newsletter schema | `newsletter` |
| ThumbnailPrompt schema | `thumbnail` |
| ContentIntelligence schema | `content_intelligence` |
| Storyboard schema | `storyboard` |

### Prompt Modification Rules

1. Only the owning domain may modify its prompts
2. Prompt changes require the domain's tests to pass
3. Prompt versioning: new versions get new filenames (e.g., `summarize_v2.md`), old versions retained until deprecated
4. Cross-domain prompt sharing is forbidden — if two domains need similar logic, extract a shared template partial

### Registry Rules

1. Every prompt must be registered before use
2. Unregistered prompts cannot be loaded (fail-fast)
3. Registry is the single source of truth for prompt locations
4. Registry config is version-controlled

### Implementation Order

1. PromptRegistry (Step 1-2) — **next implementation phase**
2. Directory restructure (Step 3-4) — after registry is stable
3. Future domain prompts (Step 5) — after CI and Storyboard generators exist

---

## Appendix: Files Inspected

| File | Purpose |
|------|---------|
| `prompts/summarize.md` | Brief generation prompt |
| `prompts/short_video.md` | Script generation prompt |
| `prompts/carousel.md` | Carousel generation prompt |
| `prompts/newsletter.md` | Newsletter generation prompt |
| `prompts/thumbnail.md` | Thumbnail generation prompt |
| `src/content_creation/generation/brief.py` | Brief generator (Pattern A loading) |
| `src/content_creation/generation/script.py` | Script generator (Pattern B loading, dead-loads 2 extra) |
| `src/content_creation/generation/carousel.py` | Carousel generator (Pattern B loading) |
| `src/content_creation/generation/newsletter.py` | Newsletter generator (Pattern B loading) |
| `src/content_creation/generation/thumbnail.py` | Thumbnail generator (Pattern B loading) |
| `src/content_creation/cli.py` | CLI entry point (3 prompt path sites) |
| `tests/test_generation_scaffold.py` | Generation tests (tmp_path fixtures) |
| `tests/test_manifest.py` | Manifest tests (1 prompt reference) |
