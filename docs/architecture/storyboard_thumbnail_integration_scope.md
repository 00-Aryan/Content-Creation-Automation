# Storyboard → Thumbnail Integration Scope

> Phase: Pre-Integration Analysis  
> Date: 2026-05-31  
> Status: Design Only — No Implementation  
> Depends on: Storyboard Domain v1 (implemented)

---

## 1. Current Thumbnail Flow

```
Brief ──▶ ThumbnailGenerator ──▶ LLM ──▶ ThumbnailPrompt
```

**Input:** Brief (7 fields injected into prompt)  
**Processing:** Single LLM call invents all 6 content fields  
**Output:** ThumbnailPrompt (8 fields total)

The LLM currently performs three distinct tasks in one call:
1. **Invents** `title_text` (a hook compressed to 6 words)
2. **Infers** `style` (from topic type, which it must guess from Brief text)
3. **Invents** `visual_metaphor` (from Brief.analogy or its own imagination)
4. **Invents** `supporting_text`, `negative_prompt`, `readability_notes`

---

## 2. Field Ownership Matrix

| ThumbnailPrompt Field | Current Source | Storyboard Equivalent | Overlap? |
|----------------------|---------------|----------------------|:---:|
| `title_text` | LLM invents from Brief | `Storyboard.thumbnail_hook` | ✓ Direct |
| `style` | LLM infers from Brief text | `Storyboard.visual_style` | ✓ Direct |
| `visual_metaphor` | LLM invents from Brief.analogy | `Storyboard.visual_metaphor` | ✓ Direct |
| `supporting_text` | LLM invents | — | ✗ |
| `negative_prompt` | LLM invents (4 baseline + topic-specific) | — | ✗ |
| `readability_notes` | LLM invents | — | ✗ |
| `topic_id` | Brief pass-through | — | — (identity) |
| `review_status` | LLM / pipeline | — | — (state) |
| `generated_at` | Pipeline timestamp | — | — (metadata) |

**Summary:** 3 of 6 content fields have direct Storyboard equivalents. 3 remain Thumbnail-owned.

---

## 3. Integration Design

### Minimal Change: Inject 3 Storyboard Fields as Constraints

Instead of the LLM inventing `title_text`, `style`, and `visual_metaphor`, the Thumbnail prompt receives them as **pre-decided constraints** from Storyboard.

**Before (legacy mode):**
```
Prompt says: "Choose style based on topic type..."
LLM decides: style = "diagram_overlay"
```

**After (Storyboard mode):**
```
Prompt says: "Use this exact style: diagram_overlay"
LLM accepts: style = "diagram_overlay"
```

### What Changes in the Generator

```python
# Current signature
def generate(self, brief: Brief) -> ThumbnailPrompt:

# New signature (backward compatible)
def generate(self, brief: Brief, storyboard: Optional[Storyboard] = None) -> ThumbnailPrompt:
```

When `storyboard` is provided:
- `title_text` ← `storyboard.thumbnail_hook` (injected as constraint)
- `style` ← `storyboard.visual_style` (injected as constraint)
- `visual_metaphor` ← `storyboard.visual_metaphor` (injected as constraint)
- LLM still generates: `supporting_text`, `negative_prompt`, `readability_notes`

When `storyboard` is None:
- Existing behavior unchanged (full LLM generation)

---

## 4. Compatibility Plan

### Dual-Mode Operation

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Legacy** | `storyboard=None` | Current behavior — LLM invents all 6 fields |
| **Storyboard** | `storyboard` provided | 3 fields pre-decided, LLM generates remaining 3 |

### Why Dual-Mode Is Safe

1. **Optional parameter** — No existing call site breaks
2. **Same output schema** — `ThumbnailPrompt` model unchanged
3. **Same LLM call** — Still one inference call (just with more constraints in prompt)
4. **Same fallback** — On LLM failure, returns `needs_review` object regardless of mode

### Prompt Strategy

Two options:

**Option A: Single prompt with conditional sections**
- Add optional `# Storyboard Constraints` section to existing prompt
- When Storyboard present, inject: "Use these exact values: title_text=X, style=Y, visual_metaphor=Z"
- When absent, existing rules apply

**Option B: Separate prompt file**
- `prompts/thumbnail.md` (legacy)
- `prompts/thumbnail_storyboard.md` (Storyboard mode)

**Recommendation: Option A** — Less duplication, single prompt to maintain, conditional injection is simple string replacement.

---

## 5. Testing Impact

### Existing Tests (4 tests in test_generation_scaffold.py)

| Test | Impact |
|------|--------|
| `test_generate_thumbnail_success` | ✓ Unchanged — tests legacy mode (no storyboard param) |
| `test_generate_thumbnail_malformed_json_fallback` | ✓ Unchanged |
| `test_generate_thumbnail_429_retry` | ✓ Unchanged |
| `test_generate_thumbnail_negative_prompt_as_list` | ✓ Unchanged |

**All 4 existing tests continue to pass unchanged** because they don't pass a `storyboard` argument.

### New Tests Required

| Test | Purpose |
|------|---------|
| `test_thumbnail_with_storyboard_uses_hook` | Verify `title_text` comes from `storyboard.thumbnail_hook` |
| `test_thumbnail_with_storyboard_uses_style` | Verify `style` comes from `storyboard.visual_style` |
| `test_thumbnail_with_storyboard_uses_metaphor` | Verify `visual_metaphor` comes from `storyboard.visual_metaphor` |
| `test_thumbnail_without_storyboard_unchanged` | Verify legacy behavior preserved |
| `test_thumbnail_storyboard_fallback_on_failure` | Verify fallback still works in Storyboard mode |

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| Existing tests break | Very Low | Medium | Optional param — no call site changes |
| Thumbnail quality degrades with Storyboard constraints | Low | Medium | LLM still generates supporting_text, negative_prompt, readability_notes freely |
| Storyboard.thumbnail_hook exceeds 6 words | Medium | Low | Thumbnail prompt still says "max 6 words" — LLM may truncate or use as-is |
| Storyboard.visual_metaphor is too long for thumbnail | Low | Low | Thumbnail prompt can instruct "use this metaphor concept, adapt for thumbnail" |
| CLI integration requires changes | Medium | Low | CLI passes `storyboard=None` until pipeline is wired |
| Prompt becomes complex with conditionals | Low | Low | Only 3 lines of conditional injection |

### Rollback Path

If integration causes quality issues:
1. Remove `storyboard` parameter from CLI call sites (1-2 lines)
2. Generator reverts to legacy mode automatically (`storyboard=None`)
3. No schema changes to undo
4. No prompt file changes needed (conditional section simply unused)

**Rollback cost: ~2 minutes.**

---

## 7. Go/No-Go Recommendation

### Verdict: GO

| Criterion | Status |
|-----------|--------|
| Storyboard provides all 3 needed fields | ✓ |
| Backward compatibility preserved | ✓ (Optional param) |
| Existing tests unaffected | ✓ |
| Output schema unchanged | ✓ |
| Rollback path exists | ✓ (Remove param from call site) |
| Risk level | Low |
| Implementation size | Small (~20 lines generator change + prompt addition) |

### Implementation Checklist

1. Add `storyboard: Optional[Storyboard] = None` to `ThumbnailGenerator.generate()`
2. When storyboard present, inject 3 constraint lines into prompt
3. When storyboard present, override `title_text`, `style`, `visual_metaphor` in output with storyboard values (don't trust LLM to follow constraints perfectly)
4. Add 5 new tests
5. Verify all 4 existing tests still pass
6. Do NOT wire into CLI yet (that's a separate pipeline integration step)

### Key Design Decision

**Override in code, not just in prompt.** Even though the prompt will say "use this exact style," the generator should set `style = storyboard.visual_style` in the output construction — not rely on the LLM echoing it back correctly. This makes the integration deterministic for the 3 Storyboard-owned fields.
