# WORK_QUEUE

## Current state
- Repo structure exists.
- CLAUDE.md and GEMINI.md exist.
- Source-ingestion and scoring-related work has been started.
- Review findings exist and must be resolved before further expansion.

## Next approved task
Finalize the current review-fix work so the active branch becomes merge-ready.

### Definition of done
- All approved fixes implemented.
- Tests updated and passing.
- Logging and validation improvements included.
- Deduplication edge case handled safely.
- Reviewer confirms merge-ready or lists only minor nits.

## Blockers / open questions
- Confirm exact active branch name for the fix work.
- Confirm whether `bozo` feed handling is strict-fail or log-and-continue.
- Confirm whether storage-path configurability is postponed or included now.