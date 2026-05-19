# Chapter 7 — Review and Approval: The Human Gate

## The Question

Why does human review exist in an automated pipeline? If the scoring and generation are good enough, why not auto-approve everything above a threshold?

Because LLMs make subtle errors that automated checks can't catch. A script might be factually correct but tonally wrong. A carousel might have a misleading analogy. A thumbnail prompt might produce something clickbaity. The pipeline automates the *mechanical* work (fetching, scoring, formatting) but the *editorial judgment* — "Is this good enough to publish under my name?" — remains human.

## The Answer

Every generated asset starts with `review_status: "draft"`. The CLI's `review-assets` command presents each asset for a topic, shows a summary, optionally displays full content, and accepts approve/reject/skip decisions. After all decisions, the manifest is rebuilt to reflect the new state. Rejected assets block `overall_status`, preventing scheduling.

## Files in This Stage

### cli.py (review-assets subcommand)
**Why it exists:** Provides the interactive human gate between generation and scheduling.
**What it does:** Loads the manifest for a topic, iterates non-skipped/non-missing assets, shows a summary field per type (hook for scripts, subject_line for newsletters, slide 1 title for carousels, title_text for thumbnails), offers to show full JSON, then prompts for approve/reject/skip. After all decisions, rebuilds the manifest via `ManifestBuilder.build()`.
**Key decision:** Summary-first pattern — show the key field before full content. Most approvals can be made from the summary alone; full content is only needed when something looks off.
**Connects to:** Reads assets from all data/ dirs → calls storage.update_asset_status() → triggers manifest rebuild.

### storage/local.py (update_asset_status method)
**Why it exists:** Provides atomic status updates without rewriting entire asset files.
**What it does:** `update_asset_status(asset_type, topic_id, new_status)` loads the JSON file, changes only the `review_status` field, and writes it back. Returns False if the file doesn't exist.
**Key decision:** Only the status field is modified — this preserves all generated content exactly as-is, making the review decision a metadata change, not a content change.
**Connects to:** Called by review CLI → modifies asset JSON → manifest rebuild reads new status.

### models/brief.py (ReviewStatus enum)
**Why it exists:** Defines the state machine that all assets share.
**What it does:** `ReviewStatus` is a string enum with 5 values: `draft`, `needs_review`, `reviewed`, `approved`, `rejected`. Used by Brief, Script, Carousel, Newsletter, and ThumbnailPrompt.
**Key decision:** Single enum defined once and imported everywhere — prevents typos like `"aproved"` from entering the system.
**Connects to:** Used by all asset models → checked by manifest builder → gates the planner.

## Data Flow

```
data/manifests/{topic_id}.json (TopicManifest)
    ↓
CLI: review-assets --topic-id <id>
    ↓
For each non-skipped asset:
  Show summary → optionally show full JSON
    ↓
  User decision: approve / reject / skip
    ↓
  storage.update_asset_status(asset_type, topic_id, new_status)
    ↓
  Asset JSON file: review_status field updated in-place
    ↓
ManifestBuilder.build() → rebuild manifest with new statuses
    ↓
data/manifests/{topic_id}.json (updated overall_status, ready_for_planner)
```

## Why Not the Alternative?

**Why not auto-approve high-scoring assets?** Because scoring measures *topic quality* (is this worth covering?), not *generation quality* (did the LLM produce good content?). A topic can score 95 on student_usefulness but the generated script might have a confusing analogy or a claim that's technically correct but misleading in context. The human gate catches what automated validation cannot.

## Key Insight

**The review system doesn't judge whether content is correct — it judges whether content is ready to represent you, which is a decision only a human can make.**
