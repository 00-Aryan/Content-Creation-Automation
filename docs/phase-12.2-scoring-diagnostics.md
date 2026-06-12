# Phase 12.2 Scoring Diagnostics

## Baseline

- Test count before change: 985 passed
- Sample scored files checked: 20
- Sample scores before change: [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
- Unique score values before change: [50.0]

## Root Cause

In `src/content_creation/scoring/engine.py`, the scoring engine rules were initialized using a generic `SimpleRule` class. This class returned a static default/fallback score of `50.0` rather than running any specialized feature extraction or domain-specific scoring logic. Consequently, all scored topics received identical collapsed scores regardless of their characteristics, metadata, or source materials.

## Fix Strategy

1. Replaced the generic `SimpleRule` with specialized subclass rules inheriting from `ScoringRule`:
   - `StudentUsefulnessRule`: Scores based on target keywords (e.g. "student", "learn", "course"), topic category, and presence of tags.
   - `NoveltyRule`: Decays score over time (half-life of 30 days) from the publication timestamp, with bonuses for specific categories (Papers/Releases) or novelty terms.
   - `CredibilityRule`: Assigns base scores to reliable sources (arXiv, OpenAI, Hugging Face, etc.) and bonuses for valid URLs, author metadata, and raw text length.
   - `ExplainabilityRule`: Evaluates content formatting structure, tutorial/overview keywords, and raw text length.
   - `HookPotentialRule`: Grades the title length and matches high-engaging keywords (e.g. "breakthrough", "sota", "next-gen").
2. Mapped these rule classes in `ScoringEngine._initialize_rules()` so that the engine instantiates the correct class for each enabled rule in the configuration.
3. Aligned `quality_score` with `priority_score` in `ScoringEngine.score_item()` to ensure consistent terminology downstream.
4. Added test suite coverage in `tests/test_scoring_rules.py` proving that different inputs produce differentiated scores.

## Post-Fix Evidence

- Test count after change: 987 passed (all tests green)
- Sample scores after change: [81.23, 82.99, 83.49, 85.49, 87.6, 77.99, 93.1, 82.49, 52.0, 82.23, 82.23, 82.0, 54.5, 78.73, 0.0, 80.49, 67.82, 58.0, 80.49, 79.0]
- Unique score values after change: [0.0, 52.0, 54.5, 58.0, 67.82, 77.99, 78.73, 79.0, 80.49, 81.23, 82.0, 82.23, 82.49, 82.99, 83.49, 85.49, 87.6, 93.1]

## Risk Notes

The scoring rules are heuristic-based and run locally on the topic metadata. These scores serve as a triage gate before generation, but will need continued calibration as user interactions are recorded.
