#!/usr/bin/env python3
import os
import sys

# Ensure repository root is in sys.path for direct execution imports
scripts_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(scripts_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import argparse
import hashlib
import importlib
import json
import re
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ACTIVE_RUN_PATH = ".git/issue-runner-runs/active_run.json"
BASELINE_MIN = 1000  # The baseline number of passing tests
WORKFLOW_STATES = ("planned", "run_completed", "verified", "pr_created", "merged")
NEXT_WORKFLOW_STATE = {
    "planned": "run_completed",
    "run_completed": "verified",
    "verified": "pr_created",
    "pr_created": "merged",
}
MODE_REQUIRED_STATE = {
    "run": "planned",
    "verify": "run_completed",
    "pr": "verified",
    "merge": "pr_created",
}
REQUIRED_STATE_FIELDS = {
    "issue_number",
    "padded_number",
    "branch",
    "run_dir",
    "timestamp",
    "status",
}
REQUIRED_MANIFEST_FIELDS = {
    "issue_number",
    "task_number",
    "branch",
    "verification_timestamp",
    "workflow_state_before_verification",
    "changed_files",
    "changed_python_files",
    "scope_gate_result",
    "syntax_gate_result",
    "targeted_validation_result",
    "black_result",
    "isort_result",
    "mypy_result",
    "full_pytest_exit_code",
    "full_pytest_pass_count",
    "overall_verification_result",
    "verified_working_tree_fingerprint",
    "verified_worktree_fingerprint",
    "verified_tree_sha",
}

STATUS_PREFIX = "ISSUE_RUNNER_STATUS"
GH_PR_CHECK_FIELDS = ("name", "state", "bucket", "workflow", "link")
FINGERPRINT_VERSION = "issue-runner-fingerprint-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")

PHASE_MAPPING = {
    "phase:12.3": "12.3 — Platform-Aware Content",
    "phase:12.4": "12.4 — LLM Quality Guardrails",
    "phase:12.5": "12.5 — LinkedIn Export and Publishing",
    "phase:12.6": "12.6 — YouTube Shorts Flow",
    "phase:12.7": "12.7 — Observability and Reliability",
    "phase:12.8": "12.8 — Portfolio Readiness",
    "phase:deferred-polish": "Deferred UI/Polish",
    "phase:hardening": "Technical Debt and Hardening",
}


def extract_files_from_text(text):
    mod_files = []
    cre_files = []
    current_section = None
    for line in text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        if "files to modify" in line_s.lower() or "modify files" in line_s.lower():
            current_section = "modify"
            continue
        elif "files to create" in line_s.lower() or "create files" in line_s.lower():
            current_section = "create"
            continue
        elif "files to not touch" in line_s.lower():
            current_section = None
            continue

        bullet = re.match(r"^[-*]\s+(.*)", line_s)
        if bullet:
            file_val = bullet.group(1).strip().strip("`").strip()
            file_val = re.sub(r"^\[[\sX]*\]\s*", "", file_val).strip()
            if file_val and not file_val.startswith("#"):
                if current_section == "modify":
                    mod_files.append(file_val)
                elif current_section == "create":
                    cre_files.append(file_val)
    return mod_files, cre_files


def generate_task_card_content(issue_data, metadata):
    issue_num = issue_data["number"]
    issue_title = issue_data.get("title", "").strip()
    issue_title_clean = re.sub(
        r"^TASK-\d+\s*:?\s*", "", issue_title, flags=re.IGNORECASE
    ).strip()
    issue_body = issue_data.get("body", "") or ""
    labels = [l.get("name", "") for l in issue_data.get("labels", [])]
    padded_task_num = metadata["padded_task_number"]
    task_num = int(padded_task_num)

    phase_val = None
    for l in labels:
        if l in PHASE_MAPPING:
            phase_val = PHASE_MAPPING[l]
            break
    if not phase_val:
        phase_val = get_current_phase()

    priority_val = "HIGH"
    for l in labels:
        if l.startswith("priority:"):
            priority_val = l.split(":")[1].upper()

    requires_approval = "YES"

    if task_num == 40:
        files_create = [
            "docs/platform/platform-content-contracts.md",
            "docs/platform/linkedin-content-contract.md",
            "docs/platform/youtube-shorts-content-contract.md",
            "docs/platform/source-grounding-contract.md",
            "docs/platform/platform-quality-gates.md",
            "docs/phase-12.3-platform-contracts.md",
        ]
        files_modify = [
            "docs/project/CURRENT_STATE.md",
            "docs/project/NEXT_ACTION.md",
            "docs/project/PHASES.md",
            "docs/project/ROADMAP.md",
            "docs/project/SPRINT_PLAN.md",
            "docs/project/DECISION_LOG.md",
            "docs/project/BACKLOG.md",
            "WORK_QUEUE.md",
        ]
        files_not_touch = [
            "src/",
            "tests/",
            "prompts/",
            "data/",
            "pyproject.toml",
            "uv.lock",
            ".github/workflows/",
            "docs/tasks/task_005.md",
        ]
        objective = (
            "Define precise output contracts before implementing platform generators."
        )
        context = "This task defines platform-specific content contracts to ensure generated content meets format, style, and quality constraints before ingestion. It establishes schemas for LinkedIn and YouTube Shorts. This enables platform-aware generation and validation, ensuring downstream publishing tools can consume assets without formatting errors."
        constraints = "Do not modify Python code or write tests. Do not touch prompts or schemas outside of the listed docs. Keep all contracts aligned with the roadmap and SDLC standard."
        steps = [
            "Create the platform content contract directory and write the core contract document detailing shared requirements.",
            "Define the LinkedIn content contract including character limits, tone, and formatting constraints.",
            "Define the YouTube Shorts content contract specifying scripts, thumbnails, duration, and structure.",
            "Define the source grounding contract ensuring trace logging requirements for all claims.",
            "Create the platform quality gates document listing checks required before assets are ready for export.",
            "Create the phase summary detailing the platform contracts defined.",
            "Update project tracking documentation: CURRENT_STATE.md, NEXT_ACTION.md, PHASES.md, ROADMAP.md, SPRINT_PLAN.md, DECISION_LOG.md, BACKLOG.md, and WORK_QUEUE.md.",
        ]
        validation_cmds = """# Verify all created documents exist
test -f docs/platform/platform-content-contracts.md
test -f docs/platform/linkedin-content-contract.md
test -f docs/platform/youtube-shorts-content-contract.md
test -f docs/platform/source-grounding-contract.md
test -f docs/platform/platform-quality-gates.md
test -f docs/phase-12.3-platform-contracts.md

# Verify tracked project files are modified
git status --short docs/project/"""
        success_criteria = [
            "Platform content contracts are fully defined in docs/platform/",
            "Mappings and gates are documented for both LinkedIn and YouTube Shorts",
            "Project documentation is updated to reflect Phase 12.3 progress",
        ]
        depends_on = "TASK-036"
        commit_msg = f"docs(platform): define platform content contracts for Phase 12.3 (TASK-{padded_task_num})"
    else:
        mod_extracted, cre_extracted = extract_files_from_text(issue_body)
        if not mod_extracted and not cre_extracted:
            print(
                "[-] ERROR: Cannot infer safe file scope for this issue. Create task card manually or add scope mapping.",
                file=sys.stderr,
            )
            sys.exit(1)

        files_create = cre_extracted
        files_modify = mod_extracted
        files_not_touch = [
            "src/",
            "tests/",
            "prompts/",
            "data/",
            "pyproject.toml",
            "uv.lock",
            ".github/workflows/",
            "docs/tasks/task_005.md",
        ]
        objective = issue_title
        context = f"This task addresses issue #{issue_num}: '{issue_title}'. It is a scoped modification to resolve the identified issue and align it with current requirements."
        constraints = "Keep changes focused on the declared file scope. Do not refactor unrelated modules."
        steps = [
            "Review the requirements of the task.",
            "Implement changes in the modified files list.",
            "Verify formatting, syntax, and logic using validation checks.",
        ]
        validation_cmds = "# Run project tests to ensure no regressions\nuv run python -m pytest --tb=short -q 2>&1 | tail -3"
        success_criteria = [
            "All requested modifications are implemented correctly",
            "No files outside the declared scope are modified",
        ]
        depends_on = "None"
        commit_msg = f"feat(issue-{issue_num}): resolve issue #{issue_num} (TASK-{padded_task_num})"

    create_block = "\n".join(f"- {f}" for f in files_create) if files_create else "None"
    modify_block = "\n".join(f"- {f}" for f in files_modify) if files_modify else "None"
    not_touch_block = (
        "\n".join(f"- {f}" for f in files_not_touch) if files_not_touch else "None"
    )
    steps_block = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, start=1))

    criteria_block = "\n".join(f"- [ ] {c}" for c in success_criteria)
    criteria_block += "\n- [ ] Test suite passes at baseline count (no regression)"
    criteria_block += "\n- [ ] No files outside declared scope were modified"

    today = datetime.now().strftime("%Y-%m-%d")

    card = f"""# TASK-{padded_task_num}: {issue_title_clean}

**Phase:** {phase_val}
**Status:** PENDING
**Priority:** {priority_val}
**Created:** {today}
**Completed:** —
**Requires approval:** {requires_approval}

---

## Traceability

- GitHub issue: GitHub issue #{issue_num}
- Phase target: {phase_val}
- Source: GitHub issue #{issue_num}

---

## Objective

{objective}

---

## Context

{context}

---

## Scope

### Files to create

{create_block}

### Files to modify

{modify_block}

### Files to NOT touch

{not_touch_block}

---

## Constraints

{constraints}

---

## Implementation Steps

{steps_block}

---

## Validation

```bash
# Baseline test suite — must match or exceed before-count
uv run python -m pytest --tb=short -q 2>&1 | tail -3

# Task-specific verification
{validation_cmds}
```

---

## Success Criteria

{criteria_block}

---

## Depends On

{depends_on}

---

## Blocks

None

---

## Commit Message

```
{commit_msg}
```

---

## Notes

None
"""
    return card


def run_cmd(cmd, check=True, capture=True, cwd=None):
    shell = isinstance(cmd, str)
    try:
        res = subprocess.run(
            cmd, shell=shell, capture_output=capture, text=True, check=check, cwd=cwd
        )
        return res
    except subprocess.CalledProcessError as e:
        if check:
            print(
                f"Command failed: {cmd}\nExit code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}",
                file=sys.stderr,
            )
            raise
        return e


class RunnerStateError(ValueError):
    pass


def fail(message, code=1):
    print(f"[-] ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def is_worktree_clean():
    res = run_cmd(["git", "status", "--porcelain"])
    # Ignore .runs/ directory changes and other temp files
    lines = [
        line
        for line in res.stdout.splitlines()
        if not (
            line[3:].startswith(".runs/")
            or line[3:].startswith(".git/issue-runner-runs/")
            or line[3:].startswith(".run-tasks.log")
            or ".pytest_cache" in line
            or ".mypy_cache" in line
        )
    ]
    return len(lines) == 0


def get_current_phase():
    if not os.path.exists("WORK_QUEUE.md"):
        return "Unknown"
    with open("WORK_QUEUE.md", "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"\*\*Current Phase:\*\*\s*(.*)", content)
    if match:
        return match.group(1).strip()
    return "Unknown"


def load_active_run():
    if os.path.exists(ACTIVE_RUN_PATH):
        try:
            with open(ACTIVE_RUN_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except json.JSONDecodeError as e:
            fail(f"Active run state is corrupted JSON: {ACTIVE_RUN_PATH}: {e}")
        except OSError as e:
            fail(f"Cannot read active run state: {ACTIVE_RUN_PATH}: {e}")
        try:
            validate_active_state(state)
        except RunnerStateError as e:
            fail(str(e))
        return state
    return None


def validate_active_state(state):
    if not isinstance(state, dict):
        raise RunnerStateError("Active run state must be a JSON object.")
    missing = sorted(REQUIRED_STATE_FIELDS.difference(state))
    if missing:
        raise RunnerStateError(
            f"Active run state is incomplete; missing: {', '.join(missing)}."
        )
    status = state.get("status")
    if status not in WORKFLOW_STATES:
        raise RunnerStateError(f"Active run state has invalid status: {status!r}.")
    for field in ["issue_number", "padded_number", "branch", "run_dir", "timestamp"]:
        if not isinstance(state.get(field), str) or not state[field].strip():
            raise RunnerStateError(
                f"Active run state field {field!r} must be a non-empty string."
            )
    return state


def safe_load_active_run():
    try:
        return load_active_run()
    except RunnerStateError as e:
        fail(str(e))


def save_active_run(state):
    validate_active_state(state)
    os.makedirs(os.path.dirname(ACTIVE_RUN_PATH), exist_ok=True)
    directory = os.path.dirname(ACTIVE_RUN_PATH)
    tmp_path = None
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory, delete=False
    ) as f:
        tmp_path = f.name
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, ACTIVE_RUN_PATH)


def clear_active_run():
    if os.path.exists(ACTIVE_RUN_PATH):
        os.remove(ACTIVE_RUN_PATH)


def parse_passed_count(pytest_output):
    match = re.search(r"(\d+)\s+passed", pytest_output)
    if match:
        return int(match.group(1))
    return None


def get_current_branch():
    res = run_cmd(["git", "branch", "--show-current"], check=False)
    if res.returncode != 0:
        fail(f"Cannot determine current branch: {res.stderr.strip()}")
    return res.stdout.strip()


def require_active_state(mode, require_branch=True):
    expected_status = MODE_REQUIRED_STATE[mode]
    state = load_active_run()
    if not state:
        fail(f"No active run state found. Run the previous mode before '{mode}'.")
    if state["status"] != expected_status:
        fail(
            f"Mode '{mode}' requires workflow state '{expected_status}', "
            f"but active state is '{state['status']}'."
        )
    if require_branch:
        current_branch = get_current_branch()
        if current_branch != state["branch"]:
            fail(
                f"Current branch '{current_branch}' does not match active run branch "
                f"'{state['branch']}'."
            )
    return state


def advance_state(state, new_status, **updates):
    current_status = state["status"]
    expected_next = NEXT_WORKFLOW_STATE.get(current_status)
    if expected_next != new_status:
        fail(f"Invalid workflow transition: {current_status} -> {new_status}.")
    updated = dict(state)
    updated.update(updates)
    updated["status"] = new_status
    save_active_run(updated)
    return updated


def expected_next_action(status):
    return {
        "planned": "run",
        "run_completed": "verify",
        "verified": "pr",
        "pr_created": "merge",
        "merged": "none",
    }.get(status, "unknown")


def analyze_agent_completion(returncode, stdout, stderr, expected_nonce):
    stdout_text = stdout or ""
    stderr_text = stderr or ""
    failures = []
    if returncode != 0:
        failures.append(f"agent engine exited with code {returncode}")
    if not stdout_text.strip():
        failures.append("agent output is empty")

    stdout_lines = [line.rstrip() for line in stdout_text.splitlines()]
    nonempty_stdout = [line.strip() for line in stdout_lines if line.strip()]
    final_line = nonempty_stdout[-1] if nonempty_stdout else ""
    stdout_status_lines = [
        line.strip()
        for line in stdout_lines
        if line.strip().startswith(f"{STATUS_PREFIX} ")
    ]
    stderr_status_lines = [
        line.strip()
        for line in stderr_text.splitlines()
        if line.strip().startswith(f"{STATUS_PREFIX} ")
    ]

    if stderr_status_lines:
        failures.append("agent emitted terminal status on stderr")
    if len(stdout_status_lines) > 1:
        failures.append("agent emitted multiple terminal statuses")
    if not stdout_status_lines:
        failures.append("agent did not emit ISSUE_RUNNER_STATUS terminal status")
    elif stdout_status_lines[0] != final_line:
        failures.append("agent terminal status was not the final stdout line")

    status_success = False
    if stdout_status_lines:
        status_line = stdout_status_lines[-1]
        completed_match = re.fullmatch(
            rf"{STATUS_PREFIX}\s+([0-9a-f]+)\s+COMPLETED", status_line
        )
        failed_match = re.fullmatch(
            rf"{STATUS_PREFIX}\s+([0-9a-f]+)\s+FAILED\s+(.+)", status_line
        )
        if not completed_match and not failed_match:
            failures.append("agent emitted malformed ISSUE_RUNNER_STATUS line")
        else:
            nonce = (completed_match or failed_match).group(1)
            if nonce != expected_nonce:
                failures.append("agent terminal status nonce did not match")
            if failed_match:
                failures.append(f"agent reported failure: {failed_match.group(2)}")
            status_success = bool(completed_match and nonce == expected_nonce)

    return {
        "success": not failures and status_success,
        "failures": failures,
    }


def extract_validation_bash_blocks(card_content):
    validation_match = re.search(
        r"(?ms)^## Validation\s*\n(.*?)(?=^##\s+|\Z)", card_content
    )
    if not validation_match:
        return []
    section = validation_match.group(1)
    return [
        match.group(1)
        for match in re.finditer(r"(?ms)^```bash\s*\n(.*?)\n```", section)
    ]


def write_targeted_validation_log(path, results):
    lines = []
    for result in results:
        lines.extend(
            [
                f"## Block {result['block_index']}",
                f"Exit Code: {result['exit_code']}",
                "Command:",
                "```bash",
                result["command"],
                "```",
                "STDOUT:",
                result["stdout"],
                "STDERR:",
                result["stderr"],
                "",
            ]
        )
    content = "\n".join(lines).rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if not os.path.getsize(path):
        fail(f"Targeted validation log could not be written: {path}")


def run_validation_blocks(blocks):
    results = []
    for index, block in enumerate(blocks, start=1):
        print(f"  - Executing validation bash block {index}")
        res = subprocess.run(
            ["bash", "-e", "-u", "-o", "pipefail", "-c", block],
            capture_output=True,
            text=True,
            check=False,
        )
        result = {
            "block_index": index,
            "command": block,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }
        results.append(result)
        if res.returncode != 0:
            break
    return results


def command_result(name, cmd, skipped=False, reason=None):
    if skipped:
        return {
            "name": name,
            "command": cmd,
            "skipped": True,
            "reason": reason,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "success": True,
        }
    res = run_cmd(cmd, check=False)
    return {
        "name": name,
        "command": cmd,
        "skipped": False,
        "exit_code": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "success": res.returncode == 0,
    }


def write_quality_log(path, results):
    with open(path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(f"## {result['name']}\n")
            f.write(f"Command: {json.dumps(result['command'])}\n")
            if result.get("skipped"):
                f.write(f"Skipped: {result.get('reason', '')}\n\n")
                continue
            f.write(f"Exit Code: {result['exit_code']}\n")
            f.write("STDOUT:\n")
            f.write(result.get("stdout", ""))
            f.write("\nSTDERR:\n")
            f.write(result.get("stderr", ""))
            f.write("\n\n")


def validate_repo_relative_path(path):
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Changed file path must be a non-empty string.")
    path_obj = Path(path)
    if path_obj.is_absolute() or ".." in path_obj.parts:
        raise ValueError(f"Unsafe changed file path: {path}")
    if any(part.startswith("-") for part in path_obj.parts):
        raise ValueError(f"Changed file path cannot be option-like: {path}")
    if any(ord(ch) < 32 for ch in path):
        raise ValueError(f"Changed file path contains control characters: {path}")
    return path


def validate_changed_files(changed_files):
    validated = []
    for status, path in changed_files:
        validated.append((status, validate_repo_relative_path(path)))
    return set(validated)


def compute_working_tree_fingerprint(branch, changed_files):
    hasher = hashlib.sha256()
    hasher.update(f"{FINGERPRINT_VERSION}\n".encode("utf-8"))
    hasher.update(f"branch:{branch}\n".encode("utf-8"))

    for cmd_name, cmd in [
        ("worktree-diff", ["git", "diff", "--binary"]),
        ("staged-diff", ["git", "diff", "--cached", "--binary"]),
    ]:
        res = run_cmd(cmd, check=False)
        hasher.update(f"{cmd_name}:exit:{res.returncode}\n".encode("utf-8"))
        hasher.update((res.stdout or "").encode("utf-8", errors="surrogateescape"))
        hasher.update((res.stderr or "").encode("utf-8", errors="surrogateescape"))

    for status, path in sorted(changed_files, key=lambda item: item[1]):
        if "?" not in status:
            continue
        hasher.update(f"untracked:{path}\n".encode("utf-8"))
        file_path = Path(path)
        if file_path.is_file():
            hasher.update(file_path.read_bytes())
        else:
            hasher.update(b"<missing>")
        hasher.update(b"\n")

    return {
        "algorithm": "sha256",
        "version": FINGERPRINT_VERSION,
        "contract": (
            "sha256 over fingerprint version, branch name, git diff --binary, "
            "git diff --cached --binary, and contents of untracked changed files"
        ),
        "value": hasher.hexdigest(),
    }


def changed_python_paths(changed_files):
    return sorted(
        path
        for status, path in validate_changed_files(changed_files)
        if path.endswith(".py") and "D" not in status
    )


def files_to_commit_from_scope(changed_files, allowed_all, card_path):
    files = []
    allowed = set(allowed_all)
    allowed.update({"WORK_QUEUE.md", card_path})
    for _, path in sorted(
        validate_changed_files(changed_files), key=lambda item: item[1]
    ):
        if path in allowed:
            files.append(path)
    return sorted(set(files))


def _run_git_with_temp_index(index_path, args):
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index_path
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def compute_tree_sha_for_files(files):
    safe_files = [validate_repo_relative_path(path) for path in sorted(set(files))]
    directory = tempfile.mkdtemp(prefix="issue-runner-index-")
    index_path = os.path.join(directory, "index")
    try:
        res_read = _run_git_with_temp_index(index_path, ["read-tree", "HEAD"])
        if res_read.returncode != 0:
            raise ValueError(
                f"Cannot initialize temporary Git index: {res_read.stderr.strip()}"
            )
        if safe_files:
            res_add = _run_git_with_temp_index(
                index_path, ["add", "-A", "--"] + safe_files
            )
            if res_add.returncode != 0:
                raise ValueError(
                    "Cannot stage verified files in temporary index: "
                    f"{res_add.stderr.strip()}"
                )
        res_tree = _run_git_with_temp_index(index_path, ["write-tree"])
        if res_tree.returncode != 0:
            raise ValueError(
                f"Cannot compute verified tree SHA: {res_tree.stderr.strip()}"
            )
        tree_sha = res_tree.stdout.strip()
        if not GIT_SHA_RE.fullmatch(tree_sha):
            raise ValueError(f"Git produced invalid tree SHA: {tree_sha!r}")
        return tree_sha
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def current_staged_files():
    res = run_cmd(["git", "diff", "--cached", "--name-only"], check=False)
    if res.returncode != 0:
        fail(f"Cannot inspect staged files: {res.stderr.strip()}")
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def stage_files_for_commit(files):
    safe_files = [validate_repo_relative_path(path) for path in sorted(set(files))]
    if not safe_files:
        fail("No allowed changes to commit.")
    run_cmd(["git", "add", "-A", "--"] + safe_files)


def write_pr_metadata(run_dir, data):
    path = os.path.join(run_dir, "pr_metadata.json")
    write_json_file(path, data)
    return path


def load_pr_metadata(run_dir):
    path = os.path.join(run_dir, "pr_metadata.json")
    if not os.path.exists(path):
        raise ValueError(f"PR metadata is missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def manifest_path(run_dir):
    return os.path.join(run_dir, "verification.json")


def _require_gate_success(manifest, key, failures):
    result = manifest.get(key)
    if not isinstance(result, dict):
        failures.append(f"{key} must be an object")
        return
    if result.get("success") is not True:
        failures.append(f"{key} is not successful")


def _require_quality_success(manifest, key, changed_python_files, failures):
    result = manifest.get(key)
    if not isinstance(result, dict):
        failures.append(f"{key} must be an object")
        return
    if result.get("skipped"):
        if changed_python_files:
            failures.append(f"{key} skipped despite changed Python files")
        if result.get("reason") != "no_changed_python_files":
            failures.append(f"{key} has invalid skip reason")
        if result.get("success") is not True:
            failures.append(f"{key} skipped result must still be successful")
        return
    if result.get("success") is not True:
        failures.append(f"{key} is not successful")
    if not isinstance(result.get("exit_code"), int) or result.get("exit_code") != 0:
        failures.append(f"{key} exit code is not 0")


def validate_manifest_payload(
    manifest,
    expected_issue=None,
    expected_task=None,
    expected_branch=None,
):
    failures = []
    if not isinstance(manifest, dict):
        raise ValueError("Verification manifest must be a JSON object.")
    missing = sorted(REQUIRED_MANIFEST_FIELDS.difference(manifest))
    if missing:
        failures.append(f"missing fields: {', '.join(missing)}")

    for key in ["issue_number", "task_number", "branch", "verification_timestamp"]:
        if key in manifest and not isinstance(manifest.get(key), str):
            failures.append(f"{key} must be a string")
    if expected_issue is not None and manifest.get("issue_number") != str(
        expected_issue
    ):
        failures.append("manifest issue number does not match active state")
    if expected_task is not None and manifest.get("task_number") != str(expected_task):
        failures.append("manifest task number does not match active state")
    if expected_branch is not None and manifest.get("branch") != expected_branch:
        failures.append("manifest branch does not match active state")

    changed_files = manifest.get("changed_files")
    if not isinstance(changed_files, list):
        failures.append("changed_files must be a list")
    else:
        for item in changed_files:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("status"), str)
                or not isinstance(item.get("path"), str)
            ):
                failures.append(
                    "changed_files entries must contain string status and path"
                )
                break
            try:
                validate_repo_relative_path(item["path"])
            except ValueError as e:
                failures.append(str(e))
                break

    changed_python_files = manifest.get("changed_python_files")
    if not isinstance(changed_python_files, list) or not all(
        isinstance(path, str) for path in changed_python_files
    ):
        failures.append("changed_python_files must be a list of strings")
        changed_python_files = []
    else:
        for path in changed_python_files:
            try:
                validate_repo_relative_path(path)
            except ValueError as e:
                failures.append(str(e))
                break

    _require_gate_success(manifest, "scope_gate_result", failures)
    _require_gate_success(manifest, "syntax_gate_result", failures)
    _require_gate_success(manifest, "targeted_validation_result", failures)
    for key in ["black_result", "isort_result", "mypy_result"]:
        _require_quality_success(manifest, key, changed_python_files, failures)

    pytest_exit = manifest.get("full_pytest_exit_code")
    pytest_count = manifest.get("full_pytest_pass_count")
    if not isinstance(pytest_exit, int) or pytest_exit != 0:
        failures.append("full pytest exit code must be integer 0")
    if not isinstance(pytest_count, int):
        failures.append("full pytest pass count must be an integer")
    elif pytest_count < BASELINE_MIN:
        failures.append("full pytest pass count is below baseline")

    fingerprint = manifest.get("verified_working_tree_fingerprint")
    if not isinstance(fingerprint, dict):
        failures.append("verified_working_tree_fingerprint must be an object")
    else:
        if fingerprint.get("algorithm") != "sha256":
            failures.append("fingerprint algorithm must be sha256")
        if fingerprint.get("version") != FINGERPRINT_VERSION:
            failures.append("fingerprint version is invalid")
        if not isinstance(fingerprint.get("value"), str) or not SHA256_RE.fullmatch(
            fingerprint["value"]
        ):
            failures.append("fingerprint digest is invalid")

    alias_fingerprint = manifest.get("verified_worktree_fingerprint")
    if alias_fingerprint != fingerprint:
        failures.append("verified_worktree_fingerprint must match fingerprint object")

    tree_sha = manifest.get("verified_tree_sha")
    if not isinstance(tree_sha, str) or not GIT_SHA_RE.fullmatch(tree_sha):
        failures.append("verified_tree_sha is invalid")

    if manifest.get("overall_verification_result") != "success":
        failures.append("overall verification result is not success")

    if failures:
        raise ValueError("Verification manifest is invalid: " + "; ".join(failures))
    return manifest


def load_verification_manifest(
    run_dir,
    expected_issue=None,
    expected_task=None,
    expected_branch=None,
):
    path = manifest_path(run_dir)
    if not os.path.exists(path):
        raise ValueError(f"Verification manifest is missing: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Verification manifest is invalid JSON: {e}") from e
    return validate_manifest_payload(
        manifest,
        expected_issue=expected_issue,
        expected_task=expected_task,
        expected_branch=expected_branch,
    )


def require_nonempty_log(run_dir, filename):
    path = os.path.join(run_dir, filename)
    run_root = Path(run_dir).resolve()
    resolved = Path(path).resolve()
    if run_root not in resolved.parents and resolved != run_root:
        raise ValueError(f"Required evidence log escapes run directory: {path}")
    if os.path.islink(path):
        raise ValueError(f"Required evidence log is a symlink: {path}")
    if not os.path.exists(path):
        raise ValueError(f"Required evidence log is missing: {path}")
    if os.path.getsize(path) == 0:
        raise ValueError(f"Required evidence log is empty: {path}")
    return path


def validate_current_evidence(state):
    run_dir = state["run_dir"]
    manifest = load_verification_manifest(
        run_dir,
        expected_issue=state["issue_number"],
        expected_task=state["padded_number"],
        expected_branch=state["branch"],
    )
    for filename in [
        "scope_check.txt",
        "targeted_tests.log",
        "quality_checks.log",
        "full_tests.log",
    ]:
        require_nonempty_log(run_dir, filename)
    changed_files = [
        (item["status"], item["path"]) for item in manifest["changed_files"]
    ]
    manifest_changed_files = validate_changed_files(changed_files)
    current_changed_files = validate_changed_files(
        load_scope_guard_module().get_changed_files()
    )
    if current_changed_files != manifest_changed_files:
        raise ValueError(
            "Current changed-file set does not match verified evidence. "
            "Run verify again before creating a PR."
        )
    current_fingerprint = compute_working_tree_fingerprint(
        state["branch"], current_changed_files
    )
    if (
        current_fingerprint["value"]
        != manifest["verified_working_tree_fingerprint"]["value"]
    ):
        raise ValueError(
            "Current working-tree fingerprint does not match verified evidence. "
            "Run verify again before creating a PR."
        )
    return manifest


def parse_commit_message_from_card(card_content):
    section_match = re.search(
        r"(?ms)^## Commit Message\s*\n(.*?)(?=^##\s+|\Z)", card_content
    )
    if not section_match:
        raise ValueError("Task card is missing ## Commit Message section.")
    section = section_match.group(1).strip("\n")

    fenced = re.search(r"(?ms)^```\w*\s*\n(.*?)\n```", section)
    if fenced:
        lines = [line.strip() for line in fenced.group(1).splitlines() if line.strip()]
    else:
        indented = []
        for line in section.splitlines():
            if line.startswith("    ") or line.startswith("\t"):
                indented.append(line.strip())
            elif indented:
                break
        if indented:
            lines = [line for line in indented if line]
        else:
            lines = []
            for line in section.splitlines():
                stripped = line.strip()
                if not stripped or stripped in {"---"}:
                    continue
                if stripped.startswith("```"):
                    continue
                lines.append(stripped)
                break

    if len(lines) != 1:
        raise ValueError(
            "Commit Message section must contain exactly one non-empty title line."
        )
    return lines[0]


def write_json_file(path, data):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=directory, delete=False
        ) as f:
            tmp_path = f.name
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def archive_final_state(run_dir, state):
    path = os.path.join(run_dir, "final_state.json")
    write_json_file(path, state)
    with open(path, "r", encoding="utf-8") as f:
        archived = json.load(f)
    if archived != state:
        raise ValueError("final_state.json readback did not match archived state")
    return path


def archive_abort_state(run_dir, state):
    path = os.path.join(run_dir, "abort_state.json")
    write_json_file(path, state)
    with open(path, "r", encoding="utf-8") as f:
        archived = json.load(f)
    if archived != state:
        raise ValueError("abort_state.json readback did not match archived state")
    return path


def get_pr_info(pr_number):
    res = run_cmd(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,url,state,isDraft,mergeable,mergeStateStatus,headRefOid,mergedAt",
        ],
        check=False,
    )
    if res.returncode != 0:
        fail(f"Cannot read PR #{pr_number}: {res.stderr.strip()}")
    return json.loads(res.stdout)


def get_pr_info_for_branch(branch_name):
    res = run_cmd(
        [
            "gh",
            "pr",
            "view",
            branch_name,
            "--json",
            "number,url,state,isDraft,mergeable,mergeStateStatus,headRefOid,mergedAt",
        ],
        check=False,
    )
    if res.returncode != 0:
        fail(f"Cannot resolve PR for branch {branch_name}: {res.stderr.strip()}")
    return json.loads(res.stdout)


def checks_are_successful(pr_number):
    res = run_cmd(
        [
            "gh",
            "pr",
            "checks",
            str(pr_number),
            "--json",
            ",".join(GH_PR_CHECK_FIELDS),
        ],
        check=False,
    )
    if res.returncode != 0:
        fail(f"Cannot read PR checks for #{pr_number}: {res.stderr.strip()}")
    try:
        checks = json.loads(res.stdout or "[]")
    except json.JSONDecodeError as e:
        fail(f"Cannot parse PR checks JSON for #{pr_number}: {e}")
    if not isinstance(checks, list):
        fail(f"PR checks JSON for #{pr_number} is not a list.")
    failures = []
    if not checks:
        failures.append("no check evidence returned")
    for check in checks:
        if not isinstance(check, dict):
            failures.append("malformed check entry")
            continue
        name = check.get("name", "<unnamed>")
        state = str(check.get("state", "")).upper()
        bucket = str(check.get("bucket", "")).lower()
        if bucket != "pass":
            failures.append(f"{name}: bucket={bucket}")
        elif state and state not in {"COMPLETED", "SUCCESS", "PASS"}:
            failures.append(f"{name}: state={state}")
    return checks, failures


def load_scope_guard_module():
    try:
        return importlib.import_module("scripts.issue_scope_guard")
    except ModuleNotFoundError:
        return importlib.import_module("issue_scope_guard")


# --- MODES ---


def extract_task_id_from_title(title):
    match = re.search(r"\bTASK-(\d+)\b", title, re.IGNORECASE)
    if not match:
        return None
    return f"{int(match.group(1)):03d}"


def extract_metadata(issue_data, allow_no_task=False):
    issue_num = str(issue_data["number"])
    padded_issue_num = f"{int(issue_num):03d}"

    title = issue_data.get("title", "").strip()
    task_id = extract_task_id_from_title(title)

    if not task_id:
        if not allow_no_task:
            print(
                f"[-] ERROR: Issue title '{title}' does not contain a TASK ID (e.g. TASK-040).",
                file=sys.stderr,
            )
            sys.exit(1)
        task_num = int(issue_num)
    else:
        task_num = int(task_id)

    padded_task_num = f"{task_num:03d}"
    task_code = f"TASK-{padded_task_num}"

    # Calculate slug
    # Remove TASK-XXX prefix
    title_clean = re.sub(r"^TASK-\d+\s*:?\s*", "", title, flags=re.IGNORECASE)
    # Strip common leading action words
    title_clean = re.sub(
        r"^(define|create|update|fix|repair|add|remove|delete|build|implement|extend|explain|restore|align|format|restructure|trace)\b\s*",
        "",
        title_clean,
        flags=re.IGNORECASE,
    )
    # Normalize characters to lowercase alphanumeric and hyphens
    slug = title_clean.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        slug = "task"

    card_path = f"docs/tasks/task_{padded_task_num}.md"
    branch_name = f"issue-{padded_issue_num}-task-{padded_task_num}-{slug}"
    run_dir_prefix = (
        f".git/issue-runner-runs/issue-{padded_issue_num}-task-{padded_task_num}-"
    )

    return {
        "issue_number": issue_num,
        "padded_issue_number": padded_issue_num,
        "task_number": str(task_num),
        "padded_task_number": padded_task_num,
        "task_code": task_code,
        "slug": slug,
        "card_path": card_path,
        "branch_name": branch_name,
        "run_dir_prefix": run_dir_prefix,
    }


def mode_plan(issue_num, force=False, allow_no_task=False):
    print(f"[*] Starting plan mode for issue #{issue_num}...")

    # 1. Refuse dirty worktree unless force
    if not is_worktree_clean() and not force:
        print(
            "[-] ERROR: Working tree is dirty. Clean changes or use --force to bypass.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Get issue details via gh
    try:
        res = run_cmd(
            [
                "gh",
                "issue",
                "view",
                str(issue_num),
                "--json",
                "number,title,body,labels",
            ]
        )
        issue_data = json.loads(res.stdout)
    except Exception as e:
        print(
            f"[-] ERROR: Failed to fetch issue details from GitHub: {e}",
            file=sys.stderr,
        )
        print("Please ensure you are logged in using 'gh auth login'.", file=sys.stderr)
        sys.exit(1)

    issue_title = issue_data.get("title", "")
    issue_body = issue_data.get("body", "") or ""
    labels = [l.get("name", "") for l in issue_data.get("labels", [])]

    is_sensitive = any(
        l.lower() in ["security", "ci", "architecture", "hardening"] for l in labels
    )

    # Extract metadata using the new helper
    metadata = extract_metadata(issue_data, allow_no_task=allow_no_task)

    padded_task_num = metadata["padded_task_number"]
    branch_name = metadata["branch_name"]
    card_path = metadata["card_path"]
    run_dir_prefix = metadata["run_dir_prefix"]

    active_state = load_active_run()
    if active_state:
        same_run = (
            active_state.get("issue_number") == str(issue_num)
            and active_state.get("padded_number") == padded_task_num
            and active_state.get("branch") == branch_name
        )
        if not same_run:
            fail(
                "Refusing to overwrite unrelated active run "
                f"for issue #{active_state.get('issue_number')} on branch "
                f"{active_state.get('branch')}. Inspect or abort it first."
            )
        if not force:
            fail(
                "Active run already exists for this issue. Use --force only if you intend to re-plan it."
            )

    # 3. Create run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"{run_dir_prefix}{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    # Save issue.json
    with open(os.path.join(run_dir, "issue.json"), "w", encoding="utf-8") as f:
        json.dump(issue_data, f, indent=2)

    # 4. Checkout/create issue branch
    print(f"[*] Creating or checking out branch: {branch_name}...")
    # Check if branch exists
    res = run_cmd(["git", "branch", "--list", branch_name])
    if res.stdout.strip():
        run_cmd(["git", "checkout", branch_name])
    else:
        run_cmd(["git", "checkout", "-b", branch_name])

    # 5. Create Task Card from template or use existing
    card_existed = os.path.exists(card_path)

    if card_existed and not force:
        print(
            f"[-] ERROR: Task card {card_path} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[*] Generating task card content for {card_path}...")
    if card_existed:
        with open(card_path, "r", encoding="utf-8") as f:
            card_content_before = f.read()
        # Write copy to run_dir
        with open(
            os.path.join(run_dir, "task_card_before.md"), "w", encoding="utf-8"
        ) as f:
            f.write(card_content_before)

    # Generate task card content
    card_content = generate_task_card_content(issue_data, metadata)

    # Validate generated card before writing
    # Placeholder checks
    placeholders = [
        "<Specific, observable criterion",
        "Replace this comment",
        "Section Name",
        "phaseXX",
    ]
    for p in placeholders:
        if p in card_content:
            print(
                f"[-] ERROR: Generated card contains placeholder: '{p}'",
                file=sys.stderr,
            )
            sys.exit(1)

    # Empty sections checks
    def is_section_empty(text, header):
        pattern = re.compile(rf"{re.escape(header)}\s*\n(.*?)(?=\n#|$)", re.DOTALL)
        match = pattern.search(text)
        if not match:
            return True
        content = match.group(1).strip()
        # Strip comments
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
        return len(content) == 0

    if is_section_empty(card_content, "### Files to create"):
        print(
            "[-] ERROR: Generated card has empty ### Files to create section",
            file=sys.stderr,
        )
        sys.exit(1)
    if is_section_empty(card_content, "### Files to modify"):
        print(
            "[-] ERROR: Generated card has empty ### Files to modify section",
            file=sys.stderr,
        )
        sys.exit(1)
    if is_section_empty(card_content, "## Implementation Steps"):
        print(
            "[-] ERROR: Generated card has empty ## Implementation Steps section",
            file=sys.stderr,
        )
        sys.exit(1)

    # Write the task card
    os.makedirs(os.path.dirname(card_path), exist_ok=True)
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card_content)

    # Setup mod_extracted and cre_extracted for allowed files log
    task_num = int(metadata["padded_task_number"])
    if task_num == 40:
        cre_extracted = [
            "docs/platform/platform-content-contracts.md",
            "docs/platform/linkedin-content-contract.md",
            "docs/platform/youtube-shorts-content-contract.md",
            "docs/platform/source-grounding-contract.md",
            "docs/platform/platform-quality-gates.md",
            "docs/phase-12.3-platform-contracts.md",
        ]
        mod_extracted = [
            "docs/project/CURRENT_STATE.md",
            "docs/project/NEXT_ACTION.md",
            "docs/project/PHASES.md",
            "docs/project/ROADMAP.md",
            "docs/project/SPRINT_PLAN.md",
            "docs/project/DECISION_LOG.md",
            "docs/project/BACKLOG.md",
            "WORK_QUEUE.md",
        ]
    else:
        mod_extracted, cre_extracted = extract_files_from_text(issue_body)

    # Create allowed files list
    allowed_files = set(mod_extracted).union(cre_extracted)
    with open(os.path.join(run_dir, "allowed_files.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(allowed_files)))

    # Save active state
    state = {
        "issue_number": str(issue_num),
        "padded_number": padded_task_num,
        "branch": branch_name,
        "run_dir": run_dir,
        "timestamp": timestamp,
        "is_sensitive": is_sensitive,
        "allow_no_task": allow_no_task,
        "status": "planned",
    }
    save_active_run(state)

    print(f"[+] Plan completed successfully! Task card created/used at {card_path}.")
    print(f"[*] State saved to {ACTIVE_RUN_PATH}.")
    return state


def mode_run(engine="agy"):
    print(f"[*] Starting run mode using engine: {engine}...")
    state = require_active_state("run")

    padded_num = state["padded_number"]
    card_path = f"docs/tasks/task_{padded_num}.md"
    run_dir = state["run_dir"]

    if not os.path.exists(card_path):
        print(f"[-] ERROR: Task card {card_path} is missing.", file=sys.stderr)
        sys.exit(1)

    # Load issue.json from run_dir to get issue title
    issue_json_path = os.path.join(run_dir, "issue.json")
    if not os.path.exists(issue_json_path):
        print(
            f"[-] ERROR: issue.json is missing in run directory: {run_dir}",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(issue_json_path, "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    title = issue_data.get("title", "")

    # Refuse to use task_005.md for GitHub issue #5
    if state["issue_number"] == "5" and padded_num == "005":
        print(
            "[-] ERROR: Refusing to use task_005.md for GitHub issue #5 (must map to TASK-040).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Refuse to run if the task card does not match the issue title task ID
    expected_task_id = extract_task_id_from_title(title)
    if expected_task_id:
        if padded_num != expected_task_id:
            print(
                f"[-] ERROR: Task ID mismatch. Active run task ID is {padded_num}, but issue title task ID is {expected_task_id}.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        if not state.get("allow_no_task", False):
            print(
                f"[-] ERROR: Issue title '{title}' does not contain a TASK ID, and allow_no_task was not set.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Read task card
    with open(card_path, "r", encoding="utf-8") as f:
        card_content = f.read()

    # Save copy of task card before run
    with open(os.path.join(run_dir, "task_card_before.md"), "w", encoding="utf-8") as f:
        f.write(card_content)

    # Extract allowed scope
    parse_task_card = load_scope_guard_module().parse_task_card
    modify_files, create_files = parse_task_card(card_path)
    allowed_all = modify_files.union(create_files)

    scope_constraint = (
        f"You are ONLY allowed to modify: {list(modify_files)}. "
        f"You are ONLY allowed to create: {list(create_files)}."
    )

    status_nonce = secrets.token_hex(16)

    # Construct prompt
    prompt = f"""Execute the following task card exactly as written.

{card_content}

---
EXECUTION RULES (non-negotiable):
1. Read the entire task card before touching any file.
2. Scope constraint:
   - {scope_constraint}
   - You must NOT touch any other files.
3. NEVER modify: run-tasks.sh, AGENTS.md, CLAUDE.md, .gitignore, pyproject.toml, uv.lock
4. NEVER modify: WORK_QUEUE.md or any file in docs/tasks/
5. Follow each Implementation Step in order. Do not skip steps.
6. Run every command in the Validation section and confirm it passes.
7. Do NOT run git add, git commit, git push, or any git command.
8. CRITICAL: You MUST NOT run git add, git commit, git push, or any git command under any circumstances.
   The run-tasks.sh script exclusively handles all git operations. If you run a git command,
   the workflow breaks. If a task says to commit, that is handled externally — just make the file changes.
9. If a step fails, stop immediately and report the reason in normal output.
10. Your status nonce is: {status_nonce}
11. At the very end, print exactly one terminal status line on stdout.
    Success line grammar: ISSUE_RUNNER_STATUS, then the status nonce, then COMPLETED.
    Failure line grammar: ISSUE_RUNNER_STATUS, then the status nonce, then FAILED, then a concise reason.
    Do not print any text after the terminal status line.
"""

    print(f"[*] Invoking engine {engine}...")
    agent_log_path = os.path.join(run_dir, "agent_output.log")

    if engine == "agy":
        cmd = ["agy", "--print", "--dangerously-skip-permissions", prompt]
    elif engine == "codex":
        cmd = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", prompt]
    else:
        print(f"[-] ERROR: Unknown engine: {engine}", file=sys.stderr)
        sys.exit(1)

    # Run the engine
    res = run_cmd(cmd, check=False, capture=True)

    # Save agent output log
    with open(agent_log_path, "w", encoding="utf-8") as f:
        f.write(res.stdout)
        if res.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(res.stderr)

    print(f"[*] Engine finished. Exit code: {res.returncode}")

    # Save copy of task card after run
    if os.path.exists(card_path):
        with open(card_path, "r", encoding="utf-8") as f:
            card_content_after = f.read()
        with open(
            os.path.join(run_dir, "task_card_after.md"), "w", encoding="utf-8"
        ) as f:
            f.write(card_content_after)

    completion = analyze_agent_completion(
        res.returncode, res.stdout, res.stderr, expected_nonce=status_nonce
    )
    if not completion["success"]:
        print(
            "[-] ERROR: Agent execution did not satisfy completion contract:",
            file=sys.stderr,
        )
        for reason in completion["failures"]:
            print(f"  - {reason}", file=sys.stderr)
        print("[*] Active run remains in planned state.", file=sys.stderr)
        sys.exit(1)

    state = advance_state(state, "run_completed")
    print(f"[+] Run completed successfully! Agent log saved to {agent_log_path}.")
    return state


def mode_verify():
    print("[*] Starting verification...")
    state = require_active_state("verify")

    padded_num = state["padded_number"]
    card_path = f"docs/tasks/task_{padded_num}.md"
    run_dir = state["run_dir"]
    issue_num = state["issue_number"]
    branch = state["branch"]

    print(f"[*] Starting verification for Issue #{issue_num} (TASK-{padded_num})...")

    gate_failures = []

    # 1. Run scope check
    print("[*] Running scope guard...")
    res_scope = run_cmd(
        ["python3", "scripts/issue_scope_guard.py", card_path], check=False
    )
    scope_out = res_scope.stdout + res_scope.stderr
    scope_log_path = os.path.join(run_dir, "scope_check.txt")
    with open(scope_log_path, "w", encoding="utf-8") as f:
        f.write(scope_out)
    scope_gate_result = {
        "command": ["python3", "scripts/issue_scope_guard.py", card_path],
        "exit_code": res_scope.returncode,
        "stdout": res_scope.stdout,
        "stderr": res_scope.stderr,
        "success": res_scope.returncode == 0,
    }
    if res_scope.returncode != 0:
        gate_failures.append("scope guard failed")

    # Save changed files list
    scope_guard = load_scope_guard_module()
    get_changed_files = scope_guard.get_changed_files
    changed_files = validate_changed_files(get_changed_files())
    changed_file_entries = [
        {"status": status, "path": path} for status, path in sorted(changed_files)
    ]
    changed_python_files = changed_python_paths(changed_files)
    with open(os.path.join(run_dir, "changed_files.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(f"{status} {path}" for status, path in sorted(changed_files)))

    # 2. Syntax check
    print("[*] Running syntax checks...")
    syntax_results = []
    for _, path in changed_files:
        if path.endswith(".sh"):
            print(f"  - Shell check: {path}")
            res_sh = run_cmd(["bash", "-n", path], check=False)
            syntax_results.append(
                {
                    "path": path,
                    "command": ["bash", "-n", path],
                    "exit_code": res_sh.returncode,
                    "stdout": res_sh.stdout,
                    "stderr": res_sh.stderr,
                    "success": res_sh.returncode == 0,
                }
            )
            if res_sh.returncode != 0:
                gate_failures.append(f"syntax error in shell script: {path}")
        elif path.endswith(".py"):
            print(f"  - Python compilation check: {path}")
            res_py = run_cmd(["python3", "-m", "py_compile", path], check=False)
            syntax_results.append(
                {
                    "path": path,
                    "command": ["python3", "-m", "py_compile", path],
                    "exit_code": res_py.returncode,
                    "stdout": res_py.stdout,
                    "stderr": res_py.stderr,
                    "success": res_py.returncode == 0,
                }
            )
            if res_py.returncode != 0:
                gate_failures.append(f"compilation error in Python file: {path}")
    syntax_gate_result = {
        "success": all(result["success"] for result in syntax_results),
        "results": syntax_results,
    }

    # 3. Targeted test commands from validation section
    print("[*] Running targeted validation commands...")
    with open(card_path, "r", encoding="utf-8") as f:
        card_content = f.read()
    validation_blocks = extract_validation_bash_blocks(card_content)
    targeted_results = run_validation_blocks(validation_blocks)
    targeted_log_path = os.path.join(run_dir, "targeted_tests.log")
    if targeted_results:
        write_targeted_validation_log(targeted_log_path, targeted_results)
    else:
        with open(targeted_log_path, "w", encoding="utf-8") as f:
            f.write("No bash validation blocks found in task card.\n")
    targeted_validation_result = {
        "success": bool(targeted_results)
        and all(result["exit_code"] == 0 for result in targeted_results),
        "blocks": targeted_results,
    }
    if not targeted_validation_result["success"]:
        gate_failures.append("targeted validation failed")

    # 4. Local quality checks for changed Python files
    print("[*] Running local quality checks for changed Python files...")
    if changed_python_files:
        quality_results = [
            command_result(
                "black",
                ["uv", "run", "black", "--check", "--"] + changed_python_files,
            ),
            command_result(
                "isort",
                ["uv", "run", "isort", "--check-only", "--"] + changed_python_files,
            ),
            command_result(
                "mypy",
                ["uv", "run", "mypy", "--explicit-package-bases", "--"]
                + changed_python_files,
            ),
        ]
    else:
        quality_results = [
            command_result(
                "black",
                ["uv", "run", "black", "--check"],
                skipped=True,
                reason="no_changed_python_files",
            ),
            command_result(
                "isort",
                ["uv", "run", "isort", "--check-only"],
                skipped=True,
                reason="no_changed_python_files",
            ),
            command_result(
                "mypy",
                ["uv", "run", "mypy"],
                skipped=True,
                reason="no_changed_python_files",
            ),
        ]
    write_quality_log(os.path.join(run_dir, "quality_checks.log"), quality_results)
    black_result = next(
        result for result in quality_results if result["name"] == "black"
    )
    isort_result = next(
        result for result in quality_results if result["name"] == "isort"
    )
    mypy_result = next(result for result in quality_results if result["name"] == "mypy")
    for result in quality_results:
        if not result["success"]:
            gate_failures.append(f"{result['name']} failed")

    # 5. Full pytest suite run
    print("[*] Running full pytest suite...")
    # Set cache dir
    os.environ["UV_CACHE_DIR"] = "/tmp/uv-cache"
    res_pytest = run_cmd(
        ["uv", "run", "python", "-m", "pytest", "--tb=short", "-q"], check=False
    )
    pytest_out = res_pytest.stdout + res_pytest.stderr
    full_tests_path = os.path.join(run_dir, "full_tests.log")
    with open(full_tests_path, "w", encoding="utf-8") as f:
        f.write(pytest_out)
    if not os.path.exists(full_tests_path) or os.path.getsize(full_tests_path) == 0:
        gate_failures.append(
            "full pytest output is empty or full_tests.log was not written"
        )

    passed_count = parse_passed_count(pytest_out)
    print(f"[*] Pytest output summary: {passed_count} passed tests.")
    if res_pytest.returncode != 0:
        gate_failures.append(f"full pytest exited with code {res_pytest.returncode}")
    if passed_count is None:
        gate_failures.append("full pytest pass count could not be parsed")
    elif passed_count < BASELINE_MIN:
        gate_failures.append(
            f"test count decreased below baseline; baseline {BASELINE_MIN}, got {passed_count}"
        )

    try:
        modify_files, create_files = scope_guard.parse_task_card(card_path)
        files_to_commit = files_to_commit_from_scope(
            changed_files, modify_files.union(create_files), card_path
        )
        verified_tree_sha = compute_tree_sha_for_files(files_to_commit)
    except ValueError as e:
        verified_tree_sha = ""
        gate_failures.append(str(e))

    fingerprint = compute_working_tree_fingerprint(branch, changed_files)
    overall_success = not gate_failures
    manifest = {
        "issue_number": issue_num,
        "task_number": padded_num,
        "branch": branch,
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow_state_before_verification": state["status"],
        "changed_files": changed_file_entries,
        "changed_python_files": changed_python_files,
        "scope_gate_result": scope_gate_result,
        "syntax_gate_result": syntax_gate_result,
        "targeted_validation_result": targeted_validation_result,
        "black_result": black_result,
        "isort_result": isort_result,
        "mypy_result": mypy_result,
        "full_pytest_exit_code": res_pytest.returncode,
        "full_pytest_pass_count": passed_count,
        "full_pytest_baseline_min": BASELINE_MIN,
        "overall_verification_result": "success" if overall_success else "failure",
        "gate_failures": gate_failures,
        "verified_working_tree_fingerprint": fingerprint,
        "verified_worktree_fingerprint": fingerprint,
        "verified_tree_sha": verified_tree_sha,
    }
    write_json_file(manifest_path(run_dir), manifest)

    if not overall_success:
        for failure in gate_failures:
            print(f"[-] Verification gate failed: {failure}", file=sys.stderr)
        print("[*] Active run remains in run_completed state.", file=sys.stderr)
        sys.exit(1)

    state = advance_state(state, "verified")
    print(
        f"[+] Verification passed successfully for Issue #{issue_num} (TASK-{padded_num})!"
    )
    return state


def mode_pr():
    print("[*] Creating pull request...")
    state = require_active_state("pr")

    padded_num = state["padded_number"]
    card_path = f"docs/tasks/task_{padded_num}.md"
    run_dir = state["run_dir"]
    issue_num = state["issue_number"]
    branch_name = state["branch"]

    if not os.path.exists(card_path):
        print(f"[-] ERROR: Task card {card_path} is missing.", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = validate_current_evidence(state)
    except ValueError as e:
        fail(str(e))

    # 1. Parse commit message from task card
    with open(card_path, "r", encoding="utf-8") as f:
        card_content = f.read()

    try:
        commit_msg = parse_commit_message_from_card(card_content)
    except ValueError as e:
        fail(str(e))

    # 2. Stage only allowed files + WORK_QUEUE.md + task card
    parse_task_card = load_scope_guard_module().parse_task_card
    modify_files, create_files = parse_task_card(card_path)
    allowed_all = modify_files.union(create_files)

    print("[*] Staging files for commit...")
    # Add files that are allowed and actually changed/created
    get_changed_files = load_scope_guard_module().get_changed_files
    changed_files = validate_changed_files(get_changed_files())

    staged_before = current_staged_files()
    if staged_before:
        fail(
            "Pre-existing staged changes are not allowed before PR creation: "
            + ", ".join(staged_before)
        )

    files_to_add = files_to_commit_from_scope(changed_files, allowed_all, card_path)
    stage_files_for_commit(files_to_add)

    staged_tree_sha = run_cmd(["git", "write-tree"], check=False).stdout.strip()
    if staged_tree_sha != manifest["verified_tree_sha"]:
        fail(
            "Staged tree does not match verified tree. "
            "Run verify again before creating a PR."
        )

    # 3. Commit
    print(f"[*] Committing changes: {commit_msg}")
    res_commit = run_cmd(["git", "commit", "-m", commit_msg])
    with open(os.path.join(run_dir, "commit.txt"), "w", encoding="utf-8") as f:
        f.write(res_commit.stdout + res_commit.stderr)
    committed_head_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
    committed_tree_sha = run_cmd(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
    if committed_tree_sha != manifest["verified_tree_sha"]:
        fail("Committed tree does not match verified tree; active state preserved.")

    # 4. Push branch
    print(f"[*] Pushing branch {branch_name} to origin...")
    run_cmd(["git", "push", "--set-upstream", "origin", branch_name])
    pushed_head_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
    if pushed_head_sha != committed_head_sha:
        fail("Pushed head SHA does not match committed head SHA.")

    # 5. Generate PR Body and Create PR
    print("[*] Generating PR body...")
    res_pr_body = run_cmd(
        ["python3", "scripts/issue_pr_body.py", str(issue_num), run_dir]
    )
    pr_body = res_pr_body.stdout

    pr_title = commit_msg

    print("[*] Creating pull request on GitHub...")
    res_pr_create = run_cmd(
        [
            "gh",
            "pr",
            "create",
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--head",
            branch_name,
            "--base",
            "main",
        ]
    )

    with open(os.path.join(run_dir, "pr.txt"), "w", encoding="utf-8") as f:
        f.write(res_pr_create.stdout + res_pr_create.stderr)

    pr_info = get_pr_info_for_branch(branch_name)
    pr_number = str(pr_info.get("number", "")).strip()
    pr_url = str(pr_info.get("url", "")).strip() or res_pr_create.stdout.strip()
    if not pr_number:
        fail("PR was created but PR number could not be resolved.")
    pr_head_sha = pr_info.get("headRefOid")
    if pr_head_sha and pr_head_sha != pushed_head_sha:
        fail(
            f"Resolved PR head {pr_head_sha} does not match pushed head {pushed_head_sha}."
        )
    if not pr_head_sha:
        fail("PR was created but head SHA could not be resolved.")

    pr_metadata = {
        "commit_sha": committed_head_sha,
        "commit_tree_sha": committed_tree_sha,
        "pushed_head_sha": pushed_head_sha,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_head_sha": pr_head_sha,
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    write_pr_metadata(run_dir, pr_metadata)

    state = advance_state(
        state,
        "pr_created",
        committed_head_sha=committed_head_sha,
        committed_tree_sha=committed_tree_sha,
        pushed_head_sha=pushed_head_sha,
        pr_head_sha=pr_head_sha,
        verified_tree_sha=manifest["verified_tree_sha"],
        pr_number=pr_number,
        pr_url=pr_url,
    )
    print(f"[+] Pull request created successfully: {pr_url}")
    return state


def mode_merge():
    print("[*] Checking merge conditions...")
    state = require_active_state("merge", require_branch=False)

    issue_num = state["issue_number"]
    branch_name = state["branch"]
    is_sensitive = state.get("is_sensitive", False)
    pr_number = state.get("pr_number")
    committed_head_sha = state.get("committed_head_sha")
    pushed_head_sha = state.get("pushed_head_sha")
    pr_head_sha = state.get("pr_head_sha")
    verified_tree_sha = state.get("verified_tree_sha")

    if not pr_number:
        fail("Active state is pr_created but does not record a PR number.")
    if not committed_head_sha:
        fail("Active state is pr_created but does not record committed_head_sha.")
    if not pushed_head_sha:
        fail("Active state is pr_created but does not record pushed_head_sha.")
    if not pr_head_sha:
        fail("Active state is pr_created but does not record pr_head_sha.")
    if not verified_tree_sha:
        fail("Active state is pr_created but does not record verified_tree_sha.")
    if committed_head_sha != pushed_head_sha or pr_head_sha != pushed_head_sha:
        fail("Committed, pushed, and recorded PR head SHA must match.")

    # 1. Refuse if sensitive label found
    if is_sensitive:
        print(
            "[-] ERROR: Auto-merge is blocked for security, CI, architecture, or hardening issues.",
            file=sys.stderr,
        )
        print("Please review and merge the PR manually on GitHub.", file=sys.stderr)
        sys.exit(1)

    # 2. Refuse if working tree is dirty
    if not is_worktree_clean():
        print(
            "[-] ERROR: Working tree is dirty. Clean changes before merging.",
            file=sys.stderr,
        )
        sys.exit(1)

    pr_info = get_pr_info(pr_number)
    if pr_info.get("state") != "OPEN":
        fail(f"PR #{pr_number} is not open; state is {pr_info.get('state')}.")
    if pr_info.get("isDraft"):
        fail(f"PR #{pr_number} is draft.")
    if str(pr_info.get("mergeable", "")).upper() not in {"MERGEABLE", "TRUE"}:
        fail(f"PR #{pr_number} is not mergeable: {pr_info.get('mergeable')}.")
    if str(pr_info.get("mergeStateStatus", "")).upper() != "CLEAN":
        fail(
            f"PR #{pr_number} merge state is not clean: {pr_info.get('mergeStateStatus')}."
        )
    if pr_info.get("headRefOid") != pushed_head_sha:
        fail(
            f"PR head {pr_info.get('headRefOid')} differs from recorded head {pushed_head_sha}."
        )

    checks, check_failures = checks_are_successful(pr_number)
    if not checks:
        fail(f"PR #{pr_number} has no completed check evidence.")
    if check_failures:
        fail("Required PR checks are not all successful: " + "; ".join(check_failures))

    # 3. Merge PR squash pinned to the verified head
    print(f"[*] Merging pull request #{pr_number} for branch {branch_name}...")
    res_merge = run_cmd(
        [
            "gh",
            "pr",
            "merge",
            str(pr_number),
            "--squash",
            "--delete-branch",
            "--match-head-commit",
            pushed_head_sha,
        ],
        check=False,
    )
    if res_merge.returncode != 0:
        fail(f"Merge failed; active state preserved. {res_merge.stderr.strip()}")

    print(f"[+] Merge output:\n{res_merge.stdout}")

    confirmed = get_pr_info(pr_number)
    if confirmed.get("state") != "MERGED":
        fail("GitHub did not confirm merged PR state; active state preserved.")

    # 4. Checkout main and fast-forward to origin/main
    print("[*] Updating local main branch...")
    for cmd in [
        ["git", "checkout", "main"],
        ["git", "fetch", "origin", "main"],
        ["git", "merge", "--ff-only", "origin/main"],
    ]:
        res_sync = run_cmd(cmd, check=False)
        if res_sync.returncode != 0:
            fail(
                "Local synchronization failed after merge; active state preserved. "
                f"Run {' '.join(cmd)} after resolving the problem. {res_sync.stderr.strip()}"
            )

    local_main = run_cmd(["git", "rev-parse", "main"]).stdout.strip()
    origin_main = run_cmd(["git", "rev-parse", "origin/main"]).stdout.strip()
    if local_main != origin_main:
        fail(
            "Local main does not match origin/main after synchronization; "
            "active state preserved."
        )

    merged_state = dict(state)
    merged_state["status"] = "merged"
    merged_state["merged_at"] = datetime.now(timezone.utc).isoformat()
    try:
        archive_final_state(state["run_dir"], merged_state)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        fail(
            "GitHub merge was confirmed and local main is synchronized, but final "
            "state archive failed. Active state is preserved as pr_created. "
            f"Recovery: inspect {state['run_dir']} and rerun merge cleanup after "
            f"writing final_state.json. Details: {e}"
        )
    clear_active_run()
    print("[+] Merge completed and branch cleaned up!")


def mode_inspect(issue_num=None, allow_no_task=False):
    # 1. Show current branch
    try:
        res_branch = run_cmd(["git", "branch", "--show-current"])
        current_branch = res_branch.stdout.strip()
    except Exception:
        current_branch = "unknown"
    print(f"Current Git Branch: {current_branch}")

    # expected base log dir
    log_base_dir = ".git/issue-runner-runs"
    print(f"Run Log Base Directory: {log_base_dir}")

    # Show whether directory exists
    runs_exists = os.path.exists(log_base_dir)
    print(f"Run log base directory exists: {runs_exists}")

    # 3. Show latest run for the issue if any
    latest_run = None
    if runs_exists:
        run_dirs = []
        for d in os.listdir(log_base_dir):
            full_path = os.path.join(log_base_dir, d)
            if os.path.isdir(full_path):
                if issue_num:
                    padded_issue_num = f"{int(issue_num):03d}"
                    if f"issue-{padded_issue_num}-" in d or f"issue-{issue_num}-" in d:
                        run_dirs.append((os.path.getmtime(full_path), full_path))
                else:
                    run_dirs.append((os.path.getmtime(full_path), full_path))
        if run_dirs:
            run_dirs.sort(reverse=True)
            latest_run = run_dirs[0][1]
            print(f"Latest run directory: {latest_run}")
        else:
            print("No run directories found.")
    else:
        print("No run directories found.")

    # 4. If an active run state exists, show its details
    state = load_active_run()
    if state:
        print("\n================ ACTIVE RUN DETAILS ================")
        print(f"Issue Number:  #{state['issue_number']}")
        print(f"Padded Task:   TASK-{state['padded_number']}")
        print(f"Git Branch:    {state['branch']}")
        print(f"Timestamp:     {state['timestamp']}")
        print(f"Run Directory: {state['run_dir']}")
        print(f"Is Sensitive:  {state.get('is_sensitive', False)}")
        print(f"Status:        {state['status'].upper()}")
        print(f"Next Action:   {expected_next_action(state['status'])}")
        branch_matches = current_branch == state["branch"]
        print(f"Branch Match:  {branch_matches}")
        if state.get("pr_number"):
            print(f"PR Number:     {state['pr_number']}")
        if state.get("committed_head_sha"):
            print(f"Committed Head:{state['committed_head_sha']}")
        if state.get("pushed_head_sha"):
            print(f"Pushed Head:   {state['pushed_head_sha']}")
        if state.get("pr_head_sha"):
            print(f"PR Head:       {state['pr_head_sha']}")
        if state.get("verified_tree_sha"):
            print(f"Verified Tree: {state['verified_tree_sha']}")
        print("====================================================")

        # Show warning if stale
        if not branch_matches:
            print(
                f"\n[!] WARNING: active_run.json points to issue branch '{state['branch']}' but current branch is '{current_branch}' (stale run)."
            )

        verification_path = manifest_path(state["run_dir"])
        print(f"Verification manifest exists: {os.path.exists(verification_path)}")
        if os.path.exists(verification_path):
            try:
                manifest = load_verification_manifest(state["run_dir"])
                print("Verification result: success")
                changed_files = [
                    (item["status"], item["path"]) for item in manifest["changed_files"]
                ]
                current_fingerprint = compute_working_tree_fingerprint(
                    state["branch"], changed_files
                )
                fingerprint_matches = (
                    current_fingerprint["value"]
                    == manifest["verified_working_tree_fingerprint"]["value"]
                )
                print(
                    f"Verified fingerprint matches current worktree: {fingerprint_matches}"
                )
                print(
                    "Verified fingerprint: "
                    f"{manifest['verified_working_tree_fingerprint']['value']}"
                )
            except ValueError as e:
                print(f"Verification result: invalid or failed evidence ({e})")

        # Show changed files in git status
        get_changed_files = load_scope_guard_module().get_changed_files
        try:
            changed = get_changed_files()
            if changed:
                print("\nChanged files in worktree:")
                for status, path in sorted(changed):
                    print(f"  {status} {path}")
            else:
                print("\nNo changed files in worktree.")
        except Exception as e:
            print(f"\nFailed to get changed files: {e}")
    else:
        print("\nNo active automation run found in progress.")
    effective_issue_num = issue_num
    if not effective_issue_num and state:
        try:
            effective_issue_num = int(state.get("issue_number"))
        except (ValueError, TypeError):
            pass

    if effective_issue_num:
        print(f"\nExpected / Derived Metadata for Issue #{effective_issue_num}:")
        gh_exists = shutil.which("gh") is not None

        if gh_exists:
            try:
                res = subprocess.run(
                    [
                        "gh",
                        "issue",
                        "view",
                        str(effective_issue_num),
                        "--json",
                        "title,number,labels",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                issue_data = json.loads(res.stdout)
                title = issue_data.get("title", "")
                print(f"Issue Title: {title}")
                meta = extract_metadata(issue_data, allow_no_task=allow_no_task)
                print(f"Derived Task ID: {meta['task_code']}")
                print(f"Derived Task Card Path: {meta['card_path']}")
                if not os.path.exists(meta["card_path"]):
                    print(
                        f"Note: Task card file '{meta['card_path']}' does not exist yet."
                    )
                print(f"Derived Branch Name: {meta['branch_name']}")
                print(f"Derived Run Directory Prefix: {meta['run_dir_prefix']}")
            except Exception as e:
                print(f"Failed to fetch issue details from GitHub via gh: {e}")
        else:
            print(
                "Note: GitHub CLI (gh) is not available or not logged in, cannot fetch issue details."
            )


def mode_abort():
    state = load_active_run()
    if not state:
        print("No active run to abort.")
        return

    branch_name = state["branch"]
    print(f"[*] Aborting active run for issue #{state['issue_number']}...")

    current_branch = get_current_branch()
    if current_branch != branch_name:
        fail(
            f"Refusing abort: current branch '{current_branch}' does not match "
            f"active run branch '{branch_name}'."
        )
    if not is_worktree_clean():
        fail("Refusing abort: working tree is dirty; preserve or remove changes first.")

    res_unmerged = run_cmd(
        ["git", "rev-list", "--count", "origin/main..HEAD"], check=False
    )
    if res_unmerged.returncode != 0:
        fail(
            "Refusing abort: cannot determine whether branch has unmerged commits. "
            f"{res_unmerged.stderr.strip()}"
        )
    try:
        unmerged_count = int(res_unmerged.stdout.strip() or "0")
    except ValueError:
        fail("Refusing abort: unmerged commit count was not parseable.")
    if unmerged_count:
        fail("Refusing abort: branch has unmerged commits relative to origin/main.")

    pr_number = state.get("pr_number")
    if pr_number:
        pr_info = get_pr_info(pr_number)
        if pr_info.get("state") in {"OPEN", "MERGED"}:
            fail(
                f"Refusing abort: PR #{pr_number} is {pr_info.get('state')}. "
                "Use inspect and explicit recovery instead."
            )

    aborted_state = dict(state)
    aborted_state["status"] = "aborted"
    aborted_state["aborted_at"] = datetime.now(timezone.utc).isoformat()
    try:
        archive_abort_state(state["run_dir"], aborted_state)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        fail(f"Refusing abort: could not archive aborted state. {e}")

    res_checkout = run_cmd(["git", "checkout", "main"], check=False)
    if res_checkout.returncode != 0:
        fail(
            "Refusing abort cleanup: could not switch to main; active state preserved. "
            f"{res_checkout.stderr.strip()}"
        )
    res_delete = run_cmd(["git", "branch", "-d", branch_name], check=False)
    if res_delete.returncode != 0:
        fail(
            "Refusing to clear active state: safe branch deletion failed. "
            f"{res_delete.stderr.strip()}"
        )

    clear_active_run()
    print("[+] Active run aborted successfully and state cleared.")


def mode_resume(engine="agy"):
    state = load_active_run()
    if not state:
        print("[-] ERROR: No active run to resume.", file=sys.stderr)
        sys.exit(1)

    status = state["status"]
    print(f"[*] Resuming from status: {status}")

    if status == "planned":
        return mode_run(engine=engine)
    if status == "run_completed":
        return mode_verify()
    if status == "verified":
        return mode_pr()
    if status == "pr_created":
        print("[*] PR is already created. Run 'merge' mode if you wish to auto-merge.")
        return state
    if status == "merged":
        print("[*] Active run is already merged.")
        return state
    fail(f"Cannot resume unknown workflow state: {status}")
    return state


def main():
    parser = argparse.ArgumentParser(description="Issue-Driven Automation Runner")
    parser.add_argument(
        "mode",
        choices=[
            "plan",
            "run",
            "verify",
            "pr",
            "merge",
            "full",
            "inspect",
            "abort",
            "resume",
        ],
        help="Execution mode/step to run",
    )
    parser.add_argument(
        "--issue", type=int, help="GitHub issue number (required for plan/full)"
    )
    parser.add_argument(
        "--engine",
        choices=["agy", "codex"],
        default="agy",
        help="Agent execution engine",
    )
    parser.add_argument(
        "--merge", action="store_true", help="Auto-merge after PR creation in full mode"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore dirty worktree warning in plan mode",
    )
    parser.add_argument(
        "--allow-no-task",
        action="store_true",
        help="Allow proceeding even if issue title doesn't contain TASK-XXX",
    )

    args = parser.parse_args()

    if args.mode == "plan":
        if not args.issue:
            parser.error("--issue is required for plan mode")
        mode_plan(args.issue, force=args.force, allow_no_task=args.allow_no_task)

    elif args.mode == "run":
        mode_run(engine=args.engine)

    elif args.mode == "verify":
        mode_verify()

    elif args.mode == "pr":
        mode_pr()

    elif args.mode == "merge":
        mode_merge()

    elif args.mode == "inspect":
        mode_inspect(issue_num=args.issue, allow_no_task=args.allow_no_task)

    elif args.mode == "abort":
        mode_abort()

    elif args.mode == "resume":
        mode_resume(engine=args.engine)

    elif args.mode == "full":
        if not args.issue:
            parser.error("--issue is required for full mode")
        mode_plan(args.issue, force=args.force, allow_no_task=args.allow_no_task)
        mode_run(engine=args.engine)
        mode_verify()
        mode_pr()
        if args.merge:
            mode_merge()
        else:
            print(
                "[*] Stopping before merge. Use 'merge' command to complete when ready."
            )


if __name__ == "__main__":
    main()
