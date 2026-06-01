# Dependency Audit Report

This document audits the actual dependency graph of the `content-creation` repository and evaluates whether the implemented architecture matches the target architectural design.

---

## 1. Executive Summary

A comprehensive import analysis was performed across all modules in [src/content_creation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation). The audit confirms that **architectural boundaries are being strictly respected** in terms of dependency direction, which flows cleanly upwards (from `shared` and `platform` to `domains`, then to `storage`/`orchestration`). 

### Core Audited Findings
* **0 Circular Dependencies:** There are currently **no** circular dependencies (cycles) at either the file level or package level.
* **Strict Rule Compliance:** All 5 core architectural rules evaluated as **PASS**. Sibling and downstream domain isolation boundaries are structurally clean.
* **Transitional Architectural State:** The codebase is in a transitional phase. Modern domains ([content_intelligence](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/content_intelligence) and [storyboard](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard)) are fully isolated and self-contained. Sibling formats (brief, script, carousel, newsletter, thumbnail) have been partially migrated, keeping their repositories in [domains/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains) but leaving models in the centralized [models/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models) package and generators in the legacy [generation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation) package.

### Success Criteria Answers
1. **Are architectural boundaries being respected?**  
   Yes. No low-level components (`shared`, `platform`) import high-level domain components. Upstream domains do not statically import downstream consumers.
2. **Where are the strongest couplings?**  
   The strongest couplings are centered around the shared vocabulary ([models/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models) package, 15 inbound dependencies) and the persistence facade ([storage/local.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py), which references 5 repositories and 8 models).
3. **What would be hardest to change?**  
   The shared vocabulary schemas inside [models/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models) and the central facade interface of [LocalStorage](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py#L31) would be the hardest to modify because they have the highest fan-in and are referenced across the entire application pipeline.
4. **What architectural debt exists today?**  
   * **Partial Domain Migration:** Five sibling domains are split across separate folders rather than being fully self-contained.
   * **Monolithic CLI:** [cli.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/cli.py) is a 1350-line file that couples CLI input parsing with the actual pipeline orchestration logic.
   * **Facade Persistence:** [storage/local.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) handles raw/staged topics, calendars, dryruns, and analytics directly instead of delegating to specific domain repositories.
5. **Is the project becoming more modular or less modular?**  
   **More modular.** The successful introduction of the `content_intelligence` and `storyboard` domains demonstrates a clear roadmap for self-contained domain structures.

---

## 2. Dependency Inventory

Each package's inbound (who imports it) and outbound (what it imports) dependencies have been identified within the [src/content_creation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation) workspace. 

### Inventory Table

| Package / Module | Direct Outbound Imports | Outbound Count | Inbound Count | Key Inbound Consumers |
| :--- | :--- | :---: | :---: | :--- |
| **shared/** | None | 0 | 6 | `cli`, `domains/content_intelligence`, `domains/storyboard`, `generation`, `models`, `storage` |
| **platform/** | None | 0 | 8 | `storage`, `domains/brief`, `domains/carousel`, `domains/content_intelligence`, `domains/newsletter`, `domains/script`, `domains/storyboard`, `domains/thumbnail` |
| **domains/brief/** | `models`, `platform` | 2 | 1 | `storage` |
| **domains/content_intelligence/** | `inference`, `models`, `platform`, `prompts`, `shared` | 5 | 1 | `domains/storyboard` |
| **domains/storyboard/** | `domains/content_intelligence`, `inference`, `models`, `platform`, `prompts`, `shared` | 6 | 0 | None (Except testing code) |
| **domains/script/** | `models`, `platform` | 2 | 1 | `storage` |
| **domains/carousel/** | `models`, `platform` | 2 | 1 | `storage` |
| **domains/newsletter/** | `models`, `platform` | 2 | 1 | `storage` |
| **domains/thumbnail/** | `models`, `platform` | 2 | 1 | `storage` |
| **generation/** | `inference`, `models`, `prompts`, `shared` | 4 | 1 | `cli` |
| **inference/** | None | 0 | 3 | `domains/content_intelligence`, `domains/storyboard`, `generation` |
| **storage/** | `domains/brief`, `domains/carousel`, `domains/newsletter`, `domains/script`, `domains/thumbnail`, `models`, `platform`, `shared` | 8 | 4 | `cli`, `ingestion`, `manifest`, `planning` |
| **workflow/** | None | 0 | 1 | `cli` |
| **planning/** | `models`, `storage`, `utils` | 3 | 1 | `cli` |
| **analytics** (module) | `shared.types` | 1 | 3 | `cli`, `models`, `storage` |
| **collectors/** | `models` | 1 | 1 | `ingestion` |
| **prompts/** | None | 0 | 5 | `cli`, `domains/content_intelligence`, `domains/storyboard`, `generation` |
| **cli.py** | `generation`, `ingestion`, `manifest`, `models`, `planning`, `prompts`, `scoring`, `shared`, `storage`, `utils`, `workflow` | 11 | 0 | None (Main entry point) |

*Note: `analytics` refers to the module [models/analytics.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models/analytics.py), which handles post-performance structures.*

### Dependency Direction Map
```text
                  [ cli.py ] 
                      │
     ┌────────────────┼────────────────┬──────────────┐
     ▼                ▼                ▼              ▼
[ planning ]     [ workflow ]     [ storage ]    [ generation ]
     │                                 │              │
     │      ┌──────────────────────────┤              │
     │      │                          ▼              │
     │      │   ┌────────────── [ domains ] ◄─────────┤
     │      │   │                      ▲              │
     │      │   │                      │              │
     ▼      ▼   ▼                      │              │
    [ models/vocabulary ]              ├──────────────┼──────────────┐
            │                          │              │              │
            ▼                          ▼              ▼              ▼
       [ shared ]                 [ platform ]   [ inference ]  [ prompts ]
```

---

## 3. Architecture Rule Verification

### Rule A: Shared should not depend on Domains
* **Status:** **PASS**
* **Evidence:** [src/content_creation/shared/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/shared) has 0 outbound dependencies. Its files ([enums.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/shared/enums.py) and [types.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/shared/types.py)) do not contain any imports from `domains/`, `models/`, or other application modules.

### Rule B: Platform should not depend on Domains
* **Status:** **PASS**
* **Evidence:** [src/content_creation/platform/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/platform) contains only [storage/local_backend.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/platform/storage/local_backend.py) and [storage/json_repository.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/platform/storage/json_repository.py). They operate on generic type parameters and do not import any domain models or domain repositories.

### Rule C: Domains should not depend on consuming Domains
* **Status:** **PASS**
* **Evidence:** 
  * [domains/brief/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/brief) does not import other domains.
  * [domains/content_intelligence/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/content_intelligence) does not import other domains.
  * [domains/storyboard/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard) imports `domains/content_intelligence` (upstream producer) but contains zero references to downstream consumers ([script](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/script), [carousel](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/carousel), [newsletter](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/newsletter), or [thumbnail](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/thumbnail)).
  *Slightly coupled sibling format domains consume storyboard data dynamically via parameter passing (duck typing) without importing storyboard symbols statically.*

### Rule D: Generators should not import other generators
* **Status:** **PASS**
* **Evidence:** All generator scripts in [generation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation) and domain-level generators (e.g. [domains/storyboard/generator.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard/generator.py)) only import models, inference helpers, and prompts. They do not cross-import.

### Rule E: Repositories should not depend on unrelated repositories
* **Status:** **PASS**
* **Evidence:** Each `repository.py` file inside [domains/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains) (e.g., [domains/brief/repository.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/brief/repository.py)) only imports the generic [JsonRepository](file:///home/aryan/May-2026/Content-Creation/src/content_creation/platform/storage/json_repository.py) and its local domain model.

---

## 4. Circular Dependency Analysis

### Status: 0 Cycles Detected
Both package-level and file-level depth-first search (DFS) traversals confirm **zero** circular dependency cycles.

### Potential Cycles & Mitigation Risks

| Risk Level | Risk Description | File-level Context | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Medium** | **Domain Repository to Storage Facade Cycle:** If any domain repository imports `LocalStorage` to fetch additional paths, it will form a cycle, since `LocalStorage` imports all repositories. | [domains/brief/repository.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/brief/repository.py) vs [storage/local.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) | **Enforced:** Repositories must only import `platform.storage` elements and receive directory paths strictly as constructor parameters. |
| **Low** | **Downstream Format to Storyboard Cycle:** If format generators statically import the `Storyboard` type for type-hinting, it creates an outbound link to `domains/storyboard`. | [generation/thumbnail.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation/thumbnail.py) vs [domains/storyboard/model.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard/model.py) | **Enforced:** Continue using loose parameter passing (duck typing) or define shared protocol interfaces in `shared/types.py`. |

---

## 5. Legacy Layer Audit

This audit evaluated the roles of [generation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation) and [storage/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage) to determine their trajectory toward retirement.

### Questions & Findings

1. **Are these now compatibility layers?**
   * **[storage/local.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py):** **Yes.** It is a facade bridging the modern domain repositories (`BriefRepository`, `ScriptRepository`, etc.) with legacy JSON-file storage for unmigrated objects (manifests, calendars, scored topics, analytics, and dryruns).
   * **[generation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation):** **No.** It is not a compatibility layer; it remains the active functional generator module for Briefs and the five sibling formats.

2. **Do they still contain business logic?**
   * **Yes.** `generation/` contains crucial prompt formatting templates, string replacement tags, and failure-handling defaults. `storage/local.py` contains path generation structures, validation triggers, and JSON parsing logic.

3. **Are they candidates for future retirement?**
   * **Yes.** Once the generators and schemas for Brief, Script, Carousel, Newsletter, and Thumbnail are migrated to their respective [domains/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains) folders, the central `generation/` folder can be completely retired. Once the remaining items (manifest, calendar, analytics, scored topics) are migrated to repositories, `storage/` can be retired or refactored into a platform utility.

4. **Which responsibilities remain?**
   * **[generation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation):** format-specific LLM orchestration for Brief, Script, Carousel, Newsletter, and Thumbnail.
   * **[storage/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage):** persisting unmigrated data and instantiating repository classes.

---

## 6. Domain Isolation Audit

Each domain's coupling boundary has been analyzed:

* **`brief`**:
  * **Imports:** `shared` (enums/types), `platform` (JsonRepository).
  * **Status:** **Partially Isolated.** Repository lives in domain folder, but the generator lives in `generation/brief.py` and model lives in `models/brief.py`.
* **`content_intelligence`**:
  * **Imports:** `shared`, `platform`, `inference`, `prompts`, `models.topic` (upstream reference).
  * **Status:** **Fully Isolated.** All models, quality validators, generator, and repository are packaged under [domains/content_intelligence/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/content_intelligence).
* **`storyboard`**:
  * **Imports:** `shared`, `platform`, `inference`, `prompts`, `domains/content_intelligence` (model references), `models.brief`.
  * **Status:** **Fully Isolated.** Self-contained in [domains/storyboard/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains/storyboard). It correctly depends only on upstream producer models.
* **`script` / `carousel` / `newsletter` / `thumbnail`**:
  * **Imports:** `platform` (JsonRepository), `models` (for their specific model types).
  * **Status:** **Partially Isolated.** Their repositories live in [domains/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains) subfolders, but their generators and model structures are external.

### Summary
Isolation goals are fully achieved for the new domains (`content_intelligence`, `storyboard`). For the format domains, isolation is partially achieved; there is no horizontal leak (e.g. script does not import newsletter), but they rely on centralized models and generators.

---

## 7. Dependency Hotspots

### High Fan-In (Most Imported)
1. **[models/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models) (15 inbound dependencies):** Shared vocabulary data schemas. 
   * *Risk:* Schema change ripple effect. Any change in models propagates globally.
2. **[platform/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/platform) (8 inbound dependencies):** Repository interfaces.
   * *Risk:* Altering repository interfaces might break persistence methods across all domains.
3. **[shared/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/shared) (6 inbound dependencies):** Enums and types.
   * *Risk:* Very low risk due to simple, static definitions.

### High Fan-Out (Most Dependencies)
1. **[cli.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/cli.py) (11 outbound dependencies):** 
   * *Risk:* High complexity and low cohesion. Serves as a monolith coordinating the entire application.
2. **[storage/local.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) (8 outbound dependencies):** 
   * *Risk:* Facade coupling. Changes in repository initialization or folder structures require editing this centralized file.

---

## 8. Future Integration Risk

The upcoming integration of **Storyboard → Script**, **Storyboard → Newsletter**, and **Storyboard → Carousel** was assessed for architectural risks.

* **Coupling Cycle Risk:** In the target pipeline, Storyboard coordinates the claims and hooks for Script, Newsletter, and Carousel. If the storyboard domain imports format generators statically (e.g. `StoryboardGenerator` invoking `ScriptGenerator`), it will trigger circular dependencies.
* **Type-Hint Dependency Risk:** If format generators statically import the `Storyboard` type, it establishes a dependency from format generators to `storyboard`. Since `storyboard` already depends on format models, this creates high coupling.
* **Mitigation:** The integration should follow the pattern established in [generation/thumbnail.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation/thumbnail.py#L24) (duck-typed `storyboard` parameter passing). The pipeline orchestrator in [cli.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/cli.py) should load the storyboard data and pass it into the format generators, keeping the domains independent of each other.

---

## 9. Architecture Drift Assessment

### Classification: Mostly Aligned
The actual codebase matches the target layers of `shared` ➔ `platform` ➔ `domains` ➔ `orchestration` with minimal deviation.

```text
Target Layer                  Actual Implementation Code
─────────────────────────────────────────────────────────────
Orchestration / CLI   ◄───►   src/content_creation/cli.py
                                 (Highly Aligned)
      ▲
      │
Domains               ◄───►   src/content_creation/domains/
                                 (Highly Aligned - Isolated)
      ▲
      │
Platform              ◄───►   src/content_creation/platform/
                                 (Fully Aligned)
      ▲
      │
Shared                ◄───►   src/content_creation/shared/
                                 (Fully Aligned)
```

### Deviations (Technical Debt)
* **Legacy Generation Layer:** The presence of the centralized `generation/` folder.
* **Facade Storage Wrapper:** The centralized `LocalStorage` facade in `storage/local.py` acting as an intermediary coupling point.
* **Shared Models Directory:** Shared models are stored in `models/` instead of their respective domain packages.

These deviations are artifacts of an ongoing step-by-step refactoring process rather than accidental architecture drift.

---

## 10. Recommended Backlog

This backlog prioritizes architecture-related improvements supported by the audit evidence.

### High Priority
1. **Storyboard Parameter Integration**
   * *Goal:* Integrate storyboard inputs into [generation/script.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation/script.py), [generation/carousel.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation/carousel.py), and [generation/newsletter.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation/newsletter.py).
   * *Detail:* Accept `storyboard=None` parameter and override hooks, CTAs, and claims, following the [ThumbnailGenerator](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation/thumbnail.py#L24) pattern.

### Medium Priority
2. **Generator Migration to Domains**
   * *Goal:* Move generator files from [generation/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/generation) into their respective domain packages under [domains/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/domains) (e.g. `domains/brief/generator.py`).
   * *Detail:* Consolidate prompt template loading within each domain to remove the global `generation` dependency.
3. **Model Migration to Domains**
   * *Goal:* Relocate models from [models/](file:///home/aryan/May-2026/Content-Creation/src/content_creation/models) to their domain subfolders (e.g., move `models/brief.py` to `domains/brief/model.py`).
   * *Detail:* Keep `models/__init__.py` as a compatibility re-export layer to avoid breaking external CLI references initially.

### Low Priority
4. **Decouple CLI Orchestration**
   * *Goal:* Extract pipeline stage runs from [cli.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/cli.py).
   * *Detail:* Move pipeline loop execution and multi-stage logic into a dedicated orchestrator or workflow module.
5. **Decouple Facade Storage**
   * *Goal:* Establish repositories for Manifests, Calendars, and Analytics.
   * *Detail:* Remove direct file writing from [storage/local.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) and delegate persistence strictly through repository classes.
