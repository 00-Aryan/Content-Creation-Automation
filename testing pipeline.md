# Testing Pipeline

## Purpose

Capture the test plan, commands executed, and observed results for the content creation pipeline without modifying any existing source files.

## Plan

1. Verify the current environment and project root.
2. Run `uv run python -m content_creation.cli collect --all` and record output.
3. Run `uv run python -m content_creation.cli score-topics` and record output.
4. Run `uv run python -m content_creation.cli generate-briefs --top 1` and record output.
5. Run `uv run python -m content_creation.cli build-all-manifests` and record output.
6. Run `uv run python -m content_creation.cli plan-week` and record output.
7. Run `uv run python -m content_creation.cli dry-run` and record output.
8. Note any warnings or failures and identify whether they are operational issues or expected pipeline state.

## Results

### Environment

- Working directory: `/home/aryan/May-2026/Content-Creation`
- Virtual environment: `.venv`
- `uv` warning observed: `VIRTUAL_ENV=/home/aryan/Content-Creation/.venv does not match the project environment path .venv`

### Commands

#### `uv run python -m content_creation.cli collect --all`

Output:

```text
--- COLLECT ---
2026-05-19 17:03:00,152 - content_creation.ingestion - INFO - Starting collection for source: arxiv_cs_ml
2026-05-19 17:03:03,057 - content_creation.ingestion - INFO - Fetched 875 records from arxiv_cs_ml
2026-05-19 17:03:03,154 - content_creation.ingestion - INFO - Completed arxiv_cs_ml: 0 new, 875 duplicates.
2026-05-19 17:03:03,154 - content_creation.ingestion - INFO - Starting collection for source: arxiv_cs_ai
2026-05-19 17:03:04,174 - content_creation.ingestion - INFO - Fetched 343 records from arxiv_cs_ai
2026-05-19 17:03:04,213 - content_creation.ingestion - INFO - Completed arxiv_cs_ai: 0 new, 343 duplicates.
2026-05-19 17:03:04,214 - content_creation.ingestion - INFO - Starting collection for source: openai_blog
2026-05-19 17:03:10,092 - content_creation.ingestion - INFO - Fetched 965 records from openai_blog
2026-05-19 17:03:10,186 - content_creation.ingestion - INFO - Completed openai_blog: 0 new, 965 duplicates.

Ingestion complete. Added 0 new items.
```

#### `uv run python -m content_creation.cli score-topics --limit 1`

Output:

```text
--- SCORE LIMIT 1 ---
Scoring 1 items...
2026-05-19 17:04:00,688 - content_creation.scoring.engine - INFO - Enabled student_usefulness rule (weight=0.3)
2026-05-19 17:04:00,688 - content_creation.scoring.engine - INFO - Enabled novelty rule (weight=0.25)
2026-05-19 17:04:00,688 - content_creation.scoring.engine - INFO - Enabled credibility rule (weight=0.2)
2026-05-19 17:04:00,688 - content_creation.scoring.engine - INFO - Enabled explainability rule (weight=0.15)
2026-05-19 17:04:00,688 - content_creation.scoring.engine - INFO - Enabled hook_potential rule (weight=0.1)
2026-05-19 17:04:00,688 - content_creation.scoring.engine - INFO - Processing 1 items through scoring and filters...
2026-05-19 17:04:00,689 - content_creation.scoring.base - INFO - Scored item 468a4a589f8d4a953bda8ae2a95bcf1d563f328b0000660a5ce2437a9d3f16c1: total=50.00, rules=['student_usefulness', 'novelty', 'credibility', 'explainability', 'hook_potential']
2026-05-19 17:04:00,689 - content_creation.scoring.engine - INFO - Completed: 1 scored, 0 rejected
Successfully scored 1 items.
```

#### `uv run python -m content_creation.cli generate-briefs --top 1`

Output:

```text
--- GENERATE BRIEFS ---
Generating briefs for top 1 topics...
2026-05-19 17:04:18,207 - google_genai.models - INFO - AFC is enabled with max remote calls: 10.
2026-05-19 17:04:35,682 - httpx - INFO - HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent "HTTP/1.1 200 OK"
Generated 1 briefs, 0 failed
```

#### `uv run python -m content_creation.cli build-all-manifests`

Output:

```text
2026-05-19 16:59:54,351 - content_creation.manifest - INFO - Built manifest for 468a4a589f8d4a953bda8ae2a95bcf1d563f328b0000660a5ce2437a9d3f16c1: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,352 - content_creation.manifest - INFO - Built manifest for ccde3cde2aa9e46761357a6ee5e0382351cff65da3f99ae672c0a1bc15ce1cb2: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,353 - content_creation.manifest - INFO - Built manifest for d319a59734a08b0b2658b089bd1a2e69c8d4fddddf6bd24ca1f6e74b099bbafb: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,354 - content_creation.manifest - INFO - Built manifest for 866047e526b8d4d3ab97649120e12abbb7d94e2a4ddd795a29baf2eead7f3625: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,356 - content_creation.manifest - INFO - Built manifest for 7c26d52278c42475b5df845e869e7cf5b44d54b6dea23456f3605c1244cb5f22: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,358 - content_creation.manifest - INFO - Built manifest for 2b20a8623e337127048f0d029f4dfe51230b69a63b20b1f4b48449b61c1b3ff5: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,359 - content_creation.manifest - INFO - Built manifest for 9c41388712568bdca9f2b26fb3a46b744a8d01f2415f2c9469c5873f3d3d0019: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,361 - content_creation.manifest - INFO - Built manifest for a5ff171e87668b5923fab715ad48943692ba90c192db47a5f4894d40b4905dc4: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,362 - content_creation.manifest - INFO - Built manifest for 5d2862b7a56a341ff2878e31a98425f9238296c9454c1b14a4b40d2df3360576: blocked (skipped: ['script', 'carousel', 'newsletter'])
2026-05-19 16:59:54,362 - content_creation.manifest - INFO - Built 9 manifests
Built and saved 9 manifests
  Complete: 0
  Partial: 0
  Blocked: 9
```

#### `uv run python -m content_creation.cli plan-week`

Output:

```text
--- PLAN WEEK ---
2026-05-19 17:07:19,619 - content_creation.planning.planner - INFO - PostingPlanner initialized with targets: {'short_video': 3, 'carousel': 2, 'newsletter': 1, 'thumbnail': 1}
2026-05-19 17:07:19,620 - content_creation.planning.planner - WARNING - No approved manifests found for planning
Week planned: 2026-05-25 to 2026-05-31
Total posts: 0
Saved to: /home/aryan/May-2026/Content-Creation/data/calendars/2026-05-25.json
Markdown: /home/aryan/May-2026/Content-Creation/data/calendars/2026-05-25.md
```

#### `uv run python -m content_creation.cli dry-run`

Output:

```text
--- DRY RUN ---
2026-05-19 17:07:21,335 - content_creation.planning.dryrun - INFO - DryRunValidator initialized
2026-05-19 17:07:21,336 - content_creation.planning.dryrun - INFO - Dry run complete: 0 ready, 0 warnings, 0 blocked
Dry Run: 2026-05-25 to 2026-05-31
──────────────────────────────
  ✓ Ready:    0
  ⚠ Warning:  0
  ✗ Blocked:  0
──────────────────────────────
Saved: /home/aryan/May-2026/Content-Creation/data/dryruns/2026-05-25.json
Report: /home/aryan/May-2026/Content-Creation/data/dryruns/2026-05-25.md
```

### Observations

- The pipeline commands executed successfully without modifying any source files.
- `plan-week` created an empty calendar because there are currently no approved manifests.
- `dry-run` reported zero ready/warning/blocked posts, indicating the generated calendar had no posts to validate.
- `build-all-manifests` produced 9 blocked manifests, consistent with content assets still being incomplete or not approved.

### Interpretation

The primary operational issue is not a CLI failure; it is the current pipeline state:
- briefs exist but are not yet fully approved or ready,
- thumbnail assets are missing for the topics,
- optional assets are skipped when not recommended by briefs.

This means the pipeline is behaving as designed, but there is no fully-ready content to schedule yet.

### Detailed Block Causes

- All 9 manifests are `blocked`.
- Every manifest has:
  - `brief.status = needs_review`
  - `thumbnail.status = missing`
- No asset directories contain generated reviewable content:
  - `data/thumbnails`: 0 files
  - `data/scripts`: 0 files
  - `data/carousels`: 0 files
  - `data/newsletters`: 0 files

### Final Counts

- `data/staged`: 3953
- `data/scored`: 3953
- `data/briefs`: 9
- `data/manifests`: 9
- `data/calendars`: 1
- `data/dryruns`: 1

### Notes

- `review-assets --topic-id <topic_id>` was not executed because it requires interactive human review.
- The pipeline is blocked before scheduling because briefs are still pending review and thumbnail assets have not been generated.

