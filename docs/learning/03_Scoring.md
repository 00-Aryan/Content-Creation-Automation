# Chapter 3 — Scoring: How Topics Get Ranked

## The Question

Why does scoring exist as a separate stage? Why not just generate content for everything that comes in?

Because you can't generate briefs for 50 topics a day — API costs, time, and editorial quality all degrade. Scoring is the filter that decides which topics are worth the expensive downstream processing. Without it, the pipeline either processes everything (wasteful and noisy) or requires you to manually pick topics every day (defeats the purpose of automation).

## The Answer

Scoring takes staged `TopicItem`s, applies five weighted category scores from `config/scoring.yaml`, runs hard rejection filters (too short, missing source, duplicate title, score below threshold), and outputs `ScoredTopicItem`s with a `priority_score` between 0 and 100. Topics that fail hard filters get status `REJECTED` and are saved separately. The top-scoring items proceed to brief generation.

## Files in This Stage

### scoring/config.py
**Why it exists:** Loads and validates scoring weights from YAML so the engine never runs with invalid configuration.
**What it does:** Defines `ScoringConfig` with `RuleConfig` per category (weight + enabled flag). A model validator ensures all enabled weights sum to exactly 1.0 — if you change one weight without adjusting others, the system refuses to start rather than silently producing wrong scores.
**Key decision:** The weight-sum validation catches configuration errors at startup, not after scoring 200 items with broken weights.
**Connects to:** Receives scoring.yaml → provides validated config to ScoringEngine.

### scoring/engine.py
**Why it exists:** Orchestrates scoring rules and hard rejection filters in a single pass.
**What it does:** `ScoringEngine` initializes rules from config, then `score_items()` processes a batch: first applies hard filters (raw_text < 100 chars, missing source, duplicate title), then scores survivors, then rejects anything below 0.2 priority_score. Returns a dict with `"scored"` and `"rejected"` lists.
**Key decision:** Hard filters run *before* scoring — this avoids wasting computation on items that would be rejected regardless of their score. The duplicate check uses normalized titles within the batch to catch near-duplicates from the same feed.
**Connects to:** Receives List[TopicItem] from storage → sends scored/rejected ScoredTopicItems to storage.

### scoring/rules.py
**Why it exists:** Contains individual scoring heuristics as pluggable rule classes.
**What it does:** `RecencyRule` uses exponential decay (half-life configurable). `SourceQualityRule` maps source names to quality scores. `KeywordRule` does word-boundary regex matching against topic areas. `QualityRule` checks title length, description presence, and tag availability.
**Key decision:** Each rule is a class with a `score()` method returning 0-100, not a function — this allows rules to carry configuration state (half_life_days, source weights) without global variables.
**Connects to:** Called by ScoringEngine.score_item() → contributes weighted score to priority_score.

### scoring/base.py
**Why it exists:** Defines the abstract interface that all rules and the engine must follow.
**What it does:** `ScoringRule` ABC requires `score()` and `get_rule_name()`. The `apply()` method handles the enabled check and weight multiplication. `Scorer` ABC requires `_initialize_rules()` and provides `score_item()` which iterates rules and sums weighted scores.
**Key decision:** The `apply()` wrapper means individual rules never need to check if they're enabled or multiply by their own weight — that logic is centralized.
**Connects to:** Extended by ScoringEngine and all rule classes.

## Data Flow

```
data/staged/{id}.json (TopicItem)
    ↓
ScoringEngine.score_items([items])
    ↓
Hard filters:
  raw_text < 100 chars? → REJECTED (insufficient_text)
  source missing?       → REJECTED (missing_source)
  duplicate title?      → REJECTED (duplicate_title)
    ↓
Per-rule scoring:
  student_usefulness × 0.30
  novelty            × 0.25
  credibility        × 0.20
  explainability     × 0.15
  hook_potential     × 0.10
    ↓
priority_score < 0.2? → REJECTED (low_score)
    ↓
ScoredTopicItem(priority_score, per-category scores, status="scored")
    ↓
data/scored/{id}.json
```

## Why Not the Alternative?

**Why not hardcode the scoring logic?** Because content strategy changes. Today `student_usefulness` is weighted 0.30 — next month you might want to prioritize `novelty` at 0.35 for a series on cutting-edge papers. With YAML config, you change one number and re-run. With hardcoded logic, you're editing Python, re-testing, and hoping you didn't break the weight sum.

## Key Insight

**Scoring is a two-layer filter: hard rejections remove garbage immediately, soft scores rank the survivors — and both layers are configurable without touching code.**
