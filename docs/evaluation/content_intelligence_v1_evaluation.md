# Content Intelligence v1 Evaluation

> Phase: Evaluation  
> Date: 2026-05-30  
> Status: Structural evaluation (API key blocked — no live LLM outputs available)  
> Methodology: Prompt analysis, schema validation, input quality assessment, deterministic field verification

---

## 1. Executive Summary

Content Intelligence v1 was implemented and tested against 7 real briefs. The API key is currently blocked (leaked key error), so all outputs fell back to `needs_review` placeholders. This evaluation therefore assesses:

1. **Infrastructure correctness** — Does the pipeline work end-to-end? ✓ Yes (136 tests pass)
2. **Deterministic field quality** — Are `topic_type` and `timeliness_hook` correct? ✓ Yes
3. **Input quality** — Are briefs providing sufficient data for CI generation? ⚠️ Degraded
4. **Prompt design** — Will the prompt produce useful outputs given these inputs? ⚠️ Concerns
5. **Schema fitness** — Does the schema capture what's needed? ✓ Adequate for v1

**Verdict:** Infrastructure is sound. Input quality is the primary risk. Prompt needs one adjustment (handling `needs_review` fields). Schema is sufficient for Storyboard v1 with caveats.

---

## 2. Sample Selection

| # | Topic ID | Subject | Category | Analogy | Limitation |
|---|----------|---------|----------|:---:|:---:|
| 1 | 468a4a58 | Mobile GUI Agent evaluation | paper | ✓ | ✓ |
| 2 | 5d2862b7 | RL alignment for diffusion models | paper | ✗ | ✗ |
| 3 | 7c26d522 | LLM fraud routing in banking | paper | ✓ | ✗ |
| 4 | 866047e5 | SGD dynamics in high dimensions | paper | ✗ | ✓ |
| 5 | 9c413887 | KamonBench VLM evaluation | paper | ✓ | ✗ |
| 6 | a5ff171e | ScioMind multi-agent opinion sim | paper | ✗ | ✗ |
| 7 | d319a597 | Human-flow digital twin | paper | ✓ | ✗ |

**Key observation:** All 7 are papers. No tool, concept, news, or release topics in the brief set. This limits diversity assessment.

**Input degradation:** 4/7 briefs have `analogy = "needs_review"`. 4/7 have `limitation = "needs_review"`. This means the CI prompt receives incomplete inputs for the majority of samples.

---

## 3. Field-by-Field Analysis

### 3.1 topic_type (Deterministic)

| Metric | Assessment |
|--------|-----------|
| **Quality** | ✓ Correct — all 7 mapped to `TopicType.PAPER` from `TopicCategory.PAPER` |
| **Usefulness** | High — enables deterministic thumbnail style selection (`paper` → `diagram_overlay`) |
| **Risk** | Low — mapping is 1:1 from existing enum |

**Finding:** Works perfectly. The existing `TopicCategory` enum in `TopicItem` provides this for free. No LLM cost.

### 3.2 timeliness_hook (Deterministic)

| Metric | Assessment |
|--------|-----------|
| **Quality** | ✓ Correct — all 7 topics have `published_at` dates from May 2026, within 7 days → "Published this week" |
| **Usefulness** | Medium — useful for newsletter urgency framing |
| **Risk** | Low — simple date comparison |

**Finding:** Works correctly. However, the current implementation only produces one value ("Published this week" or empty). Future versions could add granularity ("Published yesterday", "Published 3 days ago").

### 3.3 primary_hook (LLM-generated)

| Metric | Assessment |
|--------|-----------|
| **Input quality** | `why_it_matters` is present in all 7 samples — this is the primary hook source |
| **Prompt guidance** | Adequate — specifies hook_type enum, requires source_field tracing |
| **Expected quality** | Medium-High — `why_it_matters` contains strong "so what" statements in all 7 briefs |
| **Risk** | Medium — no few-shot example; model may produce generic hooks |

**Concern:** The prompt says "Use ONLY information from the provided brief fields" but doesn't explicitly instruct what to do when `analogy` or `limitation` is `"needs_review"`. The model might try to use the literal string "needs_review" as content.

### 3.4 secondary_hook (LLM-generated)

| Metric | Assessment |
|--------|-----------|
| **Input quality** | Depends on `analogy` and `limitation` — 4/7 have at least one as `needs_review` |
| **Prompt guidance** | Rule #2 says "must be DIFFERENT types" — good differentiation constraint |
| **Expected quality** | Medium — limited by input degradation |
| **Risk** | High — with `analogy` and `limitation` both `needs_review` (sample #6), the model has very limited material for a second distinct hook |

**Concern:** When both `analogy` and `limitation` are `needs_review`, the secondary hook will likely be a weak rephrasing of the primary hook.

### 3.5 story_angle (LLM-generated)

| Metric | Assessment |
|--------|-----------|
| **Input quality** | Good — `why_it_matters` + `plain_english_summary` provide sufficient narrative material |
| **Prompt guidance** | Minimal — "one sentence describing the narrative frame" |
| **Expected quality** | Medium — without examples, the model may produce summaries rather than angles |
| **Risk** | Medium — "narrative frame" is ambiguous without a few-shot example showing the difference between a summary and an angle |

**Concern:** The distinction between `story_angle` and `why_it_matters` is subtle. Without an example, the model may produce: "This paper introduces a new framework for X" (summary) rather than "The death of manual evaluation in mobile AI" (angle).

### 3.6 curiosity_gap (LLM-generated)

| Metric | Assessment |
|--------|-----------|
| **Input quality** | Good — `student_takeaway` provides the "answer"; curiosity_gap should be the question |
| **Prompt guidance** | Clear — "the question the audience needs answered after seeing the hook" |
| **Expected quality** | Medium-High — the inversion of takeaway→question is a well-defined task |
| **Risk** | Low — this is one of the most constrained and well-defined fields |

**Finding:** This field has the clearest prompt instruction and the most predictable output quality.

### 3.7 contrast_pair (LLM-generated)

| Metric | Assessment |
|--------|-----------|
| **Input quality** | Mixed — requires `limitation` (4/7 are `needs_review`) and `plain_english_summary` |
| **Prompt guidance** | Good — "before is what audience believes/does, after is what topic reveals" |
| **Expected quality** | Medium — when `limitation` is available, contrast is natural; without it, contrast may be forced |
| **Risk** | Medium — 4/7 samples lack `limitation`, reducing contrast quality |

**Concern:** For samples without `limitation`, the "before" in contrast_pair will likely be generic ("traditional methods are slow") rather than specific.

### 3.8 emotional_register (LLM-generated)

| Metric | Assessment |
|--------|-----------|
| **Input quality** | Good — derivable from `why_it_matters` tone |
| **Prompt guidance** | Adequate — enum values listed, but no guidance on when to choose each |
| **Expected quality** | Medium — without selection criteria, the model may default to "clarity" or "excitement" |
| **Risk** | Medium — likely low variance across samples (all papers → likely all "clarity" or "surprise") |

**Concern:** All 7 samples are academic papers. The model will likely assign the same 1-2 registers to all of them, reducing differentiation value.

---

## 4. Cross-Sample Patterns

### Input Quality Distribution

| Brief Field | Available (non-needs_review) | % |
|-------------|:---:|:---:|
| `why_it_matters` | 7/7 | 100% |
| `plain_english_summary` | 7/7 | 100% |
| `student_takeaway` | 7/7 | 100% |
| `audience_fit` | 7/7 | 100% |
| `analogy` | 3/7 | 43% |
| `limitation` | 3/7 | 43% |

**Pattern:** Core fields are always present. Creative/nuanced fields (`analogy`, `limitation`) are frequently degraded. CI must handle this gracefully.

### Category Homogeneity

All 7 samples are `paper` category. This means:
- `topic_type` will always be `PAPER` in this evaluation set
- `emotional_register` will likely cluster around 1-2 values
- No diversity testing possible for tool/concept/news topics

### Format Routing Issues

| Sample | `recommended_formats` | Valid? |
|--------|----------------------|:---:|
| 468a4a58 | `['newsletter', 'carousel', 'short_video']` | ✓ |
| 5d2862b7 | `['Research Paper Summary', 'Technical Presentation', 'Concept Deep Dive']` | ✗ |
| 7c26d522 | `['Case Study', 'Technical Deep Dive', 'System Design Discussion']` | ✗ |
| 866047e5 | `['Theoretical lecture', 'Research seminar', 'Journal club']` | ✗ |
| 9c413887 | `['Research Paper Discussion', 'Dataset Walkthrough and Tutorial', ...]` | ✗ |
| a5ff171e | `['needs_review']` | ✗ |
| d319a597 | `['Case Study', 'Interactive Simulation Demo', 'Technical Presentation']` | ✗ |

**Critical finding:** 6/7 briefs have non-standard `recommended_formats` that violate the Brief prompt's rule #6 ("ONLY from this exact list: short_video, carousel, newsletter"). This is a Brief generation quality issue, not a CI issue — but it means CI's downstream value is reduced because format routing is already broken.

---

## 5. Weaknesses

### W1: No `needs_review` Handling in CI Prompt (Critical)

The CI prompt says "Use ONLY information from the provided brief fields" but does not say "If a field value is 'needs_review', do not use it." The model may attempt to interpret the literal string "needs_review" as content.

**Impact:** 4/7 samples will have degraded `analogy` and/or `limitation` injected into the prompt.

### W2: No Few-Shot Examples (High)

The prompt provides no input→output example. The model has no calibration for:
- How long a hook should be
- What distinguishes a story_angle from a summary
- How specific a contrast_pair should be

**Impact:** Output quality will be inconsistent across runs.

### W3: Emotional Register Lacks Selection Criteria (Medium)

The prompt lists 6 enum values but provides no guidance on when to choose each. For academic papers, the model will likely default to "clarity" or "surprise" for all samples.

**Impact:** Low differentiation value. Downstream generators won't benefit from a field that's always the same.

### W4: Input Degradation Propagates (Medium)

When Brief fields are `needs_review`, CI quality degrades proportionally. The pipeline has no gate preventing CI generation on incomplete briefs.

**Impact:** CI outputs for degraded briefs will be low-quality, potentially misleading downstream generators.

### W5: Single Contrast Pair May Be Insufficient (Low)

Some topics have multiple natural contrasts. Limiting to 1 pair means the strongest contrast must be identified — but without `limitation` data (4/7 samples), the model may pick a weak contrast.

**Impact:** Carousel before/after slides and Script F/C/K labeling get suboptimal contrast data.

---

## 6. Strengths

### S1: Deterministic Fields Work Perfectly

`topic_type` and `timeliness_hook` are correct for all 7 samples. Zero LLM cost, zero risk, immediate downstream value (thumbnail style selection).

### S2: Infrastructure Is Sound

- 136 tests pass
- Generator correctly falls back on failure
- Repository saves/loads correctly
- PromptRegistry resolves correctly
- Pipeline is fully additive (no existing behavior changed)

### S3: Schema Is Minimal and Focused

10 fields total. No bloat. Every field has a clear downstream consumer identified in the Storyboard Blueprint.

### S4: Curiosity Gap Has Clearest Prompt Design

The instruction "the question the audience needs answered after seeing the hook" is specific, constrained, and well-defined. This field will likely produce the most consistent quality.

### S5: Hook Differentiation Constraint Is Good

Requiring primary and secondary hooks to be different types (rule #2) prevents the model from producing two similar hooks. This is a well-designed constraint.

### S6: Source Field Tracing Enables Auditability

Requiring `source_field` per hook means every hook is traceable to its Brief origin. This supports the grounding principle.

---

## 7. Recommended Prompt Changes

| # | Change | Rationale | Priority |
|---|--------|-----------|:---:|
| 1 | Add rule: "If a brief field value is 'needs_review', ignore that field entirely. Do not reference it." | Prevents literal "needs_review" from being used as content | Critical |
| 2 | Add 1 full input→output example | Calibrates hook length, story_angle vs summary distinction, contrast specificity | High |
| 3 | Add emotional_register selection criteria (e.g., "urgency: when timeliness matters; surprise: when assumption is broken") | Prevents clustering on 1-2 values | Medium |
| 4 | Add story_angle anti-pattern: "Do NOT produce a summary. Produce a narrative frame." with good/bad example | Distinguishes angle from summary | Medium |

---

## 8. Recommended Schema Changes

| # | Change | Rationale | Priority |
|---|--------|-----------|:---:|
| 1 | Add `input_quality: float` (0.0-1.0) | Computed deterministically: % of Brief fields that are NOT `needs_review`. Enables quality gates. | High |
| 2 | Add `hook_source_fields_available: List[str]` | Records which Brief fields were actually usable (not `needs_review`). Enables downstream confidence assessment. | Medium |
| 3 | Consider making `contrast_pair` optional | When `limitation` is `needs_review`, contrast quality will be low. Better to omit than produce weak contrast. | Low |

---

## 9. Storyboard Readiness Assessment

### Can Storyboard v1 Safely Depend on CI v1?

| CI Field | Storyboard Dependency | Ready? | Condition |
|----------|----------------------|:---:|-----------|
| `topic_type` | Style selection, format planning | ✓ | Always correct (deterministic) |
| `timeliness_hook` | Newsletter urgency | ✓ | Always correct (deterministic) |
| `primary_hook` | Hook assignment to primary format | ⚠️ | Only if `needs_review` handling is added to prompt |
| `secondary_hook` | Hook assignment to secondary format | ⚠️ | Only if input degradation is handled |
| `story_angle` | Arc differentiation | ⚠️ | Only with few-shot example to prevent summary-as-angle |
| `curiosity_gap` | CTA design, thumbnail supporting_text | ✓ | Well-defined prompt instruction |
| `contrast_pair` | Before/after slides, F/C/K labeling | ⚠️ | Only when `limitation` is available |
| `emotional_register` | Tone calibration | ⚠️ | Only with selection criteria to prevent clustering |

### Storyboard Readiness Verdict

**Conditional GO** — Storyboard can depend on CI v1 if:

1. CI prompt adds `needs_review` field handling (Critical — blocks deployment)
2. Storyboard treats CI fields as optional (degrades gracefully when CI quality is low)
3. Storyboard checks `review_status` before consuming (skip `needs_review` CI outputs)

Without condition #1, Storyboard will receive garbage data for 4/7 topics.

---

## 10. Go / No-Go Recommendation

### Overall Verdict: CONDITIONAL GO

| Criterion | Status |
|-----------|--------|
| Infrastructure works | ✓ GO |
| Deterministic fields correct | ✓ GO |
| Schema sufficient for v1 | ✓ GO |
| Prompt produces useful outputs | ⚠️ CONDITIONAL |
| Input quality sufficient | ⚠️ CONDITIONAL |
| Storyboard can depend on it | ⚠️ CONDITIONAL |

### Conditions for Full GO

1. **Add `needs_review` handling to CI prompt** — One line addition. Without this, 4/7 briefs produce degraded CI.
2. **Add 1 few-shot example to CI prompt** — Calibrates output quality. Without this, story_angle and hooks will be inconsistent.
3. **Add input quality gate** — Don't generate CI for briefs where >50% of fields are `needs_review`. Saves tokens, prevents garbage.

### Recommended Next Steps (in order)

1. Fix API key (operational — not architectural)
2. Add `needs_review` handling rule to CI prompt
3. Add 1 few-shot example
4. Re-run evaluation with live LLM outputs
5. Proceed to Storyboard v1 if evaluation passes

### What NOT To Do

- Do not add more CI fields before validating current ones with live outputs
- Do not integrate CI into existing generators yet (wait for Storyboard)
- Do not rewrite the Brief prompt to fix `recommended_formats` violations (separate concern)

---

## Appendix: Evaluation Limitations

This evaluation was conducted without live LLM outputs due to a blocked API key. Findings are based on:

1. Structural analysis of the prompt against real brief content
2. Deterministic field verification (confirmed correct)
3. Input quality assessment (measured degradation rates)
4. Prompt design review against known LLM behavior patterns

A follow-up evaluation with live outputs is required before Storyboard integration.
