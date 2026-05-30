# Storyboard Architecture Blueprint

> Phase: D.3 — Architecture & Discovery  
> Status: Design Only — No Implementation  
> Date: 2026-05-30  
> Depends on: D.1 Audit, D.2 Content Intelligence Blueprint, D.3a Discovery, D.3b Inputs

---

## 1. Executive Summary

Storyboard is a **content coordination layer** — not a video-planning artifact. It sits between Content Intelligence and generators, transforming raw creative strategy into per-format instruction sets that ensure all content assets work as a unified ecosystem rather than independent retellings.

**Pipeline position:**

```
Brief → Content Intelligence → Storyboard → Generators (write only)
```

**Core value:** Generators currently plan AND write. Storyboard separates planning from writing. Each generator receives explicit instructions (which hook, which claims, which arc, which visuals) and focuses solely on execution within its format constraints.

**One-sentence definition:** Storyboard is the single artifact that decides what each format says, how it differs from other formats, and how all formats connect into a content ecosystem.

---

## 2. Storyboard Domain Definition

### What Is Storyboard?

A **per-topic coordination plan** that:

1. Receives Content Intelligence (hooks, angles, visuals, audience insights)
2. Allocates those resources across planned formats
3. Ensures no duplication, full coverage, and cross-format coherence
4. Outputs per-format instruction sets that generators consume directly

### What Storyboard Is NOT

- Not a video storyboard (frames, shots, transitions)
- Not a content calendar (scheduling, cadence)
- Not a style guide (voice, brand rules)
- Not a generator (produces no final content)
- Not Content Intelligence (produces no insights — only allocates them)

### Domain Boundary

| Layer | Question It Answers |
|-------|-------------------|
| Brief | "What are the facts?" |
| Content Intelligence | "What makes this compelling?" |
| **Storyboard** | **"How do we distribute compelling facts across formats?"** |
| Generators | "How do we write this in format X?" |

---

## 3. Ownership Boundaries

### Storyboard Owns

| Concern | Rationale |
|---------|-----------|
| Format selection and prioritization | Decides which formats to generate and in what order |
| Hook assignment per format | Allocates CI hooks to specific formats with differentiation |
| CTA ecosystem design | Creates cross-referencing CTAs that drive inter-format traffic |
| Claim allocation per format | Distributes claims to prevent duplication and ensure coverage |
| Narrative arc selection per format | Chooses complementary arcs so formats don't retell the same story |
| Scope decisions per format | Determines duration/slide count/section count based on topic complexity |
| Visual palette coordination | Ensures carousel and thumbnail share visual language |
| Tone register assignment | Assigns distinct tone per format |
| Differentiation strategy | Defines each format's unique role in the ecosystem |

### Storyboard Does NOT Own

| Concern | Actual Owner | Rationale |
|---------|-------------|-----------|
| Factual extraction | Brief | Storyboard doesn't touch source material |
| Creative strategy generation | Content Intelligence | Storyboard allocates insights, doesn't generate them |
| Sentence-level writing | Generators | Word choice, rhythm, phrasing are execution |
| Slide body text | Carousel generator | 30-word constraint is format-specific |
| Script sections prose | Script generator | Speaking rhythm is format-specific |
| Newsletter section prose | Newsletter generator | Email register is format-specific |
| Image-gen technical details | Thumbnail generator | negative_prompt, readability_notes |
| Review lifecycle | Pipeline state machine | Each asset reviewed independently |
| Publishing schedule | Posting planner | Calendar concerns are separate |
| Voice and style rules | voice-and-style.md | Brand-level, not topic-level |

---

## 4. Storyboard Responsibilities

1. **Allocate** — Distribute CI resources (hooks, claims, visuals) across formats
2. **Differentiate** — Ensure each format serves a unique purpose
3. **Coordinate** — Create cross-format connections (CTAs, shared visual language)
4. **Scope** — Determine appropriate size/length per format per topic
5. **Sequence** — Define generation priority order
6. **Constrain** — Provide explicit boundaries so generators don't drift

---

## 5. Storyboard Non-Responsibilities

1. **Never generates content** — No prose, no copy, no final text
2. **Never invents facts** — All claims come from Brief via CI
3. **Never invents hooks** — All hooks come from CI; Storyboard only assigns them
4. **Never decides visual details** — Assigns concepts; generators describe specifics
5. **Never overrides editorial review** — Each asset retains independent review_status
6. **Never touches scheduling** — Calendar/planner is a separate domain

---

## 6. Storyboard Schema Proposal

```yaml
Storyboard:
  # ─── Identity ───
  topic_id: TopicId
  ci_version: str                      # Content Intelligence hash for staleness detection
  generated_at: str
  review_status: ReviewStatus

  # ─── Format Plan ───
  formats_planned:
    - format: str                      # "short_video" | "carousel" | "newsletter" | "thumbnail"
      rationale: str                   # Why this format for this topic
      priority: int                    # Generation order

  # ─── Hook Assignments ───
  hook_assignments:
    - format: str
      hook_text: str                   # From CI.hooks — assigned, not invented
      hook_type: str                   # "question" | "bold_claim" | "contrast" | "statistic"
      source_hook_index: int           # Which CI hook this came from

  # ─── CTA Assignments ───
  cta_assignments:
    - format: str                      # Format where CTA appears
      cta_text: str
      drives_to: str                   # Target format or "external"
      cross_reference: str             # What the target format offers ("visual breakdown", "60s summary")

  # ─── Claim Allocation ───
  claim_allocation:
    - format: str
      claims: List[str]               # Specific claims assigned
      allocation_reason: str           # "narrative" | "visual" | "analytical"

  # ─── Arc Assignments ───
  arc_assignments:
    - format: str
      arc_type: str                    # "hook_explain_relevance_cta" | "myth_reality_proof" | "problem_solution_evidence" | "question_exploration_answer"
      beats: List[str]                # Ordered narrative beats
      differentiation_note: str        # How this arc differs from other formats

  # ─── Scope Assignments ───
  scope_assignments:
    - format: str
      constraint_type: str             # "duration_seconds" | "slide_count" | "section_count"
      value: int
      rationale: str

  # ─── Visual Palette ───
  visual_palette:
    primary_metaphor: str              # Dominant visual concept (shared)
    style: str                         # "clean_minimal" | "bold_typographic" | "diagram_overlay" | "metaphor_illustration"
    concepts:
      - concept: str                   # From CI.visual_opportunities
        type: str                      # "diagram" | "code_snippet" | "metaphor_image" | "comparison_chart"
        assigned_to: str               # "carousel_slide_3" | "thumbnail" | etc.
    brand_avoidances: List[str]        # Shared negative prompts

  # ─── Tone Assignments ───
  tone_assignments:
    - format: str
      register: str                    # "conversational" | "professional" | "punchy" | "analytical"
      rationale: str

  # ─── Differentiation ───
  differentiation_strategy: str        # One sentence: how formats complement each other
  format_roles:
    - format: str
      role: str                        # "emotional_hook" | "visual_breakdown" | "analytical_context" | "curiosity_trigger"
      unique_angle: str                # What this format covers that others don't
```

---

## 7. Field-by-Field Ownership Analysis

### Fields Storyboard Produces (Owned)

| Field | Source Input | Transformation |
|-------|-------------|---------------|
| `formats_planned` | CI.topic_type + Brief.recommended_formats | Intelligent selection with rationale |
| `hook_assignments` | CI.hooks[] | Assignment + format-specific length adaptation |
| `cta_assignments` | Storyboard's own formats_planned | Cross-format ecosystem design |
| `claim_allocation` | Brief.plain_english_summary + CI.contrast_pairs | Distribution by format strength |
| `arc_assignments` | CI.story_angle + CI.contrast_pairs | Complementary arc selection |
| `scope_assignments` | CI.topic_type + CI.confidence_score | Complexity-based sizing |
| `visual_palette` | CI.visual_opportunities[] | Coordination + assignment |
| `tone_assignments` | CI.emotional_register | Per-format register differentiation |
| `differentiation_strategy` | All CI fields | Holistic ecosystem design |

### Fields Storyboard Consumes (From CI)

| CI Field | How Storyboard Uses It |
|----------|----------------------|
| `hooks[]` | Selects and assigns to formats |
| `story_angle` | Informs arc selection |
| `contrast_pairs[]` | Informs claim allocation (contrast claims → carousel) |
| `visual_opportunities[]` | Assigns to carousel slides and thumbnail |
| `topic_type` | Drives format selection and scope |
| `emotional_register` | Drives tone assignment |
| `audience_segment` | Informs differentiation (what angle serves this audience per format) |
| `misconception` | Allocates to highest-impact format |
| `curiosity_gap` | Informs CTA design and thumbnail |
| `controversy_angle` | Allocates to format best suited for debate |
| `timeliness_hook` | Prioritizes newsletter (urgency suits email) |
| `confidence_score` | Determines scope (low confidence → fewer formats) |

### Fields Storyboard Does NOT Touch

| Field | Owner |
|-------|-------|
| `topic_id` | Pipeline (pass-through) |
| `source_url` / `source_links` | Brief (pass-through) |
| `review_status` on assets | Pipeline state machine |
| `generated_at` on assets | Pipeline timestamp |
| All prose/copy fields | Generators |

---

## 8. Asset Consumption Matrix

### What Each Generator Receives from Storyboard

| Storyboard Field | Script | Carousel | Newsletter | Thumbnail |
|-----------------|:---:|:---:|:---:|:---:|
| `hook_assignments[format]` | ★ → `hook` | ★ → slide 1 | ★ → `subject_line` | ★ → `title_text` |
| `cta_assignments[format]` | ★ → `cta` | ★ → `cta_slide` | ★ → `cta` | — |
| `claim_allocation[format]` | ★ → `claims_used` | ★ → `claims_used` | ★ → `claims_used` | — |
| `arc_assignments[format]` | ★ → section structure | ★ → slide arc | ★ → section order | — |
| `scope_assignments[format]` | ★ → word budget | ★ → slide count | ★ → section count | — |
| `visual_palette.concepts` | — | ★ → `visual_note` | — | ★ → `visual_metaphor` |
| `visual_palette.style` | — | ○ density hint | — | ★ → `style` |
| `visual_palette.brand_avoidances` | — | — | — | ★ → seeds `negative_prompt` |
| `tone_assignments[format]` | ★ → writing style | ★ → title voice | ★ → prose register | — |
| `differentiation_strategy` | ○ context | ○ context | ○ context | — |
| `format_roles[format]` | ★ → angle | ★ → angle | ★ → angle | ○ context |

★ = directly consumed, ○ = contextual guidance, — = not consumed

---

## 9. Claim Allocation Design

### Problem

Currently: Script, Carousel, Newsletter each independently select claims from Brief. Result: same 2-3 strongest claims appear in all formats; weaker claims never surface.

### Solution

Storyboard allocates claims by **format strength**:

| Format | Claim Type | Rationale |
|--------|-----------|-----------|
| Script | Narrative claims | Claims that tell a story (cause → effect, before → after) |
| Carousel | Visual/data claims | Claims best shown as diagrams, comparisons, or code |
| Newsletter | Analytical claims | Claims requiring context, nuance, or implication analysis |

### Allocation Rules

1. **Full coverage** — Union of all format allocations must equal all available claims
2. **Minimal overlap** — A claim appears in max 2 formats (primary + supporting)
3. **Strength matching** — Each claim goes to the format where it has highest impact
4. **Minimum per format** — Each format receives ≥ 2 claims
5. **Traceability** — Every allocated claim traces to a Brief or CI source field

### Allocation Algorithm (Conceptual)

```
For each claim in CI.contrast_pairs + Brief.plain_english_summary:
  1. Classify: narrative | visual | analytical
  2. Assign to primary format based on classification
  3. If format already has 5+ claims, assign to secondary format
  4. Record allocation_reason
```

---

## 10. Hook Coordination Design

### Problem

Currently: 4 generators independently invent hooks from the same Brief. Result: near-identical openings across formats, no differentiation.

### Solution

CI generates 2-4 ranked hook candidates. Storyboard assigns the best-fit hook to each format.

### Assignment Rules

| Format | Hook Preference | Max Length | Rationale |
|--------|----------------|:---:|-----------|
| Script | Bold claim or contrast | ~15 words | Spoken hook must be punchy and immediate |
| Carousel | Question or statistic | ~8 words | Slide 1 title must be scannable |
| Newsletter | Timeliness or curiosity | ~60 chars | Subject line must drive open rate |
| Thumbnail | Compressed insight | ~6 words | Must communicate value at glance |

### Coordination Rules

1. **No duplication** — No two formats receive identical hook text
2. **Same topic, different angle** — Each hook approaches the topic from a distinct direction
3. **Length adaptation** — Same hook concept may be shortened/expanded per format constraint
4. **Source tracking** — Each assignment records which CI hook it derives from
5. **Fallback** — If CI provides < 4 hooks, Storyboard may adapt one hook into format-appropriate variants (but must note this)

---

## 11. CTA Coordination Design

### Problem

Currently: Each generator invents a CTA in isolation. CTAs cannot reference other formats because generators don't know what else exists.

### Solution

Storyboard designs a **CTA ecosystem** where each format's CTA drives traffic to another format.

### Ecosystem Pattern

```
Script CTA ──────────▶ Carousel ("swipe through the visual breakdown")
Carousel CTA ────────▶ Newsletter ("subscribe for the deep-dive")
Newsletter CTA ──────▶ Script ("watch the 60-second summary")
```

### CTA Rules

1. **Cross-reference** — Each CTA must name or describe the target format's value
2. **Low friction** — Never "like and subscribe"; always specific and actionable
3. **Ecosystem awareness** — CTA only references formats that are actually planned
4. **External fallback** — If only 1 format is planned, CTA drives to source URL or follow
5. **No circular dependency** — CTA graph must be a DAG (no A→B→A loops in 2-format plans)

### drives_to Logic

| Formats Planned | CTA Ecosystem |
|----------------|---------------|
| All 3 content formats | Script→Carousel→Newsletter→Script (triangle) |
| Script + Carousel only | Script→Carousel, Carousel→external |
| Script only | Script→external (source URL or follow) |
| Newsletter only | Newsletter→external |

---

## 12. Visual Language Design

### Problem

Currently: Carousel invents `visual_note` per slide independently. Thumbnail invents `visual_metaphor` independently. Result: inconsistent visual identity for the same topic.

### Solution

Storyboard defines a **visual palette** — a shared set of visual concepts that both Carousel and Thumbnail draw from.

### Visual Palette Structure

| Component | Purpose | Consumed By |
|-----------|---------|-------------|
| `primary_metaphor` | The dominant visual concept for this topic | Thumbnail (as `visual_metaphor`), Carousel slide 7 |
| `style` | Visual treatment category | Thumbnail (as `style`), Carousel (density guidance) |
| `concepts[]` | Pool of visual ideas with format assignments | Carousel (as `visual_note` per slide) |
| `brand_avoidances` | What to never show | Thumbnail (seeds `negative_prompt`) |

### Assignment Rules

1. **Primary metaphor shared** — Thumbnail and carousel's analogy slide use the same core metaphor
2. **Style consistency** — If thumbnail is `diagram_overlay`, carousel should be diagram-heavy
3. **Concept assignment** — Each visual concept assigned to exactly one carousel slide or thumbnail
4. **No orphans** — Every CI visual_opportunity must be assigned or explicitly excluded
5. **Brand avoidances universal** — Apply to all visual assets equally

### Style Selection (Deterministic)

| CI.topic_type | Storyboard.visual_palette.style |
|---------------|-------------------------------|
| paper | diagram_overlay |
| tool | bold_typographic |
| concept | metaphor_illustration |
| benchmark | diagram_overlay |
| industry_news | bold_typographic |
| tutorial | clean_minimal |

---

## 13. Quality Gates

### Gate 1: Completeness

| Check | Threshold | Action |
|-------|-----------|--------|
| All planned formats have hook_assignment | 100% | Block |
| All planned content formats have cta_assignment | 100% | Block |
| All planned content formats have claim_allocation | 100% | Block |
| All planned formats have arc_assignment | 100% | Block |
| All planned formats have scope_assignment | 100% | Block |
| Visual palette has ≥1 concept | Required | Block |
| Differentiation strategy non-empty | Required | Block |

### Gate 2: Coordination Integrity

| Check | Threshold | Action |
|-------|-----------|--------|
| No duplicate hook text across formats | 0 duplicates | Block |
| CTA drives_to references only planned formats | 100% | Block |
| Claim allocation union covers all available claims | ≥ 80% coverage | Warn |
| No format has 0 claims | Min 2 per format | Block |
| Arc types are not all identical | ≥ 2 distinct arcs | Warn |

### Gate 3: Consistency with CI

| Check | Threshold | Action |
|-------|-----------|--------|
| hook_assignments trace to CI.hooks | All | Block |
| visual_palette.concepts trace to CI.visual_opportunities | All | Block |
| tone_assignments consistent with CI.emotional_register | No contradiction | Warn |
| ci_version matches current CI | Exact match | Block (stale) |

### Gate 4: Scope Reasonableness

| Check | Threshold | Action |
|-------|-----------|--------|
| Script duration | 30-120 seconds | Warn if outside |
| Carousel slide count | 5-12 slides | Warn if outside |
| Newsletter section count | 2-5 sections | Warn if outside |

---

## 14. Future Format Expansion

### Adding a New Format (e.g., "thread", "podcast_segment", "blog_post")

Storyboard is designed for format extensibility. Adding a format requires:

| Step | Change Required |
|------|----------------|
| 1 | Add format to `formats_planned` options |
| 2 | Add entry to `hook_assignments` (with format-appropriate length) |
| 3 | Add entry to `cta_assignments` (integrate into ecosystem) |
| 4 | Add entry to `claim_allocation` (redistribute claims) |
| 5 | Add entry to `arc_assignments` (choose complementary arc) |
| 6 | Add entry to `scope_assignments` (define format constraints) |
| 7 | Add entry to `tone_assignments` |
| 8 | Add entry to `format_roles` |

### What Does NOT Change

- Storyboard schema structure (all fields are lists, not hardcoded format keys)
- CI schema (format-agnostic by design)
- Other generators (unaffected by new format addition)
- Quality gates (rules are format-count-agnostic)

### Extensibility Principle

Storyboard uses **list-of-assignments** pattern (not dict-keyed-by-format) specifically so new formats don't require schema changes — only new list entries.

---

## 15. Migration Strategy

### Phase 1: Schema (Week 1)

- Define `Storyboard` Pydantic model and nested types
- Add to `src/content_creation/models/`
- No pipeline changes, no generator changes

### Phase 2: Generator (Week 2)

- Create `src/content_creation/generation/storyboard.py`
- Create `prompts/storyboard.md`
- Storyboard generator accepts Brief + CI, outputs Storyboard
- Store in `data/storyboards/`
- No downstream changes

### Phase 3: Generator Rewiring (Week 3-4)

- Update Script, Carousel, Newsletter, Thumbnail generators to accept Storyboard
- Update prompt templates to include Storyboard fields
- Backward compatible: generators still work with Brief-only when Storyboard is absent
- Add CLI command: `generate-storyboard --top N`

### Phase 4: Quality Gates (Week 4)

- Implement completeness, coordination, consistency, and scope gates
- Insert between `generate-storyboard` and `generate-assets`

### Phase 5: Pipeline Integration (Week 5)

- Update `run-pipeline` to include storyboard generation
- Update manifest builder to track storyboard artifacts
- Flag: `--with-storyboard` (opt-in during migration, default after stabilization)

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| Storyboard adds latency (extra API call) | High | Medium | Cache; parallelize across topics |
| Storyboard quality inconsistent without examples | High | High | Ship prompt with 2+ full examples from day one |
| Generators ignore Storyboard fields | Medium | High | Tests verify Storyboard fields appear in output |
| Storyboard contradicts CI | Low | High | Consistency gate catches before generation |
| Over-coordination reduces creative variety | Medium | Medium | Allow generators 20% creative latitude beyond Storyboard |

### Backward Compatibility

- All generators must function with Storyboard = None (Brief-only mode)
- Storyboard fields in prompts wrapped in conditionals
- No existing tests break
- Opt-in flag during migration period

---

## 16. Governance Rules

### Ownership

| Concern | Owner |
|---------|-------|
| Storyboard schema | Architecture (this document) |
| Storyboard prompt quality | Content strategy |
| Storyboard generator implementation | Engineering |
| Quality gate thresholds | Content strategy |
| Field additions | Architecture review required |

### Schema Change Policy

1. **Adding optional fields** — Architecture review; no downstream breakage
2. **Adding required fields** — Architecture review + migration plan + generator updates
3. **Removing fields** — 2-version deprecation period
4. **Changing field types** — Major version bump; full audit

### Design Principles

1. **Allocate, never generate** — Storyboard distributes CI resources; it does not create new content
2. **Coordinate, never constrain prose** — Storyboard says "use this hook"; generator decides exact wording
3. **Differentiate, never duplicate** — Every format must have a unique angle; identical approaches are a bug
4. **Trace everything** — Every assignment traces to a CI or Brief source
5. **Degrade gracefully** — If CI provides fewer hooks than formats, Storyboard adapts rather than fails
6. **Format-agnostic schema** — List-based assignments, not hardcoded format keys

### Anti-Patterns

| Anti-Pattern | Why Dangerous |
|--------------|--------------|
| Storyboard writing prose | Violates separation; becomes a generator |
| Storyboard inventing claims | Breaks grounding chain; untraceable content |
| Hardcoding format names in schema | Prevents extensibility |
| Skipping Storyboard for "simple" topics | Creates two code paths; inconsistent quality |
| CTA referencing unplanned formats | Broken promises to audience |

---

## Appendix: Validation Summary

| Requirement | Delivered |
|-------------|-----------|
| Schema proposal | Section 6 |
| Ownership matrix | Sections 3, 7 |
| Consumer matrix | Section 8 |
| Quality gates | Section 13 |
| Migration path | Section 15 |
| Risks | Section 15 |
| Claim coordination | Section 9 |
| Hook coordination | Section 10 |
| CTA coordination | Section 11 |
| Visual coordination | Section 12 |
| Future format expansion | Section 14 |
| Governance | Section 16 |
