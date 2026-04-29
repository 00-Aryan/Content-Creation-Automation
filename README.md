# Content-Creation Factory

A Python-based content pipeline for ML/AI students. This repository automates the process of finding, ranking, and repurposing educational content from trusted technical sources.

## Current Status: Setup Phase
We are currently in the initial setup and bootstrapping phase.
- [x] Repository structure initialized.
- [x] Documentation and schemas defined.
- [ ] Week 1: Source ingestion implementation (In Progress).

## Planned Modules
1. **Collectors:** Feed loaders for arXiv, blogs, and repos.
2. **Normalizers:** Schema enforcement and data cleaning.
3. **Scoring Engine:** Student-centric relevance and novelty ranking.
4. **Brief Generator:** Source-grounded summarization.
5. **Asset Factory:** Multi-format script and prompt generation.
6. **Planner:** Content scheduling and release management.

## Repository Structure
```text
content-creation/
├── docs/               # Architecture, schemas, and rules
├── src/
│   └── content_creation/
│       ├── cli.py      # Main entry point
│       ├── collectors/ # Source-specific fetching logic
│       ├── models/     # Data schemas (Pydantic/Dataclasses)
│       └── ...
├── tests/              # Test suite
├── data/               # Raw and staged JSON storage
└── pyproject.toml      # Project configuration
```

## Branch Workflow
- All work happens in feature branches (e.g., `feature/source-ingestion`).
- Parallel development is guided by shared contracts in `docs/schema.md`.
- See `docs/branching-strategy.md` for more details.

## Setup
(Details will be added as implementation begins)
```bash
# Example setup
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---
*Note: This project is in its private-first validation window. No content is published automatically.*
