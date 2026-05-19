# Chapter 10 — Analytics: Measuring What Works

## The Question

Why does an analytics layer exist when you don't have platform API integration yet? Why build measurement infrastructure before you have data to measure?

Because the schema needs to exist before the data arrives. If you wait until you have platform APIs to design your analytics model, you'll retrofit it onto an existing pipeline — breaking the schema-first principle. By defining `PostAnalytics` now, you establish the contract that future integrations will fill, and you can manually enter performance data today to start building intuition about what content works.

## The Answer

The `init-analytics` CLI command creates a `PostAnalytics` record for each post in a calendar, with all performance fields set to `None`. The `update-analytics` command lets you manually enter metrics (views, reach, saves, comments, CTA clicks, watch time). The `post_id` format (`{topic_id}_{format}_{week_start}`) uniquely identifies each scheduled post across time.

## Files in This Stage

### models/analytics.py
**Why it exists:** Defines the measurement contract for post performance.
**What it does:** `PerformanceSnapshot` has optional int/float fields for views (24h, 7d, 30d), reach, saves, comments, cta_clicks, and watch_time_pct (video only). `PostAnalytics` wraps this with post_id, topic metadata, format, asset_path, posted_at (None until actually posted), week_start, and notes.
**Key decision:** All performance fields default to `None`, not zero — this distinguishes "not yet measured" from "measured and got zero engagement". A post with 0 views is different from a post that hasn't been checked yet.
**Connects to:** Initialized from WeeklyCalendar posts → updated manually via CLI → future: updated by platform API integration.

### cli.py (init-analytics and update-analytics subcommands)
**Why it exists:** Provides the interface for creating and updating analytics records.
**What it does:** `init-analytics` iterates calendar posts and creates one `PostAnalytics` per post (skipping existing records). `update-analytics` loads an existing record and prompts for each field interactively, keeping current values on empty input.
**Key decision:** `init-analytics` is idempotent — running it twice skips already-created records. This means you can safely re-run after adding new posts to a calendar without overwriting existing data.
**Connects to:** Reads WeeklyCalendar → creates/updates PostAnalytics in data/analytics/{post_id}.json.

## Data Flow

```
data/calendars/{week_start}.json (WeeklyCalendar)
    ↓
CLI: init-analytics --week-start 2026-05-19
    ↓
For each ScheduledPost:
  post_id = "{topic_id}_{format}_{week_start}"
  Already exists? → skip
    ↓
  PostAnalytics(
      post_id, topic_id, topic_title, format,
      asset_path, source_url,
      posted_at=None,
      week_start="2026-05-19",
      performance=PerformanceSnapshot(all None),
      last_updated=now()
  )
    ↓
data/analytics/{post_id}.json

Later:
CLI: update-analytics --post-id <id>
    ↓
Interactive prompts: views_24h, reach_7d, saves, etc.
    ↓
Updated PostAnalytics with last_updated=now()
```

## Why Not the Alternative?

**Why not add analytics later when needed?** Because the feedback loop vision — where performance data influences scoring weights — requires a stable schema that other stages can depend on. If you add analytics later with a different field structure, you'd need to update the scoring engine, the planner, and potentially the models. By defining the contract now, future integrations just fill in the `None` values without structural changes.

## Key Insight

**Analytics isn't about the data you have today — it's about the contract you're building for the feedback loop that will eventually make your scoring weights self-tuning.**
