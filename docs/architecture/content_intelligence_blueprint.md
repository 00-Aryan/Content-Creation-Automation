# Content Intelligence Blueprint

> Phase: D.2 — Architecture & Discovery  
> Status: Design Only — No Implementation  
> Date: 2026-05-30  
> Author: Principal AI Content Systems Architect  
> Depends on: D.1 Prompt & Generation Audit

---

## 1. Executive Summary

The current pipeline transforms source material into educational briefs, then generates content assets (scripts, carousels, newsletters, thumbnails) directly from those briefs. The Brief is optimized for **educational accuracy** — it answers "what happened and why it matters to students."

It does not answer the creator's question: **"How do I make this compelling?"**

Content Intelligence is a dedicated analytical layer that sits between Brief and generation. It receives the factual Brief and produces **creator-oriented insights** — hooks, story angles, misconceptions, visual opportunities, audience framing, and controversy signals — that generators consume alongside the Brief.

**Why it must exist as a separate layer:**

1. **Separation of concerns** — Factual extraction (Brief) and creative strategy (Content Intelligence) are different cognitive tasks requiring different prompting strategies.
2. **Reusability** — One Content Intelligence output feeds all downstream generators. Without it, each generator independently (and inconsistently) invents its own hooks and angles.
3. **Auditability** — Creator decisions become inspectable artifacts rather than hidden prompt behaviors.
4. **SaaS scalability** — Content Intelligence becomes a standalone product: "Given any educational brief, produce a creator strategy."

**Pipeline after Content Intelligence:**

```
Source → Brief → Content Intelligence → Script / Carousel / Newsletter / Thumbnail
                                       ↘ Future: Storyboard
```

---

## 2. Current Brief Analysis

### Fields Present

| Field | Type | Purpose | Creator Value |
|-------|------|---------|:---:|
| `topic_id` | string | Identity | — |
| `why_it_matters` | string | Educational relevance | Low |
| `plain_english_summary` | List[str] (3) | Core explanation | Low |
| `student_takeaway` | string | Learning outcome | Low |
| `analogy` | string | Pedagogical metaphor | Medium |
| `limitation` | string | Honest constraint | Low |
| `audience_fit` | string | Generic audience note | Low |
| `recommended_formats` | List[str] | Format routing | Medium |
| `source_url` | string | Provenance | — |
| `review_status` | enum | Pipeline state | — |
| `generated_at` | string | Timestamp | — |

### What Brief Does Well

- Grounded factual extraction with anti-hallucination rules
- Consistent 3-item summary structure
- Explicit limitation acknowledgment
- Format recommendation for routing

### What Brief Does Not Do

- Identify what makes this topic **interesting** (not just important)
- Surface **misconceptions** the audience holds that create tension
- Propose **story angles** that create narrative momentum
- Classify the **topic type** for downstream style decisions
- Identify **visual opportunities** inherent in the source material
- Frame the topic for a **specific audience segment** beyond generic fit
- Extract **controversy or debate** that creates engagement
- Generate **curiosity gaps** that drive click-through

---

## 3. Creator Information Gap Analysis

### Gap Matrix

| What Generators Need | Where It Should Come From | Where It Currently Comes From |
|---------------------|--------------------------|-------------------------------|
| Hook (opening line) | Content Intelligence | Invented by Script generator at generation time |
| Story angle / narrative frame | Content Intelligence | Not provided; Script uses H-C-E-P-C structure mechanically |
| Contrast / controversy | Content Intelligence | F/C/K labeling demands contrast but no contrast data exists |
| Visual opportunities | Content Intelligence | Carousel invents `visual_note` per slide with zero guidance |
| Topic type classification | Content Intelligence | Thumbnail must infer from unstructured text |
| Audience-specific framing | Content Intelligence | Generic `audience_fit` string (e.g., "ML students") |
| Misconceptions | Content Intelligence | Not available anywhere in pipeline |
| Curiosity gap | Content Intelligence | Not available anywhere in pipeline |
| Emotional register | Content Intelligence | Not available; all content defaults to neutral-educational |

### Impact of Gaps

| Generator | Current Behavior Without Intelligence | Result |
|-----------|--------------------------------------|--------|
| Script | Invents hook from `why_it_matters` | Generic, non-compelling openings |
| Script | F/C/K labeling without contrast data | Forced contrast feels artificial |
| Carousel | Invents `visual_note` per slide | Inconsistent, often generic visuals |
| Thumbnail | Infers topic type from text | Non-deterministic style selection |
| Newsletter | Uses same data as script | No differentiation in angle |
| All | No misconception to exploit | Misses strongest engagement lever |

---

## 4. Content Intelligence Responsibilities

Content Intelligence **owns** the transformation from "what is factually true" to "what is creatively useful."

### Owns

1. **Hook generation** — 2-3 candidate hooks per topic (question, statement, contrast)
2. **Story angle identification** — The narrative frame that makes facts compelling
3. **Misconception surfacing** — What the audience likely believes that this topic challenges
4. **Controversy/debate extraction** — Legitimate disagreements in the field
5. **Curiosity gap construction** — The knowledge gap that drives engagement
6. **Visual opportunity mapping** — Concrete visual concepts inherent in the source
7. **Topic type classification** — Categorical label for downstream style routing
8. **Audience segment framing** — Specific audience persona and their relationship to this topic
9. **Emotional register recommendation** — The appropriate tone (awe, urgency, surprise, clarity)
10. **Contrast pairs** — Before/after, old/new, expected/actual comparisons

### Does NOT Own

- Factual extraction (Brief's job)
- Format selection (Brief's `recommended_formats`)
- Content structure (generator's job)
- Visual design (Thumbnail/Carousel generator's job)
- Editorial voice (voice-and-style.md's job)
- Review status (pipeline state machine's job)

### Boundary Principle

> Content Intelligence answers: "Given these facts, what creator strategy maximizes educational engagement?"  
> It does NOT answer: "What are the facts?" or "How should the final asset look?"

---

## 5. Proposed Content Intelligence Schema

```yaml
ContentIntelligence:
  # Identity
  topic_id: TopicId                    # Links to Brief
  brief_version: str                   # Brief hash/timestamp for staleness detection
  generated_at: str                    # ISO timestamp

  # Classification
  topic_type: TopicType                # enum: paper, tool, concept, benchmark, industry_news, tutorial
  emotional_register: EmotionalRegister # enum: awe, urgency, surprise, clarity, concern, excitement

  # Hooks (ranked by predicted engagement)
  hooks:
    - hook_text: str                   # The actual hook line
      hook_type: HookType              # enum: question, bold_claim, contrast, statistic, misconception_challenge
      source_field: str                # Which Brief field grounded this hook

  # Story Architecture
  story_angle: str                     # One-sentence narrative frame
  contrast_pairs:
    - before: str                      # Old way / expectation / common belief
      after: str                       # New way / reality / this topic's claim
      tension_type: TensionType        # enum: paradigm_shift, efficiency_gain, assumption_broken, scale_change

  # Audience Intelligence
  audience_segment: str                # Specific persona (e.g., "junior ML engineer shipping first model")
  audience_prior_belief: str           # What they likely believe before seeing this content
  misconception: str                   # The specific wrong mental model this topic corrects
  curiosity_gap: str                   # The question this content makes them need answered

  # Visual Intelligence
  visual_opportunities:
    - visual_concept: str              # Concrete visual description
      visual_type: VisualType          # enum: diagram, code_snippet, metaphor_image, comparison_chart, process_flow
      applicable_formats: List[str]    # Which generators can use this

  # Engagement Signals
  controversy_angle: str               # Legitimate debate or disagreement (empty if none)
  timeliness_hook: str                 # Why NOW matters (empty if evergreen)
  shareability_factor: str             # What makes someone share this (empty if low)

  # Metadata
  confidence_score: float              # 0.0-1.0 overall confidence in intelligence quality
  review_status: ReviewStatus          # draft | needs_review
```

---

## 6. Required vs Optional Fields

### Required (must be present for any generator to proceed)

| Field | Rationale |
|-------|-----------|
| `topic_id` | Identity linkage |
| `topic_type` | Thumbnail style selection, format-specific behavior |
| `hooks` (min 1) | Every content asset needs an opening |
| `story_angle` | Narrative coherence across all formats |
| `audience_segment` | Framing decisions depend on knowing who |
| `curiosity_gap` | Core engagement mechanism |
| `visual_opportunities` (min 1) | Carousel and Thumbnail cannot function without |
| `emotional_register` | Tone calibration for all generators |
| `confidence_score` | Quality gate threshold |
| `review_status` | Pipeline state |

### Optional (enhance quality but generators can proceed without)

| Field | Rationale |
|-------|-----------|
| `misconception` | Not every topic challenges a belief |
| `controversy_angle` | Many topics have no legitimate debate |
| `contrast_pairs` | Some topics are additive, not contrastive |
| `audience_prior_belief` | Useful but derivable from misconception |
| `timeliness_hook` | Evergreen topics have none |
| `shareability_factor` | Nice-to-have engagement signal |
| `brief_version` | Staleness detection (future feature) |

### Degradation Rules

1. If `misconception` is empty → Script F/C/K labeling uses `contrast_pairs` instead
2. If `contrast_pairs` is empty → Script uses `story_angle` for narrative tension
3. If `controversy_angle` is empty → No controversy framing; use curiosity gap only
4. If `timeliness_hook` is empty → Treat as evergreen; no urgency framing

---

## 7. Generator Consumption Analysis

### Script Generator

| CI Field Consumed | How It's Used |
|-------------------|---------------|
| `hooks[0]` | Directly becomes the `hook` output field |
| `story_angle` | Frames the Context section (H-**C**-E-P-C) |
| `contrast_pairs` | Provides K-labeled sentences for F/C/K compliance |
| `misconception` | Powers the Explanation section's "actually..." pivot |
| `curiosity_gap` | Shapes the CTA (answers the gap or teases next content) |
| `emotional_register` | Calibrates sentence intensity and word choice |
| `audience_segment` | Determines jargon level and example selection |

**Current pain removed:** Script no longer invents hooks or forces artificial contrast.

### Carousel Generator

| CI Field Consumed | How It's Used |
|-------------------|---------------|
| `hooks[0]` | Slide 1 title/body |
| `story_angle` | Determines slide arc narrative |
| `visual_opportunities` | Directly populates `visual_note` per slide |
| `contrast_pairs` | Before/after slides (strongest carousel pattern) |
| `misconception` | "Most people think X..." → "Actually Y" slide pair |
| `audience_segment` | Example selection and complexity calibration |
| `topic_type` | Influences visual density and diagram usage |

**Current pain removed:** `visual_note` no longer invented per-slide; pre-mapped visual concepts are assigned to appropriate slides.

### Newsletter Generator

| CI Field Consumed | How It's Used |
|-------------------|---------------|
| `hooks[1]` (second hook variant) | Subject line candidate |
| `story_angle` | Frames `what_happened` section |
| `curiosity_gap` | Drives reader to click CTA |
| `timeliness_hook` | Opening urgency in `what_happened` |
| `audience_segment` | Tone and formality calibration |
| `shareability_factor` | CTA framing ("share this with your team if...") |

**Current pain removed:** Newsletter differentiates from script by using alternate hook and formal register.

### Thumbnail Generator

| CI Field Consumed | How It's Used |
|-------------------|---------------|
| `topic_type` | **Deterministic** style selection (no more inference) |
| `hooks[0].hook_text` | Candidate for `title_text` |
| `curiosity_gap` | Candidate for `supporting_text` |
| `visual_opportunities[0]` | Directly informs `visual_metaphor` |
| `emotional_register` | Color palette and typography weight guidance |
| `contrast_pairs[0]` | Visual tension (split imagery, before/after) |

**Current pain removed:** Style selection becomes a lookup (`topic_type` → `style`) instead of inference from unstructured text.

### Consumption Priority Matrix

| CI Field | Script | Carousel | Newsletter | Thumbnail | Storyboard (future) |
|----------|:---:|:---:|:---:|:---:|:---:|
| `hooks` | ★★★ | ★★★ | ★★★ | ★★☆ | ★★★ |
| `story_angle` | ★★★ | ★★★ | ★★☆ | ☆☆☆ | ★★★ |
| `contrast_pairs` | ★★★ | ★★★ | ★☆☆ | ★★☆ | ★★★ |
| `misconception` | ★★☆ | ★★★ | ★☆☆ | ☆☆☆ | ★★★ |
| `visual_opportunities` | ☆☆☆ | ★★★ | ☆☆☆ | ★★★ | ★★★ |
| `topic_type` | ★☆☆ | ★☆☆ | ☆☆☆ | ★★★ | ★★☆ |
| `curiosity_gap` | ★★☆ | ★☆☆ | ★★★ | ★★☆ | ★★☆ |
| `emotional_register` | ★★☆ | ★☆☆ | ★☆☆ | ★★☆ | ★★★ |
| `audience_segment` | ★★★ | ★★☆ | ★★☆ | ☆☆☆ | ★★★ |

---

## 8. Storyboard Integration Design

### Future Storyboard Layer

Storyboard sits **between** Content Intelligence and individual generators. It consumes CI to produce a unified multi-format content plan before any generator runs.

```
Brief → Content Intelligence → Storyboard → Script
                                           → Carousel
                                           → Newsletter
                                           → Thumbnail
```

### What Storyboard Needs from Content Intelligence

| CI Field | Storyboard Usage |
|----------|-----------------|
| `hooks` (all variants) | Assigns best hook per format (no duplication) |
| `story_angle` | Ensures narrative consistency across formats |
| `contrast_pairs` | Allocates strongest contrast to highest-impact format |
| `visual_opportunities` | Routes visuals to carousel/thumbnail, not script |
| `emotional_register` | Ensures tone coherence across the content suite |
| `audience_segment` | Single audience model shared by all formats |
| `misconception` | Decides which format gets the "myth-busting" angle |

### Storyboard's Unique Value

1. **Cross-format deduplication** — Same hook doesn't appear in script AND carousel slide 1
2. **Strength allocation** — Best contrast goes to the format that benefits most
3. **Narrative arc coordination** — Script tells the story; carousel teaches the details; newsletter summarizes the impact
4. **Visual budget** — Allocates visual concepts across carousel slides and thumbnail without repetition

### CI → Storyboard Contract

Content Intelligence exposes its full schema. Storyboard consumes all fields and produces per-generator instruction sets. Generators then receive:
- Brief (facts)
- Content Intelligence (strategy)
- Storyboard instructions (format-specific plan)

This three-layer input replaces the current single-layer (Brief-only) input.

---

## 9. Quality Gates

### Gate 1: Completeness Gate

**When:** After Content Intelligence generation, before any downstream consumption.

| Check | Threshold | Action on Fail |
|-------|-----------|----------------|
| Required fields present | All 10 required fields non-empty | Block: set `review_status = needs_review` |
| Hooks count | ≥ 2 hooks generated | Warn: proceed but flag for human review |
| Visual opportunities count | ≥ 1 visual | Block: carousel/thumbnail cannot proceed |
| Confidence score | ≥ 0.6 | Warn: flag for human review |
| Confidence score | < 0.3 | Block: regenerate or escalate |

### Gate 2: Grounding Gate

**When:** During Content Intelligence generation (prompt-enforced).

| Check | Mechanism |
|-------|-----------|
| Every hook traceable to Brief field | `source_field` required per hook |
| Misconception grounded in source | Must reference what source says vs. common belief |
| Contrast pairs derived from Brief | `before` must be inferable; `after` must be stated in Brief |
| No invented statistics | If Brief has no numbers, CI cannot introduce numbers |

### Gate 3: Consistency Gate

**When:** After Content Intelligence generation, cross-referencing Brief.

| Check | Mechanism |
|-------|-----------|
| `topic_type` consistent with `recommended_formats` | Paper topics shouldn't recommend only newsletter |
| `emotional_register` consistent with `limitation` | If limitation is severe, register shouldn't be "excitement" |
| `audience_segment` consistent with `audience_fit` | CI segment must be a refinement of Brief's fit, not a contradiction |

### Gate 4: Staleness Gate (Future)

**When:** Before generator consumption.

| Check | Mechanism |
|-------|-----------|
| `brief_version` matches current Brief | If Brief was regenerated, CI is stale |
| `generated_at` within acceptable window | CI older than 7 days triggers re-evaluation |

---

## 10. Future SaaS Applications

### Application 1: Content Intelligence as a Service

**Value proposition:** "Upload any educational brief or topic summary → receive a complete creator strategy."

| Feature | Description |
|---------|-------------|
| Input | Any structured brief (not just this pipeline's format) |
| Output | Full Content Intelligence schema |
| Pricing | Per-topic or subscription |
| Differentiator | Grounded intelligence, not generic "content ideas" |

### Application 2: Multi-Creator Intelligence

**Value proposition:** Same Brief, different creator personas → different Content Intelligence outputs.

| Feature | Description |
|---------|-------------|
| Input | Brief + Creator Profile (voice, audience, platform) |
| Output | Personalized CI tuned to creator's style |
| Use case | Agency managing multiple educational creators |

### Application 3: Intelligence Feedback Loop

**Value proposition:** Post-publish analytics feed back into CI scoring.

| Feature | Description |
|---------|-------------|
| Input | CI output + engagement metrics (views, saves, shares) |
| Output | Refined confidence scores, hook effectiveness rankings |
| Use case | "Topics with misconception hooks get 3x saves" → prioritize misconception extraction |

### Application 4: Editorial Dashboard

**Value proposition:** Human editors review CI before generation, not after.

| Feature | Description |
|---------|-------------|
| Input | Generated CI |
| Output | Editor-approved CI with modifications |
| Use case | Editor changes story angle → all downstream assets reflect the change |
| Advantage | One edit propagates to 4+ assets instead of editing each asset individually |

### Application 5: Competitive Intelligence Layer

**Value proposition:** "What angles are competitors NOT covering?"

| Feature | Description |
|---------|-------------|
| Input | CI outputs over time + competitor content analysis |
| Output | Angle gap analysis, underserved misconceptions |
| Use case | Content differentiation strategy |

### SaaS Architecture Implications

1. **CI must be stateless** — No dependency on pipeline internals; accepts any Brief-shaped input
2. **CI must be versionable** — Schema versioning for API consumers
3. **CI must support multi-tenancy** — Different creators, different audience models
4. **CI must expose confidence** — Consumers need to know when to trust vs. override
5. **CI must be cacheable** — Same Brief → same CI (deterministic within model version)

---

## 11. Migration Strategy

### Phase 1: Schema Definition (Week 1)

- Define `ContentIntelligence` Pydantic model
- Define enums: `TopicType`, `HookType`, `TensionType`, `VisualType`, `EmotionalRegister`
- Add to `src/content_creation/models/`
- No pipeline changes

### Phase 2: Generator Implementation (Week 2)

- Create `src/content_creation/generation/intelligence.py`
- Create `prompts/content_intelligence.md`
- CI generator accepts Brief, outputs ContentIntelligence
- Store outputs in `data/intelligence/`
- No downstream changes yet

### Phase 3: Generator Rewiring (Week 3)

- Update Script, Carousel, Newsletter, Thumbnail generators to accept CI alongside Brief
- Update prompt templates to include CI fields
- Existing behavior preserved when CI is absent (backward compatible)
- Add CLI command: `generate-intelligence --top N`

### Phase 4: Quality Gates (Week 4)

- Implement completeness gate
- Implement grounding gate
- Implement consistency gate
- Add to pipeline between `generate-intelligence` and `generate-assets`

### Phase 5: Pipeline Integration (Week 5)

- Update `run-pipeline` to include intelligence generation
- Update manifest builder to track CI artifacts
- Update dry-run validator to check CI presence

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| CI generation adds latency (extra API call) | High | Medium | Parallelize CI generation across topics; cache results |
| CI quality is inconsistent without few-shot examples | High | High | Ship CI prompt with 2-3 full input→output examples from day one |
| Generators ignore CI fields if not enforced | Medium | High | Prompt templates must reference CI fields explicitly; add tests |
| CI contradicts Brief | Low | High | Consistency gate catches contradictions before generation |
| Schema churn during early iterations | Medium | Medium | Version the schema; generators consume via accessor methods, not raw fields |

### Backward Compatibility

- All generators must continue to function with Brief-only input (CI = None)
- CI fields in generator prompts wrapped in conditionals: present → use; absent → skip
- No existing tests should break during migration
- `run-pipeline` flag: `--with-intelligence` (opt-in during migration, default after Phase 5)

---

## 12. Governance Rules

### Ownership

| Concern | Owner |
|---------|-------|
| CI schema definition | Architecture (this document) |
| CI prompt quality | Content strategy / editorial |
| CI generator implementation | Engineering |
| CI quality gate thresholds | Content strategy |
| CI field additions | Requires architecture review |

### Schema Change Policy

1. **Adding optional fields** — Requires architecture review; no downstream breakage
2. **Adding required fields** — Requires architecture review + migration plan + generator updates
3. **Removing fields** — Deprecation period (2 pipeline versions); generators must handle absence
4. **Changing field types** — Major version bump; full downstream audit required

### Content Intelligence Principles

1. **Grounded creativity** — CI may reframe Brief facts but cannot invent new facts
2. **Traceable insights** — Every hook, angle, and misconception must cite its Brief source field
3. **Audience-first** — CI exists to serve the audience's engagement, not the creator's ego
4. **Format-agnostic** — CI does not know which generator will consume it; it provides raw strategic material
5. **Confidence-aware** — CI must self-assess; low-confidence outputs are flagged, not hidden
6. **Deterministic classification** — `topic_type` and `emotional_register` must be reproducible given the same Brief

### Anti-Patterns to Avoid

| Anti-Pattern | Why It's Dangerous |
|--------------|-------------------|
| CI inventing statistics | Breaks grounding contract; downstream assets inherit fabrications |
| CI duplicating Brief fields | Adds noise; creates sync issues if Brief is updated |
| CI prescribing asset structure | Violates separation; that's Storyboard/generator territory |
| CI being optional forever | Generators will never adopt it if they can skip it |
| CI without confidence scoring | Consumers can't distinguish strong insights from weak guesses |

---

## Appendix A: Field Discovery Summary

| Category | Fields Discovered |
|----------|------------------|
| Classification | `topic_type`, `emotional_register` |
| Hooks | `hooks[]` (text, type, source_field) |
| Narrative | `story_angle`, `contrast_pairs[]` (before, after, tension_type) |
| Audience | `audience_segment`, `audience_prior_belief`, `misconception`, `curiosity_gap` |
| Visual | `visual_opportunities[]` (concept, type, applicable_formats) |
| Engagement | `controversy_angle`, `timeliness_hook`, `shareability_factor` |
| Meta | `confidence_score`, `brief_version`, `review_status`, `generated_at` |
| **Total** | **20 fields** (10 required, 7 optional, 3 metadata) |

## Appendix B: Missing Creator Information (Current State)

| Information | Available Today | After CI |
|-------------|:---:|:---:|
| Factual summary | ✓ | ✓ |
| Educational takeaway | ✓ | ✓ |
| Analogy | ✓ | ✓ |
| Hook candidates | ✗ | ✓ |
| Story angle | ✗ | ✓ |
| Misconception | ✗ | ✓ |
| Contrast pairs | ✗ | ✓ |
| Visual opportunities | ✗ | ✓ |
| Topic classification | ✗ | ✓ |
| Audience persona | ✗ | ✓ |
| Curiosity gap | ✗ | ✓ |
| Emotional register | ✗ | ✓ |
| Controversy signal | ✗ | ✓ |
| Timeliness signal | ✗ | ✓ |

## Appendix C: Downstream Consumer Map

```
                    ┌─────────────────────────────────────┐
                    │       Content Intelligence          │
                    │                                     │
                    │  hooks, story_angle, contrast_pairs │
                    │  misconception, visual_opportunities│
                    │  topic_type, audience_segment       │
                    │  curiosity_gap, emotional_register  │
                    └──────────┬──────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────┐   ┌──────────────┐  ┌────────────┐
     │   Script   │   │  Carousel    │  │ Newsletter │
     │            │   │              │  │            │
     │ hooks[0]   │   │ hooks[0]     │  │ hooks[1]   │
     │ story_angle│   │ visual_opps  │  │ curiosity  │
     │ contrast   │   │ contrast     │  │ timeliness │
     │ misconc.   │   │ misconc.     │  │ story_angle│
     │ audience   │   │ topic_type   │  │ audience   │
     └────────────┘   └──────────────┘  └────────────┘
                               │
                               ▼
                      ┌──────────────┐
                      │  Thumbnail   │
                      │              │
                      │ topic_type   │
                      │ visual_opps  │
                      │ hooks[0]     │
                      │ curiosity    │
                      │ emotion_reg  │
                      └──────────────┘
                               │
                               ▼
                      ┌──────────────┐
                      │  Storyboard  │
                      │   (future)   │
                      │              │
                      │ ALL CI fields│
                      │ coordinates  │
                      │ allocation   │
                      └──────────────┘
```
