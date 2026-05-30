# Prompt & Generation Audit

> Generated: 2026-05-30  
> Scope: All 5 generation prompts and their corresponding generators

---

## Summary Table

| # | Artifact | Prompt File | Prompt Lines | ~Tokens | Input Vars | Schema Fields | Examples | Few-Shot | Validation | Quality Criteria |
|---|----------|-------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Brief | `prompts/summarize.md` | 30 | ~350 | 4 | 8 | ✗ | ✗ | ✓ | ✓ |
| 2 | Script | `prompts/short_video.md` | 40 | ~450 | 8 | 5 | ✗ | ✗ | ✓ | ✓ |
| 3 | Carousel | `prompts/carousel.md` | 42 | ~470 | 8 | 4 (nested) | ✗ | ✗ | ✓ | ✓ |
| 4 | Newsletter | `prompts/newsletter.md` | 40 | ~430 | 9 | 4 (nested) | ✗ | ✗ | ✓ | ✓ |
| 5 | Thumbnail | `prompts/thumbnail.md` | 50 | ~550 | 8 | 7 | ✓ (inline) | ✗ | ✓ | ✓ |

---

## 1. Brief

| Question | Answer |
|----------|--------|
| **Prompt file** | `prompts/summarize.md` |
| **Prompt length** | ~30 lines |
| **Approx token count** | ~350 tokens |
| **Input variables** | `topic.title`, `topic.source`, `topic.url`, `topic.raw_text` |
| **Output schema size** | 8 fields (`why_it_matters`, `plain_english_summary`, `student_takeaway`, `analogy`, `limitation`, `audience_fit`, `recommended_formats`, `review_status`) |
| **Examples exist** | No |
| **Few-shot examples** | No |
| **Validation exists** | Yes — Pydantic `field_validator` enforces `plain_english_summary` has exactly 3 items; `ReviewStatus` enum constraint; `recommended_formats` restricted to `["short_video", "carousel", "newsletter"]` in prompt |
| **Quality criteria** | Yes — grounding rule (use ONLY provided raw_text), missing data → `"needs_review"`, no inference allowed |
| **Biggest weakness** | No few-shot example of a good brief. The model has no reference for tone, length, or depth calibration. The `raw_text` is truncated to 15k chars in the generator but the prompt doesn't communicate this limit to the model, risking mid-sentence cutoffs being treated as complete input. |

**Generator:** `src/content_creation/generation/brief.py`  
- Style: Functional (`generate_brief()`)
- Lines: ~65
- Template rendering: Manual `str.replace`
- Fallback: Returns a fully `"needs_review"` Brief object on any failure

---

## 2. Script

| Question | Answer |
|----------|--------|
| **Prompt file** | `prompts/short_video.md` |
| **Prompt length** | ~40 lines |
| **Approx token count** | ~450 tokens |
| **Input variables** | `brief.topic_id`, `brief.why_it_matters`, `brief.plain_english_summary`, `brief.student_takeaway`, `brief.analogy`, `brief.limitation`, `brief.audience_fit`, `brief.source_url` |
| **Output schema size** | 5 fields (`hook`, `script_sections`, `cta`, `claims_used`, `review_status`) |
| **Examples exist** | No |
| **Few-shot examples** | No |
| **Validation exists** | Yes — Pydantic `Literal["short_video", "carousel", "newsletter"]` on `format`; `ReviewStatus` enum; generator validates format before calling API |
| **Quality criteria** | Yes — H-C-E-P-C structure, max 60s speaking time, max 15 words/sentence, F/C/K labeling rule, anti-clickbait hook/CTA rules, claims traceability |
| **Biggest weakness** | The F/C/K labeling rule ("no three consecutive same labels") is an internal constraint the model must self-enforce with zero examples. Without a demonstrated output, compliance is unreliable. Also, the prompt says "max 60 seconds speaking time" but provides no word-count proxy, making enforcement ambiguous. |

**Generator:** `src/content_creation/generation/script.py`  
- Style: Class-based (`ScriptGenerator`)
- Lines: ~100
- Template rendering: Manual `str.replace`
- Fallback: Returns a fully `"needs_review"` Script object on any failure
- Note: `ScriptGenerator` loads prompts for all 3 formats but only `short_video.md` is used for script generation; the others are loaded but never called via this class

---

## 3. Carousel

| Question | Answer |
|----------|--------|
| **Prompt file** | `prompts/carousel.md` |
| **Prompt length** | ~42 lines |
| **Approx token count** | ~470 tokens |
| **Input variables** | `brief.topic_id`, `brief.why_it_matters`, `brief.plain_english_summary`, `brief.student_takeaway`, `brief.analogy`, `brief.limitation`, `brief.audience_fit`, `brief.source_url` |
| **Output schema size** | 4 fields top-level (`slides[]`, `cta_slide`, `claims_used`, `review_status`) + nested `CarouselSlide` with 4 fields (`slide_number`, `title`, `body`, `visual_note`) |
| **Examples exist** | No |
| **Few-shot examples** | No |
| **Validation exists** | Yes — Pydantic enforces `CarouselSlide` structure; `ReviewStatus` enum; prompt specifies 7-10 slides |
| **Quality criteria** | Yes — slide arc structure (Hook → Context → Teaching → Example → Takeaway → CTA), title max 6 words, body max 30 words, visual_note must describe one clear visual, claims traceability |
| **Biggest weakness** | No validation that slide count is 7-10 in the Pydantic model — the prompt requests it but the model accepts any `List[CarouselSlide]`. A single-slide fallback object passes validation, meaning the "7-10 slides" constraint is prompt-only and unenforced at the schema level. |

**Generator:** `src/content_creation/generation/carousel.py`  
- Style: Class-based (`CarouselGenerator`)
- Lines: ~95
- Template rendering: Manual `str.replace`
- Fallback: Returns a single-slide `"needs_review"` Carousel object on any failure

---

## 4. Newsletter

| Question | Answer |
|----------|--------|
| **Prompt file** | `prompts/newsletter.md` |
| **Prompt length** | ~40 lines |
| **Approx token count** | ~430 tokens |
| **Input variables** | `brief.topic_id`, `brief.why_it_matters`, `brief.plain_english_summary`, `brief.student_takeaway`, `brief.analogy`, `brief.limitation`, `brief.audience_fit`, `brief.source_url`, `brief.recommended_formats` |
| **Output schema size** | 4 fields top-level (`subject_line`, `sections[]`, `cta`, `claims_used`, `review_status`) + nested `NewsletterSection` with 2 fields (`section_name`, `content`) |
| **Examples exist** | No |
| **Few-shot examples** | No |
| **Validation exists** | Yes — Pydantic `Literal["what_happened", "why_it_matters", "student_takeaway"]` on `section_name`; `ReviewStatus` enum; prompt specifies exactly 3 sections |
| **Quality criteria** | Yes — subject_line max 60 chars, section content max 80 words, tone guidance ("slightly more formal"), claims traceability, no clickbait |
| **Biggest weakness** | The `recommended_formats` input variable is injected but never meaningfully used by the prompt's rules — it's context without instruction. Also, the 80-word section limit and 60-char subject line are prompt-only constraints with no Pydantic enforcement (no `max_length` or word-count validators). |

**Generator:** `src/content_creation/generation/newsletter.py`  
- Style: Class-based (`NewsletterGenerator`)
- Lines: ~105
- Template rendering: Manual `str.replace`
- Fallback: Returns a 3-section `"needs_review"` Newsletter object on any failure
- Note: Only generator that injects `brief.recommended_formats`

---

## 5. Thumbnail

| Question | Answer |
|----------|--------|
| **Prompt file** | `prompts/thumbnail.md` |
| **Prompt length** | ~50 lines |
| **Approx token count** | ~550 tokens |
| **Input variables** | `brief.topic_id`, `brief.why_it_matters`, `brief.plain_english_summary`, `brief.student_takeaway`, `brief.analogy`, `brief.limitation`, `brief.audience_fit`, `brief.source_url` |
| **Output schema size** | 7 fields (`title_text`, `supporting_text`, `visual_metaphor`, `style`, `negative_prompt`, `readability_notes`, `review_status`) |
| **Examples exist** | Yes — inline good/bad examples for `title_text`, `supporting_text`, `visual_metaphor`, and `negative_prompt` |
| **Few-shot examples** | No (examples are rule-level, not full input→output pairs) |
| **Validation exists** | Yes — Pydantic `Literal["clean_minimal", "bold_typographic", "diagram_overlay", "metaphor_illustration"]` on `style`; `ReviewStatus` enum |
| **Quality criteria** | Yes — title max 6 words (insight not topic name), supporting max 10 words, concrete visual metaphor, style selection logic based on topic type, mandatory baseline negative prompts, readability guidance |
| **Biggest weakness** | The style selection logic ("Papers → diagram_overlay, Tools → bold_typographic, Concepts → metaphor_illustration") requires the model to classify the topic type from brief fields, but no `topic_type` field exists in the input. The model must infer classification from unstructured text, making style selection non-deterministic. |

**Generator:** `src/content_creation/generation/thumbnail.py`  
- Style: Class-based (`ThumbnailGenerator`)
- Lines: ~85
- Template rendering: Manual `str.replace`
- Fallback: Returns a `"needs_review"` ThumbnailPrompt with `style="clean_minimal"` and single-item `negative_prompt`

---

## Cross-Cutting Observations

### Strengths

1. **Consistent grounding rules** — Every prompt enforces "use ONLY provided fields" and degrades gracefully to `"needs_review"` when data is weak.
2. **Claims traceability** — All asset prompts (script, carousel, newsletter) require `claims_used` with source field attribution.
3. **Fallback objects** — Every generator returns a valid (but flagged) object on failure, preventing pipeline crashes.
4. **ReviewStatus state machine** — Consistent `draft`/`needs_review` binary across all artifacts.
5. **Pydantic schema enforcement** — Type-level constraints (Literal types, required fields) catch structural errors post-generation.

### Weaknesses (Systemic)

| # | Issue | Impact | Affected |
|---|-------|--------|----------|
| 1 | **Zero few-shot examples** | Model has no calibration reference for output quality, length, or tone | All 5 |
| 2 | **Manual `str.replace` templating** | No escaping, no conditional logic, breaks if field values contain template syntax | All 5 |
| 3 | **Prompt-only constraints unenforced in schema** | Word limits, slide counts, character limits exist only in prompt text — Pydantic doesn't validate them | Script, Carousel, Newsletter, Thumbnail |
| 4 | **No retry or structured output mode** | Single `json.loads` attempt; no JSON repair, no retry on malformed output | All 5 |
| 5 | **No token budget awareness** | Prompts don't state output length expectations; generators don't set `max_tokens` | All 5 |
| 6 | **Fallback objects pass validation** | A single-slide carousel or 1-item `negative_prompt` is schema-valid but content-invalid | Carousel, Thumbnail |

### Recommendations (No Code Changes)

1. Add 1-2 few-shot input→output examples to each prompt file (highest ROI improvement).
2. Consider Jinja2 or a proper template engine to replace `str.replace` (handles escaping, conditionals).
3. Add Pydantic validators for prompt-stated constraints (slide count 7-10, word limits, char limits).
4. Implement structured output / JSON mode at the inference layer to reduce parse failures.
5. Add a `topic_type` field to Brief so thumbnail style selection becomes deterministic.
6. Document expected token budgets per prompt and configure `max_tokens` in InferenceManager calls.
