# Failover Investigation and Runtime Configuration Audit

This document details the investigation, runtime wiring, and verification of the failover architecture for the `content-creation` inference pipeline.

---

## 1. Direct Cause & Resolution Summary

### The Issue
During execution, Gemini API calls encountered `403 PERMISSION_DENIED` errors (due to a leaked credential block). Even though the codebase contained a robust failover architecture inside `InferenceManager`, it failed to prevent `"needs_review"` fallback stubs because **no fallback provider was wired into the generators**. Each generator constructed `InferenceManager(api_key=api_key)` with only the primary Gemini API key, leaving the fallback provider statically set to `None`.

### The Resolution
Rather than refactoring or copying configuration logic into all seven individual generators, a single, central runtime wiring was implemented directly inside the constructor of [InferenceManager](file:///home/aryan/May-2026/Content-Creation/src/content_creation/inference/manager.py#L24). If `fallback` is not explicitly specified, the manager dynamically looks for the `OPENROUTER_API_KEY` environment variable. If present, it automatically configures OpenRouter as the fallback failover target.

---

## 2. Implementation & Files Changed

### 1. Centralized Runtime Wiring
* **File:** [src/content_creation/inference/manager.py](file:///home/aryan/May-2026/Content-Creation/src/content_creation/inference/manager.py)
* **Changes:** Added environment variable detection in the `InferenceManager` constructor:
  ```python
  import os
  if fallback is None:
      openrouter_key = os.environ.get("OPENROUTER_API_KEY")
      if openrouter_key:
          fallback = "openrouter"
          fallback_api_key = openrouter_key
  ```
  This automatically activates failover capabilities on all construction sites in generators without modifying their code:
  * **Brief** Generator
  * **Content Intelligence** Generator
  * **Storyboard** Generator
  * **Script** Generator
  * **Carousel** Generator
  * **Newsletter** Generator
  * **Thumbnail** Generator

---

## 3. Unit and Integration Testing

A new test file was created at [tests/test_inference_fallback.py](file:///home/aryan/May-2026/Content-Creation/tests/test_inference_fallback.py) to validate this wiring.

### Tests Added
1. `test_fallback_unconfigured_when_openrouter_key_absent`: Verifies that if `OPENROUTER_API_KEY` is not present, no fallback provider is configured, preserving the exact legacy behavior.
2. `test_fallback_configured_when_openrouter_key_present`: Verifies that if `OPENROUTER_API_KEY` is present, OpenRouter is automatically configured with the correct credentials.
3. `test_explicit_fallback_takes_precedence_over_env_fallback`: Verifies that passing an explicit fallback provider argument (e.g. `fallback="gemini"`) overrides the environment default.

### Test Execution Results
* **Execution Command:** `uv run pytest`
* **Test Suit Count:** 171 passed tests (168 existing + 3 new fallback unit tests)
* **Status:** **PASS**

---

## 4. Live Pipeline Verification

To verify the wiring under actual failure conditions, a diagnostic script was executed with a blocked Gemini API key and an OpenRouter key configured in `.env`.

### Execution Trace
```text
[inference] task=content_intelligence error=403: 403 PERMISSION_DENIED. {'error': {'code': 403, 'message': 'Your API key was reported as leaked. Please use another API key.', 'status': 'PERMISSION_DENIED'}}
[failover] provider=gemini reason=retry_exhausted fallback=openrouter
[inference] task=content_intelligence error=401: {"error":{"message":"User not found.","code":401}}
```

### Trace Analysis
1. The primary Gemini call failed with a 403 (Permission Denied).
2. The `RetryManager` classified this as `retryable=False` (AUTH error), skipping useless backoff attempts.
3. `InferenceManager` detected the failed result and triggered failover because `self._fallback` was automatically configured:  
   `[failover] provider=gemini reason=retry_exhausted fallback=openrouter`
4. The request was successfully routed to the OpenRouter fallback provider.

*Note: The subsequent 401 error is expected as the configured OpenRouter key is a placeholder.*

---

## 5. Architectural Quality Improvements

| Improvement | Impact | Implementation Effort | Description |
| :--- | :---: | :---: | :--- |
| **Failover Config Wiring** | **High** | **Low** | Wired environment-level OpenRouter key to `InferenceManager` constructor. (Implemented) |
| **Credential Alert System** | Medium | Low | Emit clear console alarms when `ErrorCategory.AUTH` errors occur, immediately highlighting leaked/invalid key issues. |
| **Fallback Model Customization** | Medium | Low | Support configuring `FALLBACK_MODEL` via env (e.g. Groq/OpenRouter models) to customize fallback size. |
```
