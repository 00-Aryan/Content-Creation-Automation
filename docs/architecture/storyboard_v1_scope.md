# Storyboard v1 Scope

> Phase: Pre-Implementation Scoping  
> Date: 2026-05-31  
> Status: Analysis Only — No Implementation  
> Depends on: CI v1 (implemented), Storyboard Architecture Blueprint

---

## 1. Minimal Schema Proposal

```yaml
Storyboard:
  # Identity
  topic_id: TopicId
  generated_at: str
  review_status: ReviewStatus

  # Hook Assignment (which hook → which format)
  hook_assignments:
    script_hook: str           # CI.primary_hook.hook_text (spoken, punchy)
    carousel_hook: str         # CI.secondary_hook.hook_text (scannable)
    newsletter_hook: str       # Derived: curiosity_gap as subject line
    thumbnail_hook: str        # Derived: compressed primary_hook (≤6 words)

  # CTA Ecosystem (cross-format references)
  cta_assignments:
    script_cta: str            # Drives to carousel
    carousel_cta: str          # Drives to newsletter
    newsletter_cta: str        # Drives to script/external

  # Claim Allocation (Brief.plain_english_summary → formats)
  claim_allocation:
    script_claims: List[str]   # Narrative claims
    carousel_claims: List[str] # Visual/data claims
    newsletter_claims: List[str] # Analytical claims

  # Visual Style (deterministic from CI.topic_type)
  visual_style: str            # "clean_minimal" | "bold_typographic" | "diagram_overlay" | "metaphor_illustration"
  visual_metaphor: str         # From Brief.analogy or CI.contrast_pair

  # Format Plan
  formats_planned: List[str]   # Which formats to generate
```

**Total: 13 fields** (vs. 40+ in full blueprint)

---

## 2. V1 vs V2 Field Split

### V1 — Ships Now (13 fields)

| Field | Source | Reasoning Method |
|-------|--------|:---:|
| `hook_assignments.script_hook` | CI.primary_hook | Pass-through |
| `hook_assignments.carousel_hook` | CI.secondary_hook | Pass-through |
| `hook_assignments.newsletter_hook` | CI.curiosity_gap | Pass-through |
| `hook_assignments.thumbnail_hook` | CI.primary_hook (truncated) | LLM (compress to 6 words) |
| `cta_assignments.script_cta` | formats_planned | LLM (cross-reference) |
| `cta_assignments.carousel_cta` | formats_planned | LLM (cross-reference) |
| `cta_assignments.newsletter_cta` | formats_planned | LLM (cross-reference) |
| `claim_allocation.*` | Brief.plain_english_summary | LLM (classify & distribute) |
| `visual_style` | CI.topic_type | Deterministic lookup |
| `visual_metaphor` | Brief.analogy / CI.contrast_pair | Pass-through |
| `formats_planned` | Brief.recommended_formats | Pass-through + normalization |

### V2 — Deferred

| Field | Reason to Defer |
|-------|----------------|
| `arc_assignments` (per-format narrative arc) | Requires prompt rewrite of all generators |
| `scope_assignments` (duration, slide count) | Hardcoded values work for now |
| `tone_assignments` (per-format register) | CI.emotional_register is sufficient for v1 |
| `differentiation_strategy` | Nice-to-have; not consumed by current generators |
| `format_roles` | Conceptual — no generator consumes it yet |

### Cost Breakdown

| Category | Fields | Method |
|----------|:---:|--------|
| Pass-through from CI/Brief | 6 | Zero cost |
| Deterministic | 2 | Zero cost |
| LLM-generated | 5 | Single inference call |
| **Total** | **13** | **1 API call** |

---

## 3. Consumer Analysis

### Which Fields Each Generator Consumes

| Storyboard Field | Script | Carousel | Newsletter | Thumbnail |
|-----------------|:---:|:---:|:---:|:---:|
| `hook_assignments.script_hook` | ★ → `hook` | — | — | — |
| `hook_assignments.carousel_hook` | — | ★ → slide 1 | — | — |
| `hook_assignments.newsletter_hook` | — | — | ★ → `subject_line` | — |
| `hook_assignments.thumbnail_hook` | — | — | — | ★ → `title_text` |
| `cta_assignments.script_cta` | ★ → `cta` | — | — | — |
| `cta_assignments.carousel_cta` | — | ★ → `cta_slide` | — | — |
| `cta_assignments.newsletter_cta` | — | — | ★ → `cta` | — |
| `claim_allocation.script_claims` | ★ → `claims_used` | — | — | — |
| `claim_allocation.carousel_claims` | — | ★ → `claims_used` | — | — |
| `claim_allocation.newsletter_claims` | — | — | ★ → `claims_used` | — |
| `visual_style` | — | ○ context | — | ★ → `style` |
| `visual_metaphor` | — | ○ → slide 7 | — | ★ → `visual_metaphor` |

★ = directly maps to output field, ○ = contextual guidance

### Generator Change Complexity

| Generator | Fields Consumed | Change Required |
|-----------|:---:|----------------|
| **Thumbnail** | 3 (thumbnail_hook, visual_style, visual_metaphor) | Inject 3 fields into prompt; simplest integration |
| **Script** | 3 (script_hook, script_cta, script_claims) | Inject 3 fields into prompt |
| **Newsletter** | 3 (newsletter_hook, newsletter_cta, newsletter_claims) | Inject 3 fields into prompt |
| **Carousel** | 4 (carousel_hook, carousel_cta, carousel_claims, visual_metaphor) | Inject 4 fields into prompt |

---

## 4. Integration Order

### Recommended: Thumbnail First

| Criterion | Thumbnail | Script | Carousel | Newsletter |
|-----------|:---:|:---:|:---:|:---:|
| Fields consumed | 3 | 3 | 4 | 3 |
| Current pain solved | High (style inference eliminated) | Medium | Medium | Medium |
| Prompt change size | Small (3 fields replace inference logic) | Medium | Medium | Medium |
| Risk of regression | Low (no prose generation) | Medium | Medium | Medium |
| Validation ease | High (deterministic style check) | Low (subjective) | Low | Low |

**Thumbnail is the ideal first consumer because:**
1. `visual_style` is deterministic — testable without subjective judgment
2. `thumbnail_hook` replaces the model's own hook invention — measurable improvement
3. `visual_metaphor` replaces independent invention — consistency with carousel
4. No prose generation means lower risk of regression

### Phased Integration Order

```
Phase 1: Thumbnail (lowest risk, highest testability)
Phase 2: Script (hook + CTA + claims — core value)
Phase 3: Newsletter (hook + CTA + claims — same pattern as Script)
Phase 4: Carousel (most fields, visual coordination)
```

---

## 5. Rollout Plan

### Week 1: Storyboard Domain Implementation

- Create `src/content_creation/domains/storyboard/`
- Model, generator, repository, prompt
- Single LLM call produces: thumbnail_hook, 3 CTAs, claim allocation
- Deterministic: visual_style from topic_type, formats_planned from Brief
- Pass-through: hook assignments from CI, visual_metaphor from Brief.analogy
- Tests: model, generator, quality gate, repository

### Week 2: Thumbnail Integration

- Update Thumbnail generator to accept optional Storyboard
- When Storyboard present: use `visual_style`, `thumbnail_hook`, `visual_metaphor` directly
- When absent: existing behavior (backward compatible)
- Tests: verify Thumbnail output uses Storyboard fields

### Week 3: Script + Newsletter Integration

- Same pattern: inject hook, CTA, claims from Storyboard
- Generators remain backward compatible (Storyboard optional)
- Tests: verify hooks and CTAs match Storyboard assignments

### Week 4: Carousel Integration + Pipeline Wiring

- Carousel consumes hook, CTA, claims, visual_metaphor
- Update `run-pipeline` to include `generate-storyboard` step
- CLI command: `generate-storyboard --top N`
- End-to-end validation

### Cost Impact

| Metric | Before | After | Delta |
|--------|:---:|:---:|:---:|
| API calls per topic | 6 (Brief + CI + 4 assets) | 7 (+Storyboard) | +1 (14%) |
| Total tokens per topic | ~10,000 | ~11,200 | +1,200 (12%) |
| Free tier capacity | 250 topics/day | 214 topics/day | -14% |

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| Storyboard CTA references unplanned formats | Medium | Medium | Validate CTA.drives_to against formats_planned |
| Claim allocation produces uneven distribution | Medium | Low | Minimum 1 claim per format rule |
| thumbnail_hook exceeds 6 words | High | Low | Truncation in generator or prompt constraint |
| Generators ignore Storyboard when present | Medium | High | Tests assert Storyboard fields appear in output |
| Storyboard adds latency to pipeline | High | Low | Acceptable: 1 additional call (~2s) |
| Brief.recommended_formats are non-standard | High | Medium | Normalize through FREETEXT_TO_FORMAT before Storyboard |

### Key Architectural Risk

The biggest risk is **partial adoption** — if some generators consume Storyboard and others don't, the content ecosystem is inconsistent. Mitigation: Storyboard is optional during rollout but becomes required after Week 4.

---

## 7. Answers to Scoping Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Fields from CI directly? | 6: primary_hook→script, secondary_hook→carousel, curiosity_gap→newsletter, topic_type→visual_style, contrast_pair→visual_metaphor seed, story_angle (context) |
| 2 | Fields requiring new reasoning? | 5: thumbnail_hook (compression), 3 CTAs (cross-reference), claim allocation (classification) |
| 3 | Mandatory for v1? | hook_assignments, cta_assignments, claim_allocation, visual_style, formats_planned |
| 4 | Can wait for v2? | arc_assignments, scope_assignments, tone_assignments, differentiation_strategy |
| 5 | Single inference call? | **Yes** — 5 LLM fields in one call (~600 tokens in, ~400 out) |
| 6 | Smallest coordinating schema? | 13 fields (this document) |
| 7 | Minimal-change consumers? | All 4 — each needs 3-4 fields injected into prompt |
| 8 | First integration? | **Thumbnail** — deterministic style, lowest risk, highest testability |
| 9 | Implementation complexity? | Low-Medium — same pattern as CI domain (model + generator + repo + prompt) |
| 10 | Phased rollout? | Week 1: domain, Week 2: Thumbnail, Week 3: Script+Newsletter, Week 4: Carousel+pipeline |
