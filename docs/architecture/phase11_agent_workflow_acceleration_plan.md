# Phase 11 — Agent Workflow Acceleration Plan

This document outlines the rationale, structure, and guidelines for deploying autonomous and semi-autonomous coding agents (such as Antigravity, Codex, and Claude-style agents) on the Content Creation Automation platform.

## Why `AGENTS.md` Was Added

As coding pipelines evolve, development is increasingly shared between human engineers and agentic AI systems. To prevent divergence, style issues, and architectural violations, the project requires a machine-readable yet human-inspectable "governance manual."

`AGENTS.md` serves as this stable root-level anchor. It sets:
- The authoritative setup, test, and quality commands.
- The 9 strict architectural boundaries (e.g., UI isolation, worker isolation, event-driven metrics).
- Guardrails to prevent unauthorized refactoring or credential leaks.

## Skill Inventory

The platform defines five discrete repository-local "skills" located in `.agents/skills/`:

1. **`run-phase`** — Standard execution protocol for implementing scoped features exactly as defined in the phase plans.
2. **`audit-result`** — Validation protocol to compare claims in reports against actual file contents and architectural constraints.
3. **`fix-and-verify`** — Surgical debugging protocol to resolve failing tests or warnings without modifying unrelated files.
4. **`security-audit`** — Read-only check for credentials, sensitive logs, or database isolation issues.
5. **`code-review`** — Analytical review to generate a maintainability backlog without modifying run-time behavior.

## When to Use Each Skill

The following table summarizes the triggers and boundaries for activating each agent skill:

| Skill | Triggering Event | Primary Objective | Permission Bounds |
| :--- | :--- | :--- | :--- |
| **`run-phase`** | Launching a new task or phase | Implement scoped feature | Write access (scoped to task) |
| **`audit-result`** | Completing a phase or PR review | Verify delivery & boundaries | Read-only & test runner |
| **`fix-and-verify`** | Test failure, warning, or lint bug | Resolve targeted issue | Write access (minimal files) |
| **`security-audit`** | Pre-release check / regular interval | Find secrets & log hazards | Read-only (never write/modify) |
| **`code-review`** | Code cleanup phase | Create backlog list | Read-only |

## Risks of Autonomous Agents

Employing agentic AI systems introduces specific operational risks:
- **Scope Creep**: Agents may attempt to fix unrelated "code smells," introducing regressions in verified legacy code.
- **Accidental Leakage**: Hardcoded API keys or credentials can be printed in agent logs, stdout, or pushed to repository commits.
- **Flaky Workflows**: Automatic retries or loops can waste computational resources or cause race conditions in shared environments.

## Local vs. Repo-Committed Skill Strategy

- **Repo-Committed Skills (Standard)**: The definitions in `.agents/skills/` are checked into Git. This ensures that any agent checking out the repository immediately understands the project rules, folder structures, and testing expectations.
- **Local Skills (Overrides)**: Local agent prompt overrides or secrets configuration files (e.g., `.agents/local_config.json`) must remain in `.gitignore`. This permits developer-specific overrides without impacting the master repository.

> [!IMPORTANT]
> **Security Guardrails & Agent Safety Note**
> Because autonomous coding agents (including the Antigravity agentic platform) possess full capabilities to read files, run terminal commands, and define subagents, strict operational guardrails must be followed:
> 1. **Secret Redaction**: Agents must never output, print, write to artifacts, or log raw credentials or environment variables (e.g., `GEMINI_API_KEY`).
> 2. **Supervised Execution**: All shell executions proposed by agents (such as database migrations, server startup, or test runs) must go through the user-approval sandbox. Running commands in the background should be carefully monitored.
> 3. **Sandboxed Tasks**: Direct curl requests or downloads of unverified executables are strictly prohibited to prevent supply chain compromises.
