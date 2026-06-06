# TASK-003: Add SecretScrubberFilter to `utils/logger.py`

**Phase:** 11.9.3
**Status:** BLOCKED
**Priority:** MEDIUM
**Created:** 2026-06-06
**Completed:** —
**Requires approval:** NO

## Source References
- Audit finding: `docs/architecture/phase11_9_2_security_audit.md` § SEC-M1

## Objective
Prevent API keys from appearing in log files by adding a logging filter that strips Gemini key patterns before records are written.

## Context
Python exception tracebacks from failed Gemini API calls can include the `x-goog-api-key` header value. If logged with `logger.exception()`, the key leaks into `data/logs/`. This adds one class to the existing logger module without changing any other logging behaviour.

## Scope

### Files to create
None

### Files to modify
- `src/content_creation/utils/logger.py` — add SecretScrubberFilter class and register on all handlers

### Files to NOT touch
All other `.py` files, all test files, all models, all generators, all prompts

## Constraints
Do not change log levels, handlers, or logger names. Filter must be a `logging.Filter` subclass.

## Implementation Steps
1. Read `src/content_creation/utils/logger.py` fully before changing anything
2. Add after imports, before existing functions:
```python
import re as _re

class SecretScrubberFilter(logging.Filter):
    _PATTERNS = [
        _re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
        _re.compile(r"sk-[A-Za-z0-9]{20,}"),
        _re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]+"),
    ]
    _REDACTED = "[REDACTED]"

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._scrub(str(record.msg))
        record.args = tuple(
            self._scrub(str(a)) if isinstance(a, str) else a
            for a in (record.args or ())
        )
        return True

    def _scrub(self, text: str) -> str:
        for pattern in self._PATTERNS:
            text = pattern.sub(self._REDACTED, text)
        return text
```
3. Find every `addHandler` call and insert `handler.addFilter(SecretScrubberFilter())` immediately before it
4. If `basicConfig` is used instead, add after it:
   `for _h in logging.getLogger().handlers: _h.addFilter(SecretScrubberFilter())`

## Validation
```bash
export UV_CACHE_DIR=/tmp/uv-cache
python3 -c "
from content_creation.utils.logger import SecretScrubberFilter
import logging
f = SecretScrubberFilter()
r = logging.LogRecord('t', logging.ERROR, '', 0, 'key is AIzaFAKE12345678901234567890', (), None)
f.filter(r)
assert '[REDACTED]' in str(r.msg)
print('PASS')
"
uv run python -m pytest --tb=short -q 2>&1 | tail -3
```

## Success Criteria
- [ ] `SecretScrubberFilter` exists in `logger.py`
- [ ] Scrubs `AIza...` patterns to `[REDACTED]`
- [ ] Test suite shows ≥ 950 passed

## Depends On
None

## Blocks
None

## Commit Message
```
security(logger): add SecretScrubberFilter to strip credentials from logs (TASK-003)
```

## Blocker

2026-06-07: Scope mismatch — task card targets `src/content_creation/utils/logger.py`, but that file does not exist in the repository. The existing module appears to be `src/content_creation/utils/logging.py`; however, all other `.py` files are explicitly out of scope and the task card says no files should be created.
