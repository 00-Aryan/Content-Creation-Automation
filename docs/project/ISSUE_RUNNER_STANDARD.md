# Issue Runner Standard

This document details the standard operation and governance rules for the local issue-driven automation runner (`scripts/issue-runner.sh`).

## 1. Overview

The automation runner turns one GitHub issue into one controlled workflow branch, task card, agent run, scope check, test run, commit, pushed branch, and pull request. This ensures all modifications are traceable, verified, and safe.

## 2. Command Reference

All commands should be executed from the repository root.

### Preferred Command Form

The preferred way to run the issue runner is via the shell wrapper script:

```bash
./scripts/issue-runner.sh [mode] [options]
```

### Direct Script Invocation and Package Path Imports

Direct execution using python3 is also supported and expected to run reliably from the repository root without package-mode invocation wrappers (i.e. without requiring `python3 -m scripts.issue_runner`):

```bash
python3 scripts/issue_runner.py [mode] [options]
```

To achieve this, the scripts utilize robust local import path handling (by dynamically injecting the repository root into `sys.path` at startup and using try-except fallback imports for sister modules such as `issue_scope_guard.py`).

### Modes

| Mode | Command | Description |
|---|---|---|
| **Plan** | `./scripts/issue-runner.sh plan --issue <num>` | Verifies clean branch (unless `--force` is used), fetches issue description, checks out branch, and initializes task card. |
| **Run** | `./scripts/issue-runner.sh run [--engine agy\|codex]` | Runs agent on task card (default `agy`). |
| **Verify** | `./scripts/issue-runner.sh verify` | Validates file modifications against task-card scope, checks syntax, runs tests. |
| **PR** | `./scripts/issue-runner.sh pr` | Commits changes, pushes branch to origin, and creates a pull request. |
| **Merge** | `./scripts/issue-runner.sh merge` | Merges the PR, deletes the branch, and pulls main (only if safe). |
| **Full** | `./scripts/issue-runner.sh full --issue <num> [--merge]` | Executes plan, run, verify, and pr sequentially. Stops before merge unless `--merge` is specified. |
| **Inspect** | `./scripts/issue-runner.sh inspect [--issue <num>]` | Displays active run details, worktree status, and derived metadata. |
| **Abort** | `./scripts/issue-runner.sh abort` | Safely aborts only when the active branch is clean, unmerged, and has no open or merged PR. |
| **Resume** | `./scripts/issue-runner.sh resume` | Resumes the active run from the last completed stage. |

### Workflow State Machine

The runner persists exactly one active workflow state in
`.git/issue-runner-runs/active_run.json`. The only legal forward transitions are:

```text
planned -> run_completed -> verified -> pr_created -> merged
```

Each mode requires the prior state:

- `run` requires `planned`
- `verify` requires `run_completed`
- `pr` requires `verified`
- `merge` requires `pr_created`

State files are validated before use. Missing required fields, invalid states, or
corrupted JSON are operator-facing errors. State writes are atomic: the runner
writes a temporary file in the run metadata directory and replaces the active
pointer only after the write is complete. Failed operations do not advance state.
Planning refuses to overwrite an unrelated active run.

Run, verify, and PR creation require the current branch to match the branch
stored in active state. Merge may run from another branch only after the PR has
already been created, because it performs its own PR head and local-main checks.

### Agent Completion Contract

The `run` mode no longer infers success from natural language. Each run creates
a cryptographically strong status nonce. The agent engine must exit with code
`0` and the final non-empty stdout line must be exactly one nonce-bound status:

```text
ISSUE_RUNNER_STATUS <nonce> COMPLETED
ISSUE_RUNNER_STATUS <nonce> FAILED <reason>
```

The prompt describes the grammar but does not include the exact accepted final
line. Status lines are accepted only from stdout, and only when they are the
final non-empty stdout line. Wrong or missing nonce values, duplicate status
lines, status output on stderr, trailing explanatory output, non-zero engine
exit, failed status, or empty output fails the run. The agent output log is
still written on every outcome, and active state remains `planned` on failure.

### Inspect-Mode and Stale Active-Run Warnings

The `inspect` mode retrieves the current Git branch, the expected run log directory, and any active run details stored in `active_run.json`. When `--issue <num>` is passed, it derives the expected task ID, branch name, and task card path from GitHub (via `gh`).
- **Missing Task Card:** If the derived task card does not exist yet on disk, it displays a clear message (e.g. `Note: Task card file '...' does not exist yet.`) instead of crashing.
- **Stale Active Runs:** If `active_run.json` exists and points to an issue branch but the current branch is `main`, `inspect` mode tolerates this state and prints a warning (e.g. `[!] WARNING: active_run.json points to issue branch '...' but current branch is 'main'`) instead of failing or crashing.
- **No File Modifications:** The `inspect` mode is read-only and never modifies files on disk.
- **Evidence Visibility:** Inspect reports the current state, expected next
  action, branch match status, manifest presence, verification result, current
  fingerprint match status, PR number, and recorded head SHA when available.

`resume` executes only the single valid next transition for the active state. It
does not auto-advance through multiple stages.

## 3. Directory Layout for Trace Logs

Every execution is fully traceable. To ensure the working tree remains clean and free of untracked files that could block consecutive plan runs, all execution outputs and logs are written under the local git metadata directory:
`.git/issue-runner-runs/issue-<padded-issue-num>-task-<padded-task-num>-<timestamp>/`

Inside the run directory, you will find:
- `issue.json` — The fetched GitHub issue payload
- `task_card_before.md` — The generated task card prior to execution (if it already existed)
- `task_card_after.md` — The task card after execution has completed
- `allowed_files.txt` — File paths allowed to be modified or created
- `changed_files.txt` — Actual modified files in the working directory
- `scope_check.txt` — Output of the scope guard validation check
- `targeted_tests.log` — Logs of targeted tests specified in the task card
- `quality_checks.log` — Black, isort, and mypy check evidence for changed Python files
- `full_tests.log` — Full pytest run execution logs
- `verification.json` — Structured verification manifest and fingerprint evidence
- `commit.txt` — Git commit message and command log
- `pr.txt` — PR generation command output
- `agent_output.log` — Plain text output log of the executing agent

## 4. Safety Guardrails

1. **Refusal of Dirty Working Trees:** The runner will refuse to plan or merge if any uncommitted files exist in the repository (outside run metadata folders).
2. **Strict Scope Enforcement:** The scope guard will block PR creation if any files were changed/created that are not explicitly documented in the task card's `Files to modify` or `Files to create` section.
3. **Automated Merge Restrictions:** Auto-merging is strictly disabled if the GitHub issue contains any of the following labels:
   - `security`
   - `ci`
   - `architecture`
   - `hardening`
4. **Test Baselines:** The full test suite must not regress below the baseline of **1000** passing tests.

## 4.1 Verification Contract

Verification executes every fenced `bash` block from the task card's
`## Validation` section as one Bash program with
`bash -e -u -o pipefail -c <block>`. It does not split blocks into lines and
does not skip `pytest` commands. Each executed block records its index, exact
command text, exit code, stdout, and stderr in `targeted_tests.log`. Verification
stops at the first non-zero block. Empty or missing validation Bash blocks fail.

For changed Python files reported by the scope guard, verification reproduces
the local quality gates used by CI:

```bash
uv run black --check -- <changed-python-files>
uv run isort --check-only -- <changed-python-files>
uv run mypy --explicit-package-bases -- <changed-python-files>
```

These checks are skipped only when no non-deleted Python files changed, using
the manifest reason `no_changed_python_files`. Verification never auto-formats
files.

The full pytest gate requires both a process exit code of `0` and a parsed pass
count greater than or equal to `BASELINE_MIN`. A parseable pass count does not
override a non-zero pytest exit. Empty pytest output or an unparseable pass count
fails verification.

After collecting gate results, verification writes `verification.json`. The
manifest records issue number, task number, branch, timestamp, prior workflow
state, changed files, changed Python files, scope/syntax/targeted/quality/full
pytest results, overall result, the verified working-tree fingerprint, and the
verified Git tree SHA for the content that PR mode is allowed to commit.

### Fingerprint Contract

The verified fingerprint is:

```text
sha256(
  "issue-runner-fingerprint-v1",
  branch name,
  git diff --binary,
  git diff --cached --binary,
  path and contents of each untracked changed file
)
```

PR creation recomputes this fingerprint and refuses stale evidence when it no
longer matches the manifest. It also compares the current changed-file set to
the verified changed-file set so new untracked files cannot be omitted from
freshness checks.

The verified tree SHA is computed with a temporary Git index initialized from
`HEAD` and updated only with the allowed files that PR mode may commit. This does
not mutate the real index. PR mode later stages the same allowed file set in the
real index and requires `git write-tree` to match the verified tree SHA before
committing.

The manifest validator does not treat `overall_verification_result` as an
independent authority. It derives success from the nested gate results, pytest
exit/count, quality skip reasons, fingerprint schema, issue/task/branch, and
tree SHA. Manual filesystem tampering with local JSON is outside the
cryptographic trust boundary, but the runner enforces schema consistency and
current-worktree freshness before PR creation.

## 4.2 Pull Request and Merge Contract

PR creation requires:

- active state `verified`
- current branch matching active state
- successful `verification.json`
- required logs present and non-empty
- current changed-file set and working-tree fingerprint matching verified evidence
- no pre-existing staged changes
- staged tree matching the verified tree SHA
- exactly one commit-message title from the task card

The task-card commit message is used as both the Git commit message and PR
title. Missing or malformed commit-message sections are hard failures; the
runner does not fall back to a generic title.

The PR body is generated from structured manifest evidence. Missing, empty, or
failed evidence returns a non-zero error and never publishes `No log available.`
as successful validation evidence.

After committing, the runner records commit facts separately from immutable
verification evidence in `pr_metadata.json`. The verification manifest is not
modified after verify mode completes. After pushing, the runner resolves the PR
number, URL, and PR head SHA, writes complete PR metadata, and advances to
`pr_created` only after all operations succeed.

Merge requires:

- active state `pr_created`
- recorded PR number
- recorded committed, pushed, and PR head SHA
- open, non-draft, mergeable PR
- clean merge state
- PR head equal to the recorded committed and pushed SHA
- all PR checks returned by `gh pr checks --json name,state,bucket,workflow,link`
  to be in the `pass` bucket for that head

The merge command uses a squash merge pinned with `--match-head-commit`. There
is no auto-merge substitute and no unguarded fallback merge. Active state is
cleared only after GitHub confirms the PR is merged, local `main` is
fast-forwarded to match `origin/main`, and `final_state.json` is atomically
written and read back from the run directory.

Abort is safe by default. It refuses to proceed from the wrong branch, with a
dirty worktree, with unmerged commits relative to `origin/main`, with an open or
merged PR, or when the aborted-state archive cannot be written and read back.
It archives `abort_state.json`, uses normal branch deletion, preserves run logs,
and clears active state only after all abort cleanup succeeds.

## 5. Task Card Generation & Validation Rules

In plan mode, the runner dynamically generates an issue-specific task card under `docs/tasks/task_<padded-task-num>.md` instead of copying a static template with placeholders.

### Generation Workflow
1. **Title Cleanup:** Any leading task identifier (e.g. `TASK-040:`) is stripped from the GitHub issue title before assigning it to the title header, avoiding duplicate title text.
2. **Phase Label Mapping:** The runner inspects the GitHub issue labels and maps them to human-readable SDLC Phase names:
   - `phase:12.3` → `12.3 — Platform-Aware Content`
   - `phase:12.4` → `12.4 — LLM Quality Guardrails`
   - `phase:12.5` → `12.5 — LinkedIn Export and Publishing`
   - `phase:12.6` → `12.6 — YouTube Shorts Flow`
   - `phase:12.7` → `12.7 — Observability and Reliability`
   - `phase:12.8` → `12.8 — Portfolio Readiness`
   - `phase:deferred-polish` → `Deferred UI/Polish`
   - `phase:hardening` → `Technical Debt and Hardening`
3. **File Scope Inference:**
   - **Explicit Mapping:** Specific issues (e.g., `TASK-040`) have hardcoded allowed scopes mapping to their target architectural design deliverables.
   - **Body Extraction:** For other tasks, the runner attempts to parse file paths listed in the issue body under `Files to create` and `Files to modify`.
   - **Resolution and Fallback:** If a safe file scope cannot be derived from the issue, plan mode stops immediately with the error:
     `Cannot infer safe file scope for this issue. Create task card manually or add scope mapping.`
     It will not generate a placeholder card.
4. **Force Overwrite Guard:** If a task card already exists under `docs/tasks/`, plan mode will exit with an error to prevent accidental overwrites, unless the `--force` flag is explicitly passed.

### Placeholder & Emptiness Rejection
Before writing a task card, the runner scans its content to ensure no generic or incomplete sections exist. The plan run will fail if the card contains:
- Stale placeholder markers: `<Specific, observable criterion`, `Replace this comment`, `Section Name`, or `phaseXX`.
- Empty key sections: `### Files to create`, `### Files to modify`, or `## Implementation Steps` (whitespace and comment lines only).

## 6. Naming and Conventions

To ensure clean mapping between external GitHub issue tracking and internal engineering tasks, the following rules apply:

- **GitHub Issue Number vs TASK ID:** The GitHub issue number (e.g., `#5`) is sequential on GitHub and is used for closing pull requests (e.g., `Closes #5`). The TASK ID (e.g., `TASK-040`) represents the internal engineering tracker, which maps tasks to architectural deliverables and SDLC milestones. They are different and must not be used interchangeably.
- **Issue Title Requirement:** The title of the GitHub issue must contain the internal TASK ID matching the pattern `TASK-XXX` (e.g., `TASK-040: Define platform content contracts`). If it does not, the runner will refuse to proceed unless the `--allow-no-task` flag is explicitly provided.
- **Task Cards:** Task cards are named using the internal TASK ID (e.g., `docs/tasks/task_040.md`), not the GitHub issue number.
- **Branch Naming:** Branches are named according to the convention `issue-<padded-issue-num>-task-<padded-task-num>-<slug>` (e.g., `issue-005-task-040-platform-content-contracts`).
- **Run Directory Naming:** Run directories are named according to the convention `.git/issue-runner-runs/issue-<padded-issue-num>-task-<padded-task-num>-<timestamp>/`.
- **PR Closing:** The pull request uses the GitHub issue number for closing references (e.g., `Closes #5`), while all task artifacts and commits keep references to the internal TASK ID (e.g., `TASK-040`).
