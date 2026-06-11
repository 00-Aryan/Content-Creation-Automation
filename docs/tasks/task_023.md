# TASK-023: Restore Operations Dashboard job queue schema initialization

**Phase:** 12.1
**Status:** DONE
**Priority:** HIGH
**Created:** 2026-06-11
**Completed:** 2026-06-11
**Requires approval:** NO

## Objective

Fix the Operations Dashboard warning:

```text
Failed to initialize Job Queue. (ImportError)
```

without changing the working E2E content pipeline.

## Confirmed Evidence

The E2E pipeline now completes successfully through:

```text
collect → score → generate-briefs → generate-content-intelligence → generate-storyboards → generate-assets → build-manifests
```

The remaining issue is isolated to the Operations Dashboard.

The dashboard imports:

```python
from content_creation.jobs.schema import create_job_schema
from content_creation.jobs.schema import create_lock_schema
```

but local diagnostic confirms:

```text
create_job_schema failed: ImportError cannot import name 'create_job_schema'
create_lock_schema failed: ImportError cannot import name 'create_lock_schema'
create_schema OK
```

The actual schema module currently exposes `create_schema(conn)`, which creates job and lock tables in one combined schema initializer.

## Scope

### Files to inspect

* `src/content_creation/ui/pages/6_operations_dashboard.py`
* `src/content_creation/jobs/schema.py`
* `src/content_creation/jobs/sqlite_repository.py`
* `src/content_creation/jobs/sqlite_lock_repository.py`
* existing tests for jobs schema and operations dashboard

### Files to modify

* `src/content_creation/jobs/schema.py`
* `tests/test_jobs_schema.py`
* `tests/test_operations_dashboard.py`
* `docs/tasks/task_023.md`
* `WORK_QUEUE.md`

### Files frozen unless absolutely necessary

* `src/content_creation/application/pipeline_run_service.py`
* `src/content_creation/application/asset_generation_service.py`
* `src/content_creation/inference/`
* prompt files
* scoring logic
* collection logic
* content generation services

## Implementation Requirements

1. Do not modify the working E2E pipeline.

2. Do not modify provider/model/API routing.

3. Do not modify prompts.

4. Do not change Streamlit pipeline execution behavior.

5. Fix the dashboard import mismatch by restoring schema functions expected by the Operations Dashboard.

6. Prefer adding explicit compatibility functions in `src/content_creation/jobs/schema.py`:

```python
def create_job_schema(conn: sqlite3.Connection) -> None:
    ...

def create_lock_schema(conn: sqlite3.Connection) -> None:
    ...
```

7. Refactor `create_schema(conn)` so it delegates to both functions:

```python
def create_schema(conn: sqlite3.Connection) -> None:
    create_job_schema(conn)
    create_lock_schema(conn)
    conn.commit()
```

8. Preserve the existing `create_schema(conn)` public API.

9. Ensure `create_job_schema(conn)` creates only job-related tables/indexes.

10. Ensure `create_lock_schema(conn)` creates only lock-related tables/indexes.

11. Ensure database pragmas remain enabled where needed:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

12. Ensure the Operations Dashboard can initialize queue and lock schema without ImportError.

13. Do not hide errors by broadening the exception handling.

14. Do not make Queue/Worker/Lock show fake healthy status. The dashboard may still show `UNKNOWN` or `No active workers` if no worker daemon is running, but it must not fail with an import error.

## Required Tests

Add or update tests proving:

1. `create_job_schema` can be imported.

2. `create_lock_schema` can be imported.

3. `create_schema` can still be imported.

4. `create_job_schema(conn)` creates the `jobs` table and job indexes.

5. `create_lock_schema(conn)` creates the `locks` table and lock indexes.

6. `create_schema(conn)` remains backward compatible and creates both jobs and locks schema.

7. The Operations Dashboard schema imports do not raise ImportError.

## Validation Commands

Run focused tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest tests/test_jobs_schema.py tests/test_operations_dashboard.py --tb=short -q
```

Run full tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=short -q
```

Run direct import diagnostic:

```bash
python3 - <<'PY'
try:
    from content_creation.jobs.schema import create_job_schema
    print("create_job_schema OK")
except Exception as e:
    print("create_job_schema failed:", type(e).__name__, e)

try:
    from content_creation.jobs.schema import create_lock_schema
    print("create_lock_schema OK")
except Exception as e:
    print("create_lock_schema failed:", type(e).__name__, e)

try:
    from content_creation.jobs.schema import create_schema
    print("create_schema OK")
except Exception as e:
    print("create_schema failed:", type(e).__name__, e)
PY
```

Run Streamlit:

```bash
uv run streamlit run src/content_creation/ui/app.py
```

Then open Operations Dashboard and confirm:

```text
Failed to initialize Job Queue. (ImportError)
```

is no longer displayed.

## Success Criteria

* [x] Operations Dashboard no longer shows `Failed to initialize Job Queue. (ImportError)`.
* [x] `create_job_schema`, `create_lock_schema`, and `create_schema` are all importable.
* [x] `create_schema` remains backward compatible.
* [x] Queue schema initialization and lock schema initialization work independently.
* [x] No changes are made to the working E2E generation pipeline.
* [x] Full test suite passes.
* [x] Worktree is clean after commit.

## Commit Message

```bash
fix(ops): restore dashboard job queue schema initialization (TASK-023)
```
