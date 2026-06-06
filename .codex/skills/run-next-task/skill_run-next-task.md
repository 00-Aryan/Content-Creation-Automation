---
name: run-next-task
description: Execute exactly one runnable task from WORK_QUEUE using GitHub MCP-only commits.
---

# SKILL: run-next-task
## Trigger: $run-next-task

Execute exactly one runnable task from WORK_QUEUE.md.

Use this skill only in normal task-execution mode.

Do not run this skill from review, repair, stash-review, or preservation branches.

---

## Required preflight

1. Set cache:

    export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
    mkdir -p "$UV_CACHE_DIR"

2. Confirm branch:

    git branch --show-current

Required branch: main.

3. Confirm clean worktree:

    git status --short

Required output: no output.

If branch is not main or worktree is dirty, stop and report. Do not clean, stash, restore, or commit locally.

---

## Find task

Open WORK_QUEUE.md.

Find the first task where:

- Status is PENDING
- dependencies are DONE

Open the referenced docs/tasks/task_NNN.md task card.

If no runnable task exists, report "No runnable tasks" and stop.

---

## Classify task

Type A:

- any Python source file
- any test file
- any behavior-changing code

Type B:

- docs/config/task-control files only

Type A requires baseline tests before edits:

    uv run python -m pytest --tb=no -q 2>&1 | tail -3

Type B skips baseline unless task card requires it.

---

## Scope rule

Touch only files listed in the task card.

Frozen scopes require explicit task-card approval:

- src/content_creation/models/
- src/content_creation/generation/
- prompts/
- docs/schema.md

---

## Validate

Run every validation command in the task card.

Always run:

    git diff --check

For Type A, confirm final test count does not decrease from baseline.

Do not expose environment variable values.

---

## Commit rule

Agents must not create local commits or push through local Git.

Use GitHub MCP only:

    mcp__github.push_files

Implementation push:

- owner: 00-Aryan
- repo: Content-Creation-Automation
- branch: main
- message: exact task-card commit message
- files: only task-scope implementation files

Queue/status push:

- message: chore(queue): mark TASK-NNN done
- files: WORK_QUEUE.md and docs/tasks/task_NNN.md

If GitHub MCP fails, stop and report. Do not fall back to local Git.

---

## Report

Report:

- task id and title
- Type A or Type B
- status DONE or BLOCKED
- files changed
- validations run
- baseline/final tests if Type A
- GitHub MCP commit messages
- next step

Do not auto-start another task.
