# Content-Creation Factory

A Python-based content pipeline for ML/AI students. This repository automates the process of finding, ranking, and repurposing educational content from trusted technical sources.

## Current Status: Bootstrap Phase
We are currently in the bootstrap/setup phase.
- [x] Repository structure initialized.
- [x] Documentation and schemas defined.
- [x] Project foundation and CLI scaffold implemented.
- [ ] Week 1: Source ingestion implementation (Next).

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
│       ├── utils/      # Logging, config, and common helpers
│       ├── storage/    # Data persistence interfaces
│       ├── models/     # Data schemas (Pydantic/Dataclasses)
│       ├── collectors/ # Source-specific fetching logic
│       └── normalizers/ # Schema enforcement and data cleaning
├── tests/              # Test suite
├── data/               # Raw and staged JSON storage
└── pyproject.toml      # Project configuration
```

## Setup

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd content-creation
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e ".[dev]"
```

### Running the CLI

```bash
# Show help
content-creation --help

# Show version
content-creation --version

# Check status
content-creation status

# Collect (stub - not yet implemented)
content-creation collect --source arxiv
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/content_creation --cov-report=html

# Run specific test file
pytest tests/test_cli.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

## Branch Workflow
- All work happens in feature branches (e.g., `feature/source-ingestion`).
- Parallel development is guided by shared contracts in `docs/schema.md`.
- See `docs/branching-strategy.md` for more details.

---
*Note: This project is in its private-first validation window. No content is published automatically.*
