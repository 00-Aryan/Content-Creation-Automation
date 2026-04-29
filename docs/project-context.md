# Project Context: Content-Creation

## Project Purpose
This repository is a Python-based content factory designed for ML/AI students. It automates the pipeline from source ingestion to multi-format content generation, ensuring high-quality, grounded, and educational outputs.

## Target Audience
- **Primary:** ML/AI students looking for plain-English explanations of papers, tools, and news.
- **Secondary:** Educators and content creators in the AI space who need structured, source-linked briefs.

## Long-Term Pipeline Overview
1. **Source Ingestion:** Fetching from arXiv, AI blogs, and manual sources.
2. **Normalization:** Converting varied sources into a canonical `TopicItem` schema.
3. **Scoring:** Ranking topics based on student relevance, novelty, and credibility.
4. **Summarization:** Generating grounded, structured educational briefs.
5. **Script Generation:** Creating short-video scripts, carousels, and newsletters.
6. **Thumbnail Prompts:** Generating visual metaphors and prompts for assets.
7. **Posting Planner:** Scheduling and organizing the release of content assets.

## Current Phase: Pre-Implementation / Week 1 Preparation
We are currently in the **Bootstrap Phase**. The focus is on establishing the repository structure, documentation, schemas, and prompting rules to ensure safe and efficient AI-assisted development. No feature code has been implemented yet.

## Private-First Rollout Note
The first week of active implementation and the first few days of content generation will be **private-only**. This period is dedicated to:
- Validating logic and architectural assumptions.
- Tuning prompts for high-quality, non-hallucinated output.
- Ensuring the pipeline is stable before any public publishing.

## Engineering Principles
- **Correctness over Scale:** Reliable, grounded outputs are more important than high-volume generation.
- **Traceability:** Every piece of generated content must be traceable back to its original source.
- **Observability:** Extensive logging of scoring decisions and generation steps.
- **Staged Workflows:** Editorial steps are separate to reduce quality drift.

## Anti-Hallucination Philosophy
This project operates on a "Grounded-or-Nothing" basis:
- Never invent facts, paper claims, or benchmark values.
- If a source does not mention a detail, do not infer it.
- Mark uncertain or missing fields explicitly as `unknown` or `needs_review`.
- Separate raw extraction from generated interpretation at all times.

## Success in the First Month
- A working Python scaffold with a functional CLI.
- A stable ingestion pipeline for at least two trusted sources (e.g., arXiv).
- A scoring engine that successfully filters for student-relevant content.
- The ability to generate a source-grounded brief and at least one content asset (e.g., a short script) end-to-end.
- A clean, branch-based development history.
