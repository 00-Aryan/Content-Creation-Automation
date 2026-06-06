---
name: test-planner
description: Generates test plans and pytest fixtures for content-creation modules.
---

## Coverage targets
- Pure functions: 100% line coverage
- Pipeline stages: integration tests with mocked inputs
- CLI: smoke tests only
- Storage: tmp_path fixtures

## Fixture patterns
- `mock_feed_response()` for RSS/Atom
- `mock_topic_item()` for normalization
- `mock_scored_item()` for scoring
- `tmp_storage()` for file system

## Test structure
tests/unit/
├── test_models.py
├── test_collectors.py
├── test_normalizers.py
├── test_scorers.py
└── test_storage.py

tests/integration/
├── test_ingestion_pipeline.py
└── test_scoring_pipeline.py



## Invocation
`/test-planner module_name` or `/test-planner pipeline`
