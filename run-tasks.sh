#!/usr/bin/env bash
# run-tasks.sh
# Local task executor — runs on your machine where .git is writable.
# Finds next PENDING task, calls Antigravity CLI to execute it,
# then commits locally with the exact message from the task card.
#
# Usage:
#   ./run-tasks.sh          # run one task
#   ./run-tasks.sh --all    # run all PENDING tasks in sequence
#   ./run-tasks.sh --dry    # show what would run, no execution

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
export UV_CACHE_DIR=/tmp/uv-cache
mkdir -p "$UV_CACHE_DIR"

DRY=false
RUN_ALL=false
for arg in "$@"; do
  case "$arg" in --dry) DRY=true ;; --all) RUN_ALL=true ;; esac
done

# ── find next runnable task ───────────────────────────────────────────────

find_next_task() {
  python3 - <<'PY'
import re, sys

queue = open("WORK_QUEUE.md").read()
done_ids = set(re.findall(r'TASK-(\d+)[^\n]*\bDONE\b', queue))

for m in re.finditer(
    r'\|\s*(TASK-\d+)\s*\|[^|]+\|\s*PENDING\s*\|[^|]*\|([^|]*)\|\s*\[→\]\(([^)]+)\)',
    queue
):
    task_id, deps_raw, card_path = m.group(1), m.group(2).strip(), m.group(3).strip()
    deps = [d.strip() for d in deps_raw.split(',') if d.strip() and d.strip().upper() != 'NONE']
    unmet = [d for d in deps if re.sub(r'TASK-0*', '', d) not in done_ids
             and d.replace('TASK-','').lstrip('0') not in done_ids]
    if not unmet:
        print(card_path)
        sys.exit(0)
sys.exit(1)
PY
}

# ── extract commit message from task card ────────────────────────────────

get_commit_msg() {
  python3 - "$1" <<'PY'
import re, sys
card = open(sys.argv[1]).read()
m = re.search(r'## Commit Message\s*```[^\n]*\n(.+?)\n```', card, re.DOTALL)
if m:
    print(m.group(1).strip()); sys.exit(0)
m = re.search(r'^# (TASK-\d+: .+)$', card, re.MULTILINE)
print(f"chore: {m.group(1)}" if m else "chore: task execution")
PY
}

# ── mark task done in local files ────────────────────────────────────────

mark_done_locally() {
  local card="$1"
  local today
  today=$(date +%Y-%m-%d)
  sed -i "s/\*\*Status:\*\* PENDING/**Status:** DONE/" "$card"
  sed -i "s/\*\*Completed:\*\* —/**Completed:** $today/" "$card"

  local num
  num=$(basename "$card" | grep -oE '[0-9]+' | head -1)
  local task_id
  task_id="TASK-$(printf '%03d' "$((10#$num))")"
  # Update PENDING → DONE in queue (handles variable spacing)
  python3 - "$task_id" <<'PY'
import re, sys
tid = sys.argv[1]
q = open("WORK_QUEUE.md").read()
q2 = re.sub(
    rf'(\|\s*{re.escape(tid)}\s*\|[^|]*\|)\s*PENDING\s*(\|)',
    r'\1 DONE    \2',
    q
)
open("WORK_QUEUE.md", "w").write(q2)
PY
}

# ── run one task ─────────────────────────────────────────────────────────

run_one() {
  local card="$1"
  local msg
  msg=$(get_commit_msg "$card")

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " Task:   $card"
  echo " Commit: $msg"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if $DRY; then
    echo "[DRY RUN] Would execute and commit: $msg"
    return 0
  fi

  # Execute via Antigravity CLI
  # Set tool permission to always-proceed to avoid approval interrupts
  antigravity run \
    --context "$card" \
    --context AGENTS.md \
    --context CLAUDE.md \
    "Execute the task card exactly as written.
     Read every section: Objective, Scope, Constraints, Implementation Steps, Validation.
     Follow each step precisely — no additions, no improvements.
     Run all Validation commands and confirm they pass.
     Do NOT run git add, git commit, or git push — the calling script handles that.
     When complete, print exactly: TASK_COMPLETE
     If validation fails, print exactly: TASK_FAILED: <reason>"

  # Mark done locally
  mark_done_locally "$card"

  # Commit locally — .git is writable on local machine
  git add -A
  git commit -m "$msg"
  git push origin main

  echo "✓ Committed: $msg"
}

# ── main ─────────────────────────────────────────────────────────────────

if $RUN_ALL; then
  count=0
  while card=$(find_next_task 2>/dev/null); do
    run_one "$card"
    ((count++))
  done
  echo ""
  echo "Queue complete. $count task(s) executed."
else
  if card=$(find_next_task 2>/dev/null); then
    run_one "$card"
  else
    echo "No runnable tasks in queue."
  fi
fi