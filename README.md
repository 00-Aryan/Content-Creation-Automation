# Content-Creation Factory

A Python-based content pipeline for ML/AI students. This repository automates finding, scoring, and repurposing educational material from trusted technical sources into structured briefs and multi-format drafts, with local JSON storage and a manifest layer for downstream planning.

## Current Status

- **Week 3** of the internal roadmap is complete: generators for script, carousel, newsletter, and thumbnail prompt JSON; topic manifest builder; extended `data/` layout and CLI for briefs and manifests.
- **Week 4** is next: posting planner, review gates, dry-run publishing workflow, analytics placeholders, and release documentation (see `content-factory-implementation-plan.md` and `TASK_SPEC.md`).
- **Tests:** 81 passing — run with `uv run python -m pytest`.
- **Active branch:** `week2-feature-planning` (see `docs/branching-strategy.md` for workflow).

## Architecture Overview

End-to-end flow matches the seven stages in `docs/project-context.md`:

1. **Source ingestion** — RSS and configured feeds into raw and staged `TopicItem` JSON.
2. **Normalization** — canonical topic schema and validation on load.
3. **Scoring** — weighted rules engine plus post-score validation flags.
4. **Summarization** — Gemini-backed briefs from top scored topics (`prompts/summarize.md`).
5. **Script generation** — per-format prompts (`short_video`, `carousel`, `newsletter`) via `ScriptGenerator`.
6. **Carousel / newsletter / thumbnail prompts** — `CarouselGenerator`, `NewsletterGenerator`, and `ThumbnailGenerator` plus their Pydantic models and prompts.
7. **Manifests** — `ManifestBuilder` aggregates on-disk assets per topic for planner readiness (`ready_for_planner`).

Posting planner and public release steps are **Week 4**, not implemented in this tree.

## Repository Structure

```text
Content-Creation/
├── README.md
├── TASK_SPEC.md
├── CLAUDE.md
├── pyproject.toml
├── uv.lock
├── content-factory-implementation-plan.md
├── config/
│   ├── feeds.yaml
│   └── scoring.yaml
├── data/
│   ├── raw/
│   ├── staged/
│   ├── scored/
│   ├── briefs/
│   ├── scripts/
│   ├── carousels/
│   ├── newsletters/
│   ├── thumbnails/
│   └── manifests/
├── prompts/
│   ├── summarize.md
│   ├── short_video.md
│   ├── carousel.md
│   ├── newsletter.md
│   └── thumbnail.md
├── docs/
│   ├── branching-strategy.md
│   ├── project-context.md
│   ├── prompting-rules.md
│   ├── schema.md
│   └── voice-and-style.md
├── src/
│   └── content_creation/
│       ├── __init__.py
│       ├── cli.py
│       ├── ingestion.py
│       ├── manifest.py
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── rss.py
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── brief.py
│       │   ├── script.py
│       │   ├── carousel.py
│       │   ├── newsletter.py
│       │   └── thumbnail.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── topic.py
│       │   ├── brief.py
│       │   ├── script.py
│       │   ├── carousel.py
│       │   ├── newsletter.py
│       │   ├── thumbnail.py
│       │   └── manifest.py
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── config.py
│       │   ├── engine.py
│       │   ├── rules.py
│       │   └── validation.py
│       ├── storage/
│       │   └── local.py
│       └── utils/
│           ├── __init__.py
│           ├── config.py
│           └── logging.py
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_e2e_verification.py
    ├── test_generation_scaffold.py
    ├── test_ingestion.py
    ├── test_integration.py
    ├── test_manifest.py
    ├── test_models.py
    ├── test_scoring_config.py
    ├── test_scoring_rules.py
    ├── test_scoring_validation.py
    ├── test_storage.py
    └── test_utils.py
```

## Setup

### Prerequisites

- Python 3.10 or higher (see `pyproject.toml`).
- [uv](https://docs.astral.sh/uv/) for environments and commands.

### Installation

```bash
git clone <repository-url>
cd Content-Creation
uv sync --extra dev
```

Optional: install the package in editable mode for the `content-creation` console script (if configured in your environment):

```bash
uv pip install -e ".[dev]"
```

### API key

```bash
export GEMINI_API_KEY=your_key_here
```

Required for `generate-briefs` (and any future CLI that calls Gemini).

### Running the CLI

From the repository root (commands match `uv run python -m content_creation.cli --help`):

```bash
uv run python -m content_creation.cli --help
uv run python -m content_creation.cli --version
uv run python -m content_creation.cli -v <command> ...
```

Equivalent when the entry point is on your `PATH`:

```bash
uv run content-creation --help
```

### Running tests

```bash
uv run python -m pytest
uv run python -m pytest --tb=short -q
uv run python -m pytest tests/test_cli.py
```

### Code quality (optional dev tools)

```bash
uv run black src/ tests/
uv run isort src/ tests/
uv run mypy src/
```

## CLI Commands

Grouped by pipeline stage. Options are those defined in `src/content_creation/cli.py`.

### Ingestion

| Command | Purpose |
| --- | --- |
| `collect` | Ingest topics from sources (`--source <id>` or `--all`). |
| `status` | System and storage summary (staged counts, sources). |
| `list-topics` | List staged topics (`--limit`, optional `--status`). |
| `validate-items` | Confirm staged items validate against the topic schema. |

### Scoring

| Command | Purpose |
| --- | --- |
| `score-topics` | Score staged topics, validate, write to `data/scored/` (`--limit`). |
| `review-scores` | Inspect scored topics and flags (`--flagged-only`, `--min-score`, `--limit`). |
| `scoring-dashboard` | Aggregate metrics and flag breakdown. |

### Generation

| Command | Purpose |
| --- | --- |
| `generate-briefs` | Generate briefs for top scored topics via Gemini (`--top`, default 5). |

### Manifest

| Command | Purpose |
| --- | --- |
| `build-manifest` | Build and save one topic manifest (`--topic-id`, required). |
| `build-all-manifests` | Build and save manifests for all topics that have briefs. |

Global flags: `-h` / `--help`, `--version`, `-v` / `--verbose`.

## Week 4 Roadmap

- `config/publishing.yaml` and a **posting planner** module (format mix, cadence, freshness).
- **Review and approval** workflow before anything is treated as publishable.
- **Dry-run** private publishing cycle with exported plan and checklist (no auto-post).
- **Analytics-ready** metadata hooks (views, engagement placeholders).
- **GitHub release** documentation and tagging discipline.

Details: `content-factory-implementation-plan.md` (Week 4) and `TASK_SPEC.md`.

## Branch Workflow

- Work proceeds in **feature branches**; merge to `main` only when stable.
- Shared contracts live in `docs/schema.md` — coordinate schema changes across branches before merging.
- See `docs/branching-strategy.md` for branch naming and isolation practices.

---

*This project uses a private-first validation mindset: generated assets are grounded on stored sources; nothing is published automatically by this repository.*
