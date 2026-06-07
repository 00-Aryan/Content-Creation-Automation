# SKILL: run-next-task

## SETUP
export UV_CACHE_DIR=/tmp/uv-cache
mkdir -p "$UV_CACHE_DIR"

## STEP 1 — PREFLIGHT
Run: git branch --show-current
Must return "main". If not, stop and report.
That is the ONLY preflight check.
Ignore worktree state entirely. Local files are always dirty because commits
go via GitHub MCP — this is expected, not an error.

## STEP 2 — FIND NEXT TASK
Read WORK_QUEUE.md.
Find first row where Status=PENDING and all Depends On values are DONE or None.
If none found: print "Queue empty — no runnable tasks" and stop.
Open the task card file shown in that row (e.g. docs/tasks/task_002.md).
If the file does not exist locally, use mcp__github.get_file_contents to read it
from the remote repo (owner: 00-Aryan, repo: Content-Creation-Automation).
If it still cannot be found: print "Task card missing: <path>" and stop.

## STEP 3 — CLASSIFY TASK TYPE
Read the task card Scope section.
Type A: any .py file in Files to modify or Files to create → source code task
Type B: only .md, .yaml, .yml, .gitignore, .txt, .json, .toml → docs/config task

## STEP 4 — BASELINE (Type A only)
export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=no -q 2>&1 | tail -3
Record passing count. Must be ≥ 950.
Note: 16 failures in test_notification_streaming.py are pre-existing. Not a blocker.
If the command fails with a filesystem error (not pytest): retry once with
UV_CACHE_DIR=/tmp/uv-cache. If still failing, report and stop.
Type B tasks: skip this step entirely.

## STEP 5 — IMPLEMENT
Execute implementation steps from the task card exactly as written.
Write files to local disk (project directory is writable).
No additions. No improvements. Only what the card specifies.

## STEP 6 — VALIDATE
Run every command in the task card Validation section.
Type A only: re-run pytest and confirm passing count >= baseline from Step 4.

## STEP 7 — SINGLE COMMIT via GitHub MCP
Collect all changed files:
- All files listed in the task card scope (read their current content from disk)
- WORK_QUEUE.md (update the task row: PENDING → DONE)
- docs/tasks/task_NNN.md (update Status: DONE, Completed: <today YYYY-MM-DD>)

Push ALL of them in ONE mcp__github.push_files call:
  owner: "00-Aryan"
  repo: "Content-Creation-Automation"
  branch: "main"
  message: <exact commit message from task card — do not change it>
  files: [all files above]

One task = one commit. No separate status push.
If push fails: report the exact error. Mark task BLOCKED in local WORK_QUEUE.md. Stop.

## STEP 8 — REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$run-next-task COMPLETE
Task:     TASK-NNN — <title>
Type:     A (source) | B (docs/config)
Status:   DONE | BLOCKED
Commit:   <commit message> — <SHA if available>
Files:    <list of everything in the push>
Tests:    <before → after> (Type A only)
Next:     TASK-NNN — run $run-next-task again
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULES
Never use git add, git commit, or git push.
Never push files outside the declared task scope (except WORK_QUEUE.md and the task card).
Never auto-start the next task.
Never push .venv/, data/, logs/, __pycache__/, or node_modules/.
If mcp__github.get_file_contents is needed to read a remote file, that is allowed.
