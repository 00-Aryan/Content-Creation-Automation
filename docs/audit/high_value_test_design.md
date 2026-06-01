# High-Value Test Design Specifications

**Tests:** T-01, T-02, T-03  
**Date:** 2026-06-01  
**Role:** Senior Test Architect  
**Principle:** Exercise real infrastructure. Mock only at the boundary where real I/O would occur.

---

## Over-Mocking Anti-Pattern — Ground Rules

The existing test suite mocks `InferenceManager` at the class level (`patch("...InferenceManager")`). This means the manager's constructor, `generate()`, `_execute_with()`, `RetryManager`, `HealthTracker`, and `InferenceCache` never run. These tests verify that *callers pass the right arguments to a mock*, not that the infrastructure works.

The three tests below must **not** repeat this pattern. The rule for each test:

> Mock only the thing that makes a real network call or reads a real API key. Everything else runs as written.

---

## T-01 — `RetryManager.execute`

### 1. Behavior Under Test

`RetryManager.execute(fn)` runs `fn()` in a loop up to `policy.max_retries` times. On each call:

- If `fn()` returns `success=True` → return immediately, set `result.retries` to attempts used, set `result.duration_seconds`.
- If `fn()` returns `success=False` and `provider_error.retryable=False` → return immediately without sleeping.
- If `fn()` returns `success=False` and `provider_error.retryable=True` and retries remain → call `time.sleep(delay)`, then retry.
- If all `max_retries` attempts are exhausted → return a new `InferenceResult` with `success=False`, `error="Max retries exhausted (...)"`, `retries=state.retries_used`.

The loop index runs `for attempt in range(max_retries)`. The sleep only happens when `attempt < max_retries - 1`, meaning the last attempt does **not** sleep before the exhaustion return. This is a subtle correctness point.

Backoff formula: `base_delay * (backoff_factor ** attempt)`. With defaults (`base_delay=15.0`, `backoff_factor=2.0`): attempt 0 → 15s, attempt 1 → 30s, attempt 2 → 60s.

### 2. Dependencies That MUST Be Mocked

| Dependency | Why |
|---|---|
| `time.sleep` | Tests would take minutes with real delays. Patch it to a no-op and assert it was called with the correct delay value. |

### 3. Dependencies That Must NOT Be Mocked

| Dependency | Why |
|---|---|
| `RetryManager` | The entire class under test. Must be instantiated with a real `RetryPolicy`. |
| `RetryPolicy` | Plain dataclass. Use real instances with small `base_delay` (e.g. `0.0`) to avoid needing to mock sleep in some cases. |
| `RetryState` | Internal state tracking. Must run to verify `retries_used` is correct. |
| `InferenceResult` | Plain dataclass. Construct real instances as return values from the mock callable. |
| `ProviderError` | Plain dataclass. Construct real instances to control `retryable` flag. |
| The callable `fn` | Use a plain Python function or `MagicMock` with `side_effect` list — not a mock of any class. |

### 4. Success Cases

| ID | Scenario | Setup |
|---|---|---|
| S1 | First attempt succeeds | `fn` returns `success=True` on call 1 |
| S2 | Fails once (retryable), succeeds on second attempt | `fn` side_effect: `[retryable_failure, success]` |
| S3 | Fails twice (retryable), succeeds on third attempt | `fn` side_effect: `[retryable_failure, retryable_failure, success]` |

### 5. Failure Cases

| ID | Scenario | Setup |
|---|---|---|
| F1 | Non-retryable failure on first attempt | `fn` returns `success=False`, `provider_error.retryable=False` |
| F2 | All retries exhausted (all retryable) | `fn` always returns retryable failure; `max_retries=3` |
| F3 | Non-retryable failure after one retry | `fn` side_effect: `[retryable_failure, non_retryable_failure]` |
| F4 | `provider_error=None` on failure | `fn` returns `success=False`, `provider_error=None` — `is_retryable` must return `False` |

### 6. Assertions

**S1 — first attempt succeeds:**
- `result.success is True`
- `result.retries == 0`
- `result.duration_seconds >= 0.0`
- `time.sleep` was **not** called

**S2 — one retry, then success:**
- `result.success is True`
- `result.retries == 1`
- `time.sleep` called exactly once with `15.0` (attempt 0, `base_delay=15.0, backoff_factor=2.0`)

**S3 — two retries, then success:**
- `result.success is True`
- `result.retries == 2`
- `time.sleep` call args: `[call(15.0), call(30.0)]` (attempt 0 → 15s, attempt 1 → 30s)

**F1 — non-retryable, immediate return:**
- `result.success is False`
- `time.sleep` was **not** called
- `fn` called exactly once

**F2 — all retries exhausted:**
- `result.success is False`
- `result.error` starts with `"Max retries exhausted"`
- `result.retries == 2` (two sleeps happened, third attempt was the final one with no sleep)
- `time.sleep` called exactly **twice** (not three times — last attempt has no sleep)
- `fn` called exactly `max_retries` (3) times

**F3 — non-retryable after one retry:**
- `result.success is False`
- `time.sleep` called exactly once
- `fn` called exactly twice

**F4 — no `provider_error`:**
- `result.success is False`
- `time.sleep` was **not** called (non-retryable by default)
- `fn` called exactly once

### 7. Implementation Effort

**Small — 2–3 hours.** No fixtures needed beyond `RetryPolicy` with `base_delay=15.0` (real value, sleep is mocked). The callable `fn` is a plain `MagicMock(side_effect=[...])`. Eight focused test functions, no shared state.

### 8. Hidden Edge Cases

**E1 — The last attempt does not sleep.**  
The loop is `for attempt in range(max_retries)` with sleep only when `attempt < max_retries - 1`. With `max_retries=3`, sleeps happen after attempt 0 and attempt 1, but NOT after attempt 2. A test that asserts `time.sleep.call_count == max_retries - 1` (not `max_retries`) is required to catch a regression here.

**E2 — `result.retries` is set on the success result, not the failure result.**  
On success, `result.retries = state.retries_used` mutates the returned object. If `fn` returns the same `InferenceResult` object each time (e.g. a shared fixture), mutation could corrupt state. Each `side_effect` entry must be a **distinct** `InferenceResult` instance.

**E3 — `duration_seconds` is set on the returned result object.**  
On success, `result.duration_seconds` is mutated in-place. On exhaustion, a **new** `InferenceResult` is constructed. Tests for the exhaustion path must assert on the returned object, not on the last object passed to `fn`.

**E4 — Jitter changes the delay.**  
`RetryPolicy(jitter=True)` applies `random.uniform`. A test with `jitter=True` cannot assert an exact delay value. Either test with `jitter=False` (default) for exact assertions, or patch `random.uniform` to return `1.0` when testing jitter behavior.

**E5 — `calculate_delay` is called inside `record_attempt`, not inside `execute` directly.**  
`execute` calls `record_attempt`, which calls `calculate_delay`. The delay passed to `time.sleep` is the return value of `record_attempt`. Do not assert on `calculate_delay` separately — assert on `time.sleep` call args.

---

## T-02 — `InferenceManager.generate`

### 1. Behavior Under Test

`InferenceManager.generate(prompt, task_type)` orchestrates five concerns in sequence:

1. **Cache lookup** — if `enable_cache=True` and a cache hit exists, return it immediately without calling any provider.
2. **Cooldown check** — if the primary provider's `HealthTracker` state has `in_cooldown=True` and a fallback is configured, skip primary and call `_execute_with(fallback, ...)` directly.
3. **Primary execution** — call `_execute_with(primary, prompt, task_type)`, which runs `RetryManager.execute(lambda: provider.generate_once(prompt))`.
4. **Failover** — if primary result has `success=False` and a fallback is configured, call `_execute_with(fallback, prompt, task_type)`.
5. **Cache write** — inside `_execute_with`, on success, `InferenceCache.put(prompt, result)` is called.

`_execute_with` also calls `HealthTracker.record_success` or `record_failure` based on the result.

### 2. Dependencies That MUST Be Mocked

| Dependency | Why |
|---|---|
| `GeminiProvider.generate_once` | Makes a real HTTP call to the Gemini API. Patch at the method level on the instance, not the class. |
| `OpenRouterProvider.generate_once` | Makes a real HTTP call. Same approach. |

**Critical distinction:** Mock `generate_once` on the provider *instance*, not the `InferenceManager` class. This allows `InferenceManager.__init__`, `generate`, `_execute_with`, `RetryManager`, `HealthTracker`, and `InferenceCache` to all run as real code.

### 3. Dependencies That Must NOT Be Mocked

| Dependency | Why |
|---|---|
| `InferenceManager` | The class under test. Must be constructed with real `__init__`. |
| `RetryManager` | Must run its real `execute` loop so retry count and duration are real. |
| `HealthTracker` | Must run real `record_success`/`record_failure` so health state is real. |
| `InferenceCache` | Must run real `get`/`put` so cache hit/miss behavior is real. Use `tmp_path` for `cache_dir`. |
| `time.sleep` | **Do not mock** in T-02. `RetryManager` uses `base_delay=15.0` by default. Construct `InferenceManager` with a custom `RetryManager` via a subclass or inject a `RetryPolicy(max_retries=1, base_delay=0.0)` — see edge case E1 below. |

### 4. Success Cases

| ID | Scenario | Setup |
|---|---|---|
| S1 | Primary succeeds on first attempt | `generate_once` returns `success=True` |
| S2 | Cache hit — provider never called | Pre-populate cache; call `generate` twice with same prompt |
| S3 | Primary fails, fallback succeeds | Primary `generate_once` returns `success=False` (non-retryable); fallback `generate_once` returns `success=True` |
| S4 | Primary in cooldown, fallback called directly | Manually set `health.record_failure` three times to trigger cooldown; assert fallback is called without primary being called |

### 5. Failure Cases

| ID | Scenario | Setup |
|---|---|---|
| F1 | Primary fails, no fallback configured | `generate_once` returns `success=False`; `InferenceManager` constructed without `fallback` |
| F2 | Primary fails, fallback also fails | Both `generate_once` return `success=False` |
| F3 | Primary in cooldown, no fallback | Cooldown triggered; no fallback configured; primary is still called (cooldown check requires fallback to skip) |

### 6. Assertions

**S1 — primary succeeds:**
- `result.success is True`
- `result.provider == "gemini"`
- `result.text == <expected text>`
- `manager.health.get("gemini").consecutive_failures == 0`
- Cache file exists in `tmp_path` after the call

**S2 — cache hit:**
- `result.success is True`
- `result.text == <cached text>`
- `generate_once` called exactly **once** total across both `generate()` calls (second call hits cache)

**S3 — failover to fallback:**
- `result.success is True`
- `result.provider == "openrouter"`
- Primary `generate_once` called once
- Fallback `generate_once` called once
- `manager.health.get("gemini").consecutive_failures == 1`
- `manager.health.get("openrouter").consecutive_failures == 0`

**S4 — cooldown skips primary:**
- `result.success is True` (fallback succeeds)
- Primary `generate_once` **not** called
- Fallback `generate_once` called once

**F1 — primary fails, no fallback:**
- `result.success is False`
- `manager.health.get("gemini").consecutive_failures == 1`
- No cache file written

**F2 — both fail:**
- `result.success is False`
- `result.provider == "openrouter"` (last provider attempted)
- `manager.health.get("gemini").consecutive_failures >= 1`
- `manager.health.get("openrouter").consecutive_failures >= 1`

**F3 — cooldown, no fallback:**
- `result.success is False`
- Primary `generate_once` **is** called (cooldown check only skips when fallback exists)

### 7. Implementation Effort

**Medium — 3–4 hours.** The main complexity is injecting a zero-delay `RetryPolicy` to avoid real sleeps. This requires either: (a) exposing `retry_manager` as a constructor parameter on `InferenceManager` (a code change — not allowed here), or (b) patching `time.sleep` only in T-02 tests, or (c) constructing `RetryPolicy(max_retries=1, base_delay=0.0)` and monkey-patching `manager._retry_manager` after construction. Option (c) is the least invasive without code changes.

### 8. Hidden Edge Cases

**E1 — `RetryManager` default `base_delay=15.0` will cause real sleeps.**  
`InferenceManager.__init__` constructs `RetryManager()` with no arguments, using `base_delay=15.0`. If a test triggers a retry (retryable failure), `time.sleep(15.0)` will be called. Either: patch `time.sleep` in T-02 tests, or after constructing the manager, replace `manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))`. The latter is preferred because it keeps sleep real for the non-retry path.

**E2 — Cache key includes provider name and model name.**  
`InferenceCache._cache_key` hashes `f"{provider}:{model}:{prompt}"`. A cache hit test must use the exact same `provider` and `model` that the `InferenceManager` will use. Construct the manager with a known model (e.g. `model="test-model"`) and pre-populate the cache using the same values.

**E3 — `_execute_with` calls `HealthTracker.record_failure` even when fallback succeeds.**  
After primary fails and fallback is called, the primary's failure is already recorded. The fallback's success is also recorded. Both health states are mutated. Assertions must check both providers' health states independently.

**E4 — Cooldown requires exactly 3 consecutive failures.**  
`HealthTracker.record_failure` sets `cooldown_until` only when `consecutive_failures >= 3`. To put a provider in cooldown for S4, call `manager.health.record_failure("gemini")` three times directly before calling `generate`. Do not rely on `generate` calls to accumulate failures — that would require three failing `generate` calls first.

**E5 — Cache is only written on success inside `_execute_with`.**  
If primary fails and fallback succeeds, the cache is written with the **fallback's** result (provider="openrouter"). A subsequent cache hit will return the fallback result, not a primary result. This is correct behavior but must be verified explicitly if testing cache write after failover.

**E6 — `enable_cache=False` disables cache entirely.**  
`self._cache = None` when `enable_cache=False`. The cache lookup and write are both skipped. A test for S1 with `enable_cache=False` should verify no cache file is written even on success.

---

## T-03 — `generate_brief`

### 1. Behavior Under Test

`generate_brief(item, prompt_path, api_key)` is a module-level function that:

1. **Guards on text length** — raises `ValueError` if `item.raw_text` is `None` or `len < 100`.
2. **Truncates input** — slices `raw_text` to 15,000 characters before building the prompt.
3. **Reads the prompt template** — either from a `PromptRegistry` (calls `registry.get("brief", "summarize")`) or from a `Path` (opens the file directly).
4. **Substitutes placeholders** — replaces `{{ topic.title }}`, `{{ topic.source }}`, `{{ topic.url }}`, `{{ topic.raw_text }}` in the template.
5. **Constructs `InferenceManager`** — `InferenceManager(api_key=api_key)` is called inside the function. This is the injection point.
6. **Calls `manager.generate`** — with `task_type="brief_generation"`.
7. **Parses JSON response** — constructs a `Brief` from the parsed dict. If `review_status` is present in the dict, it is coerced to `ReviewStatus`.
8. **Returns fallback `Brief`** on any failure — inference failure, JSON parse error, or Pydantic validation error all fall through to the same fallback with all fields set to `"needs_review"`.

### 2. Dependencies That MUST Be Mocked

| Dependency | Why |
|---|---|
| `InferenceManager` (the class, at import site `content_creation.generation.brief.InferenceManager`) | `generate_brief` constructs `InferenceManager(api_key=api_key)` internally. There is no injection point. Must patch the class so the constructor returns a mock whose `generate` method is controlled. |

**This is the one case where class-level patching is correct** — because `generate_brief` owns the construction and there is no way to inject a pre-built manager without a code change. The patch target is `content_creation.generation.brief.InferenceManager`.

### 3. Dependencies That Must NOT Be Mocked

| Dependency | Why |
|---|---|
| `generate_brief` function | The function under test. Call it directly. |
| `ScoredTopicItem` | Plain Pydantic model. Construct real instances. |
| `Brief` | Plain Pydantic model. The function constructs it; assert on the real object. |
| `PromptRegistry` | Use a real `PromptRegistry` pointed at a `tmp_path` with a real prompt file. This exercises the `registry.get()` path including `FileNotFoundError` on missing files. |
| `ReviewStatus` | Enum. Must run real coercion logic (`ReviewStatus(data["review_status"])`). |
| JSON parsing | `json.loads` must run on the mock's return text. Do not mock it. |

### 4. Success Cases

| ID | Scenario | Setup |
|---|---|---|
| S1 | Valid JSON response → correct `Brief` | Mock `manager.generate` returns `success=True` with valid JSON text |
| S2 | Response includes `review_status: "draft"` | JSON includes `"review_status": "draft"` — verify coercion to `ReviewStatus.DRAFT` |
| S3 | `prompt_path` is a `Path` (not `PromptRegistry`) | Pass a real `Path` to a tmp prompt file; verify template is read and placeholders substituted |
| S4 | `prompt_path` is a `PromptRegistry` | Pass a real `PromptRegistry`; verify `registry.get("brief", "summarize")` is called |
| S5 | `raw_text` exactly 15,000 chars — no truncation | Verify prompt contains full text |
| S6 | `raw_text` > 15,000 chars — truncated | Verify prompt contains only first 15,000 chars |

### 5. Failure Cases

| ID | Scenario | Setup |
|---|---|---|
| F1 | `raw_text` is `None` | `item.raw_text = None` — expect `ValueError` |
| F2 | `raw_text` is 99 chars | `item.raw_text = "x" * 99` — expect `ValueError` |
| F3 | `raw_text` is exactly 100 chars | `item.raw_text = "x" * 100` — must NOT raise; must proceed |
| F4 | Inference returns `success=False` | Mock returns failure result — expect fallback `Brief` |
| F5 | Inference returns malformed JSON | Mock returns `success=True` with `text="not json"` — expect fallback `Brief` |
| F6 | JSON parses but fails Pydantic validation | Mock returns JSON missing required `Brief` fields — expect fallback `Brief` |
| F7 | `PromptRegistry` key missing | Pass registry without `"brief"/"summarize"` registered — expect `KeyError` to propagate |
| F8 | `Path` prompt file does not exist | Pass a `Path` to a non-existent file — expect `FileNotFoundError` to propagate |

### 6. Assertions

**S1 — valid response:**
- Return type is `Brief`
- `brief.topic_id == item.id`
- `brief.source_url == item.url`
- `brief.why_it_matters == <value from JSON>`
- `brief.plain_english_summary` has exactly 3 items
- `brief.review_status == ReviewStatus.DRAFT`
- `brief.generated_at` is a valid ISO-8601 string

**S3/S4 — placeholder substitution:**
- The prompt passed to `manager.generate` contains `item.title`, `item.source`, `item.url`
- Capture the prompt via `mock_manager.generate.call_args[0][0]` (or `call_args.kwargs["prompt"]`)
- Assert `item.title in prompt`, `item.url in prompt`

**S6 — truncation:**
- Capture the prompt; assert `item.raw_text[:15000] in prompt`
- Assert `item.raw_text[15000:]` is NOT in the prompt (if `raw_text` is longer than 15,000)

**F1/F2 — short text:**
- `pytest.raises(ValueError)` with message matching `"too short"` or char count

**F3 — boundary at 100:**
- No exception raised
- `manager.generate` is called (function proceeds past the guard)

**F4 — inference failure:**
- Return type is `Brief`
- `brief.review_status == ReviewStatus.NEEDS_REVIEW`
- `brief.why_it_matters == "needs_review"`
- `brief.plain_english_summary == ["needs_review", "needs_review", "needs_review"]`
- `brief.topic_id == item.id` (topic_id is always set, even in fallback)
- `brief.source_url == item.url` (source_url is always set)

**F5 — malformed JSON:**
- Same assertions as F4 (fallback Brief)
- `manager.generate` was called once

**F6 — Pydantic validation failure:**
- Same assertions as F4 (fallback Brief)
- The exception is caught internally; no exception propagates to the caller

**F7 — missing registry key:**
- `KeyError` propagates out of `generate_brief` (not caught internally)

**F8 — missing prompt file:**
- `FileNotFoundError` propagates out of `generate_brief` (not caught internally)

### 7. Implementation Effort

**Small — 2 hours.** The patch target is fixed (`content_creation.generation.brief.InferenceManager`). Fixtures needed: a `ScoredTopicItem` with `raw_text` of sufficient length, a `tmp_path` prompt file, and a `PromptRegistry` pointing at `tmp_path`. The valid JSON response must match the `Brief` schema exactly (all required fields, `plain_english_summary` with exactly 3 items).

### 8. Hidden Edge Cases

**E1 — `plain_english_summary` must have exactly 3 items.**  
`Brief` has a `field_validator` that raises `ValueError` if the list does not have exactly 3 items. A JSON response with 2 or 4 items will trigger the fallback. The valid JSON fixture must include exactly 3 summary items. A test for F6 should use a JSON response with 2 items to verify the Pydantic validation failure is caught and the fallback is returned.

**E2 — `review_status` coercion happens before `Brief` construction.**  
The function does `data["review_status"] = ReviewStatus(data["review_status"])` before passing `**data` to `Brief`. If the JSON contains an invalid status string (e.g. `"unknown_status"`), `ReviewStatus(...)` raises `ValueError` before Pydantic runs. This is caught by the outer `except Exception` and falls through to the fallback. This edge case is worth a dedicated test.

**E3 — `generated_at` is set inside `generate_brief`, not from the JSON response.**  
The function sets `generated_at = datetime.now(timezone.utc).isoformat()` before calling inference, then passes it explicitly to `Brief(generated_at=generated_at, **data)`. If the JSON response also contains a `generated_at` key, it will be passed twice and raise a `TypeError`. The valid JSON fixture must NOT include `generated_at` or `topic_id` or `source_url` — these are injected by the function.

**E4 — `topic_id` and `source_url` are also injected, not from JSON.**  
Same as E3. The function calls `Brief(topic_id=item.id, source_url=item.url, generated_at=generated_at, **data)`. If the JSON contains `topic_id` or `source_url`, the call raises `TypeError` (duplicate keyword argument). The valid JSON fixture must exclude these three fields.

**E5 — The `Path` branch opens the file with `open(prompt_path, "r")`.**  
If the file exists but is empty, the template is an empty string. Placeholder substitution produces an empty prompt. `manager.generate` is still called with an empty string. This is not guarded. A test with an empty prompt file verifies this behavior is consistent (no exception, just an empty prompt sent to inference).

**E6 — `raw_text` truncation happens before placeholder substitution.**  
`truncated_text = item.raw_text[:15000]` is computed first, then used in `prompt.replace("{{ topic.raw_text }}", truncated_text)`. The truncation is on the raw text, not on the final prompt. The final prompt may still exceed 15,000 characters due to the template and other fields. This is expected behavior, not a bug, but worth documenting.

---

## Implementation Order Recommendation

1. **T-01 first** — pure unit test, no fixtures, no file I/O, fastest to write and run. Establishes confidence in the retry loop before testing the manager that uses it.
2. **T-03 second** — isolated function, clear injection point, straightforward fixtures. Validates the brief generation entry point.
3. **T-02 last** — most complex due to the zero-delay workaround and multi-provider setup. Benefits from T-01 being green first (confirms `RetryManager` is correct before testing the manager that wraps it).
