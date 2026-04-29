# Content Factory Implementation Plan

## Overview

This document defines a practical 4-week implementation roadmap for building a Python-based AI/ML student content factory inside a `content-creation` project directory. The target system is designed to collect topics from trusted sources, summarize them, generate scripts and thumbnail prompts, and organize a posting plan through a branch-based Git workflow that supports parallel development. The plan assumes the first 3-4 days are private and focused on logic, architecture, prompt safety, and output quality before public publishing starts.[1][2][3]

The system is intentionally structured as an editorial pipeline rather than a single generator, because staged workflows are more reliable for AI-assisted educational publishing and reduce quality drift over time.[1][2] The audience is ML/AI students, so the pipeline prioritizes student usefulness, plain-English explanation, source credibility, and anti-hallucination controls over raw content volume.[1][4][5]

## Core principles

### Product goal

The repository should produce reusable content assets from one source item: a structured brief, a short-form script, a carousel outline, thumbnail prompts, and a scheduled posting recommendation. This repurposing model increases output leverage and reduces the need to constantly hunt for new topics.[2][3]

### Development philosophy

The first implementation pass should optimize for correctness, observability, and constraints rather than scale. The most important risk early on is not slow code but unreliable outputs, weak grounding, and prompt drift that causes fabricated claims.[1][4][5]

### Git workflow

A branch-per-feature model fits this project well because scraper, scorer, summarizer, script generator, planner, and reviewer can be developed in parallel with clear contracts. Parallel branch development also reduces coupling when Claude Code is used to accelerate implementation, as long as schemas and interfaces are frozen before parallel work begins.[1]

## Recommended repository shape

```text
content-creation/
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── docs/
│   ├── architecture.md
│   ├── prompting-rules.md
│   ├── schema.md
│   └── branching-strategy.md
├── config/
│   ├── feeds.yaml
│   ├── sources.yaml
│   ├── scoring.yaml
│   └── publishing.yaml
├── data/
│   ├── raw/
│   ├── staged/
│   ├── scored/
│   ├── briefs/
│   ├── scripts/
│   ├── thumbnails/
│   └── calendars/
├── prompts/
│   ├── summarize.md
│   ├── short_video.md
│   ├── carousel.md
│   ├── newsletter.md
│   ├── thumbnail.md
│   └── review.md
├── src/
│   └── content_creation/
│       ├── __init__.py
│       ├── cli.py
│       ├── models/
│       ├── collectors/
│       ├── normalizers/
│       ├── scoring/
│       ├── generation/
│       ├── planning/
│       ├── review/
│       ├── storage/
│       └── utils/
├── tests/
│   ├── test_collectors.py
│   ├── test_scoring.py
│   ├── test_generation.py
│   └── fixtures/
└── output/
```

This structure keeps prompts, configuration, content data, and source code separate, which makes branch merging easier and lets AI-assisted coding work against clearer file boundaries.[1][2][3]

## Non-negotiable constraints

These constraints should be documented before coding starts so Claude Code does not infer behavior that has not been approved:

- Never invent facts, paper claims, benchmark values, release dates, or author intent.
- Never summarize a source that was not actually fetched, stored, or quoted in the pipeline.
- Never convert speculation into statement form.
- Always retain the original source URL and publication date with each item.
- Always mark uncertain, missing, or low-confidence fields explicitly as `unknown` or `needs_review`.
- Always separate raw extraction from generated interpretation.
- Never publish automatically until review checks pass.
- Never let one module silently re-score or rewrite another module's outputs without logging it.
- Always preserve an audit trail from source item to final content asset.[1][4][5]

These rules reflect a standard quality-control pattern for AI workflows: constrain generation, preserve provenance, and keep human review in the loop.[1][5]

## Data contracts

Before parallel branches start, define shared schemas.

### Topic item schema

```json
{
  "id": "string",
  "title": "string",
  "url": "string",
  "source": "string",
  "published_at": "ISO-8601 string",
  "author": "string | null",
  "raw_text": "string",
  "excerpt": "string | null",
  "category": "paper | repo | release | concept | news | tool",
  "topic_tags": ["string"],
  "credibility_score": 0,
  "student_relevance_score": 0,
  "novelty_score": 0,
  "explainability_score": 0,
  "hook_score": 0,
  "priority_score": 0,
  "status": "raw | staged | scored | approved | rejected",
  "notes": "string | null"
}
```

### Brief schema

```json
{
  "topic_id": "string",
  "why_it_matters": "string",
  "plain_english_summary": ["string", "string", "string"],
  "student_takeaway": "string",
  "analogy": "string",
  "limitation": "string",
  "audience_fit": "string",
  "recommended_formats": ["short_video", "carousel", "newsletter"]
}
```

### Script schema

```json
{
  "topic_id": "string",
  "format": "short_video | carousel | newsletter",
  "hook": "string",
  "script_sections": ["string"],
  "cta": "string",
  "claims_used": ["string"],
  "source_links": ["string"],
  "review_status": "draft | needs_review | approved"
}
```

### Thumbnail prompt schema

```json
{
  "topic_id": "string",
  "title_text": "string",
  "supporting_text": "string",
  "visual_metaphor": "string",
  "style": "string",
  "negative_prompt": ["string"],
  "readability_notes": "string"
}
```

Schema-first design is critical here because the project will be developed in parallel branches and prompt-driven generation can become inconsistent without a shared contract.[1][2][3]

## Branching strategy

The repository should use a stable `main` branch, an optional `develop` integration branch, and short-lived feature branches. A practical setup is:

| Branch | Purpose |
|---|---|
| `main` | Stable, merge-ready code only |
| `develop` | Optional integration branch for combined testing |
| `feature/bootstrap-project` | Python project setup, config, CLI shell |
| `feature/source-ingestion` | Feed loading, scraping, normalization |
| `feature/topic-scoring` | Ranking logic and filters |
| `feature/brief-generation` | Summaries and structured educational briefs |
| `feature/script-generation` | Shorts, carousels, newsletter templates |
| `feature/thumbnail-prompts` | Prompt pack generation for visual assets |
| `feature/posting-planner` | Calendar and publishing recommendation logic |
| `feature/review-guardrails` | Hallucination checks, approval state, validation |
| `feature/tests-observability` | Logging, fixtures, regression tests |

Parallel implementation will work only if branches are not allowed to change shared schemas casually. Any schema change should be proposed through one branch, documented in `docs/schema.md`, and then rebased into dependent branches.[1][3]

## Private-first launch note

Keeping the account private for the first 3-4 days is a good decision because early output quality is usually unstable until prompts, filters, and style rules are tuned. That private period should be used to generate sample outputs, compare them against source material, and tighten review criteria before public publishing begins.[1][4][5]

A strong rule for that private window is to publish nothing automatically, even if the pipeline appears to work. The goal is validation of logic, not audience growth, during those first days.[1][5]

## Week 1 — Foundation, contracts, and ingestion

### Week 1 objective

Build the project skeleton, define schemas, set up Git branching, and implement the source ingestion pipeline that collects and normalizes trusted source items. This week exists to make later AI-assisted generation safer by grounding everything in structured inputs.[1][6][7]

### Outcomes for Week 1

By the end of Week 1, the repository should be able to fetch at least a few trusted sources, normalize them into a common schema, save them locally, and expose them through a simple CLI. The system does not need to generate polished content yet; it only needs to produce clean, inspectable topic records.[1][6][7]

### Tasks

#### Day 1 — Bootstrap

- Create `content-creation` directory and initialize Git.
- Create `main` and feature branch plan.
- Set up Python environment with either `venv`, Poetry, or `uv`.
- Add `README.md`, `.gitignore`, `.env.example`, `requirements.txt` or `pyproject.toml`.
- Create base folders: `src`, `tests`, `data`, `config`, `prompts`, `docs`, `output`.
- Add a simple CLI entry point like `python -m content_creation.cli`.
- Define coding rules for Claude Code in `docs/prompting-rules.md`.

#### Day 2 — Architecture and schemas

- Write `docs/architecture.md` describing the pipeline stages.
- Write `docs/schema.md` with all JSON contracts.
- Define source trust levels in `config/sources.yaml`.
- Add logging and deterministic file naming rules.
- Decide how IDs are generated, such as URL hash plus date.
- Freeze shared schemas before parallel branches expand.

#### Day 3 — Source registry

- Add feeds for arXiv RSS/Atom categories relevant to ML/AI students, since arXiv supports categorized feeds that are useful for research monitoring.[7]
- Add placeholders for official AI company blogs and manual input files.
- Implement a source registry loader.
- Build a `collector` interface with common methods such as `fetch()`, `parse()`, and `normalize()`.

#### Day 4 — Ingestion pipeline

- Implement at least one RSS/Atom collector.
- Normalize fields to the `TopicItem` schema.
- Save raw responses to `data/raw/`.
- Save normalized items to `data/staged/`.
- Add duplicate detection based on URL and normalized title.
- Add source metadata preservation.

#### Day 5 — Validation and CLI

- Create commands such as:
  - `collect --source arxiv`
  - `collect --all`
  - `list-topics --limit 20`
  - `validate-items`
- Add schema validation using Pydantic or dataclasses plus validators.
- Reject malformed records cleanly instead of silently fixing them.

#### Day 6 — Test and review

- Write fixture-based tests for collectors.
- Create 10-20 sample items.
- Inspect edge cases: missing dates, malformed feeds, duplicate titles, empty content.
- Add a small report that shows counts by source and category.

#### Day 7 — Lock week 1 deliverables

- Merge only after schema and output review.
- Tag an internal milestone.
- Record lessons in `docs/architecture.md`.
- Freeze any interface used by Week 2 branches.

### Week 1 deliverables

- Working Python project scaffold.
- Source registry and ingestion CLI.
- Normalized topic storage.
- Schema validation.
- Tests for basic ingestion.
- Internal documentation for branch-safe development.

## Week 2 — Scoring, filtering, and brief generation

### Week 2 objective

Convert raw topics into prioritized educational candidates and then into structured briefs that can support downstream script writing. This week determines what enters the content system and how clearly it is framed for students.[1][2][4]

### Outcomes for Week 2

By the end of Week 2, the system should rank topics, reject low-value or noisy items, and generate a grounded educational brief for each approved topic. Each brief should explain why the topic matters for students and what angle should be used for content creation.[1][2]

### Tasks

#### Day 8 — Scoring design

- Create scoring config in `config/scoring.yaml`.
- Implement weighted logic for:
  - student usefulness,
  - novelty,
  - credibility,
  - explainability,
  - hook potential.[1][2][4]
- Make weight changes config-driven, not hardcoded.
- Document how each field is computed.

#### Day 9 — Scoring engine

- Build a scoring module that reads staged topics and produces `priority_score`.
- Separate hard filters from soft scores.
- Add rejection flags such as:
  - too little source text,
  - duplicate or near-duplicate topic,
  - low credibility source,
  - too advanced for student audience,
  - no clear takeaway.

#### Day 10 — Topic queueing

- Create `approve`, `reject`, and `review` states.
- Add a CLI for queue operations.
- Implement top-N export for the day.
- Add logs explaining why a topic was ranked or rejected.

#### Day 11 — Brief design

- Finalize `Brief` schema.
- Draft prompt instructions for grounded summarization.
- Explicitly require the generator to use only extracted source material.
- Add anti-hallucination guidance such as: “If the source does not mention it, do not infer it.”

#### Day 12 — Brief generator

- Build a summarization pipeline that produces:
  - why it matters,
  - 3-bullet plain-English summary,
  - student takeaway,
  - analogy,
  - limitation or caution,
  - audience fit,
  - recommended formats.[8][2]
- Save briefs to `data/briefs/`.
- Attach source URLs and extracted claim spans where possible.

#### Day 13 — Quality checks

- Add validation checks for empty summaries, unsupported claims, duplicated bullets, and too much jargon.
- Build a review command to flag briefs with weak grounding.
- Manually inspect at least 15 generated briefs.

#### Day 14 — Lock week 2 deliverables

- Merge scoring and brief-generation branches only after reviewed samples pass.
- Record scoring thresholds that worked best.
- Freeze brief format so Week 3 can depend on it.

### Week 2 deliverables

- Configurable topic scoring engine.
- Topic approval queue.
- Brief generation module.
- Reviewable, source-grounded educational briefs.
- CLI commands for scoring and brief inspection.

## Week 3 — Script generation and thumbnail prompt engine

### Week 3 objective

Transform approved briefs into channel-ready content drafts: short scripts, carousel outlines, newsletter blocks, and thumbnail prompts. This week is about format packaging, not research.[2][3][5]

### Outcomes for Week 3

By the end of Week 3, the system should be able to take one approved brief and generate multiple asset types with consistent voice, factual grounding, and student-friendly framing. Each asset should retain a link back to the original topic and brief.[2][3]

### Tasks

#### Day 15 — Voice and style rules

- Write a house style guide in `docs/prompting-rules.md`.
- Define tone rules: plain language, non-hype, practical, student-first.
- Create banned phrase lists such as overly generic AI-marketing language.
- Define CTA categories: follow, save, comment, read, build.

#### Day 16 — Short video script generator

- Create a short-form script template with:
  - hook,
  - context,
  - explanation,
  - practical relevance,
  - CTA.[3]
- Limit length to target speaking duration.
- Add rules for readability aloud.
- Add checks for awkward repetition and overlong sentences.

#### Day 17 — Carousel generator

- Create a slide-by-slide generator:
  - slide 1 hook,
  - slide 2 context,
  - slides 3-6 teaching arc,
  - slide 7 example,
  - slide 8 takeaway or CTA.[2][3]
- Ensure each slide stays concise enough for mobile reading.
- Add title-length constraints.

#### Day 18 — Newsletter/digest generator

- Build a weekly digest formatter.
- Combine multiple approved topics into one structured update.
- Add categories such as “What happened,” “Why it matters,” and “Student takeaway.”[8][2][4]
- Keep newsletter output modular so a single item can also be reused elsewhere.

#### Day 19 — Thumbnail prompt system

- Build a prompt generator that outputs:
  - title text,
  - supporting text,
  - visual metaphor,
  - style direction,
  - negative prompt,
  - readability note.[5]
- Add explicit anti-cliche rules such as avoiding robots, neon brains, and generic futuristic art when it is not conceptually relevant.[5]

#### Day 20 — Asset linking and metadata

- Ensure every script and thumbnail prompt references `topic_id` and `brief_id`.
- Store generation timestamps and prompt version.
- Add a manifest file per topic showing all created assets.

#### Day 21 — Lock week 3 deliverables

- Review 10 generated asset packs end-to-end.
- Test whether a single topic can reliably become a short, carousel, and newsletter snippet.[2][3]
- Merge only after manual content review.

### Week 3 deliverables

- Short-video script generator.
- Carousel generator.
- Newsletter block generator.
- Thumbnail prompt generator.
- Topic asset manifest system.

## Week 4 — Posting planner, review system, and release workflow

### Week 4 objective

Build the publishing logic around the content assets: scheduling suggestions, review gates, analytics placeholders, and a release workflow suitable for gradual public rollout. This week turns the generator into an actual content factory.[1][9][10]

### Outcomes for Week 4

By the end of Week 4, the repository should be able to recommend what to post, when to post it, and in what format, while requiring review approval before anything is treated as publishable. The result should be an operational system, not just a drafting tool.[1][9]

### Tasks

#### Day 22 — Posting strategy rules

- Create `config/publishing.yaml`.
- Add cadence rules for your early-stage plan.
- Use a manageable weekly target such as 3 shorts, 2 carousels, 1 deep explainer, 1 digest, rather than chasing excessive volume immediately.[9]
- Add logic for content diversity across pillars.

#### Day 23 — Content planner

- Build a planner that selects from approved assets based on:
  - freshness,
  - topic diversity,
  - format mix,
  - urgency,
  - audience value.[1][9]
- Output a 7-day plan and a 30-day rolling plan.
- Add tags such as `urgent_update`, `evergreen`, `beginner_friendly`, `advanced`.

#### Day 24 — Review and approval guards

- Build a validation step before scheduling.
- Add checks for:
  - missing sources,
  - unsupported claims,
  - duplicated content angles,
  - overly technical language,
  - weak CTA,
  - title mismatch.
- Require explicit status changes like `draft -> reviewed -> approved`.

#### Day 25 — Analytics-ready structure

- Add placeholders for performance data such as views, saves, clicks, comments, and watch time.
- Store post IDs and asset IDs together.
- Prepare for future feedback loops where high-performing formats influence ranking and scripting.

#### Day 26 — Dry-run publishing workflow

- Run a dry 7-day content cycle privately.
- Generate the week’s asset packs.
- Review them manually.
- Adjust prompts and scoring based on weak outputs.
- Do not auto-post; only export a planner file and human-readable checklist.

#### Day 27 — GitHub release readiness

- Clean repo structure.
- Improve README with setup and branch instructions.
- Document environment variables and source configuration.
- Add sample commands and expected outputs.
- Add contribution notes for future branches.

#### Day 28 — Public rollout checkpoint

- Review results from private testing.
- Decide what should remain manual and what can be automated.
- Merge the final release set.
- Tag `v0.1.0` or equivalent.
- Start public posting only after review quality is stable.[1][5]

### Week 4 deliverables

- Posting planner.
- Review and approval state machine.
- Dry-run publishing workflow.
- Analytics-ready metadata layer.
- GitHub-ready documentation.

## Suggested CLI commands

These commands will keep the project operational and branch-friendly:

```bash
python -m content_creation.cli collect --all
python -m content_creation.cli validate-items
python -m content_creation.cli score-topics
python -m content_creation.cli list-topics --status scored --limit 20
python -m content_creation.cli generate-briefs --top 10
python -m content_creation.cli generate-scripts --format short_video --top 5
python -m content_creation.cli generate-scripts --format carousel --top 5
python -m content_creation.cli generate-thumbnails --top 10
python -m content_creation.cli plan-week
python -m content_creation.cli review-report
```

A CLI-first workflow is useful because it makes each stage testable, automatable, and easier to compare across branches.[1][2]

## Guardrails for Claude Code

To reduce hallucination and overreach while using Claude Code, add explicit implementation rules in your repo docs and prompt files:

- Do not create fields not present in the schema.
- Do not rename files or directories unless requested.
- Do not infer source metadata not found in input.
- Do not replace config-driven values with hardcoded assumptions.
- Do not silently change prompt templates used by other branches.
- Always output structured logs for generated assets.
- If a value is unavailable, return `unknown`.
- If content is weakly grounded, return `needs_review` instead of polishing it into confidence.
- Never optimize away traceability for convenience.[1][4][5]

This is especially important in a parallel branch workflow, where AI-generated edits can easily drift away from agreed contracts if constraints are not written down.[1][3]

## Review checklist

Before merging any feature branch, use this checklist:

- Does the branch change shared schema?
- Are outputs deterministic enough to review?
- Is every generated asset traceable to a source item?
- Are unknown values explicit?
- Are rejection reasons logged?
- Are prompts stored version-wise?
- Are tests present for the main code path?
- Does the branch avoid hidden assumptions?
- Can another branch consume the outputs without guessing structure?

## First public week plan

After the private logic-validation window, the first public week should favor quality over intensity. A practical rollout is 2 shorts, 1 carousel, 1 update post, and 1 mini digest compiled from already reviewed materials. This is slower than aggressive social advice, but it better fits a new educational content system still stabilizing its output quality.[9][10]

## Closing guidance

This project will succeed if it behaves like a source-grounded editorial system rather than a prompt toy. The safest order is: reliable ingestion, explicit scoring, grounded briefing, controlled generation, human review, then posting.[1][2][5]

The most important implementation decision is to freeze interfaces early and make every branch respect them. That one discipline will let Claude Code speed up development without turning the repository into a guessing machine.[1][3]