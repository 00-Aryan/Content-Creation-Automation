---
name: architecture-review
description: Review architecture, module boundaries, coupling, dependency flow, and maintainability risks.
---

# Skill: Architecture Review

## Name
architecture-review

## Description
Reviews code for architecture concerns, boundary violations, and maintainability.

## Goal
Identify coupling, cross-layer leaks, and missing abstractions without modifying code.

## Procedure
1. Inspect the target module and nearby dependencies.
2. Check whether the UI layer calls storage or repository code directly.
3. Check whether business logic is isolated from infrastructure.
4. Check for tight coupling, duplicated logic, and untyped APIs.
5. Report findings with severity and concrete evidence.

## Constraints
- **Read-only**: Do not edit files.
- **Scoped**: Stay within the files explicitly under review.
- **No hallucinations**: Base findings on code in the repository.

## Output Format
A review report with:
- **Scope**
- **Findings**
- **Architectural Risks**
- **Recommended Actions**
