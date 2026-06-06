# AGENTS.md — Content Creation Automation Platform
## Master Agent Instructions (Claude Code · Codex · Gemini CLI)

Read this file completely before taking any action.
This document governs ALL agents working in this repository.

---

## 1. WHAT THIS PROJECT IS

A production-grade, source-grounded AI pipeline that transforms ML/AI research
into educational content assets for students. Every claim is traceable to source.
Every asset requires human approval. No auto-publishing. No hallucination.

**Primary goal:** Reliable, observable, maintainable pipeline — not feature volume.

**Current state:** Read `WORK_QUEUE.md` for the active phase and next task.
Read `TASK_SPEC.md` for the latest milestone summary.
Read `docs/project-context.md` for long-term vision.

---

## 2. BEFORE YOU DO ANYTHING

### Set environment first — every session, no exceptions

export UV_CACHE_DIR=/tmp/uv-cache

### Classify the task before running anything else

Read the task card's Scope section.

Type A — any .py file in scope → source code task
Type B — only .md, .yaml, .yml, .gitignore, .txt, .json, .toml → docs/config task

### Type A tasks only — run baseline

export UV_CACHE_DIR=/tmp/uv-cache
uv run python -m pytest --tb=no -q 2>&1 | tail -3

Must show ≥ 950 passed. 16 known failures in test_notification_streaming.py
are pre-existing — they do not block execution.

If output is a filesystem error: try mkdir -p /tmp/uv-cache and retry once.
If it still fails, report and stop.

### Type B tasks — no baseline required

Proceed directly to implementation.

### Branch check (all tasks)

git branch --show-current
Must be main. If not, report and stop.

---

## 3. ABSOLUTE DO NOT RULES

These override everything else. No exceptions, no rationalizations.

**Architecture:**
- Do NOT change workflow semantics or business logic without explicit approval
- Do NOT bypass WorkflowActionExecutor, ActionAvailabilityEngine, or ReviewTransitionEngine
- Do NOT call repositories or services directly from the Streamlit UI layer
- Do NOT add Streamlit imports into domain or infrastructure layers
- Do NOT introduce external queues (Celery, Redis, RabbitMQ, Kafka) without approval
- Do NOT change Pydantic model fields without updating all dependent code and tests

**Secrets:**
- Do NOT print, log, or include any environment variable VALUE in any output
- Do NOT add fallback values to `os.environ.get("GEMINI_API_KEY", "...")` calls
- Do NOT commit a `.env` file under any circumstances
- Do NOT embed API keys, tokens, or credentials in any source file, config, or prompt
- Do NOT run `printenv`, `env`, `echo $VARIABLE` in any skill or command

**Scope:**
- Do NOT modify files outside the current task's declared scope
- Do NOT refactor opportunistically — fix only what the task specifies
- Do NOT add features during audit or security phases
- Do NOT silently change architecture

**Testing:**
- Do NOT commit if the test suite count dropped
- Do NOT skip tests to make a commit pass
- Do NOT modify tests to make them pass if the underlying code is broken

---

## 4. MANDATORY WORKFLOW FOR EVERY TASK

```
READ task card (docs/tasks/task_NNN.md)
    ↓
VERIFY scope — list exact files you will touch
    ↓
IMPLEMENT — surgical changes only, nothing beyond task scope
    ↓
VALIDATE — run the commands in the task card's Validation section
    ↓
CONFIRM test count ≥ baseline
    ↓
UPDATE task status in WORK_QUEUE.md → DONE
    ↓
COMMIT using the exact message format in the task card
    ↓
REPORT: files changed, test count before/after, what was done
```

If any step fails, stop. Update task status to BLOCKED. Report the failure.
Do not attempt the next task.

---

## 5. COMMIT MESSAGE FORMAT

```
type(scope): description (TASK-NNN)
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `security`

Examples:
```
docs(security): add .env.example template (TASK-001)
fix(gitignore): add *.db rules for Phase 11+ databases (TASK-002)
feat(ci): add GitHub Actions secret scan workflow (TASK-004)
```

Never commit without a task reference unless it is a hotfix.

---

## 6. SKILL REFERENCE

Available skills (trigger with `$skill-name`):

| Skill | Trigger | Purpose |
|---|---|---|
| run-next-task | `$run-next-task` | Execute next PENDING task from WORK_QUEUE |
| new-phase | `$new-phase` | Convert phase description into task cards + update queue |
| drift-check | `$drift-check` | Verify project has not drifted from stated goals |
| fix-and-continue | `$fix-and-continue TASK-NNN` | Apply one approved remediation item |
| security-audit | `$security-audit` | Run read-only secret and security scan |

Skill files: `.claude/skills/<name>/SKILL.md`
Codex users: same files are mirrored in `.codex/skills/<name>/SKILL.md`

---

## 7. DOCUMENT MAP

| Document | Purpose | Update frequency |
|---|---|---|
| `AGENTS.md` | This file — agent rules | When rules change |
| `WORK_QUEUE.md` | Live ordered task queue | Every task completion |
| `docs/tasks/task_NNN.md` | Individual task specs | Created per task, updated on status change |
| `docs/backlog/issues.md` | Open issues and known problems | When issues are found or closed |
| `docs/backlog/remediation_backlog.md` | Security and tech debt items | After each audit |
| `docs/architecture/phase*_security_audit.md` | Audit reports | After each audit phase |
| `TASK_SPEC.md` | Project state snapshot | After each milestone |
| `CLAUDE.md` | Claude Code specific constraints | When coding standards change |
| `GEMINI.md` | Gemini CLI specific constraints | When Gemini rules change |

---

## 8. FROZEN SCOPES

These files/modules must NOT be modified without explicit written approval:

```
src/content_creation/models/        — all Pydantic models
src/content_creation/generation/    — all generators
prompts/                            — all prompt templates
docs/schema.md                      — data contracts
```

If a task requires touching a frozen scope, stop. Request approval first.
Record the approval in the task card before proceeding.

---

## 9. VALIDATION AND COMMIT

export UV_CACHE_DIR=/tmp/uv-cache

Full test suite (Type A tasks only):
uv run python -m pytest --tb=short -q 2>&1 | tail -5

Commit method — GitHub MCP ONLY:
Local .git is read-only. Use mcp__github.push_files for all commits.
Never use git commit, git add, or git push.

mcp__github.push_files parameters:
  owner:   "00-Aryan"
  repo:    "Content-Creation-Automation"
  branch:  "main"
  message: <exact task card commit message>
  files:   [only files in task scope]

---

## 10. GOAL GUARDIAN CHECK

Before completing any task, ask:

1. Does this change serve the project goal (reliable, source-grounded content pipeline)?
2. Does this change stay within the declared task scope?
3. Does this change preserve or improve test coverage?
4. Does this change respect all frozen scopes?
5. Does this change expose any secrets or credentials?

If any answer is NO — stop, do not commit, report the conflict.
