# SKILL: run-next-task
## Trigger: $run-next-task

## ENVIRONMENT SETUP — Run first every session
export UV_CACHE_DIR=/tmp/uv-cache

## STEP 1 — Find the next task
Open WORK_QUEUE.md.
Find first row where Status=PENDING and all Depends On are DONE.
If none: report "No runnable tasks" and stop.
Open the task card at the path shown. If missing: report and stop.

## STEP 2 — Classify the task
Read Scope → Files to modify and Files to create.
Type A: any .py file → source code task → run baseline in Step 3
Type B: only .md/.yaml/.yml/.gitignore/.txt/.json/.toml → skip to Step 4

## STEP 3 — Baseline (Type A only)
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=no -q 2>&1 | tail -3
Must show ≥ 950 passed.
16 known failures in test_notification_streaming.py are pre-existing, not a blocker.

## STEP 4 — Scope check
List every file you will touch. Each must appear in the task card scope.
Frozen scopes (need approval note in task card before touching):
  src/content_creation/models/
  src/content_creation/generation/
  prompts/

## STEP 5 — Implement
Execute task card implementation steps exactly. Nothing more.

## STEP 6 — Validate
Run every command in the task card Validation section.
Type A: re-run pytest and confirm passing count >= baseline.

## STEP 7 — Commit via GitHub MCP
Use mcp__github.push_files:
  owner: "00-Aryan"
  repo: "Content-Creation-Automation"
  branch: "main"
  message: <exact commit message from task card>
  files: [only files listed in task scope — read content from disk]
Do NOT include WORK_QUEUE.md or task card in this push.

## STEP 8 — Update task status via GitHub MCP
Push in a second mcp__github.push_files call:
  message: "chore(queue): mark TASK-NNN done"
  files: [WORK_QUEUE.md with status→DONE, docs/tasks/task_NNN.md with Status→DONE and Completed→today]

## STEP 9 — Report
Task: TASK-NNN — <title>
Type: A | B
Status: DONE | BLOCKED
Files changed: <list>
Tests: <before>→<after> (Type A only)
Committed: mcp__github.push_files
Next: run $run-next-task again

## WHAT NOT TO DO
Never use git add, git commit, or git push.
Never include files outside task scope in any MCP push.
Never auto-start the next task.
