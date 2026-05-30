# Storyboard Schema Validation

> Phase: Pre-Implementation Validation  
> Date: 2026-05-31  
> Status: Schema Freeze Decision  
> Depends on: Storyboard v1 Scope

---

## 1. Field Inventory (All 13 Proposed)

| # | Field | Type |
|---|-------|------|
| 1 | `topic_id` | TopicId |
| 2 | `generated_at` | str |
| 3 | `review_status` | ReviewStatus |
| 4 | `formats_planned` | List[str] |
| 5 | `hook_assignments.script_hook` | str |
| 6 | `hook_assignments.carousel_hook` | str |
| 7 | `hook_assignments.newsletter_hook` | str |
| 8 | `hook_assignments.thumbnail_hook` | str |
| 9 | `cta_assignments.script_cta` | str |
| 10 | `cta_assignments.carousel_cta` | str |
| 11 | `cta_assignments.newsletter_cta` | str |
| 12 | `claim_allocation.script_claims` | List[str] |
| 13 | `claim_allocation.carousel_claims` | List[str] |
| 14 | `claim_allocation.newsletter_claims` | List[str] |
| 15 | `visual_style` | Literal[4 options] |
| 16 | `visual_metaphor` | str |

**Note:** The scope document stated 13 fields but the actual enumeration yields 16 distinct data fields (3 metadata + 4 hooks + 3 CTAs + 3 claim lists + 2 visual + 1 formats). This is correct — "13" counted logical groups, not individual fields.

---

## 2. Source Analysis

| # | Field | Source | Method | Cost |
|---|-------|--------|--------|:---:|
| 1 | `topic_id` | Brief | Pass-through | Zero |
| 2 | `generated_at` | Pipeline | Timestamp | Zero |
| 3 | `review_status` | Pipeline | State machine | Zero |
| 4 | `formats_planned` | Brief.recommended_formats | Normalize via FREETEXT_TO_FORMAT | Zero |
| 5 | `hook_assignments.script_hook` | CI.primary_hook.hook_text | Pass-through | Zero |
| 6 | `hook_assignments.carousel_hook` | CI.secondary_hook.hook_text | Pass-through | Zero |
| 7 | `hook_assignments.newsletter_hook` | CI.curiosity_gap | Pass-through | Zero |
| 8 | `hook_assignments.thumbnail_hook` | CI.primary_hook.hook_text | LLM: compress to ≤6 words | 1 call |
| 9 | `cta_assignments.script_cta` | formats_planned | LLM: cross-reference | (same call) |
| 10 | `cta_assignments.carousel_cta` | formats_planned | LLM: cross-reference | (same call) |
| 11 | `cta_assignments.newsletter_cta` | formats_planned | LLM: cross-reference | (same call) |
| 12 | `claim_allocation.script_claims` | Brief.plain_english_summary | LLM: classify & distribute | (same call) |
| 13 | `claim_allocation.carousel_claims` | Brief.plain_english_summary | LLM: classify & distribute | (same call) |
| 14 | `claim_allocation.newsletter_claims` | Brief.plain_english_summary | LLM: classify & distribute | (same call) |
| 15 | `visual_style` | CI.topic_type | Deterministic lookup | Zero |
| 16 | `visual_metaphor` | Brief.analogy (fallback: CI.contrast_pair) | Pass-through | Zero |

**Summary:** 9 fields zero-cost, 7 fields from single LLM call.

---

## 3. Thumbnail Consumption Matrix

| # | Field | Thumbnail Needs? | How Consumed |
|---|-------|:---:|--------------|
| 1 | `topic_id` | — | Identity (not consumed by prompt) |
| 2 | `generated_at` | — | Metadata |
| 3 | `review_status` | — | Pipeline state |
| 4 | `formats_planned` | — | Not consumed |
| 5 | `hook_assignments.script_hook` | — | Not consumed |
| 6 | `hook_assignments.carousel_hook` | — | Not consumed |
| 7 | `hook_assignments.newsletter_hook` | — | Not consumed |
| 8 | **`hook_assignments.thumbnail_hook`** | **Mandatory** | → `ThumbnailPrompt.title_text` |
| 9 | `cta_assignments.script_cta` | — | Not consumed |
| 10 | `cta_assignments.carousel_cta` | — | Not consumed |
| 11 | `cta_assignments.newsletter_cta` | — | Not consumed |
| 12 | `claim_allocation.script_claims` | — | Not consumed |
| 13 | `claim_allocation.carousel_claims` | — | Not consumed |
| 14 | `claim_allocation.newsletter_claims` | — | Not consumed |
| 15 | **`visual_style`** | **Mandatory** | → `ThumbnailPrompt.style` (deterministic, replaces inference) |
| 16 | **`visual_metaphor`** | **Mandatory** | → `ThumbnailPrompt.visual_metaphor` |

**Thumbnail consumes exactly 3 fields.** Everything else is for Script/Carousel/Newsletter.

---

## 4. Schema Recommendation

### Option A: Single Flat Model

```python
class Storyboard(BaseModel):
    topic_id: TopicId
    generated_at: str
    review_status: ReviewStatus
    formats_planned: List[str]
    script_hook: str
    carousel_hook: str
    newsletter_hook: str
    thumbnail_hook: str
    script_cta: str
    carousel_cta: str
    newsletter_cta: str
    script_claims: List[str]
    carousel_claims: List[str]
    newsletter_claims: List[str]
    visual_style: str
    visual_metaphor: str
```

### Option B: Nested Assignments

```python
class HookAssignments(BaseModel):
    script: str
    carousel: str
    newsletter: str
    thumbnail: str

class CTAAssignments(BaseModel):
    script: str
    carousel: str
    newsletter: str

class ClaimAllocation(BaseModel):
    script: List[str]
    carousel: List[str]
    newsletter: List[str]

class Storyboard(BaseModel):
    topic_id: TopicId
    generated_at: str
    review_status: ReviewStatus
    formats_planned: List[str]
    hooks: HookAssignments
    ctas: CTAAssignments
    claims: ClaimAllocation
    visual_style: str
    visual_metaphor: str
```

### Recommendation: Option A (Flat)

| Criterion | Option A (Flat) | Option B (Nested) |
|-----------|:---:|:---:|
| Simplicity | ✓ | — |
| JSON serialization | Flat keys | Nested objects |
| Prompt template injection | Direct field access | Requires `.hooks.script` |
| Adding new formats | Add field | Add field to nested model |
| Generator consumption | `storyboard.script_hook` | `storyboard.hooks.script` |
| Repository compatibility | Standard JsonRepository | Standard JsonRepository |
| Migration cost to v2 | Low (rename fields) | Low (restructure nesting) |

**Rationale:** Flat is simpler for v1. Generators access fields directly. Prompt templates use simple `{{ storyboard.script_hook }}` syntax. Nesting adds indirection without v1 benefit. If v2 needs dynamic format lists (not hardcoded script/carousel/newsletter), we can migrate to a list-of-assignments pattern then.

---

## 5. Future Compatibility Analysis

### Will Flat Schema Block v2?

| v2 Feature | Flat Schema Impact | Migration Path |
|------------|:---:|----------------|
| New format (e.g., "thread") | Add `thread_hook`, `thread_cta`, `thread_claims` fields | Additive — no breakage |
| Arc assignments | Add `script_arc`, `carousel_arc`, etc. | Additive |
| Scope assignments | Add `script_duration`, `carousel_slide_count`, etc. | Additive |
| Tone assignments | Add `script_tone`, `carousel_tone`, etc. | Additive |
| Dynamic format count | Requires schema redesign to list-based | Breaking — but only needed if format count becomes variable per topic |

**Verdict:** Flat schema supports v2 features via additive fields. Only becomes problematic if the system needs to support arbitrary/dynamic format lists (unlikely in near term — formats are a fixed set).

### Will Thumbnail Integration Block Script Integration?

No. Thumbnail consumes 3 fields. Script will consume 3 different fields. No overlap, no conflict. Both can proceed independently.

---

## 6. Claim Allocation: V1 or Defer?

### Arguments for V1

- Brief.plain_english_summary always has exactly 3 items
- 3 claims → 3 formats is a natural 1:1 distribution
- Script integration (Week 3) needs claims immediately
- Including it in the Storyboard prompt costs minimal additional tokens

### Arguments for Deferral

- Thumbnail doesn't consume claims
- Adds complexity to the Storyboard prompt
- Distribution logic may be trivial (1 claim per format)

### Recommendation: Include in V1

**Rationale:** The LLM call already exists for CTAs and thumbnail_hook. Adding claim allocation to the same call costs ~50 extra output tokens. Deferring means a second schema change when Script integrates in Week 3. Ship it now, consume it later.

---

## 7. Go/No-Go Recommendation

### Schema Decision: GO — Flat Model (Option A)

| Criterion | Status |
|-----------|--------|
| All fields identified and sourced | ✓ |
| Thumbnail consumption path clear (3 fields) | ✓ |
| Script/Newsletter consumption path clear (3 fields each) | ✓ |
| Carousel consumption path clear (4 fields) | ✓ |
| Single LLM call sufficient | ✓ |
| Backward compatible (additive domain) | ✓ |
| Future v2 migration path exists | ✓ |
| No existing schema changes required | ✓ |

### Frozen Schema (v1)

```python
class Storyboard(BaseModel):
    topic_id: TopicId
    generated_at: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    formats_planned: List[str]
    # Hooks
    script_hook: str
    carousel_hook: str
    newsletter_hook: str
    thumbnail_hook: str
    # CTAs
    script_cta: str
    carousel_cta: str
    newsletter_cta: str
    # Claims
    script_claims: List[str]
    carousel_claims: List[str]
    newsletter_claims: List[str]
    # Visual
    visual_style: str   # Literal[4 options]
    visual_metaphor: str
```

**16 data fields. 1 LLM call. Thumbnail consumes 3. Ready for implementation.**
