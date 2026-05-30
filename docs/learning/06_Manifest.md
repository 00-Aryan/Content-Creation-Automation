# Chapter 6 — The Manifest: Pipeline State in One File

## The Question

Why does a manifest exist at all? Each asset is already saved as its own JSON file — why aggregate them into a single tracking document?

Because the planner needs to answer one question: "Is this topic ready to schedule?" Without a manifest, answering that requires checking 5 different directories, reading each file's `review_status`, knowing which formats were recommended, and deciding if missing assets are blockers or expected skips. The manifest computes this once and exposes a single boolean: `ready_for_planner`.

## The Answer

The `ManifestBuilder` scans the filesystem for each topic's assets, reads their `review_status` from the JSON files, determines which assets are required vs. skipped (based on the brief's `recommended_formats`), and produces a `TopicManifest` with `overall_status` (complete/partial/blocked) and `ready_for_planner` (true only if all non-skipped assets are approved).

## Files in This Stage

### manifest.py
**Why it exists:** Aggregates per-topic asset state from the filesystem into a single queryable document.
**What it does:** `ManifestBuilder` takes a `LocalStorage` instance. `build()` checks each asset type: brief and thumbnail are always required; script, carousel, newsletter are required only if they appear in the brief's `recommended_formats`. For each asset, it checks if the file exists and reads its `review_status`. Assets not in recommended_formats get status `"skipped"`. The `overall_status` logic: if any non-skipped asset is missing or rejected → `"blocked"`; if all are approved → `"complete"`; otherwise → `"partial"`. `build_all()` iterates all briefs and builds manifests for each.
**Key decision:** The manifest is rebuilt fresh every time rather than incrementally updated — this means it's always consistent with the actual filesystem state, even if someone manually edits an asset file or deletes one.
**Connects to:** Reads from all data/ subdirectories → writes TopicManifest to data/manifests/{topic_id}.json → read by PostingPlanner.

## Data Flow

```
Brief.recommended_formats → ["short_video", "carousel"]
    ↓
ManifestBuilder.build(topic_id)
    ↓
Check data/briefs/{id}.json      → exists? read review_status
Check data/scripts/{id}.json     → exists? read review_status (required: short_video mapped)
Check data/carousels/{id}.json   → exists? read review_status (required: carousel mapped)
Check data/newsletters/{id}.json → skipped (not in recommended_formats)
Check data/thumbnails/{id}.json  → exists? read review_status (always required)
    ↓
TopicManifest(
    topic_id, topic_title, source_url,
    assets: {brief: AssetEntry, script: AssetEntry, ...},
    overall_status: "complete" | "partial" | "blocked",
    blocking_reasons: ["newsletter: needs_review"],
    ready_for_planner: true/false
)
    ↓
data/manifests/{topic_id}.json
```

## Why Not the Alternative?

**Why not update the manifest inside each generator?** Because generators shouldn't know about pipeline state. The script generator's job is to produce a script — it shouldn't also be responsible for updating a tracking document. If it did, a generator crash could leave the manifest in an inconsistent state. By rebuilding fresh from filesystem truth, the manifest is always correct regardless of how assets were created, modified, or deleted.

## Key Insight

**The manifest is a derived view, not a source of truth — it reads the filesystem and computes state, which means it can never drift from reality.**
