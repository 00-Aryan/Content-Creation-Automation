# Chapter 11 — The Full Picture: End to End

## Tracing One Topic Through the Entire Pipeline

Let's follow a real arXiv paper from RSS entry to analytics record.

**Stage 1 — Ingestion:**
arXiv RSS returns an entry with `link: "https://arxiv.org/abs/2405.12345"`. RSSCollector normalizes it:
```
TopicItem(
    id=SHA256("https://arxiv.org/abs/2405.12345") → "a3f8c2...",
    title="Efficient Attention via Sparse Routing",
    source="arxiv", category="paper", status="raw",
    raw_text="We propose a method that reduces...[4200 chars]"
)
```
Saved to `data/staged/a3f8c2.json`.

**Stage 2 — Scoring:**
ScoringEngine applies 5 rules: student_usefulness=72, novelty=80, credibility=85, explainability=60, hook_potential=55. Weighted sum: `72×0.30 + 80×0.25 + 85×0.20 + 60×0.15 + 55×0.10 = 73.1`. Passes hard filters (text > 100 chars, source present, not duplicate). Saved to `data/scored/a3f8c2.json` with `priority_score: 73.1, status: "scored"`.

**Stage 3 — Brief Generation:**
`generate_brief()` fills the prompt template with title, source, raw_text (truncated to 15k chars), calls Gemini. Returns:
```
Brief(
    topic_id="a3f8c2", why_it_matters="Attention is the bottleneck...",
    plain_english_summary=["Sparse routing skips...", "This reduces...", "The tradeoff is..."],
    recommended_formats=["short_video", "carousel"],
    review_status="draft"
)
```
Saved to `data/briefs/a3f8c2.json`.

**Stage 4 — Asset Generation:**
ScriptGenerator produces a Script (hook + sections + cta). CarouselGenerator produces 8 slides. ThumbnailGenerator produces a prompt with style="diagram_overlay". Newsletter is skipped (not in recommended_formats). Each saved to their respective `data/` directories.

**Stage 5 — Manifest:**
ManifestBuilder checks: brief ✓ approved, script ✓ draft, carousel ✓ draft, newsletter → skipped, thumbnail ✓ draft. `overall_status: "partial"`, `ready_for_planner: false`.

**Stage 6 — Review:**
`review-assets --topic-id a3f8c2` → approve brief, approve script, approve carousel, approve thumbnail. Manifest rebuilt: `overall_status: "complete"`, `ready_for_planner: true`.

**Stage 7 — Planning:**
PostingPlanner finds this manifest, schedules: Day 1 short_video, Day 4 carousel. Saved to `data/calendars/2026-05-19.json`.

**Stage 8 — Dry Run:**
DryRunValidator checks both asset files exist and are approved. `ready_count: 2, warning_count: 0`. Report: "All assets ready — safe to publish."

**Stage 9 — Analytics:**
`init-analytics` creates `PostAnalytics(post_id="a3f8c2_short_video_2026-05-19", performance=all None)`.

## The Complete File System Map

```
data/
├── raw/          ← Original XML payloads (audit trail)
├── staged/       ← Validated TopicItems (input to scoring)
├── scored/       ← ScoredTopicItems (input to brief generation)
├── briefs/       ← Briefs (input to all generators)
├── scripts/      ← Video scripts
├── carousels/    ← Carousel slide decks
├── newsletters/  ← Email content
├── thumbnails/   ← Visual prompt specs
├── manifests/    ← Per-topic state aggregation
├── calendars/    ← Weekly schedules (JSON + markdown)
├── dryruns/      ← Validation reports (JSON + markdown)
└── analytics/    ← Performance tracking records
```

## The CLI Command Sequence

```bash
uv run python -m content_creation.cli collect --all
uv run python -m content_creation.cli score-topics
uv run python -m content_creation.cli generate-briefs --top 5
uv run python -m content_creation.cli build-all-manifests
uv run python -m content_creation.cli review-assets --topic-id <id>
uv run python -m content_creation.cli plan-week
uv run python -m content_creation.cli dry-run
uv run python -m content_creation.cli init-analytics
```

## What Makes This a Pipeline, Not a Script

A script runs top-to-bottom and fails completely if any step fails. This pipeline:
- **Persists state between stages** — you can run scoring today and generation tomorrow
- **Handles partial failure** — 2 failed briefs don't block the 8 that succeeded
- **Allows re-entry** — re-run any stage without re-running predecessors
- **Separates concerns** — changing scoring weights doesn't touch generation code

## How to Add a New Asset Type

1. Create `models/podcast.py` with a Pydantic model
2. Create `generation/podcast.py` with a generator class following the existing pattern
3. Add `prompts/podcast.md` with the prompt template
4. Add save/list methods to `storage/local.py`
5. Add the format to `FORMAT_TO_ASSET` in `manifest.py`
6. Add the format to `publishing.yaml` weekly_targets

No existing files need logic changes — only registration in manifest.py and storage.

## How to Add a New Source

1. Create `collectors/hackernews.py` extending `BaseCollector`
2. Implement `fetch()`, `parse()`, `normalize()` returning TopicItems
3. Add the feed config to `config/feeds.yaml`
4. Register in the ingestion engine's collector factory

Scoring, generation, and everything downstream works unchanged — they only see TopicItems.

## Three Things That Would Break the Pipeline

1. **Changing TopicItem fields without updating ScoredTopicItem** — inheritance means the child model would fail validation on fields it expects from the parent
2. **Scoring weights not summing to 1.0** — the model validator raises at startup, preventing any scoring from running
3. **Deleting a brief file after manifest is built** — the planner would schedule it, but the dry-run would catch the missing asset

## Three Things That Make This Easy to Extend

1. **Schema-first contracts** — new stages just need to produce/consume the right Pydantic model
2. **Config-driven behavior** — new scoring categories or publishing rules are YAML changes, not code changes
3. **Filesystem as state** — no database to migrate, no ORM to update, just JSON files that any tool can inspect
