---
name: project-orchestrator
description: Coordinate project state, roadmap, current phase, next actions, backlog, and cross-document consistency.
---

# Skill: Project Orchestrator

## Name
project-orchestrator

## Description
Keeps the project’s control documents synchronized.

## Goal
Maintain consistency between the queue, task specs, backlog, and phase docs.

## Procedure
1. Read the authoritative project-control documents.
2. Compare task state, backlog state, and phase state.
3. Detect contradictions, missing links, and stale references.
4. Report corrective actions only when explicitly asked.

## Constraints
- **No implementation work**.
- **No silent queue changes**.
- **No unapproved document rewrites**.

## Output Format
- **Control-Doc Alignment**
- **Drift**
- **Recommended Corrections**
