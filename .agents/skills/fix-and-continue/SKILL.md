---
name: fix-and-continue
description: Apply one approved remediation task using GitHub MCP-only commits.
---

# SKILL: fix-and-continue
## Trigger: $fix-and-continue TASK-NNN

Apply one explicitly approved remediation task.

Use GitHub MCP only for preservation.

Do not start unrelated tasks.

---

## Required preflight

1. Set cache:

    export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
    mkdir -p "$UV_CACHE_DIR"

2. Confirm branch:

    git branch --show-current

Normal remediation requires branch main.

3. Confirm worktree:

    git status --short

Normal remediation requires a clean worktree.

If branch/worktree is not suitable, stop and report unless the user explicitly says this is review or preservation mode.

---

## Read target task

Open:

    docs/tasks/task_NNN.md

Read:

- title
- status
- scope
- files to modify
- files to create
- validation commands
- commit message

If missing or ambiguous, stop and report.

---

## Classify task

Type A:

- Python source
- tests
- behavior-changing remediation

Type B:

- docs/config/task-control remediation only

Type A baseline:

    uv run python -m pytest --tb=no -q 2>&1 | tail -3

Type B skips baseline unless required by task card.

---

## Implement

Modify only approved task-scope files.

Do not:

- refactor unrelated code
- touch frozen scopes without approval
- expose environment variable values
- hide real defects through test edits
- continue to another task

---

## Validate

Run all validation commands from the task card.

Always run:

    git diff --check

For Type A, confirm final test count does not decrease.

For secret or agent-skill work, use the scanner defined in AGENTS.md.

---

## Commit rule

Agents must not create local commits or push through local Git.

Use GitHub MCP only:

    mcp__github.push_files

Remediation push:

- owner: 00-Aryan
- repo: Content-Creation-Automation
- branch: main
- message: exact task-card commit message
- files: only files listed in task scope

Status push:

- message: chore(queue): mark TASK-NNN done
- files: WORK_QUEUE.md and docs/tasks/task_NNN.md

If GitHub MCP fails, stop and report. Do not fall back to local Git.

---

## Report

Report:

- task id and title
- status DONE or BLOCKED
- Type A or Type B
- files changed
- validation results
- baseline/final tests if Type A
- GitHub MCP commit messages
- remaining blockers

Do not continue automatically.
