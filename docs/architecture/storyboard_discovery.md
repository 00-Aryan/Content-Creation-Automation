# Storyboard Discovery

> Phase: D.2 — Architecture & Discovery  
> Status: Analysis Only — No Implementation  
> Date: 2026-05-30  
> Depends on: D.1 Prompt & Generation Audit, D.2 Content Intelligence Blueprint

---

## Purpose

This document identifies **planning-level decisions** currently embedded inside individual generators that should instead belong to a dedicated Storyboard layer. The Storyboard would sit between Content Intelligence and generators, coordinating cross-format decisions before any asset is written.

---

## 1. Script — Storyboard-Level Concerns

### Currently in Script Prompt/Schema

| Concern | Where It Lives | Why It's Storyboard |
|---------|---------------|---------------------|
| **H-C-E-P-C structure** (Hook → Context → Explanation → Practical Relevance → CTA) | Prompt rule #1 | Narrative arc selection is a **planning** decision. Different topics may warrant different structures (e.g., Problem → Solution → Proof, or Myth → Reality → Implication). Hardcoding one arc removes creative flexibility. |
| **Hook generation** | Prompt rule #5, Schema `hook` field | The hook is the single most important engagement decision. It should be chosen **once** at the planning level and coordinated across formats — not independently invented by each generator. |
| **F/C/K pacing strategy** | Prompt rule #3 | Sentence-level labeling (Fact/Consequence/Contrast) is a **pacing plan**. The decision of where contrast appears in the narrative is structural, not generative. |
| **CTA selection** | Prompt rule #6, Schema `cta` field | CTAs should be coordinated across formats. A script CTA saying "check the carousel for the visual breakdown" requires knowing the carousel exists — that's cross-format planning. |
| **60-second time constraint** | Prompt rule #2 | Duration is a **scope decision**. Some topics warrant 30s, others 90s. This should be decided at planning time based on topic complexity, not hardcoded. |
| **claims_used** | Schema field | Claim allocation — which facts go in which format — is a planning decision. Currently each generator independently selects claims, risking duplication or omission. |

### What Should Remain in Script Generator

- Sentence-level writing (word choice, rhythm)
- Formatting the hook into natural speech
- Applying voice-and-style constraints
- JSON output structure

---

## 2. Carousel — Storyboard-Level Concerns

### Currently in Carousel Prompt/Schema

| Concern | Where It Lives | Why It's Storyboard |
|---------|---------------|---------------------|
| **Slide arc** (Hook → Context → Teaching → Example → Takeaway → CTA) | Prompt rule #1 | This is a **narrative structure** decision identical in nature to Script's H-C-E-P-C. The arc should be planned, not hardcoded. |
| **Slide count** (7-10) | Prompt rule #1 | Scope decision. A simple concept needs 5 slides; a complex comparison needs 12. Should be determined by topic complexity at planning time. |
| **Hook on slide 1** | Prompt rule #1 | Same hook coordination problem as Script. Slide 1's hook should be a planned variant of the shared hook, not independently invented. |
| **visual_note per slide** | Schema `CarouselSlide.visual_note` | Visual planning across slides is a **storyboard concern**. Which slides get diagrams vs. code vs. metaphor images should be decided holistically, not per-slide in isolation. |
| **CTA slide** | Prompt rule #7, Schema `cta_slide` | Cross-format CTA coordination (same issue as Script). |
| **claims_used** | Schema field | Same claim allocation issue as Script. |
| **Teaching arc allocation** (one concept per slide) | Prompt rule #1 | Deciding which concepts go on which slides is **content planning**. The generator should receive "slide 3 covers X" not "figure out what goes where." |

### What Should Remain in Carousel Generator

- Slide title/body copywriting (word limits, phrasing)
- Visual note detail (specific diagram description)
- Formatting into slide-appropriate language
- JSON output structure

---

## 3. Thumbnail — Storyboard Consumption Opportunities

### Currently in Thumbnail That Could Consume Storyboard

| Concern | Where It Lives | What Storyboard Would Provide |
|---------|---------------|-------------------------------|
| **Style selection** | Prompt rule #4 | Storyboard decides visual identity for the content suite. Thumbnail style should match the carousel's visual language — that's a coordinated decision. |
| **title_text** (core insight in 6 words) | Prompt rule #1, Schema field | This is the **hook** compressed to thumbnail format. Storyboard already owns the hook; thumbnail just needs the shortest variant. |
| **supporting_text** (context/intrigue) | Prompt rule #2, Schema field | This is the **curiosity gap** in 10 words. Storyboard owns the curiosity gap; thumbnail receives a compressed version. |
| **visual_metaphor** | Prompt rule #3, Schema field | Should be consistent with carousel's visual language. If carousel slide 7 uses "librarian scanning books" as the analogy visual, thumbnail should use the same metaphor — not invent a different one. |
| **negative_prompt** | Prompt rule #5, Schema field | Visual avoidance is a **brand-level** decision that should be consistent across all visual assets. Storyboard enforces visual brand rules. |

### What Should Remain in Thumbnail Generator

- Specific image generation prompt engineering
- Readability/contrast technical notes
- Platform-specific sizing considerations
- JSON output structure

---

## 4. Newsletter — Storyboard-Level Concerns

### Currently in Newsletter That Belongs to Storyboard

| Concern | Where It Lives | Why It's Storyboard |
|---------|---------------|---------------------|
| **Section structure** (what_happened → why_it_matters → student_takeaway) | Prompt rule #1 | Fixed 3-section structure is a planning decision. Some topics warrant a different newsletter arc (e.g., Myth → Reality → Action). |
| **subject_line** | Prompt rule #2, Schema field | This is a **hook variant** for email. Should be coordinated with Script hook and Carousel slide 1 — different angle, same topic. |
| **CTA** | Prompt rule #7, Schema field | Cross-format CTA coordination. Newsletter CTA might say "watch the 60-second breakdown" — requires knowing the script exists. |
| **claims_used** | Schema field | Same claim allocation issue. |
| **Tone register** ("slightly more formal") | Prompt rule #4 | Tone differentiation across formats is a **planning decision**. Storyboard decides: script = conversational, newsletter = professional, carousel = punchy. |

### What Should Remain in Newsletter Generator

- Section content writing (80-word limit, phrasing)
- Email-specific formatting
- Subject line character optimization
- JSON output structure

---

## 5. Shared Planning Concepts Already Present

These concepts appear across multiple generators today, proving they are **cross-cutting planning concerns** that belong in a coordination layer:

### 5.1 Hook (appears in all 4 formats)

| Format | Field | Current Behavior |
|--------|-------|-----------------|
| Script | `hook` | Invented from Brief |
| Carousel | Slide 1 title + body | Invented from Brief |
| Newsletter | `subject_line` | Invented from Brief |
| Thumbnail | `title_text` | Invented from Brief |

**Problem:** Four independent hook inventions from the same Brief. No coordination, no differentiation strategy, potential duplication.

**Storyboard solution:** Generate 3-4 hook variants once. Assign best-fit variant to each format.

### 5.2 CTA (appears in 3 formats)

| Format | Field | Current Behavior |
|--------|-------|-----------------|
| Script | `cta` | Invented independently |
| Carousel | `cta_slide` | Invented independently |
| Newsletter | `cta` | Invented independently |

**Problem:** CTAs cannot cross-reference other formats because generators don't know what else exists. A script CTA can't say "swipe through the carousel" if it doesn't know a carousel was planned.

**Storyboard solution:** Plan CTAs that create a content ecosystem. Each format's CTA drives traffic to another format.

### 5.3 Claims Allocation (appears in all 4 formats)

| Format | Field | Current Behavior |
|--------|-------|-----------------|
| Script | `claims_used` | Selects claims independently |
| Carousel | `claims_used` | Selects claims independently |
| Newsletter | `claims_used` | Selects claims independently |
| Thumbnail | (implicit in title_text) | Selects core claim independently |

**Problem:** All formats may select the same 2-3 strongest claims, leaving weaker-but-important claims uncovered. Or they may all avoid the same claim, creating a coverage gap.

**Storyboard solution:** Allocate claims across formats. Script gets the narrative claims. Carousel gets the visual/data claims. Newsletter gets the context claims.

### 5.4 Narrative Arc (appears in 3 formats)

| Format | Structure | Current Behavior |
|--------|-----------|-----------------|
| Script | H-C-E-P-C (5 beats) | Hardcoded |
| Carousel | Hook-Context-Teaching-Example-Takeaway-CTA (6 beats) | Hardcoded |
| Newsletter | what_happened-why_it_matters-student_takeaway (3 beats) | Hardcoded |

**Problem:** All three use nearly identical arcs (hook → context → content → takeaway → CTA). No differentiation. The audience consuming all three formats gets the same story told three times.

**Storyboard solution:** Assign different narrative angles per format. Script: the "why" story. Carousel: the "how" breakdown. Newsletter: the "so what" analysis.

### 5.5 Visual Language (appears in 2 formats)

| Format | Field | Current Behavior |
|--------|-------|-----------------|
| Carousel | `visual_note` per slide | Invented per-slide |
| Thumbnail | `visual_metaphor`, `style` | Invented independently |

**Problem:** Carousel and thumbnail may use completely different visual metaphors for the same topic. Brand inconsistency.

**Storyboard solution:** Define a visual concept palette for the topic. Carousel and thumbnail draw from the same palette.

### 5.6 Format Routing (exists in CLI orchestration)

| Component | Current Behavior |
|-----------|-----------------|
| `Brief.recommended_formats` | LLM suggests formats |
| `FREETEXT_TO_FORMAT` | Maps free-text to canonical format names |
| `FORMAT_TO_ASSET` | Maps formats to generator types |
| CLI `generate-assets` loop | Iterates formats, calls generators sequentially |

**Problem:** This is already a primitive storyboard — it decides which formats to generate. But it has no intelligence. It doesn't consider: topic complexity (should this be 3 formats or 1?), audience fatigue (did we already publish a carousel yesterday?), or content differentiation (what unique angle does each format serve?).

**Storyboard solution:** Replace mechanical format routing with intelligent format planning that considers topic, audience, calendar, and differentiation.

---

## 6. Boundary Summary

### What Storyboard Owns

| Responsibility | Currently Owned By |
|---------------|-------------------|
| Hook variant selection and assignment | Each generator independently |
| Narrative arc selection per format | Hardcoded in each prompt |
| CTA coordination across formats | Each generator independently |
| Claim allocation across formats | Each generator independently |
| Visual concept palette | Carousel + Thumbnail independently |
| Scope decisions (slide count, duration, section count) | Hardcoded in each prompt |
| Format differentiation strategy | Nobody (all formats tell same story) |
| Tone register assignment per format | Hardcoded in each prompt |
| Format selection intelligence | CLI loop + Brief.recommended_formats |

### What Storyboard Does NOT Own

| Responsibility | Remains With |
|---------------|-------------|
| Factual extraction | Brief |
| Creator strategy (hooks, angles, misconceptions) | Content Intelligence |
| Sentence-level writing | Individual generators |
| Platform-specific formatting | Individual generators |
| Voice and style enforcement | voice-and-style.md + generators |
| Review status | Pipeline state machine |
| Publishing schedule | Posting planner |

---

## 7. Evidence of Missing Coordination

### Duplication Risk

Without Storyboard, the same Brief produces:
- Script hook: "Attention is all you need — but why did it replace everything?"
- Carousel slide 1: "Why did attention replace recurrence?"
- Newsletter subject: "The mechanism that replaced RNNs"
- Thumbnail title: "Why Attention Replaced Recurrence"

Four variations of the same hook. No differentiation. The audience sees the same opening four times.

### Coverage Gap Risk

Without claim allocation:
- Script uses claims A, B, C (strongest narrative claims)
- Carousel uses claims A, B, C (strongest visual claims — same ones)
- Newsletter uses claims A, B (strongest summary claims — subset)
- Claims D, E, F never appear in any format

### Inconsistency Risk

Without visual coordination:
- Carousel slide 7 visual_note: "a conveyor belt sorting packages by label"
- Thumbnail visual_metaphor: "a spotlight illuminating one word in a sentence"

Two completely different metaphors for the same topic. Brand confusion.

---

## 8. Proposed Storyboard Position in Pipeline

```
Source → Brief → Content Intelligence → Storyboard → Script
                                                    → Carousel
                                                    → Newsletter
                                                    → Thumbnail
```

### Storyboard Input

- Brief (facts)
- Content Intelligence (creator strategy: hooks, angles, visuals, audience)

### Storyboard Output (per-format instruction sets)

```yaml
Storyboard:
  topic_id: str
  
  # Cross-format decisions
  hook_assignments:
    script: str          # "Bold claim hook"
    carousel: str        # "Question hook"  
    newsletter: str      # "Timeliness hook"
    thumbnail: str       # "Compressed insight hook"
  
  cta_ecosystem:
    script: str          # "Check the carousel for the visual breakdown"
    carousel: str        # "Subscribe for the newsletter deep-dive"
    newsletter: str      # "Watch the 60-second video summary"
  
  claim_allocation:
    script: List[str]    # Claims best told as narrative
    carousel: List[str]  # Claims best shown visually
    newsletter: List[str] # Claims best analyzed in depth
  
  # Per-format plans
  script_plan:
    arc_type: str        # "contrast" | "revelation" | "problem_solution"
    duration_seconds: int
    pacing_strategy: str # Which beats get emphasis
  
  carousel_plan:
    slide_count: int
    arc_type: str
    visual_palette: List[str]  # Shared visual concepts
    concept_per_slide: List[str]
  
  newsletter_plan:
    arc_type: str
    tone_register: str
    angle: str           # How newsletter differs from script
  
  thumbnail_plan:
    style: str           # Determined by topic_type + visual palette
    primary_metaphor: str # From visual palette
    hook_variant: str    # Shortest hook form
  
  # Coordination metadata
  differentiation_strategy: str  # One sentence: how formats complement each other
  generated_at: str
  review_status: ReviewStatus
```

---

## 9. Key Insight

The current pipeline treats each format as an **independent translation** of the same Brief. The result is four parallel retellings with no coordination.

A Storyboard layer transforms this into a **content ecosystem** where each format serves a unique purpose:

| Format | Role in Ecosystem |
|--------|------------------|
| Script | The emotional hook — makes you care in 60 seconds |
| Carousel | The visual breakdown — teaches the mechanism |
| Newsletter | The analytical context — explains implications |
| Thumbnail | The curiosity trigger — makes you click |

This differentiation is impossible without a planning layer that sees all formats simultaneously.
