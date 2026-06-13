#!/usr/bin/env python3
import sys
import os
import json
import argparse
import subprocess
import re
from datetime import datetime

ACTIVE_RUN_PATH = ".runs/active_run.json"
BASELINE_MIN = 1000  # The baseline number of passing tests

def run_cmd(cmd, check=True, capture=True, cwd=None):
    shell = isinstance(cmd, str)
    try:
        res = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture,
            text=True,
            check=check,
            cwd=cwd
        )
        return res
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Command failed: {cmd}\nExit code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}", file=sys.stderr)
            raise
        return e

def is_worktree_clean():
    res = run_cmd(["git", "status", "--porcelain"])
    # Ignore .runs/ directory changes and other temp files
    lines = [line for line in res.stdout.splitlines() if not (
        line[3:].startswith(".runs/") or
        line[3:].startswith(".run-tasks.log") or
        ".pytest_cache" in line or
        ".mypy_cache" in line
    )]
    return len(lines) == 0

def get_current_phase():
    if not os.path.exists("WORK_QUEUE.md"):
        return "Unknown"
    with open("WORK_QUEUE.md", "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'\*\*Current Phase:\*\*\s*(.*)', content)
    if match:
        return match.group(1).strip()
    return "Unknown"

def load_active_run():
    if os.path.exists(ACTIVE_RUN_PATH):
        try:
            with open(ACTIVE_RUN_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_active_run(state):
    os.makedirs(os.path.dirname(ACTIVE_RUN_PATH), exist_ok=True)
    with open(ACTIVE_RUN_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def clear_active_run():
    if os.path.exists(ACTIVE_RUN_PATH):
        try:
            os.remove(ACTIVE_RUN_PATH)
        except Exception:
            pass

def parse_passed_count(pytest_output):
    match = re.search(r'(\d+)\s+passed', pytest_output)
    if match:
        return int(match.group(1))
    return 0

# --- MODES ---

def extract_task_id_from_title(title):
    match = re.search(r'\bTASK-(\d+)\b', title, re.IGNORECASE)
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
            print(f"[-] ERROR: Issue title '{title}' does not contain a TASK ID (e.g. TASK-040).", file=sys.stderr)
            sys.exit(1)
        task_num = int(issue_num)
    else:
        task_num = int(task_id)

    padded_task_num = f"{task_num:03d}"
    task_code = f"TASK-{padded_task_num}"

    # Calculate slug
    # Remove TASK-XXX prefix
    title_clean = re.sub(r'^TASK-\d+\s*:?\s*', '', title, flags=re.IGNORECASE)
    # Strip common leading action words
    title_clean = re.sub(r'^(define|create|update|fix|repair|add|remove|delete|build|implement|extend|explain|restore|align|format|restructure|trace)\b\s*', '', title_clean, flags=re.IGNORECASE)
    # Normalize characters to lowercase alphanumeric and hyphens
    slug = title_clean.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')

    if not slug:
        slug = "task"

    card_path = f"docs/tasks/task_{padded_task_num}.md"
    branch_name = f"issue-{padded_issue_num}-task-{padded_task_num}-{slug}"
    run_dir_prefix = f".runs/issue-{padded_issue_num}-task-{padded_task_num}-"

    return {
        "issue_number": issue_num,
        "padded_issue_number": padded_issue_num,
        "task_number": str(task_num),
        "padded_task_number": padded_task_num,
        "task_code": task_code,
        "slug": slug,
        "card_path": card_path,
        "branch_name": branch_name,
        "run_dir_prefix": run_dir_prefix
    }

def mode_plan(issue_num, force=False, allow_no_task=False):
    print(f"[*] Starting plan mode for issue #{issue_num}...")

    # 1. Refuse dirty worktree unless force
    if not is_worktree_clean() and not force:
        print("[-] ERROR: Working tree is dirty. Clean changes or use --force to bypass.", file=sys.stderr)
        sys.exit(1)

    # 2. Get issue details via gh
    try:
        res = run_cmd(["gh", "issue", "view", str(issue_num), "--json", "number,title,body,labels"])
        issue_data = json.loads(res.stdout)
    except Exception as e:
        print(f"[-] ERROR: Failed to fetch issue details from GitHub: {e}", file=sys.stderr)
        print("Please ensure you are logged in using 'gh auth login'.", file=sys.stderr)
        sys.exit(1)

    issue_title = issue_data.get("title", "")
    issue_body = issue_data.get("body", "") or ""
    labels = [l.get("name", "") for l in issue_data.get("labels", [])]

    is_sensitive = any(l.lower() in ["security", "ci", "architecture", "hardening"] for l in labels)

    # Extract metadata using the new helper
    metadata = extract_metadata(issue_data, allow_no_task=allow_no_task)

    padded_task_num = metadata["padded_task_number"]
    branch_name = metadata["branch_name"]
    card_path = metadata["card_path"]
    run_dir_prefix = metadata["run_dir_prefix"]

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

    if card_existed:
        print(f"[*] Task card {card_path} already exists. Using existing content.")
        with open(card_path, "r", encoding="utf-8") as f:
            card_content = f.read()

        # Write copy to run_dir
        with open(os.path.join(run_dir, "task_card_before.md"), "w", encoding="utf-8") as f:
            f.write(card_content)

        from scripts.issue_scope_guard import parse_task_card
        mod_extracted, cre_extracted = parse_task_card(card_path)
    else:
        print(f"[*] Task card {card_path} does not exist. Creating from template...")
        # Read template
        template_path = "docs/tasks/TASK_TEMPLATE.md"
        if not os.path.exists(template_path):
            # Fallback to minimal template if template is missing
            template_content = f"# TASK-{padded_task_num}: {issue_title}\n\n**Status:** PENDING\n\n## Objective\n{issue_title}\n"
        else:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

        # Substitute values
        curr_phase = get_current_phase()
        today = datetime.now().strftime("%Y-%m-%d")

        # Basic body extraction for scope
        # Let's extract file candidates from the issue body
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

                bullet = re.match(r'^[-*]\s+(.*)', line_s)
                if bullet:
                    file_val = bullet.group(1).strip().strip('`').strip()
                    file_val = re.sub(r'^\[[\sX]*\]\s*', '', file_val).strip()
                    if file_val and not file_val.startswith('#'):
                        if current_section == "modify":
                            mod_files.append(file_val)
                        elif current_section == "create":
                            cre_files.append(file_val)
            return mod_files, cre_files

        mod_extracted, cre_extracted = extract_files_from_text(issue_body)

        # Setup replacements
        replacements = {
            "TASK-NNN": f"TASK-{padded_task_num}",
            "<Short imperative title — max 60 characters>": issue_title[:60],
            "<e.g., 11.9.3>": curr_phase,
            "YYYY-MM-DD": today,
            "CRITICAL | HIGH | MEDIUM | LOW": "HIGH",
            "YES | NO": "YES",
            "ISSUE-NNN": f"ISSUE-{issue_num}",
            "<!-- One sentence only. What does this task achieve and why does it matter? -->": issue_title,
            "type(scope): description (TASK-NNN)": f"feat(issue-{issue_num}): resolve issue #{issue_num} (TASK-{padded_task_num})"
        }

        card_content = template_content
        for k, v in replacements.items():
            card_content = card_content.replace(k, v)

        # Replace the Files to modify and Files to create in the template
        if mod_extracted:
            mod_block = "\n".join(f"- {f}" for f in mod_extracted)
            card_content = re.sub(r'### Files to modify\n.*?(\n### |\n---|$)', f'### Files to modify\n{mod_block}\n\\1', card_content, flags=re.DOTALL)
        if cre_extracted:
            cre_block = "\n".join(f"- {f}" for f in cre_extracted)
            card_content = re.sub(r'### Files to create\n.*?(\n### |\n---|$)', f'### Files to create\n{cre_block}\n\\1', card_content, flags=re.DOTALL)

        # Write the task card
        os.makedirs(os.path.dirname(card_path), exist_ok=True)
        with open(card_path, "w", encoding="utf-8") as f:
            f.write(card_content)

        # Note: we do NOT write task_card_before.md if it did not exist before plan mode (per requirement 2)

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
        "status": "planned"
    }
    save_active_run(state)

    print(f"[+] Plan completed successfully! Task card created/used at {card_path}.")
    print(f"[*] State saved to {ACTIVE_RUN_PATH}.")
    return state

def mode_run(engine="agy"):
    print(f"[*] Starting run mode using engine: {engine}...")
    state = load_active_run()
    if not state:
        print("[-] ERROR: No active run state found. Run 'plan' mode first.", file=sys.stderr)
        sys.exit(1)

    padded_num = state["padded_number"]
    card_path = f"docs/tasks/task_{padded_num}.md"
    run_dir = state["run_dir"]

    if not os.path.exists(card_path):
        print(f"[-] ERROR: Task card {card_path} is missing.", file=sys.stderr)
        sys.exit(1)

    # Load issue.json from run_dir to get issue title
    issue_json_path = os.path.join(run_dir, "issue.json")
    if not os.path.exists(issue_json_path):
        print(f"[-] ERROR: issue.json is missing in run directory: {run_dir}", file=sys.stderr)
        sys.exit(1)
    with open(issue_json_path, "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    title = issue_data.get("title", "")

    # Refuse to use task_005.md for GitHub issue #5
    if state["issue_number"] == "5" and padded_num == "005":
        print("[-] ERROR: Refusing to use task_005.md for GitHub issue #5 (must map to TASK-040).", file=sys.stderr)
        sys.exit(1)

    # Refuse to run if the task card does not match the issue title task ID
    expected_task_id = extract_task_id_from_title(title)
    if expected_task_id:
        if padded_num != expected_task_id:
            print(f"[-] ERROR: Task ID mismatch. Active run task ID is {padded_num}, but issue title task ID is {expected_task_id}.", file=sys.stderr)
            sys.exit(1)
    else:
        if not state.get("allow_no_task", False):
            print(f"[-] ERROR: Issue title '{title}' does not contain a TASK ID, and allow_no_task was not set.", file=sys.stderr)
            sys.exit(1)

    # Read task card
    with open(card_path, "r", encoding="utf-8") as f:
        card_content = f.read()

    # Save copy of task card before run
    with open(os.path.join(run_dir, "task_card_before.md"), "w", encoding="utf-8") as f:
        f.write(card_content)

    # Extract allowed scope
    from scripts.issue_scope_guard import parse_task_card
    modify_files, create_files = parse_task_card(card_path)
    allowed_all = modify_files.union(create_files)

    scope_constraint = (
        f"You are ONLY allowed to modify: {list(modify_files)}. "
        f"You are ONLY allowed to create: {list(create_files)}."
    )

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
9. If a step fails, stop and print: TASK_FAILED: <reason>
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
        with open(os.path.join(run_dir, "task_card_after.md"), "w", encoding="utf-8") as f:
            f.write(card_content_after)

    if "TASK_FAILED:" in res.stdout:
        print("[-] ERROR: Agent reported task failure.", file=sys.stderr)
        sys.exit(1)

    state["status"] = "run_completed"
    save_active_run(state)
    print(f"[+] Run completed successfully! Agent log saved to {agent_log_path}.")
    return state

def mode_verify():
    print("[*] Starting verification...")
    state = load_active_run()
    if not state:
        print("[-] ERROR: No active run state found. Run 'plan' & 'run' modes first.", file=sys.stderr)
        sys.exit(1)

    padded_num = state["padded_number"]
    card_path = f"docs/tasks/task_{padded_num}.md"
    run_dir = state["run_dir"]
    issue_num = state["issue_number"]

    print(f"[*] Starting verification for Issue #{issue_num} (TASK-{padded_num})...")

    # 1. Run scope check
    print("[*] Running scope guard...")
    try:
        res_scope = run_cmd(["python3", "scripts/issue_scope_guard.py", card_path], check=False)
        scope_out = res_scope.stdout + res_scope.stderr
        with open(os.path.join(run_dir, "scope_check.txt"), "w", encoding="utf-8") as f:
            f.write(scope_out)
        if res_scope.returncode != 0:
            print("[-] ERROR: Scope check failed! Violations written to scope_check.txt.", file=sys.stderr)
            print(scope_out, file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[-] ERROR: Failed to run scope guard: {e}", file=sys.stderr)
        sys.exit(1)

    # Save changed files list
    from scripts.issue_scope_guard import get_changed_files, parse_task_card
    changed_files = get_changed_files()
    with open(os.path.join(run_dir, "changed_files.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(f"{status} {path}" for status, path in sorted(changed_files)))

    # 2. Syntax check
    print("[*] Running syntax checks...")
    for _, path in changed_files:
        if path.endswith(".sh"):
            print(f"  - Shell check: {path}")
            res_sh = run_cmd(["bash", "-n", path], check=False)
            if res_sh.returncode != 0:
                print(f"[-] ERROR: Syntax error in shell script: {path}", file=sys.stderr)
                sys.exit(1)
        elif path.endswith(".py"):
            print(f"  - Python compilation check: {path}")
            res_py = run_cmd(["python3", "-m", "py_compile", path], check=False)
            if res_py.returncode != 0:
                print(f"[-] ERROR: Compilation error in Python file: {path}", file=sys.stderr)
                sys.exit(1)

    # 3. Targeted test commands from validation section
    print("[*] Running targeted validation commands...")
    targeted_log = []
    if os.path.exists(card_path):
        with open(card_path, "r", encoding="utf-8") as f:
            card_content = f.read()
        # Find validation block
        validation_match = re.search(r'## Validation.*?\n(.*?)(?:\n## |---|$)', card_content, re.DOTALL)
        if validation_match:
            code_blocks = re.findall(r'```bash\s*\n(.*?)\n```', validation_match.group(1), re.DOTALL)
            for block in code_blocks:
                for line in block.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and "pytest" not in line:
                        print(f"  - Executing command: {line}")
                        res_val = run_cmd(line, check=False)
                        targeted_log.append(f"Command: {line}\nExit Code: {res_val.returncode}\nOutput:\n{res_val.stdout}\n{res_val.stderr}\n")
                        if res_val.returncode != 0:
                            print(f"[-] WARNING: Validation command failed: {line}", file=sys.stderr)

    with open(os.path.join(run_dir, "targeted_tests.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(targeted_log))

    # 4. Full pytest suite run
    print("[*] Running full pytest suite...")
    # Set cache dir
    os.environ["UV_CACHE_DIR"] = "/tmp/uv-cache"
    res_pytest = run_cmd(["uv", "run", "python", "-m", "pytest", "--tb=short", "-q"], check=False)
    pytest_out = res_pytest.stdout + res_pytest.stderr
    with open(os.path.join(run_dir, "full_tests.log"), "w", encoding="utf-8") as f:
        f.write(pytest_out)

    passed_count = parse_passed_count(pytest_out)
    print(f"[*] Pytest output summary: {passed_count} passed tests.")
    if passed_count < BASELINE_MIN:
        print(f"[-] ERROR: Test count decreased below baseline! Baseline: {BASELINE_MIN}, Got: {passed_count}", file=sys.stderr)
        sys.exit(1)

    state["status"] = "verified"
    save_active_run(state)
    print(f"[+] Verification passed successfully for Issue #{issue_num} (TASK-{padded_num})!")
    return state

def mode_pr():
    print("[*] Creating pull request...")
    state = load_active_run()
    if not state:
        print("[-] ERROR: No active run state found. Run 'plan', 'run', & 'verify' first.", file=sys.stderr)
        sys.exit(1)

    padded_num = state["padded_number"]
    card_path = f"docs/tasks/task_{padded_num}.md"
    run_dir = state["run_dir"]
    issue_num = state["issue_number"]
    branch_name = state["branch"]

    if not os.path.exists(card_path):
        print(f"[-] ERROR: Task card {card_path} is missing.", file=sys.stderr)
        sys.exit(1)

    # 1. Parse commit message from task card
    with open(card_path, "r", encoding="utf-8") as f:
        card_content = f.read()

    commit_match = re.search(r'## Commit Message.*?\n```\s*\n(.*?)\n```', card_content, re.DOTALL)
    if commit_match:
        commit_msg = commit_match.group(1).strip()
    else:
        commit_msg = f"feat(issue-{issue_num}): resolve issue #{issue_num} (TASK-{padded_num})"

    # 2. Stage only allowed files + WORK_QUEUE.md + task card
    from scripts.issue_scope_guard import parse_task_card
    modify_files, create_files = parse_task_card(card_path)
    allowed_all = modify_files.union(create_files)

    print("[*] Staging files for commit...")
    # Add files that are allowed and actually changed/created
    from scripts.issue_scope_guard import get_changed_files
    changed_files = get_changed_files()

    files_to_add = []
    for _, path in changed_files:
        if path in allowed_all or path == "WORK_QUEUE.md" or path == card_path:
            files_to_add.append(path)

    if not files_to_add:
        print("[-] No changes to commit.", file=sys.stderr)
    else:
        run_cmd(["git", "add"] + files_to_add)

    # 3. Commit
    print(f"[*] Committing changes: {commit_msg}")
    res_commit = run_cmd(["git", "commit", "-m", commit_msg])
    with open(os.path.join(run_dir, "commit.txt"), "w", encoding="utf-8") as f:
        f.write(res_commit.stdout + res_commit.stderr)

    # 4. Push branch
    print(f"[*] Pushing branch {branch_name} to origin...")
    run_cmd(["git", "push", "--set-upstream", "origin", branch_name])

    # 5. Generate PR Body and Create PR
    print("[*] Generating PR body...")
    res_pr_body = run_cmd(["python3", "scripts/issue_pr_body.py", str(issue_num), run_dir])
    pr_body = res_pr_body.stdout

    # Fetch issue details for title
    with open(os.path.join(run_dir, "issue.json"), "r", encoding="utf-8") as f:
        issue_data = json.load(f)
    issue_title = issue_data.get("title", f"Resolve issue #{issue_num}")

    pr_title = f"Resolve issue #{issue_num}: {issue_title}"

    print("[*] Creating pull request on GitHub...")
    res_pr_create = run_cmd([
        "gh", "pr", "create",
        "--title", pr_title,
        "--body", pr_body,
        "--head", branch_name,
        "--base", "main"
    ])

    with open(os.path.join(run_dir, "pr.txt"), "w", encoding="utf-8") as f:
        f.write(res_pr_create.stdout + res_pr_create.stderr)

    state["status"] = "pr_created"
    save_active_run(state)
    print(f"[+] Pull request created successfully: {res_pr_create.stdout.strip()}")
    return state

def mode_merge():
    print("[*] Checking merge conditions...")
    state = load_active_run()
    if not state:
        print("[-] ERROR: No active run state found.", file=sys.stderr)
        sys.exit(1)

    issue_num = state["issue_number"]
    branch_name = state["branch"]
    is_sensitive = state.get("is_sensitive", False)

    # 1. Refuse if sensitive label found
    if is_sensitive:
        print("[-] ERROR: Auto-merge is blocked for security, CI, architecture, or hardening issues.", file=sys.stderr)
        print("Please review and merge the PR manually on GitHub.", file=sys.stderr)
        sys.exit(1)

    # 2. Refuse if working tree is dirty
    if not is_worktree_clean():
        print("[-] ERROR: Working tree is dirty. Clean changes before merging.", file=sys.stderr)
        sys.exit(1)

    # 3. Merge PR squash
    print(f"[*] Merging pull request for branch {branch_name}...")
    res_merge = run_cmd(["gh", "pr", "merge", "--squash", "--delete-branch", "--auto"], check=False)
    if res_merge.returncode != 0:
        # Fallback to non-auto merge
        res_merge = run_cmd(["gh", "pr", "merge", "--squash", "--delete-branch"])

    print(f"[+] Merge output:\n{res_merge.stdout}")

    # 4. Checkout main and pull
    print("[*] Updating local main branch...")
    run_cmd(["git", "checkout", "main"])
    run_cmd(["git", "pull", "origin", "main"])

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

    # 2. Show whether .runs exists
    runs_exists = os.path.exists(".runs")
    print(f".runs/ directory exists: {runs_exists}")

    # 3. Show latest run for the issue if any
    latest_run = None
    if runs_exists:
        run_dirs = []
        for d in os.listdir(".runs"):
            full_path = os.path.join(".runs", d)
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
        print("====================================================")

        # Show changed files in git status
        from scripts.issue_scope_guard import get_changed_files
        changed = get_changed_files()
        if changed:
            print("\nChanged files in worktree:")
            for status, path in sorted(changed):
                print(f"  {status} {path}")
        else:
            print("\nNo changed files in worktree.")
    else:
        print("\nNo active automation run found in progress.")

    # 5. if --issue is provided and gh exists, show issue title and derived task ID
    if issue_num:
        gh_exists = False
        try:
            res_gh = subprocess.run(["command", "-v", "gh"], shell=True, capture_output=True)
            gh_exists = (res_gh.returncode == 0)
        except Exception:
            pass

        if gh_exists:
            print(f"\nFetching details for GitHub Issue #{issue_num}...")
            try:
                res = subprocess.run(
                    ["gh", "issue", "view", str(issue_num), "--json", "title,number"],
                    capture_output=True, text=True, check=True
                )
                issue_data = json.loads(res.stdout)
                title = issue_data.get("title", "")
                print(f"Issue Title: {title}")
                try:
                    meta = extract_metadata(issue_data, allow_no_task=allow_no_task)
                    print(f"Derived Task ID: {meta['task_code']}")
                    print(f"Derived Task Card Path: {meta['card_path']}")
                    print(f"Derived Branch Name: {meta['branch_name']}")
                    print(f"Derived Run Directory Prefix: {meta['run_dir_prefix']}")
                except SystemExit:
                    print("Failed to derive task ID (no TASK-XXX in title and --allow-no-task not set).")
            except Exception as e:
                print(f"Failed to fetch issue details from GitHub via gh: {e}")

def mode_abort():
    state = load_active_run()
    if not state:
        print("No active run to abort.")
        return

    branch_name = state["branch"]
    print(f"[*] Aborting active run for issue #{state['issue_number']}...")

    # Checkout main
    run_cmd(["git", "checkout", "main"])

    # Delete branch locally
    run_cmd(["git", "branch", "-D", branch_name], check=False)

    # Clear active run state
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
        state = mode_run(engine=engine)
        status = state["status"]

    if status == "run_completed":
        state = mode_verify()
        status = state["status"]

    if status == "verified":
        state = mode_pr()
        status = state["status"]

    if status == "pr_created":
        print("[*] PR is already created. Run 'merge' mode if you wish to auto-merge.")

    return state

def main():
    parser = argparse.ArgumentParser(description="Issue-Driven Automation Runner")
    parser.add_argument("mode", choices=["plan", "run", "verify", "pr", "merge", "full", "inspect", "abort", "resume"],
                        help="Execution mode/step to run")
    parser.add_argument("--issue", type=int, help="GitHub issue number (required for plan/full)")
    parser.add_argument("--engine", choices=["agy", "codex"], default="agy", help="Agent execution engine")
    parser.add_argument("--merge", action="store_true", help="Auto-merge after PR creation in full mode")
    parser.add_argument("--force", action="store_true", help="Ignore dirty worktree warning in plan mode")
    parser.add_argument("--allow-no-task", action="store_true", help="Allow proceeding even if issue title doesn't contain TASK-XXX")

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
            print("[*] Stopping before merge. Use 'merge' command to complete when ready.")

if __name__ == "__main__":
    main()
