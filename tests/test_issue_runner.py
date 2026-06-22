import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest

pr_body = importlib.import_module("scripts.issue_pr_body")
runner = importlib.import_module("scripts.issue_runner")
scope_guard = importlib.import_module("scripts.issue_scope_guard")
NONCE = "abcd1234"
VALID_DIGEST = "a" * 64
VALID_TREE = "b" * 40
VALID_COMMIT = "c" * 40


def cp(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


@pytest.fixture
def runner_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git" / "issue-runner-runs").mkdir(parents=True)
    (tmp_path / "docs" / "tasks").mkdir(parents=True)
    monkeypatch.setattr(
        runner,
        "ACTIVE_RUN_PATH",
        str(tmp_path / ".git" / "issue-runner-runs" / "active_run.json"),
    )
    return tmp_path


def write_state(tmp_path, status="planned", branch="issue-058-task-093-x", **extra):
    run_dir = tmp_path / ".git" / "issue-runner-runs" / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "issue_number": "58",
        "padded_number": "093",
        "branch": branch,
        "run_dir": str(run_dir),
        "timestamp": "20260622_000000",
        "status": status,
    }
    state.update(extra)
    runner.save_active_run(state)
    return state, run_dir


def write_task_card(tmp_path, commit_message="fix(tooling): harden runner (TASK-093)"):
    card = tmp_path / "docs" / "tasks" / "task_093.md"
    card.write_text(
        f"""# TASK-093

## Files to create
- tests/test_issue_runner.py

## Files to modify
- scripts/issue_runner.py
- scripts/issue_pr_body.py
- docs/project/ISSUE_RUNNER_STANDARD.md
- docs/tasks/task_093.md
- WORK_QUEUE.md

## Validation

```bash
pytest tests/test_issue_runner.py -q
```

## Commit Message

```
{commit_message}
```
""",
        encoding="utf-8",
    )
    return card


def write_issue(run_dir):
    (run_dir / "issue.json").write_text(
        json.dumps({"title": "TASK-093: harden runner", "number": 58}),
        encoding="utf-8",
    )


def fake_branch_run_cmd(branch="issue-058-task-093-x"):
    def _run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd == ["git", "branch", "--show-current"]:
            return cp(stdout=f"{branch}\n")
        return cp()

    return _run_cmd


def test_agent_nonzero_exit_fails():
    result = runner.analyze_agent_completion(
        1, f"{runner.STATUS_PREFIX} {NONCE} COMPLETED\n", "", NONCE
    )
    assert not result["success"]
    assert "agent engine exited with code 1" in result["failures"]


def test_agent_task_failed_output_fails():
    result = runner.analyze_agent_completion(
        0, f"{runner.STATUS_PREFIX} {NONCE} FAILED bad\n", "", NONCE
    )
    assert not result["success"]
    assert any("agent reported failure" in failure for failure in result["failures"])


def test_agent_missing_completion_fails():
    result = runner.analyze_agent_completion(0, "done\n", "", NONCE)
    assert not result["success"]
    assert (
        "agent did not emit ISSUE_RUNNER_STATUS terminal status" in result["failures"]
    )


def test_agent_conflicting_statuses_fail():
    result = runner.analyze_agent_completion(
        0,
        f"{runner.STATUS_PREFIX} {NONCE} COMPLETED\n"
        f"{runner.STATUS_PREFIX} {NONCE} FAILED bad\n",
        "",
        NONCE,
    )
    assert not result["success"]
    assert "agent emitted multiple terminal statuses" in result["failures"]


def test_agent_success_requires_explicit_completion():
    result = runner.analyze_agent_completion(
        0, f"work\n{runner.STATUS_PREFIX} {NONCE} COMPLETED\n", "", NONCE
    )
    assert result["success"]


def test_agent_echoed_old_prompt_marker_does_not_complete():
    result = runner.analyze_agent_completion(
        0, "The prompt says:\nTASK_COMPLETED\n", "", NONCE
    )
    assert not result["success"]


def test_agent_wrong_nonce_fails():
    result = runner.analyze_agent_completion(
        0, f"{runner.STATUS_PREFIX} deadbeef COMPLETED\n", "", NONCE
    )
    assert not result["success"]
    assert "agent terminal status nonce did not match" in result["failures"]


def test_agent_status_followed_by_text_fails():
    result = runner.analyze_agent_completion(
        0, f"{runner.STATUS_PREFIX} {NONCE} COMPLETED\nextra\n", "", NONCE
    )
    assert not result["success"]
    assert "agent terminal status was not the final stdout line" in result["failures"]


def test_agent_status_on_stderr_fails():
    result = runner.analyze_agent_completion(
        0, "", f"{runner.STATUS_PREFIX} {NONCE} COMPLETED\n", NONCE
    )
    assert not result["success"]
    assert "agent emitted terminal status on stderr" in result["failures"]


def test_agent_log_preserved_on_failure(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "planned")
    write_task_card(runner_workspace)
    write_issue(run_dir)

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd == ["git", "branch", "--show-current"]:
            return cp(stdout=f"{state['branch']}\n")
        if cmd and cmd[0] == "agy":
            return cp(stdout="partial output\n", stderr="engine failed\n", returncode=1)
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    with pytest.raises(SystemExit):
        runner.mode_run("agy")

    assert "partial output" in (run_dir / "agent_output.log").read_text(
        encoding="utf-8"
    )
    assert runner.load_active_run()["status"] == "planned"


@pytest.mark.parametrize(
    "mode,status",
    [
        ("run", "verified"),
        ("verify", "planned"),
        ("pr", "run_completed"),
        ("merge", "verified"),
    ],
)
def test_modes_reject_wrong_state(runner_workspace, monkeypatch, mode, status):
    write_state(runner_workspace, status)
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd())

    with pytest.raises(SystemExit):
        runner.require_active_state(mode, require_branch=mode != "merge")


def test_wrong_active_branch_blocks_mode(runner_workspace, monkeypatch):
    write_state(runner_workspace, "run_completed", branch="expected")
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd(branch="actual"))

    with pytest.raises(SystemExit):
        runner.require_active_state("verify")


def test_unrelated_active_run_blocks_planning(runner_workspace, monkeypatch):
    write_state(
        runner_workspace,
        "planned",
        branch="other",
        issue_number="99",
        padded_number="099",
    )
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd[:3] == ["gh", "issue", "view"]:
            return cp(
                stdout=json.dumps(
                    {
                        "number": 58,
                        "title": "TASK-093: harden runner",
                        "body": "Files to modify\n- scripts/issue_runner.py",
                        "labels": [],
                    }
                )
            )
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    with pytest.raises(SystemExit):
        runner.mode_plan(58)


def test_save_active_run_uses_atomic_replace(runner_workspace, monkeypatch):
    calls = []
    real_replace = os.replace

    def tracking_replace(src, dst):
        calls.append((src, dst))
        real_replace(src, dst)

    monkeypatch.setattr(runner.os, "replace", tracking_replace)
    write_state(runner_workspace, "planned")

    assert calls
    assert calls[-1][1] == runner.ACTIVE_RUN_PATH


def test_corrupted_state_file_fails(runner_workspace):
    Path(runner.ACTIVE_RUN_PATH).write_text("{bad json", encoding="utf-8")
    with pytest.raises(SystemExit):
        runner.load_active_run()


def test_resume_executes_only_next_transition(runner_workspace, monkeypatch):
    write_state(runner_workspace, "planned")
    called = []

    def fake_run(engine="agy"):
        called.append("run")
        return {"status": "run_completed"}

    monkeypatch.setattr(runner, "mode_run", fake_run)
    monkeypatch.setattr(runner, "mode_verify", lambda: called.append("verify"))

    runner.mode_resume()

    assert called == ["run"]


def test_validation_extracts_multiline_and_continuation():
    card = """## Validation

```bash
VALUE=one
printf '%s' "$VALUE" \\
  | cat
```

## Next
"""
    blocks = runner.extract_validation_bash_blocks(card)
    assert blocks == ["VALUE=one\nprintf '%s' \"$VALUE\" \\\n  | cat"]


def test_validation_uses_bash_pipefail(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output=True, text=True, check=False):
        calls.append(cmd)
        return cp(returncode=1)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    results = runner.run_validation_blocks(["false | true"])

    assert calls == [["bash", "-e", "-u", "-o", "pipefail", "-c", "false | true"]]
    assert results[0]["exit_code"] == 1


def test_targeted_pytest_command_is_preserved():
    blocks = runner.extract_validation_bash_blocks(
        "## Validation\n\n```bash\nuv run python -m pytest tests/test_issue_runner.py -q\n```"
    )
    assert "pytest" in blocks[0]


def test_validation_sequential_failure_stops_block():
    results = runner.run_validation_blocks(["false\necho later"])
    assert results[0]["exit_code"] != 0
    assert "later" not in results[0]["stdout"]


def test_validation_successful_sequential_commands_pass():
    results = runner.run_validation_blocks(["echo first\necho second"])
    assert results[0]["exit_code"] == 0
    assert "second" in results[0]["stdout"]


def test_validation_multiple_blocks_stop_at_first_failure():
    results = runner.run_validation_blocks(["false", "echo should-not-run"])
    assert len(results) == 1
    assert results[0]["exit_code"] != 0


def test_validation_ignores_bash_blocks_outside_validation():
    card = "```bash\necho outside\n```\n\n## Validation\n\nNo commands.\n"
    assert runner.extract_validation_bash_blocks(card) == []


def configure_verify(
    monkeypatch, branch, changed_files, command_results, validation_results=None
):
    validation_results = validation_results or [
        {
            "block_index": 1,
            "command": "true",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        }
    ]
    monkeypatch.setattr(scope_guard, "get_changed_files", lambda: set(changed_files))
    monkeypatch.setattr(
        scope_guard, "parse_task_card", lambda card_path: (set(), set())
    )
    monkeypatch.setattr(
        runner, "run_validation_blocks", lambda blocks: validation_results
    )
    monkeypatch.setattr(runner, "compute_tree_sha_for_files", lambda files: VALID_TREE)

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        key = tuple(cmd) if isinstance(cmd, list) else cmd
        if cmd == ["git", "branch", "--show-current"]:
            return cp(stdout=f"{branch}\n")
        if cmd[:3] == ["python3", "scripts/issue_scope_guard.py"]:
            return command_results.get("scope", cp(stdout="scope ok\n"))
        if cmd[:3] == ["python3", "-m", "py_compile"]:
            return command_results.get("py_compile", cp())
        if isinstance(key, tuple) and key[:3] == ("uv", "run", "black"):
            return command_results.get("black", cp())
        if isinstance(key, tuple) and key[:3] == ("uv", "run", "isort"):
            return command_results.get("isort", cp())
        if isinstance(key, tuple) and key[:3] == ("uv", "run", "mypy"):
            return command_results.get("mypy", cp())
        if cmd == ["uv", "run", "python", "-m", "pytest", "--tb=short", "-q"]:
            return command_results.get("pytest", cp(stdout="1032 passed\n"))
        if cmd[:2] == ["git", "diff"]:
            return cp(stdout="")
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)


def test_failed_targeted_block_fails_verification(runner_workspace, monkeypatch):
    state, _ = write_state(runner_workspace, "run_completed")
    write_task_card(runner_workspace)
    configure_verify(
        monkeypatch,
        state["branch"],
        {("M", "scripts/issue_runner.py")},
        {},
        [
            {
                "block_index": 1,
                "command": "false",
                "exit_code": 1,
                "stdout": "",
                "stderr": "",
            }
        ],
    )

    with pytest.raises(SystemExit):
        runner.mode_verify()

    assert runner.load_active_run()["status"] == "run_completed"


@pytest.mark.parametrize("tool", ["black", "isort", "mypy"])
def test_quality_gate_failures_block_verification(runner_workspace, monkeypatch, tool):
    state, _ = write_state(runner_workspace, "run_completed")
    write_task_card(runner_workspace)
    configure_verify(
        monkeypatch,
        state["branch"],
        {("M", "scripts/issue_runner.py")},
        {tool: cp(stderr="bad\n", returncode=1)},
    )

    with pytest.raises(SystemExit):
        runner.mode_verify()


def test_no_changed_python_skips_quality_gates(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "run_completed")
    write_task_card(runner_workspace)
    configure_verify(monkeypatch, state["branch"], {("M", "WORK_QUEUE.md")}, {})

    runner.mode_verify()

    manifest = json.loads((run_dir / "verification.json").read_text(encoding="utf-8"))
    assert manifest["black_result"]["skipped"]
    assert manifest["isort_result"]["skipped"]
    assert manifest["mypy_result"]["skipped"]
    assert runner.load_active_run()["status"] == "verified"


def test_pytest_zero_with_valid_count_succeeds(runner_workspace, monkeypatch):
    state, _ = write_state(runner_workspace, "run_completed")
    write_task_card(runner_workspace)
    configure_verify(
        monkeypatch,
        state["branch"],
        {("M", "WORK_QUEUE.md")},
        {"pytest": cp(stdout="1000 passed\n")},
    )

    runner.mode_verify()
    assert runner.load_active_run()["status"] == "verified"


@pytest.mark.parametrize(
    "pytest_result",
    [
        cp(stdout="1032 passed\n", returncode=1),
        cp(stdout="999 passed\n", returncode=0),
        cp(stdout="", returncode=0),
    ],
)
def test_full_pytest_failures_block_verification(
    runner_workspace, monkeypatch, pytest_result
):
    state, _ = write_state(runner_workspace, "run_completed")
    write_task_card(runner_workspace)
    configure_verify(
        monkeypatch,
        state["branch"],
        {("M", "WORK_QUEUE.md")},
        {"pytest": pytest_result},
    )

    with pytest.raises(SystemExit):
        runner.mode_verify()


def test_manifest_contains_required_fields(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "run_completed")
    write_task_card(runner_workspace)
    configure_verify(monkeypatch, state["branch"], {("M", "WORK_QUEUE.md")}, {})

    runner.mode_verify()

    manifest = json.loads((run_dir / "verification.json").read_text(encoding="utf-8"))
    assert runner.REQUIRED_MANIFEST_FIELDS.issubset(manifest)


def test_fingerprint_is_deterministic_and_changes(runner_workspace, monkeypatch):
    Path("changed.txt").write_text("one", encoding="utf-8")
    monkeypatch.setattr(
        runner, "run_cmd", lambda cmd, check=True, capture=True, cwd=None: cp()
    )
    first = runner.compute_working_tree_fingerprint("branch", {("??", "changed.txt")})
    second = runner.compute_working_tree_fingerprint("branch", {("??", "changed.txt")})
    Path("changed.txt").write_text("two", encoding="utf-8")
    third = runner.compute_working_tree_fingerprint("branch", {("??", "changed.txt")})

    assert first == second
    assert third["value"] != first["value"]


def init_temp_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "WORK_QUEUE.md").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "WORK_QUEUE.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True)


def test_temp_git_verified_tree_matches_staged_tree(tmp_path, monkeypatch):
    init_temp_git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "WORK_QUEUE.md").write_text("two\n", encoding="utf-8")

    verified_tree = runner.compute_tree_sha_for_files(["WORK_QUEUE.md"])
    subprocess.run(
        ["git", "add", "-A", "--", "WORK_QUEUE.md"], cwd=tmp_path, check=True
    )
    staged_tree = subprocess.run(
        ["git", "write-tree"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert staged_tree == verified_tree


def test_temp_git_file_mutation_changes_verified_tree(tmp_path, monkeypatch):
    init_temp_git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "WORK_QUEUE.md").write_text("two\n", encoding="utf-8")
    verified_tree = runner.compute_tree_sha_for_files(["WORK_QUEUE.md"])
    (tmp_path / "WORK_QUEUE.md").write_text("three\n", encoding="utf-8")
    mutated_tree = runner.compute_tree_sha_for_files(["WORK_QUEUE.md"])

    assert mutated_tree != verified_tree


def valid_manifest(run_dir, branch="issue-058-task-093-x", result="success"):
    manifest = {
        "issue_number": "58",
        "task_number": "093",
        "branch": branch,
        "verification_timestamp": "2026-06-22T00:00:00+00:00",
        "workflow_state_before_verification": "run_completed",
        "changed_files": [{"status": "M", "path": "WORK_QUEUE.md"}],
        "changed_python_files": [],
        "scope_gate_result": {"success": True, "exit_code": 0},
        "syntax_gate_result": {"success": True, "results": []},
        "targeted_validation_result": {"success": True, "blocks": [{"exit_code": 0}]},
        "black_result": {
            "name": "black",
            "success": True,
            "skipped": True,
            "reason": "no_changed_python_files",
        },
        "isort_result": {
            "name": "isort",
            "success": True,
            "skipped": True,
            "reason": "no_changed_python_files",
        },
        "mypy_result": {
            "name": "mypy",
            "success": True,
            "skipped": True,
            "reason": "no_changed_python_files",
        },
        "full_pytest_exit_code": 0,
        "full_pytest_pass_count": 1032,
        "overall_verification_result": result,
        "verified_working_tree_fingerprint": {
            "algorithm": "sha256",
            "version": runner.FINGERPRINT_VERSION,
            "contract": "test",
            "value": VALID_DIGEST,
        },
        "verified_worktree_fingerprint": {
            "algorithm": "sha256",
            "version": runner.FINGERPRINT_VERSION,
            "contract": "test",
            "value": VALID_DIGEST,
        },
        "verified_tree_sha": VALID_TREE,
    }
    (run_dir / "verification.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in [
        "scope_check.txt",
        "targeted_tests.log",
        "quality_checks.log",
        "full_tests.log",
    ]:
        (run_dir / name).write_text("ok\n", encoding="utf-8")
    return manifest


def test_missing_manifest_blocks_pr(runner_workspace, monkeypatch):
    state, _ = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd(state["branch"]))

    with pytest.raises(SystemExit):
        runner.mode_pr()


def test_failed_manifest_blocks_pr(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir, result="failure")
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd(state["branch"]))

    with pytest.raises(SystemExit):
        runner.mode_pr()


@pytest.mark.parametrize(
    "mutator",
    [
        lambda m: m["scope_gate_result"].update({"success": False}),
        lambda m: m["targeted_validation_result"].update({"success": False}),
        lambda m: m["mypy_result"].update(
            {"success": False, "skipped": False, "exit_code": 1}
        ),
        lambda m: m.update({"issue_number": "99"}),
        lambda m: m.update({"task_number": "999"}),
        lambda m: m.update({"branch": "wrong-branch"}),
        lambda m: m.update({"full_pytest_pass_count": runner.BASELINE_MIN - 1}),
        lambda m: m["verified_working_tree_fingerprint"].update({"value": "bad"}),
    ],
)
def test_manifest_validator_rejects_forged_success(tmp_path, mutator):
    manifest = valid_manifest(tmp_path)
    mutator(manifest)
    with pytest.raises(ValueError):
        runner.validate_manifest_payload(
            manifest,
            expected_issue="58",
            expected_task="093",
            expected_branch="issue-058-task-093-x",
        )


def test_manifest_validator_allows_quality_skip_only_without_python(tmp_path):
    manifest = valid_manifest(tmp_path)
    runner.validate_manifest_payload(manifest)
    manifest["changed_python_files"] = ["scripts/issue_runner.py"]
    with pytest.raises(ValueError):
        runner.validate_manifest_payload(manifest)


def test_empty_targeted_log_blocks_pr(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir)
    (run_dir / "targeted_tests.log").write_text("", encoding="utf-8")
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd(state["branch"]))

    with pytest.raises(SystemExit):
        runner.mode_pr()


def test_stale_fingerprint_blocks_pr(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir)
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd(state["branch"]))
    monkeypatch.setattr(
        scope_guard, "get_changed_files", lambda: {("M", "WORK_QUEUE.md")}
    )
    monkeypatch.setattr(
        runner,
        "compute_working_tree_fingerprint",
        lambda branch, changed: {
            "algorithm": "sha256",
            "version": runner.FINGERPRINT_VERSION,
            "value": "d" * 64,
        },
    )

    with pytest.raises(SystemExit):
        runner.mode_pr()


def test_new_changed_file_set_blocks_pr(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir)
    monkeypatch.setattr(runner, "run_cmd", fake_branch_run_cmd(state["branch"]))
    monkeypatch.setattr(
        scope_guard,
        "get_changed_files",
        lambda: {("M", "WORK_QUEUE.md"), ("??", "scripts/issue_runner.py")},
    )

    with pytest.raises(SystemExit):
        runner.mode_pr()


def test_successful_pr_records_head_and_pr(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir)
    monkeypatch.setattr(
        scope_guard, "get_changed_files", lambda: {("M", "WORK_QUEUE.md")}
    )
    monkeypatch.setattr(
        scope_guard, "parse_task_card", lambda path: ({"WORK_QUEUE.md"}, set())
    )
    monkeypatch.setattr(
        runner,
        "compute_working_tree_fingerprint",
        lambda branch, changed: {
            "algorithm": "sha256",
            "version": runner.FINGERPRINT_VERSION,
            "contract": "test",
            "value": VALID_DIGEST,
        },
    )
    monkeypatch.setattr(
        runner,
        "get_pr_info_for_branch",
        lambda branch: {
            "number": 12,
            "url": "https://example/pr/12",
            "headRefOid": VALID_COMMIT,
        },
    )

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd == ["git", "branch", "--show-current"]:
            return cp(stdout=f"{state['branch']}\n")
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            return cp(stdout="")
        if cmd[:4] == ["git", "add", "-A", "--"]:
            return cp()
        if cmd == ["git", "write-tree"]:
            return cp(stdout=f"{VALID_TREE}\n")
        if cmd == ["git", "commit", "-m", "fix(tooling): harden runner (TASK-093)"]:
            return cp(stdout="commit ok\n")
        if cmd == ["git", "rev-parse", "HEAD"]:
            return cp(stdout=f"{VALID_COMMIT}\n")
        if cmd == ["git", "rev-parse", "HEAD^{tree}"]:
            return cp(stdout=f"{VALID_TREE}\n")
        if cmd[:3] == ["git", "push", "--set-upstream"]:
            return cp()
        if cmd[:2] == ["python3", "scripts/issue_pr_body.py"]:
            return cp(stdout="body")
        return cp(stdout="")

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    runner.mode_pr()

    saved = runner.load_active_run()
    assert saved["status"] == "pr_created"
    assert saved["pushed_head_sha"] == VALID_COMMIT
    assert saved["pr_number"] == "12"


def test_pr_refuses_preexisting_staged_files(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir)
    monkeypatch.setattr(
        scope_guard, "get_changed_files", lambda: {("M", "WORK_QUEUE.md")}
    )
    monkeypatch.setattr(
        runner,
        "compute_working_tree_fingerprint",
        lambda branch, changed: {
            "algorithm": "sha256",
            "version": runner.FINGERPRINT_VERSION,
            "contract": "test",
            "value": VALID_DIGEST,
        },
    )

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd == ["git", "branch", "--show-current"]:
            return cp(stdout=f"{state['branch']}\n")
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            return cp(stdout="unrelated.txt\n")
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    with pytest.raises(SystemExit):
        runner.mode_pr()


def test_pr_does_not_mutate_verification_manifest(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "verified")
    write_task_card(runner_workspace)
    valid_manifest(run_dir)
    before = (run_dir / "verification.json").read_bytes()
    monkeypatch.setattr(
        scope_guard, "get_changed_files", lambda: {("M", "WORK_QUEUE.md")}
    )
    monkeypatch.setattr(
        scope_guard, "parse_task_card", lambda path: ({"WORK_QUEUE.md"}, set())
    )
    monkeypatch.setattr(
        runner,
        "compute_working_tree_fingerprint",
        lambda branch, changed: {
            "algorithm": "sha256",
            "version": runner.FINGERPRINT_VERSION,
            "contract": "test",
            "value": VALID_DIGEST,
        },
    )
    monkeypatch.setattr(
        runner,
        "get_pr_info_for_branch",
        lambda branch: {
            "number": 12,
            "url": "https://example/pr/12",
            "headRefOid": VALID_COMMIT,
        },
    )

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd == ["git", "branch", "--show-current"]:
            return cp(stdout=f"{state['branch']}\n")
        if cmd == ["git", "diff", "--cached", "--name-only"]:
            return cp(stdout="")
        if cmd == ["git", "write-tree"]:
            return cp(stdout=f"{VALID_TREE}\n")
        if cmd == ["git", "rev-parse", "HEAD"]:
            return cp(stdout=f"{VALID_COMMIT}\n")
        if cmd == ["git", "rev-parse", "HEAD^{tree}"]:
            return cp(stdout=f"{VALID_TREE}\n")
        return cp(
            stdout="body" if cmd[:2] == ["python3", "scripts/issue_pr_body.py"] else ""
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    runner.mode_pr()
    assert (run_dir / "verification.json").read_bytes() == before


def test_commit_message_parses_fenced_block():
    assert (
        runner.parse_commit_message_from_card(
            "## Commit Message\n\n```\nfix(x): title\n```"
        )
        == "fix(x): title"
    )


def test_commit_message_parses_indented_block():
    assert (
        runner.parse_commit_message_from_card(
            "## Commit Message\n\n    fix(x): title\n"
        )
        == "fix(x): title"
    )


def test_malformed_commit_message_fails():
    with pytest.raises(ValueError):
        runner.parse_commit_message_from_card("## Commit Message\n\n")


def test_pr_body_rejects_missing_evidence(tmp_path):
    with pytest.raises(ValueError):
        pr_body.generate_pr_body("58", str(tmp_path))


def test_pr_body_summarizes_successful_evidence(tmp_path):
    manifest = valid_manifest(tmp_path)
    (tmp_path / "pr_metadata.json").write_text(
        json.dumps({"commit_sha": VALID_COMMIT, "pushed_head_sha": VALID_COMMIT}),
        encoding="utf-8",
    )
    (tmp_path / "verification.json").write_text(json.dumps(manifest), encoding="utf-8")

    body = pr_body.generate_pr_body("58", str(tmp_path))

    assert "Closes #58" in body
    assert "Full pytest: 1032 passed" in body
    assert f"Verified fingerprint: `{VALID_DIGEST}`" in body
    assert "No log available" not in body


def write_merge_state(tmp_path, **extra):
    fields = {
        "pr_number": "12",
        "committed_head_sha": VALID_COMMIT,
        "committed_tree_sha": VALID_TREE,
        "pushed_head_sha": VALID_COMMIT,
        "pr_head_sha": VALID_COMMIT,
        "verified_tree_sha": VALID_TREE,
    }
    fields.update(extra)
    return write_state(tmp_path, "pr_created", **fields)


@pytest.mark.parametrize(
    "extra,error_field",
    [({"pr_number": ""}, "pr_number"), ({"pushed_head_sha": ""}, "pushed_head_sha")],
)
def test_merge_requires_recorded_pr_and_head(runner_workspace, extra, error_field):
    write_merge_state(runner_workspace, **extra)
    with pytest.raises(SystemExit):
        runner.mode_merge()


@pytest.mark.parametrize(
    "pr_info",
    [
        {
            "state": "OPEN",
            "isDraft": True,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": VALID_COMMIT,
        },
        {
            "state": "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "DIRTY",
            "headRefOid": VALID_COMMIT,
        },
        {
            "state": "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": "d" * 40,
        },
    ],
)
def test_merge_rejects_unsafe_pr_state(runner_workspace, monkeypatch, pr_info):
    write_merge_state(runner_workspace)
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(runner, "get_pr_info", lambda pr: pr_info)

    with pytest.raises(SystemExit):
        runner.mode_merge()


@pytest.mark.parametrize(
    "checks",
    [
        (
            [
                {
                    "name": "ci",
                    "state": "IN_PROGRESS",
                    "conclusion": "",
                    "bucket": "pending",
                }
            ],
        ),
        (
            [
                {
                    "name": "ci",
                    "state": "COMPLETED",
                    "conclusion": "FAILURE",
                    "bucket": "fail",
                }
            ],
        ),
        (
            [
                {
                    "name": "ci",
                    "state": "COMPLETED",
                    "conclusion": "CANCELLED",
                    "bucket": "cancel",
                }
            ],
        ),
    ],
)
def test_merge_rejects_pending_failed_or_cancelled_checks(
    runner_workspace, monkeypatch, checks
):
    write_merge_state(runner_workspace)
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(
        runner,
        "get_pr_info",
        lambda pr: {
            "state": "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": VALID_COMMIT,
        },
    )
    monkeypatch.setattr(
        runner, "checks_are_successful", lambda pr: (checks[0], ["bad check"])
    )

    with pytest.raises(SystemExit):
        runner.mode_merge()


def test_checks_use_supported_gh_fields(monkeypatch):
    calls = []

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        calls.append(cmd)
        return cp(
            stdout=json.dumps(
                [
                    {
                        "name": "ci",
                        "state": "COMPLETED",
                        "bucket": "pass",
                        "workflow": "tests",
                        "link": "https://example/check",
                    }
                ]
            )
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    _, failures = runner.checks_are_successful("12")

    assert not failures
    assert calls[0] == [
        "gh",
        "pr",
        "checks",
        "12",
        "--json",
        "name,state,bucket,workflow,link",
    ]


@pytest.mark.parametrize("bucket", ["pending", "fail", "cancel", "skipping", ""])
def test_checks_reject_nonpassing_buckets(monkeypatch, bucket):
    monkeypatch.setattr(
        runner,
        "run_cmd",
        lambda cmd, check=True, capture=True, cwd=None: cp(
            stdout=json.dumps(
                [{"name": "ci", "state": "IN_PROGRESS", "bucket": bucket}]
            )
        ),
    )
    _, failures = runner.checks_are_successful("12")
    assert failures


def test_checks_reject_empty_and_malformed(monkeypatch):
    monkeypatch.setattr(
        runner,
        "run_cmd",
        lambda cmd, check=True, capture=True, cwd=None: cp(stdout="[]"),
    )
    _, failures = runner.checks_are_successful("12")
    assert failures

    monkeypatch.setattr(
        runner,
        "run_cmd",
        lambda cmd, check=True, capture=True, cwd=None: cp(stdout="{bad"),
    )
    with pytest.raises(SystemExit):
        runner.checks_are_successful("12")


def test_successful_exact_head_merge_clears_active_state(runner_workspace, monkeypatch):
    write_merge_state(runner_workspace)
    infos = [
        {
            "state": "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": VALID_COMMIT,
        },
        {"state": "MERGED"},
    ]
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(runner, "get_pr_info", lambda pr: infos.pop(0))
    monkeypatch.setattr(
        runner,
        "checks_are_successful",
        lambda pr: (
            [
                {
                    "name": "ci",
                    "state": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "bucket": "pass",
                }
            ],
            [],
        ),
    )

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd in (["git", "rev-parse", "main"], ["git", "rev-parse", "origin/main"]):
            return cp(stdout="mainsha\n")
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    runner.mode_merge()

    assert not Path(runner.ACTIVE_RUN_PATH).exists()


def test_merge_archive_failure_preserves_active_state(runner_workspace, monkeypatch):
    write_merge_state(runner_workspace)
    monkeypatch.setattr(runner, "_merge_confirmed", False, raising=False)
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(
        runner,
        "get_pr_info",
        lambda pr: {
            "state": "MERGED" if getattr(runner, "_merge_confirmed", False) else "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": VALID_COMMIT,
        },
    )
    monkeypatch.setattr(
        runner,
        "checks_are_successful",
        lambda pr: ([{"name": "ci", "state": "COMPLETED", "bucket": "pass"}], []),
    )

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd[:3] == ["gh", "pr", "merge"]:
            setattr(runner, "_merge_confirmed", True)
            return cp()
        if cmd in (["git", "rev-parse", "main"], ["git", "rev-parse", "origin/main"]):
            return cp(stdout="mainsha\n")
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(
        runner,
        "archive_final_state",
        lambda run_dir, state: (_ for _ in ()).throw(OSError("archive failed")),
    )
    with pytest.raises(SystemExit):
        runner.mode_merge()

    assert runner.load_active_run()["status"] == "pr_created"


def test_merge_confirmation_failure_preserves_active_state(
    runner_workspace, monkeypatch
):
    write_merge_state(runner_workspace)
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(
        runner,
        "get_pr_info",
        lambda pr: {
            "state": "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": VALID_COMMIT,
        },
    )
    monkeypatch.setattr(
        runner,
        "checks_are_successful",
        lambda pr: (
            [
                {
                    "name": "ci",
                    "state": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "bucket": "pass",
                }
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        runner, "run_cmd", lambda cmd, check=True, capture=True, cwd=None: cp()
    )

    with pytest.raises(SystemExit):
        runner.mode_merge()

    assert runner.load_active_run()["status"] == "pr_created"


def test_abort_refuses_dirty_worktree(runner_workspace, monkeypatch):
    state, _ = write_state(runner_workspace, "planned")
    monkeypatch.setattr(runner, "get_current_branch", lambda: state["branch"])
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: False)

    with pytest.raises(SystemExit):
        runner.mode_abort()

    assert runner.load_active_run()["status"] == "planned"


def test_abort_refuses_wrong_branch(runner_workspace, monkeypatch):
    write_state(runner_workspace, "planned", branch="expected")
    monkeypatch.setattr(runner, "get_current_branch", lambda: "actual")

    with pytest.raises(SystemExit):
        runner.mode_abort()


def test_abort_refuses_unmerged_commits(runner_workspace, monkeypatch):
    state, _ = write_state(runner_workspace, "planned")
    monkeypatch.setattr(runner, "get_current_branch", lambda: state["branch"])
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(
        runner,
        "run_cmd",
        lambda cmd, check=True, capture=True, cwd=None: (
            cp(stdout="1\n") if cmd[:3] == ["git", "rev-list", "--count"] else cp()
        ),
    )

    with pytest.raises(SystemExit):
        runner.mode_abort()


def test_safe_abort_archives_then_clears(runner_workspace, monkeypatch):
    state, run_dir = write_state(runner_workspace, "planned")
    monkeypatch.setattr(runner, "get_current_branch", lambda: state["branch"])
    monkeypatch.setattr(runner, "is_worktree_clean", lambda: True)

    def fake_run_cmd(cmd, check=True, capture=True, cwd=None):
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return cp(stdout="0\n")
        return cp()

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    runner.mode_abort()

    assert not Path(runner.ACTIVE_RUN_PATH).exists()
    assert (run_dir / "abort_state.json").exists()
