# TASK-041: Add LinkedIn post generator

**Phase:** 12.3 Platform-Aware Content  
**Status:** DONE  
**Priority:** HIGH  
**GitHub Issue:** #6  
**Depends On:** TASK-040  

---

## Objective

Implement a LinkedIn-specific content generator based on the platform content contract created in TASK-040.

The generator must produce LinkedIn-ready content that is not generic platform-agnostic output.

---

## Context

TASK-040 introduced the LinkedIn platform contract in:

- `docs/platform/linkedin-content-contract.md`

That contract requires LinkedIn posts to include:

- a strong hook
- a LinkedIn-ready post body
- a clear takeaway
- exactly one CTA
- 3 to 5 hashtags
- source reference preservation
- mobile-readable paragraph formatting
- no publishing behavior

Existing generation patterns are available in:

- `src/content_creation/generation/script.py`
- `src/content_creation/generation/newsletter.py`
- `src/content_creation/models/script.py`
- `src/content_creation/models/newsletter.py`
- `tests/test_generation_scaffold.py`

Follow the existing `InferenceManager` + JSON parsing + fallback behavior pattern.

---

## Required Scope

### Files to create

- `src/content_creation/models/linkedin.py`
- `src/content_creation/generation/linkedin.py`
- `prompts/linkedin_post.md`
- `tests/test_linkedin_generation.py`

### Files to modify

- `src/content_creation/models/__init__.py`
- `src/content_creation/generation/__init__.py`
- `src/content_creation/prompts/registry.py`
- `WORK_QUEUE.md`
- `docs/tasks/task_041.md`

### Files to read but not modify

- `docs/platform/linkedin-content-contract.md`
- `docs/platform/source-grounding-contract.md`
- `docs/platform/platform-quality-gates.md`
- `src/content_creation/generation/script.py`
- `src/content_creation/generation/newsletter.py`
- `src/content_creation/models/script.py`
- `src/content_creation/models/newsletter.py`
- `tests/test_generation_scaffold.py`

### Files and directories not allowed

- `.github/workflows/`
- `pyproject.toml`
- `uv.lock`
- `data/`
- `docs/tasks/task_005.md`
- `docs/platform/*.md`
- any `__pycache__/` directory
- any `.pyc` file

---

## Implementation Requirements

### 1. Add LinkedIn model

Create `src/content_creation/models/linkedin.py`.

The model should represent one LinkedIn-ready generated post.

Required fields:

- `topic_id`
- `hook`
- `post_body`
- `takeaway`
- `cta`
- `hashtags`
- `source_reference`
- `source_links`
- `claims_used`
- `review_status`
- `generated_at`

Expected constraints:

- `hashtags` must support 3 to 5 items.
- `source_links` must preserve the source URL from the brief.
- `review_status` must default to `ReviewStatus.DRAFT`.
- Use existing project typing style where possible.

Do not add publishing fields.

Do not add scheduling fields.

Do not add external API integration.

---

### 2. Add LinkedIn generator

Create `src/content_creation/generation/linkedin.py`.

The generator should follow the existing style used by `ScriptGenerator` and `NewsletterGenerator`.

Required class:

- `LinkedInPostGenerator`

Required behavior:

- accepts optional `api_key`
- accepts optional `prompt_dir` as either `Path` or `PromptRegistry`
- loads the LinkedIn prompt from registry key `("linkedin", "post")`
- supports fallback to a prompt file named `linkedin_post.md` when `prompt_dir` is a `Path`
- injects brief fields into the prompt
- calls `InferenceManager.generate`
- parses JSON response into the LinkedIn post model
- preserves `brief.source_url` in `source_links`
- preserves source reference from generated JSON when present
- falls back to `needs_review` fields when inference fails or JSON parsing fails

Required task type:

- `linkedin_post_generation`

---

### 3. Add prompt

Create `prompts/linkedin_post.md`.

Prompt must require JSON output with these keys:

- `hook`
- `post_body`
- `takeaway`
- `cta`
- `hashtags`
- `source_reference`
- `claims_used`
- `review_status`

The prompt must encode the LinkedIn contract constraints:

- max 1,800 character soft target
- max 2 hook lines
- max 3 lines per paragraph
- exactly one CTA
- 3 to 5 hashtags
- preserve source grounding
- no emoji spam
- no generic motivational content
- no publishing instructions

---

### 4. Register prompt

Update `src/content_creation/prompts/registry.py`.

Add:

    ("linkedin", "post"): "prompts/linkedin_post.md"

Do not remove or rename existing registry entries.

---

### 5. Export model and generator

Update `src/content_creation/models/__init__.py`.

Export:

- `LinkedInPost`

Update `src/content_creation/generation/__init__.py`.

Export:

- `LinkedInPostGenerator`

---

### 6. Add focused tests

Create `tests/test_linkedin_generation.py`.

Required tests:

1. successful LinkedIn post generation from valid JSON
2. malformed JSON falls back to `needs_review`
3. missing optional/generated fields are handled safely
4. source URL from the brief is preserved in `source_links`
5. generated source reference is preserved
6. hashtag count follows 3 to 5 item contract
7. prompt registry resolves `("linkedin", "post")`

Tests must mock `InferenceManager`.

Do not make real LLM calls.

Do not require external network access.

---

## Acceptance Criteria

- LinkedIn output is platform-specific, not generic content.
- Output includes hook, post body, takeaway, CTA, hashtags, and source reference.
- Source grounding is preserved.
- The generator does not implement publishing.
- Tests cover valid output, malformed JSON fallback, missing optional fields, and source-reference preservation.
- Existing tests continue passing.
- No unrelated files are modified.

---

## Validation Commands

Run targeted tests:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest tests/test_linkedin_generation.py -q

Run full tests:

    export UV_CACHE_DIR=/tmp/uv-cache
    uv run python -m pytest --tb=short -q

Run scope check:

    git diff --name-only

Expected changed files only:

    WORK_QUEUE.md
    docs/tasks/task_041.md
    prompts/linkedin_post.md
    src/content_creation/generation/__init__.py
    src/content_creation/generation/linkedin.py
    src/content_creation/models/__init__.py
    src/content_creation/models/linkedin.py
    src/content_creation/prompts/registry.py
    tests/test_linkedin_generation.py

---

## Success Criteria

- [x] `LinkedInPost` model exists.
- [x] `LinkedInPostGenerator` exists.
- [x] LinkedIn prompt exists.
- [x] Prompt registry includes `("linkedin", "post")`.
- [x] Model and generator are exported.
- [x] Focused LinkedIn generation tests pass.
- [x] Full test suite passes.
- [x] No publishing behavior is implemented.
- [x] No blocked files are modified.

---

## Commit Message

feat(platform): add LinkedIn post generator (TASK-041)
