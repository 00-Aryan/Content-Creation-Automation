# Issue Runner Standard

This document details the standard operation and governance rules for the local issue-driven automation runner (`scripts/issue-runner.sh`).

## 1. Overview

The automation runner turns one GitHub issue into one controlled workflow branch, task card, agent run, scope check, test run, commit, pushed branch, and pull request. This ensures all modifications are traceable, verified, and safe.

## 2. Command Reference

All commands should be executed from the repository root.

```bash
./scripts/issue-runner.sh [mode] [options]
```

### Modes

| Mode | Command | Description |
|---|---|---|
| **Plan** | `./scripts/issue-runner.sh plan --issue <num>` | Verifies clean branch, fetches issue description, checks out branch, and initializes task card. |
| **Run** | `./scripts/issue-runner.sh run [--engine agy\|codex]` | Runs agent on task card (default `agy`). |
| **Verify** | `./scripts/issue-runner.sh verify` | Validates file modifications against task-card scope, checks syntax, runs tests. |
| **PR** | `./scripts/issue-runner.sh pr` | Commits changes, pushes branch to origin, and creates a pull request. |
| **Merge** | `./scripts/issue-runner.sh merge` | Merges the PR, deletes the branch, and pulls main (only if safe). |
| **Full** | `./scripts/issue-runner.sh full --issue <num> [--merge]` | Executes plan, run, verify, and pr sequentially. Stops before merge unless `--merge` is specified. |
| **Inspect** | `./scripts/issue-runner.sh inspect` | Displays active run state and status. |
| **Abort** | `./scripts/issue-runner.sh abort` | Discards branch, resets changes, and cleans active run state. |
| **Resume** | `./scripts/issue-runner.sh resume` | Resumes the active run from the last completed stage. |

## 3. Directory Layout for Trace Logs

Every execution is fully traceable. Execution outputs and logs are written under:
`.runs/issue-<number>-<timestamp>/`

Inside the run directory, you will find:
- `issue.json` — The fetched GitHub issue payload
- `task_card_before.md` — The generated task card prior to execution
- `task_card_after.md` — The task card after execution has completed
- `allowed_files.txt` — File paths allowed to be modified or created
- `changed_files.txt` — Actual modified files in the working directory
- `scope_check.txt` — Output of the scope guard validation check
- `targeted_tests.log` — Logs of targeted tests specified in the task card
- `full_tests.log` — Full pytest run execution logs
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
