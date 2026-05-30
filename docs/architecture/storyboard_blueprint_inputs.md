# Storyboard Blueprint Inputs

> Phase: D.2 — Architecture & Discovery  
> Status: Analysis Only — No Implementation  
> Date: 2026-05-30  
> Depends on: Storyboard Discovery, Content Intelligence Blueprint

---

## 1. Complete Field Inventory

### Script (9 fields)

| Field | Type | Current Owner |
|-------|------|---------------|
| `topic_id` | TopicId | Pipeline identity |
| `format` | Literal["short_video", "carousel", "newsletter"] | Generator routing |
| `hook` | str | Generator invents |
| `script_sections` | List[str] (4 items) | Generator writes |
| `cta` | str | Generator invents |
| `claims_used` | List[str] | Generator selects |
| `source_links` | List[str] | Generator copies from Brief |
| `review_status` | ReviewStatus | Pipeline state |
| `generated_at` | str | Pipeline timestamp |

### Carousel (7 top-level + CarouselSlide nested)

| Field | Type | Current Owner |
|-------|------|---------------|
| `topic_id` | TopicId | Pipeline identity |
| `slides` | List[CarouselSlide] | Generator invents |
| `slides[].slide_number` | int | Generator assigns |
| `slides[].title` | str | Generator writes |
| `slides[].body` | str | Generator writes |
| `slides[].visual_note` | str | Generator invents |
| `cta_slide` | str | Generator invents |
| `claims_used` | List[str] | Generator selects |
| `source_links` | List[str] | Generator copies from Brief |
| `review_status` | ReviewStatus | Pipeline state |
| `generated_at` | str | Pipeline timestamp |

### Newsletter (7 top-level + NewsletterSection nested)

| Field | Type | Current Owner |
|-------|------|---------------|
| `topic_id` | TopicId | Pipeline identity |
| `subject_line` | str | Generator invents |
| `sections` | List[NewsletterSection] (3 items) | Generator writes |
| `sections[].section_name` | Literal[...] | Hardcoded structure |
| `sections[].content` | str | Generator writes |
| `cta` | str | Generator invents |
| `claims_used` | List[str] | Generator selects |
| `source_links` | List[str] | Generator copies from Brief |
| `review_status` | ReviewStatus | Pipeline state |
| `generated_at` | str | Pipeline timestamp |

### Thumbnail (8 fields)

| Field | Type | Current Owner |
|-------|------|---------------|
| `topic_id` | TopicId | Pipeline identity |
| `title_text` | str | Generator invents |
| `supporting_text` | str | Generator invents |
| `visual_metaphor` | str | Generator invents |
| `style` | Literal[4 options] | Generator infers from topic |
| `negative_prompt` | List[str] | Generator selects |
| `readability_notes` | str | Generator writes |
| `review_status` | ReviewStatus | Pipeline state |
| `generated_at` | str | Pipeline timestamp |

---

## 2. Field Ownership Classification

### Fields That Become Storyboard-Owned

These fields represent **planning decisions** that should be made once and distributed to generators.

| Current Field | Current Model | Why Storyboard Owns It |
|---------------|---------------|----------------------|
| `hook` | Script | Hook is a cross-format engagement decision. All formats need one; they should be coordinated variants, not independent inventions. |
| `slides[0].title` + `slides[0].body` | Carousel | Slide 1 is the carousel's hook. Same coordination need. |
| `subject_line` | Newsletter | The email hook. Same coordination need. |
| `title_text` | Thumbnail | The visual hook. Same coordination need. |
| `cta` | Script | CTAs should cross-reference other formats ("see the carousel breakdown"). Requires knowing what formats exist. |
| `cta_slide` | Carousel | Same cross-format CTA coordination. |
| `cta` | Newsletter | Same cross-format CTA coordination. |
| `claims_used` | Script, Carousel, Newsletter | Claim allocation across formats prevents duplication and ensures coverage. |
| `format` | Script | Which formats to generate is a planning decision, not a generator concern. |
| `style` | Thumbnail | Visual style should be consistent with carousel visual language. Coordinated decision. |
| `visual_metaphor` | Thumbnail | Should match carousel's visual palette. |
| `slides[].visual_note` (palette) | Carousel | Visual concept selection is planning; specific descriptions remain with generator. |

### Fields That Remain Asset-Specific

These fields represent **execution-level writing** that generators own.

| Field | Model | Why It Stays |
|-------|-------|-------------|
| `script_sections` | Script | Sentence-level writing is the generator's core job. |
| `slides[].title` (slides 2+) | Carousel | Per-slide copywriting within the planned arc. |
| `slides[].body` | Carousel | Per-slide body text is execution. |
| `slides[].visual_note` (detail) | Carousel | Specific visual description within the planned concept. |
| `sections[].content` | Newsletter | Section prose is execution. |
| `supporting_text` | Thumbnail | Specific phrasing of the curiosity gap. |
| `negative_prompt` | Thumbnail | Technical image-generation avoidance list. |
| `readability_notes` | Thumbnail | Technical contrast/layout guidance. |

### Fields That Are Pipeline Infrastructure (Neither Storyboard Nor Generator)

| Field | Model(s) | Owner |
|-------|----------|-------|
| `topic_id` | All | Pipeline identity — passed through unchanged |
| `source_links` | Script, Carousel, Newsletter | Provenance — copied from Brief, not a decision |
| `review_status` | All | State machine — set by pipeline, not by planning or generation |
| `generated_at` | All | Timestamp — set by pipeline |
| `slide_number` | Carousel | Structural index — mechanical, not creative |
| `sections[].section_name` | Newsletter | Structural label — currently hardcoded |

---

## 3. Fields Generated Once and Shared

These fields should be computed **once** by Storyboard and consumed by **multiple** generators.

| Shared Concept | Storyboard Field | Consumed By |
|---------------|-----------------|-------------|
| **Hook variants** | `hook_assignments.{format}` | Script (as `hook`), Carousel (as slide 1), Newsletter (as `subject_line`), Thumbnail (as `title_text`) |
| **CTA ecosystem** | `cta_assignments.{format}` | Script (as `cta`), Carousel (as `cta_slide`), Newsletter (as `cta`) |
| **Claim allocation** | `claim_allocation.{format}` | Script, Carousel, Newsletter (as `claims_used`) |
| **Visual palette** | `visual_palette[]` | Carousel (as `visual_note` source), Thumbnail (as `visual_metaphor` source) |
| **Visual style** | `visual_style` | Thumbnail (as `style`), Carousel (as visual density guidance) |
| **Narrative arc type** | `arc_assignments.{format}` | Script (H-C-E-P-C or alternative), Carousel (slide arc), Newsletter (section arc) |
| **Tone register** | `tone_assignments.{format}` | Script (conversational), Newsletter (professional), Carousel (punchy) |
| **Scope** | `scope.{format}` | Script (duration), Carousel (slide count), Newsletter (section count) |
| **Differentiation angle** | `angle_assignments.{format}` | All — what unique perspective each format takes |

### Sharing Rules

1. Hook variants must be **distinct** — no two formats receive the same hook text
2. CTAs must **cross-reference** — each CTA drives traffic to another format
3. Claims must have **full coverage** — union of all allocations = all available claims
4. Visual palette is **shared** — carousel and thumbnail draw from same concepts
5. Arcs must be **complementary** — no two formats tell the same story structure

---

## 4. Fields That Should Never Be Shared

| Field | Model | Why It Must Not Be Shared |
|-------|-------|--------------------------|
| `script_sections` content | Script | Voice, rhythm, and word choice are format-specific. A script sentence cannot be reused as carousel body text. |
| `sections[].content` prose | Newsletter | Email prose has different register, length, and structure than any other format. |
| `slides[].body` text | Carousel | 30-word slide bodies are a unique constraint. Cannot be derived from script or newsletter. |
| `negative_prompt` | Thumbnail | Image-generation avoidance is a technical concern specific to visual synthesis. |
| `readability_notes` | Thumbnail | Layout/contrast guidance is platform-specific (thumbnail dimensions, mobile rendering). |
| `review_status` | All | Each asset has independent review lifecycle. Approving a script doesn't approve the carousel. |

### Why These Must Not Be Shared

**Sharing execution-level content creates coupling.** If script_sections were derived from a shared source, changing the script would require re-evaluating whether the carousel still makes sense. Each generator must be independently editable after Storyboard planning is complete.

**Principle:** Storyboard shares **decisions** (what to say, which angle, which claims). Generators own **execution** (how to say it in their format's constraints).

---

## 5. Proposed Storyboard Schema

Derived from evidence in existing models. Every field traces to a current gap or coordination failure identified in the field inventory.

```yaml
Storyboard:
  # ─── Identity ───
  topic_id: TopicId
  generated_at: str
  review_status: ReviewStatus

  # ─── Format Plan ───
  # Replaces: Brief.recommended_formats + CLI routing logic
  # Evidence: Script.format field, FREETEXT_TO_FORMAT mapping, FORMAT_TO_ASSET mapping
  formats_planned: List[FormatPlan]
  
  FormatPlan:
    format: str                    # "short_video" | "carousel" | "newsletter" | "thumbnail"
    rationale: str                 # Why this format was selected for this topic
    priority: int                  # Generation order (1 = first)

  # ─── Hook Assignments ───
  # Replaces: Script.hook, Carousel.slides[0], Newsletter.subject_line, Thumbnail.title_text
  # Evidence: 4 models independently invent hooks from same Brief
  hook_assignments: List[HookAssignment]
  
  HookAssignment:
    format: str                    # Target format
    hook_text: str                 # The assigned hook
    hook_type: str                 # "question" | "bold_claim" | "contrast" | "statistic"
    max_length: int                # Format constraint (e.g., 60 chars for subject_line)

  # ─── CTA Ecosystem ───
  # Replaces: Script.cta, Carousel.cta_slide, Newsletter.cta
  # Evidence: 3 models have CTA fields that cannot cross-reference each other
  cta_assignments: List[CTAAssignment]
  
  CTAAssignment:
    format: str                    # Source format (where CTA appears)
    cta_text: str                  # The CTA content
    drives_to: str                 # Target format this CTA promotes (or "external")

  # ─── Claim Allocation ───
  # Replaces: Script.claims_used, Carousel.claims_used, Newsletter.claims_used
  # Evidence: 3 models independently select claims, risking duplication/gaps
  claim_allocation: List[ClaimAllocation]
  
  ClaimAllocation:
    format: str                    # Target format
    claims: List[str]             # Claims assigned to this format
    allocation_reason: str         # Why these claims suit this format

  # ─── Narrative Arc ───
  # Replaces: Hardcoded H-C-E-P-C (Script), slide arc (Carousel), 3-section structure (Newsletter)
  # Evidence: All 3 content formats use nearly identical arcs with no differentiation
  arc_assignments: List[ArcAssignment]
  
  ArcAssignment:
    format: str
    arc_type: str                  # "hook_context_explain_relevance_cta" | "myth_reality_proof" | "problem_solution_evidence" | "question_exploration_answer"
    beats: List[str]              # Ordered narrative beats for this format
    differentiation_note: str      # How this arc differs from other formats

  # ─── Scope Decisions ───
  # Replaces: Hardcoded "60 seconds" (Script), "7-10 slides" (Carousel), "3 sections" (Newsletter)
  # Evidence: All scope constraints are hardcoded in prompts regardless of topic complexity
  scope_assignments: List[ScopeAssignment]
  
  ScopeAssignment:
    format: str
    constraint_type: str           # "duration_seconds" | "slide_count" | "section_count"
    value: int                     # The planned scope
    rationale: str                 # Why this scope for this topic

  # ─── Visual Palette ───
  # Replaces: Carousel.slides[].visual_note (invented per-slide), Thumbnail.visual_metaphor + style
  # Evidence: Carousel and Thumbnail invent independent visual metaphors for same topic
  visual_palette: VisualPalette
  
  VisualPalette:
    primary_metaphor: str          # The dominant visual concept (shared by carousel + thumbnail)
    style: str                     # "clean_minimal" | "bold_typographic" | "diagram_overlay" | "metaphor_illustration"
    visual_concepts: List[VisualConcept]
    brand_avoidances: List[str]    # Baseline negative prompts (shared across visual assets)
  
  VisualConcept:
    concept: str                   # Concrete visual description
    type: str                      # "diagram" | "code_snippet" | "metaphor_image" | "comparison_chart" | "process_flow"
    assigned_to: str               # "carousel_slide_3" | "thumbnail" | "carousel_slide_7" etc.

  # ─── Tone Register ───
  # Replaces: Hardcoded "slightly more formal" (Newsletter), implicit conversational (Script)
  # Evidence: Tone decisions are buried in prompt rules, not explicit planning
  tone_assignments: List[ToneAssignment]
  
  ToneAssignment:
    format: str
    register: str                  # "conversational" | "professional" | "punchy" | "analytical"
    rationale: str

  # ─── Differentiation Strategy ───
  # Does not exist anywhere today
  # Evidence: All formats tell the same story from the same angle
  differentiation_strategy: str    # One sentence: how formats complement each other
  format_roles: List[FormatRole]
  
  FormatRole:
    format: str
    role: str                      # "emotional_hook" | "visual_breakdown" | "analytical_context" | "curiosity_trigger"
    unique_angle: str              # What this format covers that others don't
```

---

## 6. Evidence Traceability

Every Storyboard field traces to a concrete problem in the current models:

| Storyboard Field | Problem It Solves | Evidence |
|-----------------|-------------------|----------|
| `hook_assignments` | 4 independent hook inventions | Script.hook, Carousel.slides[0], Newsletter.subject_line, Thumbnail.title_text all invented from same Brief |
| `cta_assignments` | CTAs can't cross-reference formats | Script.cta, Carousel.cta_slide, Newsletter.cta have no awareness of each other |
| `claim_allocation` | Duplication and coverage gaps | Script.claims_used, Carousel.claims_used, Newsletter.claims_used all independently select |
| `arc_assignments` | All formats use same narrative structure | H-C-E-P-C ≈ Hook-Context-Teaching-Takeaway-CTA ≈ what_happened-why-takeaway |
| `scope_assignments` | Hardcoded constraints ignore topic complexity | "60 seconds", "7-10 slides", "3 sections" regardless of topic |
| `visual_palette` | Inconsistent visual metaphors | Carousel.visual_note and Thumbnail.visual_metaphor invented independently |
| `tone_assignments` | Tone buried in prompt rules | Newsletter "slightly more formal" is the only explicit tone guidance |
| `differentiation_strategy` | No concept exists today | All formats retell the same story from the same angle |
| `formats_planned` | Mechanical routing without intelligence | Brief.recommended_formats → FREETEXT_TO_FORMAT → FORMAT_TO_ASSET |

---

## 7. Ownership Transfer Summary

```
BEFORE (current):
┌─────────┐     ┌──────────────────────────────────────────────┐
│  Brief  │────▶│  Generator (plans + writes simultaneously)   │
└─────────┘     └──────────────────────────────────────────────┘

AFTER (with Storyboard):
┌─────────┐     ┌─────────────┐     ┌──────────────────────────┐
│  Brief  │────▶│  Storyboard │────▶│  Generator (writes only) │
└─────────┘     │  (plans)    │     └──────────────────────────┘
                └─────────────┘
```

### What Moves to Storyboard

| Concept | Moves From | Moves To |
|---------|-----------|----------|
| Hook selection | Script, Carousel, Newsletter, Thumbnail generators | `Storyboard.hook_assignments` |
| CTA content | Script, Carousel, Newsletter generators | `Storyboard.cta_assignments` |
| Claim selection | Script, Carousel, Newsletter generators | `Storyboard.claim_allocation` |
| Arc structure | Prompt rules (hardcoded) | `Storyboard.arc_assignments` |
| Scope constraints | Prompt rules (hardcoded) | `Storyboard.scope_assignments` |
| Visual concept selection | Carousel, Thumbnail generators | `Storyboard.visual_palette` |
| Style decision | Thumbnail generator (inferred) | `Storyboard.visual_palette.style` |
| Tone decision | Prompt rules (implicit) | `Storyboard.tone_assignments` |
| Format routing | CLI loop + Brief.recommended_formats | `Storyboard.formats_planned` |

### What Stays With Generators

| Concept | Stays With | Reason |
|---------|-----------|--------|
| Sentence-level writing | Script generator | Word choice, rhythm, 15-word limit |
| Slide body copywriting | Carousel generator | 30-word constraint, slide-specific phrasing |
| Section prose | Newsletter generator | 80-word limit, email register |
| Visual note detail | Carousel generator | Specific diagram/code descriptions within planned concept |
| Negative prompt specifics | Thumbnail generator | Technical image-gen avoidance |
| Readability notes | Thumbnail generator | Platform-specific layout guidance |
| Supporting text phrasing | Thumbnail generator | 10-word curiosity gap compression |

---

## 8. Generator Input Change

### Current Generator Input

```
Generator receives: Brief
Generator must: Plan + Write
```

### Future Generator Input

```
Generator receives: Brief + Storyboard
Generator must: Write only (planning already done)
```

### Per-Generator Contract

**Script Generator receives from Storyboard:**
- `hook_assignments["short_video"].hook_text` → becomes `Script.hook`
- `cta_assignments["short_video"].cta_text` → becomes `Script.cta`
- `claim_allocation["short_video"].claims` → becomes `Script.claims_used`
- `arc_assignments["short_video"].beats` → structures `Script.script_sections`
- `scope_assignments["short_video"].value` → word budget for sections
- `tone_assignments["short_video"].register` → writing style constraint

**Carousel Generator receives from Storyboard:**
- `hook_assignments["carousel"].hook_text` → becomes slide 1 content
- `cta_assignments["carousel"].cta_text` → becomes `Carousel.cta_slide`
- `claim_allocation["carousel"].claims` → becomes `Carousel.claims_used`
- `arc_assignments["carousel"].beats` → determines slide arc
- `scope_assignments["carousel"].value` → determines slide count
- `visual_palette.visual_concepts[assigned_to="carousel_*"]` → guides `visual_note` per slide

**Newsletter Generator receives from Storyboard:**
- `hook_assignments["newsletter"].hook_text` → becomes `Newsletter.subject_line`
- `cta_assignments["newsletter"].cta_text` → becomes `Newsletter.cta`
- `claim_allocation["newsletter"].claims` → becomes `Newsletter.claims_used`
- `arc_assignments["newsletter"].beats` → determines section structure
- `tone_assignments["newsletter"].register` → writing style constraint

**Thumbnail Generator receives from Storyboard:**
- `hook_assignments["thumbnail"].hook_text` → becomes `ThumbnailPrompt.title_text`
- `visual_palette.primary_metaphor` → becomes `ThumbnailPrompt.visual_metaphor`
- `visual_palette.style` → becomes `ThumbnailPrompt.style`
- `visual_palette.brand_avoidances` → seeds `ThumbnailPrompt.negative_prompt`

---

## 9. Validation Checklist

| Requirement | Status |
|-------------|--------|
| Every existing model field classified | ✓ (Section 1-2) |
| Storyboard-owned fields identified with evidence | ✓ (Section 2, 6) |
| Asset-specific fields preserved | ✓ (Section 2, 4) |
| Shared-once fields enumerated | ✓ (Section 3) |
| Never-shared fields protected | ✓ (Section 4) |
| Proposed schema grounded in existing model evidence | ✓ (Section 5-6) |
| Generator consumption contracts defined | ✓ (Section 8) |
| No code changes | ✓ |
| No new models created | ✓ |
