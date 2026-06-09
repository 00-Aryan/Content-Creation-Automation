#!/usr/bin/env bash
# run-tasks.sh
# Runs next task from WORK_QUEUE.md via Antigravity CLI (agy),
# then commits locally with the exact message from the task card.
#
# Usage:
#   ./run-tasks.sh          — run one task
#   ./run-tasks.sh --all    — run all PENDING tasks in sequence
#   ./run-tasks.sh --dry    — show what would run, no execution

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
# FIX: normalise all task numbers to plain integers before comparing
# so TASK-009 (stored as "009") matches dep "TASK-009" correctly

find_next_task() {
  python3 - <<'PY'
import re, sys

queue = open("WORK_QUEUE.md").read()

# Collect done IDs as plain integers ("009" → 9, "12" → 12)
done = set()
for m in re.finditer(r'TASK-(\d+)[^\n]*\bDONE\b', queue):
    done.add(int(m.group(1)))

for m in re.finditer(
    r'\|\s*(TASK-\d+)\s*\|[^|]+\|\s*PENDING\s*\|[^|]*\|([^|]*)\|\s*\[→\]\(([^)]+)\)',
    queue
):
    task_id, deps_raw, card_path = m.group(1), m.group(2).strip(), m.group(3).strip()

    # Parse deps — skip "None" and blank
    deps = [d.strip() for d in deps_raw.split(',')
            if d.strip() and d.strip().upper() != 'NONE']

    # All deps must be done (compare as plain integers)
    unmet = []
    for dep in deps:
        nums = re.findall(r'\d+', dep)
        if nums and int(nums[0]) not in done:
            unmet.append(dep)

    if not unmet:
        print(card_path)
        sys.exit(0)

sys.exit(1)
PY
}

# ── extract commit message ────────────────────────────────────────────────

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

# ── classify task type ────────────────────────────────────────────────────
# Type A = touches .py files → pytest required
# Type B = only docs/config files → no pytest

get_task_type() {
  python3 - "$1" <<'PY'
import re, sys
card = open(sys.argv[1]).read()
scope = re.search(r'## Scope(.+?)^##', card, re.DOTALL | re.MULTILINE)
if scope and re.search(r'\.py\b', scope.group(1)):
    print("A")
else:
    print("B")
PY
}

# ── mark done in local files ──────────────────────────────────────────────

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

# ── run one task ──────────────────────────────────────────────────────────

run_one() {
  local card="$1"
  local msg task_type
  msg=$(get_commit_msg "$card")
  task_type=$(get_task_type "$card")

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " Task:   $card"
  echo " Type:   $task_type"
  echo " Commit: $msg"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if $DRY; then
    echo "[DRY RUN] Would execute and commit."
    return 0
  fi

  # Type A: run pytest baseline before
  local baseline=0
  if [ "$task_type" = "A" ]; then
    echo "Running baseline tests..."
    baseline=$(uv run python -m pytest --tb=no -q 2>&1 | grep -oE '^[0-9]+' | head -1 || echo 0)
    echo "Baseline: $baseline passed"
    if [ "$baseline" -lt 950 ]; then
      echo "BLOCKED: baseline is below 950. Fix tests before running tasks."
      exit 1
    fi
  fi

  # Snapshot what files exist before agent runs
  local before_hash
  before_hash=$(find . -not -path './.git/*' -not -path './.venv/*' \
    -not -path './data/*' -not -path './__pycache__/*' \
    -type f -newer "$card" 2>/dev/null | sort | md5sum | cut -d' ' -f1 || echo "none")

  # ── EXECUTE VIA AGY (Antigravity CLI) ─────────────────────────────────

echo "===== CARD ====="
cat "$card"
echo "================"

agy --print --dangerously-skip-permissions "$(cat <<PROMPT
...
Execute this task card exactly as written. Do not skip any step.
)"
$(cat "$card")

AGENTS.md rules apply. After completing all implementation steps and
validation commands, stop. Do NOT run git add, git commit, or git push.
The run-tasks.sh script handles all git operations.
PROMPT
)"

  local agent_exit=$?

  # ── GUARD: verify actual work was done (Bug 3 fix) ────────────────────
  local after_hash
  after_hash=$(find . -not -path './.git/*' -not -path './.venv/*' \
    -not -path './data/*' -not -path './__pycache__/*' \
    -type f -newer "$card" 2>/dev/null | sort | md5sum | cut -d' ' -f1 || echo "none")

  local changed_files
  changed_files=$(git diff --name-only)

  if [ -z "$changed_files" ]; then
    echo ""
    echo "✗ TASK FAILED: Agent ran but no files were changed."
    echo "  The task was not executed. Check agy output above."
    echo "  Task remains PENDING. Fix manually or re-run."
    exit 1
  fi

  echo "Files changed by agent:"
  echo "$changed_files" | sed 's/^/  /'

  # Type A: confirm tests still pass
  if [ "$task_type" = "A" ]; then
    echo "Re-running tests after changes..."
    local after_count
    after_count=$(uv run python -m pytest --tb=short -q 2>&1 | grep -oE '^[0-9]+' | head -1 || echo 0)
    echo "After: $after_count passed (baseline was $baseline)"
    if [ "$after_count" -lt "$baseline" ]; then
      echo "✗ TASK FAILED: Test count dropped ($baseline → $after_count). Not committing."
      echo "  Revert changes and investigate."
      git checkout -- .
      exit 1
    fi
  fi

  # Mark done in local files
  mark_done_locally "$card"

  # Commit — only tracked + newly created files (no stray files)
  git add -A
  git commit -m "$msg"
  git push origin main

  echo ""
  echo "✓ Done: $msg"
}

# ── main ──────────────────────────────────────────────────────────────────

if $RUN_ALL; then
  count=0
  while card=$(find_next_task 2>/dev/null); do
    run_one "$card"
    ((count++)) || true
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