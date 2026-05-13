# TASK_SPEC: Merge-Blocking Fixes for Week 1 Stability

## Status
- **Approved Fixes implemented:** Scoring clamping, keyword regex, RSS validation, and concurrency handling are completed.
- **Goal:** Finalize merge-blocking fixes to ensure the active branch is stable, testable, and ready for integration into `main`.

## Implementation Items
1.  **RSS bozo/status handling:** Update `RSSCollector.fetch` in `src/content_creation/collectors/rss.py` to log `bozo` errors as `WARNING` with exception details but proceed if `result.entries` is populated. Ensure HTTP status >= 400 remains a hard failure.
2. **Scoring weight validation:** Modify `load_scoring_config` in `src/content_creation/scoring/config.py` to raise a `ValueError` if the total weights of enabled scoring rules do not sum to 1.0 within a small tolerance (for example using `math.isclose`).
3. **Storage writeability sanity check:** Add a check in `LocalStorage.__init__` in `src/content_creation/storage/local.py` to verify that the `base_dir` is writeable using a safe write-attempt/EAFP-style check before proceeding with normal storage operations.
4.  **Tests for fixes:**
    - Add a test case for `RSSCollector` simulating a `bozo` feed with entries.
    - Add a test case for `load_scoring_config` with weights summing to != 1.0.
    - Add a test case for `LocalStorage` initialization in a read-only directory.
5.  **End-to-end mocked integration run:** Perform a final verification by running the `collect --all` and `score-topics` commands against a mocked feed registry to confirm end-to-end Week 1 pipeline stability.

## Files Likely to Change
- `src/content_creation/collectors/rss.py`
- `src/content_creation/scoring/config.py`
- `src/content_creation/storage/local.py`
- `tests/test_ingestion.py`
- `tests/test_scoring_validation.py`
- `tests/test_storage.py`

## Test Expectations
- **RSS:** `collector.fetch()` should return data for a malformed (bozo) feed if entries are present, but still raise for HTTP 404/500.
- **Config:** `load_scoring_config()` must raise `ValueError` if total enabled weights are e.g., 0.8 or 1.2.
- **Storage:** `LocalStorage()` should raise an informative error if the target filesystem is read-only.

## Review Criteria
- **Robustness:** Does the system handle malformed XML (bozo) gracefully when entries exist?
- **Correctness:** Are scoring weights validated to prevent ranking bias from misconfiguration?
- **Safety:** Is storage writeability verified at the earliest possible stage?
- **Stability:** Does the end-to-end mocked run complete without unhandled exceptions?
