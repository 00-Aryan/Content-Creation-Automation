# Chapter 9 — The Dry Run: Validate Before Publishing

## The Question

Why does a dry-run exist as a separate step? The planner already only schedules approved manifests — what could go wrong between planning and publishing?

Because state can change between planning and execution. An asset file could be deleted. A review status could be reverted. A new rejection could come in after the calendar was generated. The dry-run is the final checkpoint that answers: "Right now, at this moment, is everything in this calendar actually ready to go live?"

## The Answer

The `DryRunValidator` takes a `WeeklyCalendar`, checks every scheduled post's asset file for existence and current `review_status`, and produces a `DryRunReport` with per-asset checks, aggregate counts (ready/warning/blocked), human-readable warnings, and recommended actions. It never modifies any files — it's purely observational.

## Files in This Stage

### planning/dryrun.py
**Why it exists:** Provides a read-only validation pass between planning and publishing.
**What it does:** `DryRunValidator.run(calendar)` iterates each `ScheduledPost`, checks if `asset_path` exists on disk, reads `review_status` from the JSON, and creates an `AssetCheck` per post. Aggregates into ready/warning/blocked counts. Generates `recommended_actions` based on what problems were found (drafts → run review, needs_review → approve, rejected → regenerate, missing → run generation). `export_markdown()` produces a human-readable checklist.
**Key decision:** Soft-warn philosophy — non-approved assets are flagged but included in the report. The dry-run doesn't block or delete anything. It gives you the full picture and lets you decide.
**Connects to:** Receives WeeklyCalendar → writes DryRunReport to data/dryruns/{week_start}.json + .md.

### models/dryrun.py
**Why it exists:** Defines the validation report contract.
**What it does:** `AssetCheck` has topic_id, format, asset_path, review_status, is_ready (true only if approved), and optional warning. `DryRunReport` has week range, counts, list of checks, warnings, recommended_actions, and generated_at.
**Key decision:** `is_ready` is a computed boolean — downstream consumers don't need to know the difference between "draft" and "needs_review", they just need: ready or not ready.
**Connects to:** Produced by DryRunValidator → consumed by human (via markdown) or future automation.

## Data Flow

```
data/calendars/{week_start}.json (WeeklyCalendar)
    ↓
DryRunValidator.run(calendar)
    ↓
For each ScheduledPost:
  Check: does data/{format_dir}/{topic_id}.json exist?
    No  → AssetCheck(is_ready=False, warning="file not found")
    Yes → Read review_status from JSON
          "approved" → AssetCheck(is_ready=True)
          anything else → AssetCheck(is_ready=False, warning="not approved")
    ↓
DryRunReport(
    total_scheduled=7, ready_count=5, warning_count=1, blocked_count=1,
    checks: [AssetCheck, ...],
    warnings: ["⚠ carousel for Topic X is needs_review"],
    recommended_actions: ["Review and approve needs_review assets"]
)
    ↓
data/dryruns/{week_start}.json
data/dryruns/{week_start}.md (human-readable checklist)
```

## Why Not the Alternative?

**Why not just check manually?** Because with 7 posts across 4 formats, you'd need to check up to 7 different files, remember which statuses are blocking, and mentally compute whether the week is publishable. The dry-run does this in one command and gives you a prioritized action list. It also creates an audit trail — you can look back and see what the state was before you published.

## Key Insight

**The dry-run is the pipeline's immune system — it detects problems without causing side effects, giving you the information to act without forcing a decision.**
