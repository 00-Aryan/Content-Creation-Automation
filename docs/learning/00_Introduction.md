# Why This Project Exists

## The Origin Story

Every morning you were doing the same thing: open arXiv, scan Twitter, check a few blogs, skim Hacker News. You were looking for the one or two ML/AI developments worth explaining to students. The problem wasn't finding content — it was that the process was manual, repetitive, and produced inconsistent results. Some days you'd find three great topics. Other days you'd waste an hour and find nothing usable.

The insight was simple: **a single, highly constrained pipeline with a strict "grounded-or-nothing" rule beats a dozen noisy feeds.** Instead of you being the bottleneck at every stage — finding, evaluating, summarizing, scripting, scheduling — you built a system where each stage is automated, validated, and independently replaceable.

## What This Book Is

This is not a Python tutorial. This is an architecture document written as a learning book. It explains *why* your pipeline is built the way it is — the decisions behind the code, the alternatives you rejected, and the contracts that hold everything together.

Each chapter covers one pipeline stage. You can read them in order to trace a topic from RSS feed to analytics record, or jump to any chapter independently.

## The Full Pipeline Map

```
RSS/arXiv Feeds
    ↓
[1] INGESTION → TopicItem (data/staged/)
    ↓
[2] SCORING → ScoredTopicItem (data/scored/)
    ↓
[3] BRIEF GENERATION → Brief (data/briefs/)
    ↓
[4] ASSET GENERATORS → Script, Carousel, Newsletter, ThumbnailPrompt
    ↓                   (data/scripts/, data/carousels/, data/newsletters/, data/thumbnails/)
[5] MANIFEST → TopicManifest (data/manifests/)
    ↓
[6] REVIEW → ReviewStatus state machine (updates asset JSON files)
    ↓
[7] POSTING PLANNER → WeeklyCalendar (data/calendars/)
    ↓
[8] DRY RUN → DryRunReport (data/dryruns/)
    ↓
[9] ANALYTICS → PostAnalytics (data/analytics/)
```

## How to Navigate

| Chapter | Stage | Core Question |
|---------|-------|---------------|
| 01 | Foundation | Why do models exist before any code runs? |
| 02 | Ingestion | How does raw XML become a validated TopicItem? |
| 03 | Scoring | How do topics get ranked without human judgment? |
| 04 | Brief Generation | How does the LLM summarize without hallucinating? |
| 05 | Asset Generators | How does one brief become four content formats? |
| 06 | Manifest | How does the pipeline know what's done and what's missing? |
| 07 | Review | Why does a human gate exist in an automated system? |
| 08 | Posting Planner | How does scheduling enforce content diversity? |
| 09 | Dry Run | Why validate before publishing instead of just publishing? |
| 10 | Analytics | Why build measurement infrastructure before you have data? |
| 11 | Full Picture | How does one topic flow through every stage end to end? |

## The Underlying Philosophy

Three principles run through every chapter:

1. **Schema-first:** Freeze the data contracts, then build stages in parallel. If `TopicItem` changes, everything downstream knows immediately.
2. **Grounded-or-nothing:** If a source doesn't state it, the pipeline doesn't infer it. Missing data is `"unknown"`, never guessed.
3. **Config-driven:** Scoring weights, publishing targets, and diversity rules live in YAML. The code executes strategy; it doesn't define it.
