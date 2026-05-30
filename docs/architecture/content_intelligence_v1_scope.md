# Content Intelligence v1 Scope

> Phase: D.2 — Architecture & Discovery  
> Status: Analysis Only — No Implementation  
> Date: 2026-05-30  
> Goal: Find the smallest useful CI implementation

---

## 1. Brief Fields Already Present

| Brief Field | Type | CI-Relevant Information |
|-------------|------|------------------------|
| `why_it_matters` | str | Contains the "so what" — raw material for hooks and story angles |
| `plain_english_summary` | List[str] (3) | Core claims — raw material for contrast pairs and claim allocation |
| `student_takeaway` | str | Learning outcome — raw material for curiosity gap |
| `analogy` | str | Pedagogical metaphor — directly usable as visual_metaphor seed |
| `limitation` | str | Honest constraint — raw material for controversy/nuance |
| `audience_fit` | str | Generic audience note — seed for audience_segment |
| `recommended_formats` | List[str] | Format routing — already exists, no CI needed |

**Additionally available from TopicItem (upstream of Brief):**

| TopicItem Field | Type | CI-Relevant Information |
|-----------------|------|------------------------|
| `category` | TopicCategory enum | paper, repo, release, concept, news, tool, unknown — **maps directly to CI.topic_type** |
| `topic_tags` | List[str] | Keywords — can inform visual type selection |
| `hook_potential_score` | float | Scoring engine already estimates hook potential |

---

## 2. CI Fields Derivable Without LLM Call

| CI Field | Derivation Method | Source | Confidence |
|----------|------------------|--------|:---:|
| `topic_type` | Deterministic mapping | `TopicItem.category` → `TopicType` | 100% |
| `visual_opportunities[0].visual_concept` | Direct copy | `Brief.analogy` | 90% |
| `visual_opportunities[0].visual_type` | Rule-based | If analogy contains "diagram"→diagram, else→metaphor_image | 70% |
| `audience_segment` | Light transformation | Prefix `Brief.audience_fit` with specificity (e.g., "ML students" → "junior ML student building first project") | 60% |
| `timeliness_hook` | Rule-based | If `TopicItem.published_at` < 7 days → "Published this week"; else → empty | 80% |

**Total derivable without LLM: 5 of 20 fields (25%)**

---

## 3. CI Fields Requiring LLM Call

| CI Field | Why LLM Required | Input Fields Used |
|----------|-----------------|-------------------|
| `hooks[]` | Requires creative reframing of facts into engagement-optimized openings | `why_it_matters`, `plain_english_summary`, `limitation` |
| `story_angle` | Requires narrative judgment — which frame makes this compelling | `why_it_matters`, `plain_english_summary` |
| `contrast_pairs[]` | Requires identifying before/after or old/new tensions | `plain_english_summary`, `limitation`, `why_it_matters` |
| `emotional_register` | Requires tone judgment based on content nature | `why_it_matters`, `limitation`, `topic_type` |
| `misconception` | Requires reasoning about what audience likely believes wrong | `plain_english_summary`, `audience_fit`, `limitation` |
| `curiosity_gap` | Requires identifying the knowledge gap that drives engagement | `why_it_matters`, `student_takeaway` |
| `controversy_angle` | Requires identifying legitimate debate in the field | `limitation`, `plain_english_summary` |
| `audience_prior_belief` | Requires modeling what audience thinks before exposure | `audience_fit`, `plain_english_summary` |
| `shareability_factor` | Requires predicting social sharing motivation | `why_it_matters`, `analogy` |
| `confidence_score` | Requires self-assessment of output quality | All generated fields |

**Total requiring LLM: 10 of 20 fields (50%)**

---

## 4. Field Classification Breakdown

| Category | Fields | % of Total |
|----------|:---:|:---:|
| **Deterministic transformations** (zero-cost, code-only) | `topic_type`, `timeliness_hook` | 10% |
| **Rule-based derivations** (zero-cost, heuristic) | `visual_opportunities[0]`, `audience_segment` (partial), `visual_type` | 15% |
| **LLM-generated insights** (one API call) | `hooks`, `story_angle`, `contrast_pairs`, `emotional_register`, `misconception`, `curiosity_gap`, `controversy_angle`, `audience_prior_belief`, `shareability_factor`, `confidence_score` | 50% |
| **Metadata / pass-through** | `topic_id`, `brief_version`, `generated_at`, `review_status` | 20% |
| **Redundant with Brief** | `audience_segment` (≈ `audience_fit` refinement) | 5% |

---

## 5. Smallest Viable CI v1

### Design Principle

> One LLM call producing the highest-value fields. Deterministic fields computed in code. Optional fields deferred to v2.

### v1 Scope: 7 Fields (1 LLM call + 2 deterministic)

| Field | Source | Cost |
|-------|--------|------|
| `topic_type` | Deterministic from `TopicItem.category` | Zero |
| `timeliness_hook` | Rule-based from `TopicItem.published_at` | Zero |
| `hooks` (2 variants) | LLM | 1 call |
| `story_angle` | LLM | (same call) |
| `contrast_pairs` (1 pair) | LLM | (same call) |
| `curiosity_gap` | LLM | (same call) |
| `emotional_register` | LLM | (same call) |

### Why These 7

| Field | Downstream Impact | Justification |
|-------|------------------|---------------|
| `topic_type` | Thumbnail style becomes deterministic | Eliminates #1 weakness from D.1 audit |
| `hooks` (2) | Script, Carousel, Newsletter, Thumbnail all need hooks | Highest cross-format value |
| `story_angle` | All content formats need a narrative frame | Enables Storyboard differentiation |
| `contrast_pairs` | Script F/C/K labeling, Carousel before/after slides | Solves forced-contrast problem |
| `curiosity_gap` | Newsletter CTA, Thumbnail supporting_text | Drives engagement across formats |
| `emotional_register` | Tone calibration for all generators | Prevents flat-neutral default |
| `timeliness_hook` | Newsletter urgency, Script context | Zero-cost high-value signal |

### What v1 Defers

| Field | Reason to Defer | v2 Trigger |
|-------|----------------|------------|
| `misconception` | High value but not every topic has one; adds prompt complexity | When engagement data shows misconception-hooks outperform |
| `controversy_angle` | Many topics have none; empty field adds noise | When editorial workflow requests debate framing |
| `audience_prior_belief` | Derivable from misconception; redundant without it | Ships with misconception in v2 |
| `shareability_factor` | Nice-to-have; no current generator consumes it | When social posting is implemented |
| `visual_opportunities` (full) | `Brief.analogy` covers 80% of the need for v1 | When carousel visual quality is measured |
| `audience_segment` | `Brief.audience_fit` is sufficient for v1 generators | When multi-persona support is needed |
| `confidence_score` | Useful but adds prompt complexity; can be approximated by review_status | When quality gates need numeric thresholds |

---

## 6. Token Cost Estimate

### Current Pipeline (per topic)

| Stage | Tokens In | Tokens Out | Calls |
|-------|:---------:|:----------:|:-----:|
| Brief | ~4,000 (raw_text) | ~300 | 1 |
| Script | ~500 (brief fields) | ~400 | 1 |
| Carousel | ~500 | ~600 | 1 |
| Newsletter | ~500 | ~400 | 1 |
| Thumbnail | ~500 | ~200 | 1 |
| **Total** | **~6,000** | **~1,900** | **5** |

### With CI v1 (per topic)

| Stage | Tokens In | Tokens Out | Calls |
|-------|:---------:|:----------:|:-----:|
| Brief | ~4,000 | ~300 | 1 |
| **CI v1** | **~600** (brief fields) | **~400** | **1** |
| Script | ~800 (brief + CI) | ~400 | 1 |
| Carousel | ~800 | ~600 | 1 |
| Newsletter | ~800 | ~400 | 1 |
| Thumbnail | ~700 | ~200 | 1 |
| **Total** | **~7,700** | **~2,300** | **6** |

### Cost Delta

| Metric | Before | After | Delta |
|--------|:------:|:-----:|:-----:|
| API calls per topic | 5 | 6 | +1 (20%) |
| Input tokens per topic | ~6,000 | ~7,700 | +1,700 (28%) |
| Output tokens per topic | ~1,900 | ~2,300 | +400 (21%) |
| Gemini free tier (1,500 req/day) | 300 topics/day | 250 topics/day | -17% capacity |

**Verdict:** Acceptable. One additional call per topic. The quality improvement in downstream assets justifies the 20% cost increase.

---

## 7. v1 Schema (Minimal)

```yaml
ContentIntelligence:
  # Identity (pass-through)
  topic_id: TopicId
  generated_at: str
  review_status: ReviewStatus

  # Deterministic (computed in code, no LLM)
  topic_type: TopicType          # from TopicItem.category
  timeliness_hook: str           # from TopicItem.published_at (empty if evergreen)

  # LLM-generated (single call)
  hooks:                         # exactly 2
    - hook_text: str
      hook_type: HookType        # question | bold_claim | contrast | statistic
      source_field: str          # which Brief field grounded this
  story_angle: str               # one-sentence narrative frame
  contrast_pairs:                # exactly 1
    - before: str
      after: str
  curiosity_gap: str             # the question that drives engagement
  emotional_register: EmotionalRegister  # awe | urgency | surprise | clarity | concern | excitement
```

**Total fields: 10** (vs. 20 in full blueprint)  
**LLM-generated: 5** (hooks, story_angle, contrast_pairs, curiosity_gap, emotional_register)  
**Deterministic: 2** (topic_type, timeliness_hook)  
**Metadata: 3** (topic_id, generated_at, review_status)

---

## 8. Recommendation

Ship CI v1 with:
- **2 deterministic fields** computed in code (zero cost)
- **5 LLM fields** in a single prompt call (~600 tokens in, ~400 out)
- **Exactly 1 additional API call per topic**

This delivers:
- Deterministic thumbnail style selection (topic_type)
- Pre-built hooks for all 4 generators
- Narrative frame for Storyboard
- Contrast data for Script F/C/K compliance
- Curiosity gap for CTAs and thumbnails
- Tone calibration for all generators

At a cost of 20% more API calls — the highest-ROI investment in the pipeline.
