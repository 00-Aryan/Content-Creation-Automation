---
name: code-review
description: Review current code changes for correctness, maintainability, test coverage, regressions, and architectural drift.
---

# Skill: Code Review

## Name
code-review

## Description
Reviews code changes against project rules and surfaces risks.

## Goal
Find correctness bugs, regressions, weak abstractions, and missing tests before merge.

## Procedure
1. Read the diff and surrounding context.
2. Check behavior, tests, and error handling.
3. Check architectural boundaries and scope compliance.
4. Note any security concerns.
5. Report findings in severity order.

## Constraints
- **Read-only**.
- **Do not refactor or patch**.
- **Do not assume missing context**; verify from code.

## Output Format
- **Findings**
- **Open Questions**
- **Change Summary**
