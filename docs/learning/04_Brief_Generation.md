# Chapter 4 — Brief Generation: Grounded Summarization

## The Question

Why do briefs exist as an intermediate step? Why not generate scripts directly from the raw topic text?

Because raw text is noisy, variable-length, and unstructured. A 15,000-character arXiv abstract contains information that's irrelevant to a 60-second video. The brief is the *editorial decision layer* — it extracts exactly what matters for students, in a fixed structure that all downstream generators can rely on. Without it, every generator would independently interpret raw text, producing inconsistent framing across formats.

## The Answer

Brief generation takes a `ScoredTopicItem`, fills a prompt template with its fields, sends it to Gemini API, and parses the structured JSON response into a validated `Brief` model. The brief contains exactly the fields that the voice-and-style guide requires: `why_it_matters`, `plain_english_summary` (3 items), `student_takeaway`, `analogy`, `limitation`, `audience_fit`, and `recommended_formats`. If the API fails after retries, a fallback brief with `"needs_review"` placeholders is created — the pipeline never stops.

## Files in This Stage

### generation/brief.py
**Why it exists:** Wraps the Gemini API call with retry logic, input truncation, and fallback handling.
**What it does:** `generate_brief()` reads a prompt template from `prompts/summarize.md`, replaces `{{ topic.title }}`, `{{ topic.raw_text }}` etc. with actual values (truncated to 15k chars), calls Gemini, strips markdown fences from the response, parses JSON, and constructs a validated `Brief`. On 429 (rate limit), it retries with exponential backoff (15s, 30s, 60s). On any other failure, it returns a fallback brief.
**Key decision:** The fallback returns a valid `Brief` with `review_status=NEEDS_REVIEW` rather than raising an exception — this means the pipeline can process 10 topics and gracefully degrade on 2 failures without losing the other 8.
**Connects to:** Receives ScoredTopicItem from storage → sends Brief to storage.save_brief().

### prompts/summarize.md (referenced, not in src/)
**Why it exists:** Separates prompt engineering from Python code.
**What it does:** Contains the system prompt with placeholder syntax (`{{ topic.title }}`) that gets string-replaced before sending to the API. This means prompt iteration doesn't require code changes or re-testing Python logic.
**Key decision:** Prompts are markdown files, not Python strings — this makes them editable by non-developers and version-controllable independently of code changes.
**Connects to:** Read by generate_brief() → filled with topic data → sent to Gemini.

## Data Flow

```
data/scored/{id}.json (ScoredTopicItem)
    ↓
generate_brief(item, prompt_path, api_key)
    ↓
Read prompts/summarize.md template
    ↓
Replace {{ topic.title }}, {{ topic.raw_text[:15000] }}, etc.
    ↓
Gemini API call (gemini-2.5-flash)
    ↓ (retry on 429: 15s → 30s → 60s)
Strip ```json fences → json.loads()
    ↓
Brief(
    topic_id, why_it_matters, plain_english_summary[3],
    student_takeaway, analogy, limitation,
    audience_fit, recommended_formats,
    source_url, review_status="draft"
)
    ↓
data/briefs/{topic_id}.json
```

## Why Not the Alternative?

**Why not generate scripts directly from raw text?** Because then every format (video, carousel, newsletter) would independently interpret the same raw text, likely producing contradictory framings. The brief is the single editorial interpretation — all generators read the same `why_it_matters`, the same `analogy`, the same `limitation`. This guarantees that your video and your carousel tell the same story, just in different shapes.

## Key Insight

**The brief is not a summary — it's an editorial contract that guarantees all downstream formats share the same grounded interpretation of the source material.**
