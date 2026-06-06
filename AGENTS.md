# AGENTS.md — Content Creation Automation Platform
## Master Agent Instructions

Read this file completely before taking any action.

This document governs all AI coding agents working in this repository, including Codex, Claude Code, Gemini CLI, and similar tools.

---

## 1. What This Project Is

A production-grade, source-grounded AI pipeline that transforms ML/AI research into educational content assets for students.

Core principles:

- Every claim must be traceable to source material.
- Every asset requires human approval.
- No auto-publishing.
- No hallucinated claims.
- Reliability, observability, and maintainability matter more than feature volume.
- Agent workflows must be repeatable, auditable, and scope-controlled.

Current-state documents:

- `WORK_QUEUE.md` — active phase and ordered task queue.
- `TASK_SPEC.md` — latest milestone summary.
- `docs/project-context.md` — long-term project vision.
- `docs/backlog/issues.md` — known issues and remediation items.
- `docs/tasks/task_NNN.md` — individual task cards.

---

## 2. Operating Modes

Agents must first determine which mode they are operating in.

### 2.1 Normal task-execution mode

This mode applies when running:

- `$run-next-task`
- a task from `WORK_QUEUE.md`
- a specific `docs/tasks/task_NNN.md` task
- any implementation, validation, or queue-update task

Requirements:

- Branch must be `main`.
- Worktree must be clean before starting.
- Task scope must come from the task card.
- All commits must use GitHub MCP.
- Do not use local `git add`, `git commit`, or `git push`.

### 2.2 Review / repair / preservation mode

This mode applies when the user is reviewing a stash, worktree, migration branch, or repair branch.

Examples:

- `review/stashed-work`
- `repair/*`
- `audit/*`
- temporary worktrees created with `git worktree`

Allowed:

- Inspect files.
- Edit governance/docs/config files explicitly requested by the user.
- Clean scratch files.
- Prepare a reviewed set of files for later preservation.

Not allowed:

- Do not run `$run-next-task`.
- Do not update `WORK_QUEUE.md` as if a normal task completed.
- Do not mark task cards DONE unless explicitly instructed.
- Do not assume the review branch is suitable for normal task execution.
- Do not commit locally.

If preserving reviewed work, use GitHub MCP only, or report the exact files ready for MCP push.

---

## 3. Session Setup and Preflight

Run preflight in this order.

### 3.1 Set environment

Run at the start of every session:

```bash
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
mkdir -p "$UV_CACHE_DIR"
```

### 3.2 Confirm branch

```bash
git branch --show-current
```

For normal task-execution mode, required branch:

```text
main
```

If running normal task execution and the branch is not `main`, stop and report.

For review / repair / preservation mode, non-main branches are allowed when explicitly created for review, such as:

```text
review/stashed-work
```

In that case, do not run `$run-next-task`.

### 3.3 Confirm worktree state

```bash
git status --short
```

For normal task-execution mode, required output is no output.

If the worktree is dirty during normal task execution, stop and report. Do not stash, restore, clean, commit, or discard files unless the user explicitly instructs you to do so.

For review / repair / preservation mode, a dirty worktree may be expected. In that case, report the dirty files and classify them before making changes.

---

## 4. Task Classification

Before running validations or making edits, classify the task.

### 4.1 Type A — source-code task

A task is Type A if any of the following are in scope:

- `.py` source files
- test files
- behavior changes
- models
- services
- repositories
- UI code
- CLI code
- workflow engine code
- infrastructure code
- database logic
- migration logic

Type A tasks require baseline tests before implementation.

### 4.2 Type B — docs/config task

A task is Type B if only these file types are in scope:

- `.md`
- `.yaml`
- `.yml`
- `.gitignore`
- `.txt`
- `.json`
- `.toml`
- task-control files
- documentation-only files
- agent skill files

Type B tasks do not require a full baseline test run unless the task card explicitly requires it.

---

## 5. Baseline Test Rule

### Type A tasks

Run before implementation:

```bash
uv run python -m pytest --tb=no -q 2>&1 | tail -3
```

Record the baseline result.

The final passing count must not decrease compared with the baseline unless the task card explicitly documents an accepted change.

If the test run fails because of filesystem or cache setup, run:

```bash
mkdir -p /tmp/uv-cache
```

Then retry once.

If it still fails, stop and report.

### Type B tasks

No baseline test run is required unless the task card explicitly requires it.

Still run every validation command listed in the task card.

---

## 6. Absolute Do-Not Rules

These override every other instruction.

### 6.1 Architecture

Do not:

- change workflow semantics or business logic without explicit approval
- bypass `WorkflowActionExecutor`, `ActionAvailabilityEngine`, or `ReviewTransitionEngine`
- call repositories or services directly from the Streamlit UI layer
- add Streamlit imports into domain or infrastructure layers
- introduce external queues such as Celery, Redis, RabbitMQ, or Kafka without approval
- change Pydantic model fields without updating all dependent code and tests
- silently change public APIs, persisted schemas, or task contracts
- refactor unrelated modules during a scoped task

### 6.2 Secrets

Do not:

- print, log, or include any environment variable value in any output
- run `printenv`
- run `env`
- run `echo $VARIABLE`
- run commands that print `os.environ`
- add fallback values to `os.environ.get("GEMINI_API_KEY", "...")`
- commit a `.env` file
- embed API keys, GitHub tokens, access tokens, credentials, or bearer tokens in source files
- embed real secrets in docs, config, prompts, task cards, logs, reports, or examples
- include real secrets in tests
- include real secrets in screenshots, markdown, JSON, TOML, YAML, or generated artifacts

Allowed:

- reference secret names such as `GEMINI_API_KEY=`
- use placeholder values such as `your_api_key_here`
- document required environment variable names without values

### 6.3 Scope

Do not:

- modify files outside the current task card scope
- refactor opportunistically
- add features during audit, security, or remediation tasks
- update historical reports unless the task explicitly asks for that file
- edit frozen scopes without written approval in the task card
- silently delete agent skills or workflow files

### 6.4 Testing

Do not:

- skip tests merely to make a commit pass
- modify tests to hide a real defect
- reduce the passing test count without explicit documented approval
- treat unrelated pre-existing failures as fixed unless verified
- change test semantics during docs/config tasks

### 6.5 Git

Agents must not use local Git for commits.

Never run:

```bash
git add
git commit
git push
```

Local `.git` is read-only for agents.

All repository updates must be made through GitHub MCP using `mcp__github.push_files`.

If GitHub MCP is unavailable, stop and report. Do not fall back to local Git unless the user explicitly overrides this rule.

---

## 7. Mandatory Workflow for Normal Tasks

Use this workflow for `$run-next-task` and all task-card execution.

```text
READ WORK_QUEUE.md
    ↓
FIND first runnable PENDING task
    ↓
READ docs/tasks/task_NNN.md completely
    ↓
VERIFY dependencies are DONE
    ↓
VERIFY branch is main
    ↓
VERIFY worktree is clean
    ↓
CLASSIFY task as Type A or Type B
    ↓
RUN baseline only if Type A
    ↓
LIST exact files to touch
    ↓
IMPLEMENT only declared scope
    ↓
VALIDATE using task card commands
    ↓
CONFIRM Type A test count did not decrease
    ↓
PUSH task-scoped files via GitHub MCP
    ↓
PUSH queue/task status update via GitHub MCP
    ↓
REPORT files changed, validation result, commits, and next step
```

If any step fails:

1. Stop.
2. Do not attempt the next task.
3. Mark the task as BLOCKED only if the task card or workflow permits status updates.
4. Report the blocker precisely.

---

## 8. Mandatory Workflow for Review / Repair / Preservation

Use this workflow when reviewing stashed work, repair branches, or migration branches.

```text
IDENTIFY current branch and worktree
    ↓
CONFIRM this is not normal task execution
    ↓
LIST dirty files
    ↓
CLASSIFY files as intentional, scratch, local config, or unsafe
    ↓
REMOVE only obvious scratch/local files with user approval or explicit instruction
    ↓
CHECK active governance files for consistency
    ↓
RUN read-only secret scan
    ↓
RUN git diff --check
    ↓
REPORT reviewed files and remaining risks
    ↓
WAIT for explicit push/commit instruction
```

Review branches may be dirty.

Do not run `$run-next-task` from a review branch.

Do not mark queue tasks DONE from a review branch unless the user explicitly instructs it and the files match the task scope.

---

## 9. Commit Method — GitHub MCP Only

Use `mcp__github.push_files` for all commits.

Standard parameters:

```text
owner:   "00-Aryan"
repo:    "Content-Creation-Automation"
branch:  "main"
message: <exact task card commit message>
files:   [only files in task scope]
```

Task implementation push:

```text
message: <exact task card commit message>
files:   [only implementation files declared in the task scope]
```

Task status push:

```text
message: "chore(queue): mark TASK-NNN done"
files:   ["WORK_QUEUE.md", "docs/tasks/task_NNN.md"]
```

For preservation or repair pushes without a task card, use a clear hotfix/governance message, for example:

```text
docs(agents): align agent workflow governance with MCP commits
test(notification): skip socket streaming tests when local sockets unavailable
docs(security): update phase 11.9.2 security audit report
```

Do not include unrelated files in any push.

If a required deletion cannot be represented through the available MCP operation, stop and report that deletion support is unavailable. Do not silently leave remote state inconsistent.

---

## 10. Commit Message Format

Use the exact commit message from the task card.

Default format:

```text
type(scope): description (TASK-NNN)
```

Allowed types:

```text
feat
fix
docs
refactor
test
chore
security
```

Examples:

```text
docs(security): add .env.example template (TASK-001)
fix(gitignore): add database ignore rules (TASK-002)
feat(ci): add GitHub Actions secret scan workflow (TASK-004)
test(notification): skip socket streaming tests when local sockets unavailable
docs(agents): align agent workflow governance with MCP commits
```

Never create a task-related commit without a task reference unless the user explicitly approves a hotfix or governance repair.

---

## 11. Skill Reference

Available skills:

| Skill | Trigger | Purpose |
|---|---|---|
| run-next-task | `$run-next-task` | Execute the next runnable PENDING task from `WORK_QUEUE.md` |
| new-phase | `$new-phase` | Convert a phase description into task cards and queue updates |
| drift-check | `$drift-check` | Verify project has not drifted from stated goals |
| fix-and-continue | `$fix-and-continue TASK-NNN` | Apply one approved remediation item |
| security-audit | `$security-audit` | Run read-only secret and security checks |

Skill file locations:

- Canonical agent skills: `.agents/skills/<name>/SKILL.md`
- Codex-compatible mirrors: `.codex/skills/<name>/SKILL.md` or `.codex/skills/<name>/skill_<name>.md`
- Claude-specific skill directories are not canonical in this repository unless explicitly reintroduced.

When skill instructions conflict with this file, `AGENTS.md` wins.

---

## 12. Agent Skill Migration Rules

`.agents/skills` is the canonical skill source.

`.codex/skills` is a compatibility mirror for Codex-style skill loading. Existing mirrors may use either `SKILL.md` or `skill_<name>.md`.

`.claude/skills` is not canonical unless explicitly reintroduced.

When adding or updating a skill:

1. Update `.agents/skills/<name>/SKILL.md`.
2. Update the matching `.codex/skills/<name>/SKILL.md` or `.codex/skills/<name>/skill_<name>.md` if Codex compatibility is required.
3. Ensure neither file contains commands that print environment values.
4. Ensure the skill respects GitHub MCP-only commits.
5. Ensure the skill does not use local `git add`, `git commit`, or `git push`.

Do not delete legacy skill directories unless the replacement path is documented and the user explicitly approves the migration.

---

## 13. Document Map

| Document | Purpose | Update frequency |
|---|---|---|
| `AGENTS.md` | Agent rules and workflow governance | When rules change |
| `WORK_QUEUE.md` | Live ordered task queue | Every task completion |
| `docs/tasks/task_NNN.md` | Individual task specs | Created per task, updated on status change |
| `docs/tasks/TASK_TEMPLATE.md` | Standard task-card template | When task format changes |
| `docs/backlog/issues.md` | Open issues and known problems | When issues are found or closed |
| `docs/backlog/remediation_backlog.md` | Security and tech-debt backlog | After audits or remediation planning |
| `docs/architecture/phase*_security_audit.md` | Security audit reports | After security audit phases |
| `TASK_SPEC.md` | Project state snapshot | After each milestone |
| `CLAUDE.md` | Legacy Claude-specific constraints, if retained | When Claude-specific rules change |
| `GEMINI.md` | Gemini CLI-specific constraints | When Gemini rules change |

Historical architecture documents may mention older skill paths such as `.claude/skills/`.

Do not update historical references unless the task explicitly requires that file.

---

## 14. Frozen Scopes

These paths must not be modified without explicit written approval in the task card:

```text
src/content_creation/models/        — Pydantic models
src/content_creation/generation/    — generators
prompts/                            — prompt templates
docs/schema.md                      — data contracts
```

If a task requires touching a frozen scope:

1. Stop.
2. Request approval.
3. Record the approval in the task card before proceeding.

---

## 15. Validation Command Reference

Set cache directory:

```bash
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
mkdir -p "$UV_CACHE_DIR"
```

Full test suite — Type A tasks only unless the task card says otherwise:

```bash
uv run python -m pytest --tb=short -q 2>&1 | tail -5
```

Type checking — only when required by the task card:

```bash
uv run mypy src/content_creation --strict
```

Formatting check — only when required by the task card:

```bash
uv run black src/ tests/ --check
uv run isort src/ tests/ --check-only
```

Read-only secret scan:

```bash
python - <<'PYSCAN'
from pathlib import Path
import re

roots = [
    Path("AGENTS.md"),
    Path(".agents"),
    Path(".codex"),
    Path("docs"),
    Path("tests"),
    Path("src"),
    Path(".gitignore"),
]

patterns = [
    ("classic GitHub PAT", re.compile("g" + "hp_" + r"[A-Za-z0-9_]{20,}")),
    ("fine-grained GitHub PAT", re.compile("github" + "_pat_" + r"[A-Za-z0-9_]{20,}")),
    ("bearer token", re.compile("Bearer" + r"\s+(" + "g" + "hp_|github" + "_pat_" + r")[A-Za-z0-9_]+")),
    ("Gemini-looking key", re.compile("AI" + "za" + r"[0-9A-Za-z_-]{20,}")),
    ("OpenAI-looking key", re.compile("s" + "k-" + r"[A-Za-z0-9_-]{20,}")),
    ("assigned GitHub token env", re.compile(r"GITHUB_PERSONAL_ACCESS_TOKEN\s*=\s*['\"]?[^'\"]+")),
]

def iter_files(root: Path):
    if root.is_file():
        yield root
    elif root.is_dir():
        for p in root.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                yield p

hits = []
for root in roots:
    for file_path in iter_files(root):
        try:
            content = file_path.read_text(errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            for label, pattern in patterns:
                if pattern.search(line):
                    hits.append((str(file_path), line_no, label))

for file_path, line_no, label in hits:
    print(f"{file_path}:{line_no}: potential {label}")

raise SystemExit(1 if hits else 0)
PYSCAN
```

Database ignore check:

```bash
git check-ignore -v jobs.db events.db audit.db 2>/dev/null || echo "WARNING: db files not ignored"
```

Worktree check:

```bash
git status --short
```

Whitespace check:

```bash
git diff --check
```

---

## 16. Security-Audit Rules

Security-audit tasks are read-only unless the task card explicitly authorizes edits.

Security scans must not expose values.

Allowed scan pattern:

```bash
python - <<'PYSCAN'
from pathlib import Path
import re

roots = [
    Path("AGENTS.md"),
    Path(".agents"),
    Path(".codex"),
    Path("docs"),
    Path("tests"),
    Path("src"),
    Path(".gitignore"),
]

patterns = [
    ("classic GitHub PAT", re.compile("g" + "hp_" + r"[A-Za-z0-9_]{20,}")),
    ("fine-grained GitHub PAT", re.compile("github" + "_pat_" + r"[A-Za-z0-9_]{20,}")),
    ("bearer token", re.compile("Bearer" + r"\s+(" + "g" + "hp_|github" + "_pat_" + r")[A-Za-z0-9_]+")),
    ("Gemini-looking key", re.compile("AI" + "za" + r"[0-9A-Za-z_-]{20,}")),
    ("OpenAI-looking key", re.compile("s" + "k-" + r"[A-Za-z0-9_-]{20,}")),
    ("assigned GitHub token env", re.compile(r"GITHUB_PERSONAL_ACCESS_TOKEN\s*=\s*['\"]?[^'\"]+")),
]

def iter_files(root: Path):
    if root.is_file():
        yield root
    elif root.is_dir():
        for p in root.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                yield p

hits = []
for root in roots:
    for file_path in iter_files(root):
        try:
            content = file_path.read_text(errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            for label, pattern in patterns:
                if pattern.search(line):
                    hits.append((str(file_path), line_no, label))

for file_path, line_no, label in hits:
    print(f"{file_path}:{line_no}: potential {label}")

raise SystemExit(1 if hits else 0)
PYSCAN
```

Forbidden scan patterns:

```bash
printenv
env
echo $GEMINI_API_KEY
echo $GITHUB_PERSONAL_ACCESS_TOKEN
python -c "import os; print(os.environ)"
```

If a potential secret is found:

1. Do not print the full value.
2. Report only the file path, line number, and secret type.
3. Recommend rotation if exposure is confirmed.
4. Do not rewrite Git history unless explicitly instructed.

---

## 17. Gitignore and Local Config Rules

Never commit local-only agent settings.

Ignored local config should include:

```text
.codex/settings.local.json
```

Do not commit:

```text
.env
*.db
*.sqlite
*.sqlite3
*.log
credentials.json
token.json
```

Project-level reusable skills may be committed under:

```text
.agents/skills/
.codex/skills/
```

Do not commit Codex caches, sessions, logs, shell snapshots, or local runtime state.

---

## 18. Goal Guardian Check

Before completing any task, verify:

1. Does this change serve the project goal: reliable, source-grounded content pipeline?
2. Does this change stay within the declared task scope?
3. Does this change preserve or improve test coverage?
4. Does this change respect frozen scopes?
5. Does this change avoid exposing secrets or credentials?
6. Does this change preserve the MCP-only commit workflow?
7. Does this change avoid accidental architecture drift?
8. Does this change avoid mixing unrelated repair, test, docs, and governance changes?

If any answer is no, stop and report the conflict.

---

## 19. Reporting Format

Final report for normal task execution:

```text
Task: TASK-NNN — <title>
Type: A | B
Status: DONE | BLOCKED
Files changed:
- <file>
Validation:
- <command>: <result>
Tests:
- baseline: <count or N/A>
- final: <count or N/A>
Commit method:
- GitHub MCP push_files
Commits:
- <message>
Notes:
- <important constraints, blockers, or follow-up>
```

Final report for review / repair / preservation:

```text
Mode: Review / repair / preservation
Branch: <branch>
Files reviewed:
- <file>
Files changed:
- <file>
Files excluded:
- <file>
Validation:
- git diff --check: <result>
- secret scan: <result>
Ready for MCP push:
- yes/no
Remaining risks:
- <risk or none>
```

Do not auto-start the next task. Wait for the next explicit instruction or `$run-next-task`.
