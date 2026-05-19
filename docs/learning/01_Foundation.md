# Chapter 1 — The Foundation: Models and Schemas

## The Question

Why do you define Pydantic models before writing any pipeline logic? What would break if you just passed dictionaries between stages?

Without frozen schemas, parallel development is impossible. If the ingestion stage outputs a dict with `"pub_date"` and the scoring stage expects `"published_at"`, you discover the mismatch at runtime — after both stages are built. Models are the contracts that let stages be developed, tested, and replaced independently.

## The Answer

Every pipeline stage has its own Pydantic model that defines exactly what data enters and leaves. `TopicItem` is the canonical input. `ScoredTopicItem` extends it with scores. `Brief` is the summarization output. `Script`, `Carousel`, `Newsletter`, and `ThumbnailPrompt` are the generation outputs. `TopicManifest` tracks state. `WeeklyCalendar` is the schedule. `DryRunReport` is the validation. `PostAnalytics` is the measurement.

Each model validates on construction — if a field is wrong type, missing, or out of range, the error surfaces immediately, not three stages later.

## Files in This Stage

### models/topic.py
**Why it exists:** Defines the canonical data contract for everything entering the pipeline.
**What it does:** Contains `TopicItem` (the base schema with id, title, url, raw_text, source, published_at, category, topic_tags, status) and `ScoredTopicItem` (extends TopicItem with priority_score and per-category scores). The `generate_id()` classmethod creates deterministic SHA256 IDs from URLs. Validators enforce ISO-8601 dates and convert None/empty to `"unknown"`.
**Key decision:** `ScoredTopicItem` inherits from `TopicItem` rather than being a separate model — this means a scored item *is* a topic item, preserving all original fields without copying.
**Connects to:** Receives raw data from collectors → sends to scoring engine → scored version sent to brief generation.

### models/brief.py
**Why it exists:** Defines the summarization contract between scoring and generation.
**What it does:** Contains `Brief` with fields that map directly to the voice-and-style guide: `why_it_matters`, `plain_english_summary` (exactly 3 items, validated), `student_takeaway`, `analogy`, `limitation`, `audience_fit`, `recommended_formats`. Also defines `ReviewStatus` enum used across all asset models.
**Key decision:** `plain_english_summary` is validated to exactly 3 items — this forces the LLM to be concise and prevents unbounded lists.
**Connects to:** Receives topic_id from ScoredTopicItem → sends to all asset generators.

### models/script.py
**Why it exists:** Defines the video script output contract.
**What it does:** Contains `Script` with `hook`, `script_sections` (list), `cta`, `claims_used`, `source_links`. The `format` field is a Literal type constraining to `"short_video" | "carousel" | "newsletter"`.
**Key decision:** `claims_used` and `source_links` enforce traceability — every claim in the script must reference its origin.
**Connects to:** Receives Brief → stored in data/scripts/ → read by manifest builder.

### models/carousel.py
**Why it exists:** Carousels need nested structure that scripts don't.
**What it does:** Defines `CarouselSlide` (slide_number, title, body, visual_note) and `Carousel` (list of slides plus cta_slide). The nested model enforces per-slide word limits and visual metadata.
**Key decision:** `visual_note` on every slide — this forces the generator to think about visual representation, not just text.
**Connects to:** Receives Brief → stored in data/carousels/ → read by manifest builder.

### models/newsletter.py
**Why it exists:** Newsletters have named sections, not numbered slides or free-form scripts.
**What it does:** Defines `NewsletterSection` with `section_name` as a Literal (`"what_happened" | "why_it_matters" | "student_takeaway"`) and `Newsletter` containing a list of these sections.
**Key decision:** Section names are Literal types, not free strings — this prevents the LLM from inventing section names and ensures consistent structure.
**Connects to:** Receives Brief → stored in data/newsletters/ → read by manifest builder.

### models/thumbnail.py
**Why it exists:** Thumbnail prompts need constrained visual vocabulary.
**What it does:** Defines `ThumbnailPrompt` with `style` as a Literal of 4 options (`clean_minimal`, `bold_typographic`, `diagram_overlay`, `metaphor_illustration`), plus `negative_prompt` list and `readability_notes`.
**Key decision:** `style` is a closed enum, not a free string — this prevents the LLM from generating unbounded visual styles that can't be consistently produced.
**Connects to:** Receives Brief → stored in data/thumbnails/ → read by manifest builder.

### models/manifest.py, calendar.py, analytics.py, dryrun.py
**Why they exist:** Each downstream stage (tracking, scheduling, validation, measurement) has its own frozen contract.
**What they do:** `TopicManifest` aggregates asset statuses. `WeeklyCalendar` holds scheduled posts. `DryRunReport` holds validation checks. `PostAnalytics` holds performance data.
**Key decision:** Each model is independent — the planner doesn't need to know about analytics fields, and the dry-run doesn't need to know about scoring weights.
**Connects to:** Each feeds the next stage in sequence: manifest → planner → dry-run → analytics.

## Data Flow

```
Python dict (from collector or API)
    ↓
Pydantic model constructor (validates types, ranges, enums)
    ↓
Valid model instance (or ValidationError raised immediately)
    ↓
.model_dump_json() → JSON file in data/{stage}/
    ↓
Next stage loads JSON → Pydantic model constructor (re-validates)
```

## Why Not the Alternative?

**Why not just use dictionaries?** Dictionaries don't fail on construction — they fail when you access a missing key three stages later. With Pydantic, if the brief generator returns `"summry"` instead of `"plain_english_summary"`, the error is immediate and the message is clear. Dictionaries also can't enforce value ranges (`priority_score` must be 0-100), list lengths (exactly 3 summary items), or enum membership (status must be one of 5 values).

## Key Insight

**Models are not data containers — they are executable contracts that make invalid pipeline states unrepresentable.**
