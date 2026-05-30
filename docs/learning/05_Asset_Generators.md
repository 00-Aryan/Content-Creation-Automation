# Chapter 5 — Asset Generators: One Brief, Four Formats

## The Question

Why are there four separate generator classes instead of one generator with a format parameter? Why classes instead of functions?

Because each format has fundamentally different structural requirements. A carousel needs nested slides with visual notes. A newsletter needs named sections with Literal types. A thumbnail needs a constrained style vocabulary. A single generator would need format-specific branching everywhere, making it untestable and unmaintainable. Classes exist because each generator holds a Gemini client instance — initializing it once per generator avoids repeated API key validation and connection setup.

## The Answer

Each generator (`ScriptGenerator`, `CarouselGenerator`, `NewsletterGenerator`, `ThumbnailGenerator`) follows the same pattern: read a format-specific prompt template, fill placeholders from the Brief's fields, call Gemini, parse the JSON response into the format's Pydantic model, and return a fallback on failure. The brief's `recommended_formats` field determines which generators run for each topic.

## Files in This Stage

### generation/script.py
**Why it exists:** Generates video scripts from briefs using format-specific prompts.
**What it does:** `ScriptGenerator` holds a client and a dict mapping format names to prompt file paths. The `generate()` method validates the format, reads the template, replaces all `{{ brief.* }}` placeholders (including converting `plain_english_summary` to bullet points), calls Gemini, and parses into a `Script` model. Forces `source_links` to always contain `brief.source_url` regardless of what the LLM returns.
**Key decision:** `source_links` is overridden from the LLM response — the model might hallucinate URLs, so the code forces traceability by always using the brief's verified source_url.
**Connects to:** Receives Brief → stores Script in data/scripts/{topic_id}.json.

### generation/carousel.py
**Why it exists:** Carousels need nested slide parsing that scripts don't.
**What it does:** `CarouselGenerator` follows the same pattern but additionally parses a `slides` array from the JSON response into `CarouselSlide` objects. Each slide has `slide_number`, `title`, `body`, and `visual_note`.
**Key decision:** Slides are popped from the response dict and constructed separately — this isolates slide validation from the top-level carousel validation, giving clearer error messages when one slide is malformed.
**Connects to:** Receives Brief → stores Carousel in data/carousels/{topic_id}.json.

### generation/newsletter.py
**Why it exists:** Newsletters have named sections with Literal-typed names.
**What it does:** `NewsletterGenerator` parses `sections` from the response into `NewsletterSection` objects where `section_name` must be one of `"what_happened" | "why_it_matters" | "student_takeaway"`. Also replaces `{{ brief.recommended_formats }}` as a bullet list.
**Key decision:** Section names are Literal types — if the LLM invents a section name like `"conclusion"`, Pydantic rejects it immediately rather than producing a newsletter with unexpected structure.
**Connects to:** Receives Brief → stores Newsletter in data/newsletters/{topic_id}.json.

### generation/thumbnail.py
**Why it exists:** Thumbnail prompts need constrained visual vocabulary, not free-form text.
**What it does:** `ThumbnailGenerator` produces a `ThumbnailPrompt` with `style` constrained to 4 Literal options, a `negative_prompt` list (what to avoid), and `readability_notes`. No nested structures — simpler than carousel/newsletter.
**Key decision:** `negative_prompt` as a list — this gives explicit anti-patterns (e.g., "no neon brains", "no circuit boards") that align with the voice-and-style guide's banned visual patterns.
**Connects to:** Receives Brief → stores ThumbnailPrompt in data/thumbnails/{topic_id}.json.

## Data Flow

```
data/briefs/{topic_id}.json (Brief)
    ↓
brief.recommended_formats → ["short_video", "carousel", "newsletter"]
    ↓
ScriptGenerator.generate(brief, "short_video")
    ↓ prompts/short_video.md → Gemini → Script
CarouselGenerator.generate(brief)
    ↓ prompts/carousel.md → Gemini → Carousel
NewsletterGenerator.generate(brief)
    ↓ prompts/newsletter.md → Gemini → Newsletter
ThumbnailGenerator.generate(brief)  ← always runs
    ↓ prompts/thumbnail.md → Gemini → ThumbnailPrompt
    ↓
data/scripts/{topic_id}.json
data/carousels/{topic_id}.json
data/newsletters/{topic_id}.json
data/thumbnails/{topic_id}.json
```

## Why Not the Alternative?

**Why not one generator with a format parameter?** Because the output models are structurally different. A `Script` has `hook` + `script_sections` + `cta`. A `Carousel` has `slides: List[CarouselSlide]`. A `Newsletter` has `sections: List[NewsletterSection]`. A single generator would need `if format == "carousel": parse_slides()` branching everywhere, mixing concerns and making each format's logic harder to test in isolation.

## Key Insight

**Each generator is a pure function from Brief to validated asset — same input pattern, same retry logic, same fallback strategy, but structurally different outputs that each enforce their format's constraints.**
