#!/usr/bin/env bash
# run-tasks.sh v3.0
# Expert-grade local task executor for Content-Creation-Automation
# Uses agy (Antigravity CLI) for execution, local git for commits
#
# Usage:
#   ./run-tasks.sh              — run next PENDING task
#   ./run-tasks.sh --all        — run all PENDING tasks in order
#   ./run-tasks.sh --dry        — preview without executing
#   ./run-tasks.sh TASK-010     — run a specific task by ID
#   ./run-tasks.sh -v           — verbose debug output
#   ./run-tasks.sh --help       — show help

set -euo pipefail

# ── CONFIG ───────────────────────────────────────────────────────────────────

VERSION="3.0.0"
BASELINE_MIN=950
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
LOG_FILE=".run-tasks.log"

# agy must never touch these files
PROTECTED=(
    "run-tasks.sh"
    "AGENTS.md"
    "CLAUDE.md"
    ".gitignore"
    "pyproject.toml"
    "uv.lock"
)

# ── FLAGS ────────────────────────────────────────────────────────────────────

DRY=false
RUN_ALL=false
VERBOSE=false
TASK_OVERRIDE=""

for arg in "$@"; do
    case "$arg" in
        --dry)   DRY=true ;;
        --all)   RUN_ALL=true ;;
        -v|--verbose) VERBOSE=true ;;
        --help|-h) cat <<EOF
run-tasks.sh v3.0.0 — see script header for full docs
EOF
exit 0 ;;
        TASK-*)  TASK_OVERRIDE="$arg" ;;
        *)       echo "Unknown option: $arg. Run --help."; exit 1 ;;
    esac
done

# ── HELPERS ──────────────────────────────────────────────────────────────────

ts()    { date '+%H:%M:%S'; }
log()   { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }
debug() { $VERBOSE && echo "[$(ts)] DEBUG: $*" | tee -a "$LOG_FILE" || true; }
warn()  { echo "" && echo "⚠  WARNING: $*" >&2; }
die()   {
    echo ""
    echo "✗ ERROR: $*" >&2
    echo "  See $LOG_FILE for full output."
    exit 1
}

hr() { echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

show_help() {
    cat <<EOF
run-tasks.sh v$VERSION

USAGE
  ./run-tasks.sh              Run next PENDING task in queue
  ./run-tasks.sh --all        Run all runnable PENDING tasks
  ./run-tasks.sh --dry        Show what would run without executing
  ./run-tasks.sh TASK-010     Run a specific task (must be PENDING)
  ./run-tasks.sh -v           Verbose: show debug info and scope parsing
  ./run-tasks.sh --help       Show this message

REQUIREMENTS
  agy         Antigravity CLI in PATH (~/.local/bin/agy)
  git         Remote 'origin' configured, on branch main
  python3     For queue parsing
  uv          For running tests (Type A tasks)

  WORK_QUEUE.md          must exist in repo root
  docs/tasks/task_NNN.md must exist for every queued task

LOGS
  .run-tasks.log          Full execution log (appended each run)

WHAT IT DOES
  1. Finds the next PENDING task whose dependencies are all DONE
  2. Classifies it: Type A (touches .py) or Type B (docs/config only)
  3. Type A: runs pytest baseline (must be >= $BASELINE_MIN)
  4. Invokes agy with the task card and strict scope constraints
  5. Validates that scope files actually changed
  6. Type A: re-runs pytest and checks for regression
  7. Marks task DONE and commits with the task card's exact message
EOF
}

# ── PREFLIGHT ────────────────────────────────────────────────────────────────

preflight() {
    log "=== run-tasks.sh v$VERSION starting ==="
    log "Repo: $(pwd)"
    log "Flags: dry=$DRY all=$RUN_ALL verbose=$VERBOSE override=${TASK_OVERRIDE:-none}"

    # Required tools
    local missing=()
    command -v agy     &>/dev/null || missing+=("agy (~/.local/bin/agy)")
    command -v git     &>/dev/null || missing+=("git")
    command -v python3 &>/dev/null || missing+=("python3")

    [ ${#missing[@]} -eq 0 ] || die "Missing required tools:\n  ${missing[*]}\nInstall them and retry."

    # agy version check
    local agy_ver
    agy_ver=$(agy --version 2>/dev/null | head -1 || echo "unknown")
    log "agy version: $agy_ver"

    # Repo root
    git rev-parse --show-toplevel &>/dev/null || die "Not inside a git repository."
    local repo_root
    repo_root=$(git rev-parse --show-toplevel)
    cd "$repo_root"
    log "Working directory: $repo_root"

    # Required files
    [ -f "WORK_QUEUE.md" ]  || die "WORK_QUEUE.md not found in $repo_root"
    [ -d "docs/tasks" ]     || die "docs/tasks/ directory not found — create it and add task cards"

    # Branch
    local branch
    branch=$(git branch --show-current)
    debug "Branch: $branch"
    [ "$branch" = "main" ] || warn "Not on 'main' branch — currently on '$branch'"

    # Git remote
    git remote -v | grep -q origin || die "No 'origin' remote configured. Run: git remote add origin <url>"

    # UV cache
    export UV_CACHE_DIR
    mkdir -p "$UV_CACHE_DIR"
    debug "UV_CACHE_DIR: $UV_CACHE_DIR"

    log "Preflight passed."
}

# ── QUEUE PARSING ────────────────────────────────────────────────────────────

find_next_task() {
    python3 - "$TASK_OVERRIDE" <<'PY'
import re, sys

override = sys.argv[1].strip()
try:
    queue = open("WORK_QUEUE.md").read()
except FileNotFoundError:
    print("WORK_QUEUE.md not found", file=sys.stderr)
    sys.exit(2)

# Collect all DONE task numbers as plain integers
done = set()
for m in re.finditer(r'TASK-(\d+)[^\n]*\bDONE\b', queue):
    done.add(int(m.group(1)))

# If a specific task was requested
if override:
    num_match = re.search(r'\d+', override)
    if not num_match:
        print(f"Could not parse task number from: {override}", file=sys.stderr)
        sys.exit(2)
    num = int(num_match.group(0))

    # Find its card path in any row (PENDING or otherwise)
    m = re.search(
        rf'\|\s*TASK-0*{num}\b[^|]*\|[^|]*\|([^|]*)\|[^|]*\|[^|]*\|\s*\[→\]\(([^)]+)\)',
        queue
    )
    if not m:
        print(f"TASK-{num:03d} not found in WORK_QUEUE.md", file=sys.stderr)
        sys.exit(2)
    status = m.group(1).strip()
    card_path = m.group(2).strip()
    if 'DONE' in status:
        print(f"TASK-{num:03d} is already DONE", file=sys.stderr)
        sys.exit(2)
    print(card_path)
    sys.exit(0)

# Find first runnable PENDING task
found_pending = False
for m in re.finditer(
    r'\|\s*(TASK-\d+)\s*\|([^|]+)\|\s*PENDING\s*\|([^|]*)\|([^|]*)\|\s*\[→\]\(([^)]+)\)',
    queue
):
    task_id   = m.group(1).strip()
    deps_raw  = m.group(4).strip()
    card_path = m.group(5).strip()
    found_pending = True

    deps = [d.strip() for d in deps_raw.split(',')
            if d.strip() and d.strip().upper() != 'NONE']

    unmet = []
    for dep in deps:
        nums = re.findall(r'\d+', dep)
        if nums and int(nums[0]) not in done:
            unmet.append(dep)

    if unmet:
        print(f"  {task_id}: waiting on {', '.join(unmet)}", file=sys.stderr)
        continue

    print(card_path)
    sys.exit(0)

if not found_pending:
    print("No PENDING tasks found in WORK_QUEUE.md — queue may be complete.", file=sys.stderr)

sys.exit(1)
PY
}

# ── TASK CARD PARSING ────────────────────────────────────────────────────────

get_task_title() {
    head -1 "$1" | sed 's/^# //'
}

get_commit_msg() {
    python3 - "$1" <<'PY'
import re, sys

try:
    card = open(sys.argv[1]).read()
except FileNotFoundError:
    print(f"ERROR: Task card not found: {sys.argv[1]}", file=sys.stderr)
    sys.exit(1)

m = re.search(r'## Commit Message\s*```[^\n]*\n(.+?)\n```', card, re.DOTALL)
if m:
    msg = m.group(1).strip()
    # Strip any trailing whitespace or stray backtick lines
    msg = re.sub(r'\s+$', '', msg)
    print(msg)
    sys.exit(0)

# Fallback
m = re.search(r'^# (TASK-\d+: .+)$', card, re.MULTILINE)
if m:
    print(f"chore: {m.group(1).lower()}")
    sys.exit(0)

print("chore: task execution")
PY
}

get_task_type() {
    # Returns "A" if task modifies .py files, "B" otherwise
    python3 - "$1" <<'PY'
import re, sys

try:
    card = open(sys.argv[1]).read()
except FileNotFoundError:
    print("B")  # default safe
    sys.exit(0)

# Extract the Scope section
scope_m = re.search(r'## Scope\s*\n(.*?)(?=\n## |\Z)', card, re.DOTALL)
if not scope_m:
    print("B")
    sys.exit(0)

scope = scope_m.group(1)

# Split into subsections
create_m = re.search(r'### Files to create\s*\n(.*?)(?=\n###|\Z)', scope, re.DOTALL)
modify_m = re.search(r'### Files to modify\s*\n(.*?)(?=\n###|\Z)', scope, re.DOTALL)

active_text = ""
if create_m: active_text += create_m.group(1)
if modify_m: active_text += modify_m.group(1)

# Does the active scope reference any .py file?
py_refs = re.findall(r'[\w./\-]+\.py\b', active_text)
# Exclude placeholders like "None" or "none"
py_refs = [p for p in py_refs if p.lower() not in ('none', 'none.py')]

if py_refs:
    print("A")  # source code task
    sys.stderr.write(f"Type A — .py files in scope: {py_refs}\n")
else:
    print("B")  # docs/config task
    sys.stderr.write("Type B — no .py files in scope\n")
PY
}

get_scope_files() {
    # Returns list of files that should change (one per line)
    python3 - "$1" <<'PY'
import re, sys

try:
    card = open(sys.argv[1]).read()
except FileNotFoundError:
    sys.exit(0)

scope_m = re.search(r'## Scope\s*\n(.*?)(?=\n## |\Z)', card, re.DOTALL)
if not scope_m:
    sys.exit(0)

scope = scope_m.group(1)
create_m = re.search(r'### Files to create\s*\n(.*?)(?=\n###|\Z)', scope, re.DOTALL)
modify_m = re.search(r'### Files to modify\s*\n(.*?)(?=\n###|\Z)', scope, re.DOTALL)

files = []
for section in [create_m, modify_m]:
    if not section:
        continue
    text = section.group(1)
    # Skip "None" lines
    if re.match(r'^\s*None\s*$', text, re.IGNORECASE):
        continue
    # Extract file paths: lines starting with - ` or directly containing a path
    for path in re.findall(r'[`"]?([\w.\-]+(?:/[\w.\-]+)+)[`"]?', text):
        if path.lower() not in ('none', 'all') and '.' in path:
            files.append(path)

for f in sorted(set(files)):
    print(f)
PY
}

# ── PROTECTED FILE SNAPSHOT ───────────────────────────────────────────────────

snapshot_protected() {
    for f in "${PROTECTED[@]}"; do
        if [ -f "$f" ]; then
            md5sum "$f" 2>/dev/null
        else
            echo "missing  $f"
        fi
    done
}

restore_protected() {
    local snapshot="$1"
    while IFS= read -r line; do
        local expected_hash file
        expected_hash=$(echo "$line" | awk '{print $1}')
        file=$(echo "$line" | awk '{print $2}')

        [ "$expected_hash" = "missing" ] && continue
        [ -f "$file" ] || continue

        local current_hash
        current_hash=$(md5sum "$file" 2>/dev/null | awk '{print $1}')
        if [ "$current_hash" != "$expected_hash" ]; then
            warn "Protected file was modified by agent: $file — reverting"
            git checkout -- "$file" 2>/dev/null && log "Reverted: $file" || warn "Could not revert $file"
        fi
    done <<< "$snapshot"
}

# ── CORE RUNNER ───────────────────────────────────────────────────────────────

run_one() {
    local card="$1"

    # ── Validate card exists ───────────────────────────────────────────────
    if [ ! -f "$card" ]; then
        die "Task card not found: $card\n\n  Available cards:\n  $(ls docs/tasks/*.md 2>/dev/null | head -10 || echo '  (none found)')\n\n  Create the missing card or update WORK_QUEUE.md."
    fi

    # ── Parse task metadata ────────────────────────────────────────────────
    local title msg task_type task_id scope_files
    title=$(get_task_title "$card")
    msg=$(get_commit_msg "$card") || die "Could not extract commit message from $card"
    task_type=$(get_task_type "$card" 2>/tmp/type_debug)
    task_id=$(grep -oE 'TASK-[0-9]+' "$card" | head -1 || echo "TASK-???")
    scope_files=$(get_scope_files "$card" 2>/dev/null || echo "")

    local type_detail
    type_detail=$(cat /tmp/type_debug 2>/dev/null || echo "")

    # Validate commit message is not empty or generic
    if [ -z "$msg" ] || [ "$msg" = "chore: task execution" ]; then
        warn "Commit message is generic — task card may be missing '## Commit Message' section"
    fi

    hr
    echo " Task:    $title"
    echo " Card:    $card"
    echo " Type:    $task_type  ($type_detail)"
    echo " Scope:   ${scope_files:-"(not parsed — check task card format)"}"
    echo " Commit:  $msg"
    hr

    $DRY && { echo "[DRY RUN] Would execute and commit."; return 0; }

    # ── Type A: pytest baseline ────────────────────────────────────────────
    local baseline=0
    if [ "$task_type" = "A" ]; then
        log "Running pytest baseline..."
        local pytest_out
        pytest_out=$(uv run python -m pytest --tb=no -q 2>&1 || true)
        baseline=$(echo "$pytest_out" | grep -oE '^[0-9]+' | head -1 || echo 0)
        echo "  Baseline: $baseline passed"
        debug "pytest output: $pytest_out"
        [ "$baseline" -ge "$BASELINE_MIN" ] || die "Baseline $baseline < $BASELINE_MIN. Fix failing tests first."
    fi

    # ── Snapshot protected files ───────────────────────────────────────────
    local snap
    snap=$(snapshot_protected)
    debug "Protected file snapshot taken"

    # ── Build agy prompt ──────────────────────────────────────────────────
    local scope_constraint
    if [ -n "$scope_files" ]; then
        scope_constraint="Files you MAY modify or create (and ONLY these):\n$scope_files"
    else
        scope_constraint="Refer to the ## Scope section of the task card for allowed files."
    fi

    local prompt
    prompt="$(cat <<PROMPT
Execute the following task card exactly as written.

$(cat "$card")

---
EXECUTION RULES (non-negotiable):
1. Read the entire task card before touching any file.
2. $scope_constraint
3. NEVER modify: run-tasks.sh, AGENTS.md, CLAUDE.md, .gitignore, pyproject.toml, uv.lock
4. NEVER modify: WORK_QUEUE.md or any file in docs/tasks/
5. Follow each Implementation Step in order. Do not skip steps.
6. Run every command in the Validation section and confirm it passes.
7. Do NOT run git add, git commit, git push, or any git command.
8. CRITICAL: You MUST NOT run git add, git commit, git push, or any git command under any circumstances.
   The run-tasks.sh script exclusively handles all git operations. If you run a git command,
   the workflow breaks. If a task says to commit, that is handled externally — just make the file changes.
9. If a step fails, stop and print: TASK_FAILED: <reason>
PROMPT
)"

    # ── Invoke agy ────────────────────────────────────────────────────────
    log "Invoking agy --print..."
    local agy_output
    if ! agy_output=$(agy --print --dangerously-skip-permissions "$prompt" 2>&1); then
        warn "agy exited with non-zero status"
    fi

    echo "$agy_output" | tee -a "$LOG_FILE"

    # Check for explicit failure signal
    if echo "$agy_output" | grep -q "TASK_FAILED:"; then
        local reason
        reason=$(echo "$agy_output" | grep "TASK_FAILED:" | head -1)
        die "Agent reported failure: $reason"
    fi

    # Restore any protected files the agent wrongly modified
    restore_protected "$snap"

    # ── Diff check ────────────────────────────────────────────────────────
    local all_changed status_files actual_changed
    all_changed=$(git diff --name-only)
    # Status files that mark_done_locally will write — ignore for now
    status_files="WORK_QUEUE.md docs/tasks/$(basename "$card")"
    actual_changed=$(echo "$all_changed" | grep -v "^WORK_QUEUE.md$" \
                                         | grep -v "^docs/tasks/" \
                                         | grep -v "^run-tasks.sh$" \
                                         | grep -v "^\.run-tasks\.log$" || true)

    debug "All changed: $(echo "$all_changed" | tr '\n' ' ')"
    debug "Actual (excl. status): $(echo "$actual_changed" | tr '\n' ' ')"

    if [ -z "$actual_changed" ]; then
        echo ""
        echo "✗ TASK NOT EXECUTED"
        echo "  agy ran but made no changes to task scope files."
        if [ -n "$scope_files" ]; then
            echo "  Expected to see changes in:"
            echo "$scope_files" | sed 's/^/    /'
        fi
        echo "  Check the agy output above."
        echo "  The task remains PENDING — nothing was committed."
        return 1
    fi

    echo ""
    echo "Files changed:"
    echo "$actual_changed" | sed 's/^/  /'

    # Scope file presence check
    if [ -n "$scope_files" ]; then
        local scope_hit=false
        while IFS= read -r sf; do
            [ -z "$sf" ] && continue
            if echo "$actual_changed" | grep -qF "$sf"; then
                scope_hit=true
                debug "Scope match: $sf"
            else
                debug "Scope miss: $sf"
            fi
        done <<< "$scope_files"

        if ! $scope_hit; then
            warn "None of the declared scope files appear in the diff."
            warn "Expected: $(echo "$scope_files" | tr '\n' ' ')"
            warn "Got:      $(echo "$actual_changed" | tr '\n' ' ')"
            echo "Reverting..."
            git checkout -- .
            die "Task scope mismatch — reverted. Check task card scope section."
        fi
    fi

    # ── Type A: post-task pytest ───────────────────────────────────────────
    if [ "$task_type" = "A" ]; then
        log "Re-running pytest after changes..."
        local after_out after_count
        after_out=$(uv run python -m pytest --tb=short -q 2>&1 || true)
        after_count=$(echo "$after_out" | grep -oE '^[0-9]+' | head -1 || echo 0)
        echo "  Tests: $baseline → $after_count passed"
        debug "$after_out"
        if [ "$after_count" -lt "$baseline" ]; then
            echo "$after_out"
            echo ""
            echo "Reverting changes..."
            git checkout -- .
            die "Test regression: $baseline → $after_count. Changes reverted."
        fi
    fi

    # ── Mark done + commit ────────────────────────────────────────────────
    mark_done_locally "$card"

    git add -A
    git commit -m "$msg"
    git push origin main

    echo ""
    echo "✓ $task_id complete: $msg"
    log "=== $task_id DONE ==="
}

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
print(f"Updated {tid} → DONE in WORK_QUEUE.md")
PY
}

# ── ENTRY ────────────────────────────────────────────────────────────────────

preflight

if $RUN_ALL; then
    count=0
    while card=$(find_next_task 2>/tmp/queue_debug); do
        run_one "$card" || {
            warn "Task failed — stopping --all"
            cat /tmp/queue_debug 2>/dev/null || true
            break
        }
        ((count++)) || true
    done
    echo ""
    echo "Run complete. $count task(s) executed."
    [ $count -gt 0 ] || { echo "Queue status:"; cat /tmp/queue_debug 2>/dev/null || true; }

elif [ -n "$TASK_OVERRIDE" ]; then
    card=$(find_next_task 2>/tmp/queue_debug) || {
        die "$TASK_OVERRIDE not found or not runnable.\n$(cat /tmp/queue_debug 2>/dev/null)"
    }
    run_one "$card"

else
    if card=$(find_next_task 2>/tmp/queue_debug); then
        run_one "$card"
    else
        echo "No runnable tasks found."
        echo ""
        echo "Reason:"
        cat /tmp/queue_debug 2>/dev/null | sed 's/^/  /'
        echo ""
        echo "Check WORK_QUEUE.md for:"
        echo "  - BLOCKED tasks with unfinished dependencies"
        echo "  - Missing task card files in docs/tasks/"
        echo "  - Tasks already DONE"
        echo ""
        echo "Run with -v for debug output."
    fi
fi