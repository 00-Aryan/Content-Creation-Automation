# Chapter 8 — The Posting Planner: Scheduling With Rules

## The Question

Why does a planner exist instead of just posting everything that's approved? If assets pass review, why not publish them immediately?

Because content strategy requires rhythm, diversity, and pacing. Publishing three carousel posts in a row bores your audience. Covering the same topic on consecutive days looks repetitive. Posting 7 items on Monday and nothing the rest of the week wastes reach. The planner turns a pile of approved assets into a *schedule* that maximizes engagement through variety and consistency.

## The Answer

The `PostingPlanner` reads approved manifests, applies diversity rules from `config/publishing.yaml` (weekly targets per format, no consecutive same-topic or same-format days, freshness priority), and produces a `WeeklyCalendar` with one `ScheduledPost` per slot. It stores a `config_snapshot` of the publishing config at plan time so you can audit what rules produced a given calendar.

## Files in This Stage

### planning/planner.py
**Why it exists:** Transforms approved manifests into a constrained weekly schedule.
**What it does:** `PostingPlanner` loads publishing config (weekly_targets, scheduling_rules, diversity_rules). `plan_week(week_start)` filters manifests to `ready_for_planner=True`, sorts by freshness (generated_at descending), then iterates format targets trying to fill slots. For each slot, it finds the first topic satisfying: max 2 appearances per week, minimum 2 days gap between same topic, never same format on consecutive days. If no topic satisfies constraints, the slot is skipped with a warning.
**Key decision:** `config_snapshot` is stored in the calendar — you can look at any past calendar and know exactly what rules produced it, even if publishing.yaml has since changed.
**Connects to:** Reads manifests from storage → writes WeeklyCalendar to data/calendars/{week_start}.json.

### config/publishing.yaml
**Why it exists:** Externalizes scheduling strategy so it can change without code modifications.
**What it does:** Defines `weekly_targets` (short_video: 3, carousel: 2, newsletter: 1, thumbnail: 1), `scheduling_rules` (max_same_topic_per_week: 2, min_days_between_same_topic: 2, formats_per_day: 1), and `diversity_rules` (never_same_format_consecutive_days, never_same_topic_consecutive_days).
**Key decision:** Targets are *goals*, not hard requirements — if there aren't enough approved topics, the planner skips rather than violating diversity rules. Quality over quantity.
**Connects to:** Read by PostingPlanner at initialization → rules applied during plan_week().

### models/calendar.py
**Why it exists:** Defines the schedule contract that the dry-run validator consumes.
**What it does:** `ScheduledPost` has day (1-7), date, topic_id, format, asset_path, source_url. `WeeklyCalendar` has week_start/end, list of posts, format_counts, topics_used, and config_snapshot.
**Key decision:** `asset_path` is stored in each post — the dry-run validator can directly check if the file exists without re-deriving paths.
**Connects to:** Produced by PostingPlanner → consumed by DryRunValidator.

## Data Flow

```
data/manifests/*.json (where ready_for_planner=true)
    ↓
PostingPlanner.plan_week(week_start=2026-05-19)
    ↓
Sort by freshness (generated_at descending)
    ↓
For each format target (short_video×3, carousel×2, newsletter×1, thumbnail×1):
  Find topic satisfying:
    - appearances < max_same_topic_per_week (2)
    - days since last use >= min_days_between_same_topic (2)
    - format not same as previous day
    ↓
WeeklyCalendar(
    week_start="2026-05-19", week_end="2026-05-25",
    posts: [ScheduledPost(day=1, format="short_video", ...), ...],
    format_counts: {"short_video": 3, "carousel": 2, ...},
    config_snapshot: {full publishing.yaml contents}
)
    ↓
data/calendars/2026-05-19.json
```

## Why Not the Alternative?

**Why not just post everything that's approved?** Because audience attention is finite and platform algorithms reward consistency. Dumping 5 posts on one day and zero the next signals inconsistency. The planner's diversity rules ensure your feed looks intentional — varied formats, spread topics, predictable cadence — which is what both algorithms and humans reward.

## Key Insight

**The planner doesn't decide *what* to publish — the review stage already did that. It decides *when* and *in what order*, optimizing for audience diversity rather than pipeline throughput.**
