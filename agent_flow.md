# Agent Flow Map
Generated: 2026-06-07

## Directory Structure
.agents/skills/architecture-review/SKILL.md
.agents/skills/audit-result/SKILL.md
.agents/skills/backlog-manager/SKILL.md
.agents/skills/code-review/SKILL.md
.agents/skills/drift-check/SKILL.md
.agents/skills/fix-and-continue/SKILL.md
.agents/skills/fix-and-verify/SKILL.md
.agents/skills/new-phase/SKILL.md
.agents/skills/phase-closeout/SKILL.md
.agents/skills/project-orchestrator/SKILL.md
.agents/skills/run-next-task/SKILL.md
.agents/skills/run-phase/SKILL.md
.agents/skills/security-audit/SKILL.md

---

## Skills Inventory

### architecture-review
- File: .agents/skills/architecture-review/SKILL.md
- Trigger: Manual invocation or called by other agent skills (no explicit trigger phrase, name is `architecture-review`)
- Reads: Target module and nearby dependencies
- Writes/Calls: A review report
- State: PARTIAL
- Notes: Standard checklist for boundary checking, tight coupling, and code concerns. Lacks automation script support.

### audit-result
- File: .agents/skills/audit-result/SKILL.md
- Trigger: Called by other skills (like security-audit/architecture-review) to structure findings
- Reads: Source audit notes
- Writes/Calls: Structured audit issues (finding, severity, evidence, impact, recommendation)
- State: COMPLETE
- Notes: Purely formatting utility to transform notes into prioritized backlog-ready issues.

### backlog-manager
- File: .agents/skills/backlog-manager/SKILL.md
- Trigger: Manual invocation or called by project-orchestrator
- Reads: Backlog source document or task card
- Writes/Calls: Organized backlog state report (item ID, severity, phase, status, criteria)
- State: PARTIAL
- Notes: Documentation-only skill. Lacks automated sync, verification, or validation tools.

### code-review
- File: .agents/skills/code-review/SKILL.md
- Trigger: Manual invocation or run-next-task verification step
- Reads: Git diff and surrounding source code context
- Writes/Calls: Code review report (findings, open questions, change summary)
- State: PARTIAL
- Notes: Read-only check for correctness, regression, boundaries, and security. Lacks automated diff inspection scripts.

### drift-check
- File: .agents/skills/drift-check/SKILL.md
- Trigger: `$drift-check`
- Reads: `docs/project-context.md`, `AGENTS.md`, `CLAUDE.md`, `TASK_SPEC.md`, `WORK_QUEUE.md`, git history, python code search pattern scans, `docs/backlog/issues.md`, and test suites
- Writes/Calls: Outputs a drift report; appends CRITICAL drift findings to `docs/backlog/issues.md` if found; runs pytest and git log commands
- State: COMPLETE
- Notes: Highly defined execution sequence with detailed integrity check commands.

### fix-and-continue
- File: .agents/skills/fix-and-continue/SKILL.md
- Trigger: `$fix-and-continue TASK-NNN`
- Reads: `docs/tasks/task_NNN.md` (metadata), `WORK_QUEUE.md` status, baseline tests (for Type A)
- Writes/Calls: Scoped task files, updates `WORK_QUEUE.md` and task card status, pushes files via GitHub MCP `mcp__github.push_files`, runs pytest, git diff, and secret scanner
- State: COMPLETE
- Notes: Restricts agent to executing a single explicitly approved remediation task with strict MCP commit controls.

### fix-and-verify
- File: .agents/skills/fix-and-verify/SKILL.md
- Trigger: Called by other skills/agents when a bug is identified
- Reads: Task/issue description, scoped files
- Writes/Calls: Scoped file fixes, validation tests
- State: DUPLICATE
- Notes: Overlaps significantly with `fix-and-continue` but lacks work queue integration, GitHub MCP constraints, and strict preflight/commit structure.

### new-phase
- File: .agents/skills/new-phase/SKILL.md
- Trigger: `$new-phase <phase description>`
- Reads: `WORK_QUEUE.md` (highest task number), `TASK_SPEC.md`, `docs/tasks/` (existing files), `docs/architecture/` (most recent report), `docs/backlog/issues.md`
- Writes/Calls: `docs/tasks/task_NNN.md` files (max 5 per phase), updates `WORK_QUEUE.md`, pushes files via GitHub MCP `mcp__github.push_files`
- State: COMPLETE
- Notes: Enforces atomic, bounded, verifiable, small, and ordered task card templates.

### phase-closeout
- File: .agents/skills/phase-closeout/SKILL.md
- Trigger: Called at end of phase
- Reads: Phase task list, expected deliverables, validation results
- Writes/Calls: Closeout summary report (phase status, verified deliverables, open risks, next phase readiness)
- State: PARTIAL
- Notes: Overlaps with `drift-check` and `project-orchestrator`. General checklist with no automation scripts.

### project-orchestrator
- File: .agents/skills/project-orchestrator/SKILL.md
- Trigger: Manual or automated sync checks
- Reads: Project control docs (`WORK_QUEUE.md`, `TASK_SPEC.md`, backlog documents, phase docs)
- Writes/Calls: Alignment/drift/corrective action report
- State: PARTIAL
- Notes: Focuses on synchronizing control docs but relies on manual checks.

### run-next-task
- File: .agents/skills/run-next-task/SKILL.md
- Trigger: `$run-next-task`
- Reads: `WORK_QUEUE.md`, `docs/tasks/task_NNN.md` (local or via MCP), baseline tests (pytest), local workspace files
- Writes/Calls: Updates `docs/tasks/task_NNN.md` and `WORK_QUEUE.md` status, executes code implementation, validates changes, pushes files via GitHub MCP `mcp__github.push_files` in a single commit
- State: COMPLETE
- Notes: Primary automation driver for executing queue tasks. Enforces strict baseline test comparisons and single-commit rules.

### run-phase
- File: .agents/skills/run-phase/SKILL.md
- Trigger: Called to run a named phase
- Reads: Phase plan, task cards, validation scripts/configs
- Writes/Calls: Task executions, updates control documents
- State: DUPLICATE
- Notes: Overlaps with `run-next-task` and `new-phase`. Running a phase is implicitly driven by repeatedly executing `run-next-task`.

### security-audit
- File: .agents/skills/security-audit/SKILL.md
- Trigger: `$security-audit`
- Reads: Git history (`git log`), working tree files (`git grep`), gitignore configuration, `.env.example`, `.pre-commit-config.yaml`, and CI workflows
- Writes/Calls: Security audit report; does not modify files (read-only)
- State: COMPLETE
- Notes: Comprehensive local security scan utility covering secrets, gitignore, and pre-commit hook gaps.

---

## Current Flow (what actually happens end to end)

```
       $new-phase <phase description>
                    │
                    ▼ (Appends tasks to WORK_QUEUE.md, writes docs/tasks/task_NNN.md)
              WORK_QUEUE.md
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  $run-next-task     $fix-and-continue TASK-NNN
        │                       │
        └───────────┬───────────┘
                    │
                    ▼ (Type A baseline pytest checks)
            Local Workspace
                    │
                    ▼ (Updates WORK_QUEUE.md and docs/tasks/task_NNN.md status to DONE)
         mcp__github.push_files (GitHub MCP Commit)
                    │
                    ├──────────────────────┐
                    ▼                      ▼
               $drift-check         $security-audit
                    │                      │
                    └───────────┬──────────┘
                                │
                                ▼ (Finds issues)
                      docs/backlog/issues.md
                                │
                                ▼
                         phase-closeout (Final check to close phase)
```

1. **Phase Setup**: The workflow begins when the user runs `$new-phase <phase description>`. This reads the project state and backlog, creating up to 5 atomic task cards (`docs/tasks/task_NNN.md`) and appending them to `WORK_QUEUE.md`.
2. **Task Execution**: Tasks are processed sequentially. Running `$run-next-task` automatically picks the next runnable task from `WORK_QUEUE.md`, validates the setup, executes code modifications, runs validation checks, and performs tests. Alternatively, targeted bug fixes can be run via `$fix-and-continue TASK-NNN`.
3. **Task Completion**: After successful validation, the agent updates statuses in the task card and `WORK_QUEUE.md`, committing all task-related changes in a single push via GitHub MCP.
4. **Project Audit**: After completing tasks or phases, `$drift-check` or `$security-audit` is run to detect goal drift, architectural violations, or credential exposure. Structured results are recorded in the backlog via `audit-result` and `backlog-manager`.
5. **Phase Closeout**: Finally, the phase is checked for completion and next-phase readiness using the `phase-closeout` criteria.

---

## What Is Missing

- **Automated Queue Dependency Checker**: No dedicated skill exists to automatically parse the `Depends On` column in `WORK_QUEUE.md`, detect cycles, or warn of missing task card dependencies before executing.
- **Automated Source Grounding/Hallucination Scanner**: There is no skill file to check whether the LLM-generated assets (briefs, scripts, newsletters) are strictly grounded in technical source inputs.
- **Git Remote Sync Validator**: Since agents are forbidden from using local Git commits/pushes (must use GitHub MCP `mcp__github.push_files`), there is no skill to verify that the local workspace and remote repository states are in sync.
- **Pre-commit / Secret Scan Automation**: No automated skill wraps the secret scanner check defined in `AGENTS.md` (which is currently run as copy-paste inline python code).
- **Automated Code Quality & Type Enforcement**: No skill automated runner exists to enforce code linting/formatting (`black`, `isort`, `mypy`) during tasks, leaving them as manual checklist items.

---

## What Is Duplicated or Conflicting

- **`fix-and-continue` vs `fix-and-verify`**: Both are designed to apply a fix and verify it. `fix-and-continue` is specific, integrated with `WORK_QUEUE.md` and GitHub MCP, whereas `fix-and-verify` is generic, lacks queue logic, and has no MCP constraints.
- **`run-phase` vs `run-next-task` & `new-phase`**: `run-phase` conceptually duplicates running the phase, which in practice is driven dynamically task-by-task via `run-next-task` and planned via `new-phase`.
- **`architecture-review` vs `code-review`**: Both review code quality and architecture boundaries. They share overlapping goals and checklists, leading to duplication of code inspection workflows.

---

## What Should Exist But Doesn't

- **Content Compliance & Style Auditor**: An automated validation tool that reads generated assets against `docs/voice-and-style.md` and reports rule violations before the plan or manifest is generated.
- **Automated Schema/Model Sync Tester**: A test/verification skill that checks if any fields in Pydantic models under `src/content_creation/models/` have drifted from `docs/schema.md` or vice versa.
- **Remote Git Status Checker**: A tool to query the remote GitHub branch status to ensure the local workspace does not contain uncommitted drift before running tasks.
- **Pre-commit / Gitleaks Preflight Scanner**: A skill that runs Gitleaks or `detect-secrets` locally before files are pushed via MCP, reducing the risk of a CI block.

---

## Recommended Single Source of Truth

- **Task Execution Flow**: `run-next-task/SKILL.md` (fully defines preflight, implementation, validation, and MCP commit rules).
- **Bug Remediation**: `fix-and-continue/SKILL.md` (authoritative for applying specific hotfixes to queue tasks).
- **Phase Creation**: `new-phase/SKILL.md` (defines task limits, atomic criteria, and task card formatting).
- **Goal Drift & Project Control**: `drift-check/SKILL.md` (defines specific checks for model modifications, dependencies, test counts, and issues).
- **Security Scans**: `security-audit/SKILL.md` (defines working tree, history, gitignore, and pre-commit checks).
- **Global Agent Governance**: `AGENTS.md` (master rules for environment setup, branch verification, MCP commits, and secret scanner scripts).
