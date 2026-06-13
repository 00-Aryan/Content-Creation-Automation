#!/usr/bin/env python3
import sys
import os
import re
import subprocess

def parse_task_card(card_path):
    if not os.path.exists(card_path):
        return set(), set()
    
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    modify_files = set()
    create_files = set()
    current_section = None
    
    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        header_match = re.match(r'^#+\s+(.*)', line_stripped)
        if header_match:
            header_text = header_match.group(1).lower().strip()
            if "files to modify" in header_text:
                current_section = "modify"
            elif "files to create" in header_text:
                current_section = "create"
            else:
                current_section = None
            continue
        
        if current_section:
            bullet_match = re.match(r'^[-*]\s+(.*)', line_stripped)
            if bullet_match:
                file_path = bullet_match.group(1).strip().strip('`').strip()
                if file_path:
                    file_path = os.path.normpath(file_path)
                    if current_section == "modify":
                        modify_files.add(file_path)
                    elif current_section == "create":
                        create_files.add(file_path)
                        
    return modify_files, create_files

def get_changed_files():
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        print(f"Error running git status: {e}", file=sys.stderr)
        return set()
    
    changed = set()
    for line in res.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip()
        file_path = line[3:].strip()
        if " -> " in file_path:
            parts = file_path.split(" -> ")
            file_path = parts[-1].strip()
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        
        file_path = os.path.normpath(file_path)
        changed.add((status, file_path))
    return changed

def run_scope_check(card_path):
    modify_allowed, create_allowed = parse_task_card(card_path)
    allowed_all = modify_allowed.union(create_allowed)
    
    changed = get_changed_files()
    violations = []
    
    ignored_patterns = [
        re.compile(r'^WORK_QUEUE\.md$'),
        re.compile(r'^docs/tasks/task_.*\.md$'),
        re.compile(r'^\.runs/'),
        re.compile(r'^\.run-tasks\.log$'),
        re.compile(r'^\.pytest_cache/'),
        re.compile(r'^\.mypy_cache/'),
    ]
    
    def is_ignored(path):
        for pattern in ignored_patterns:
            if pattern.search(path):
                return True
        return False
    
    for status, path in changed:
        if is_ignored(path):
            continue
        if path not in allowed_all:
            violations.append(f"Unexpected file changed/created: {path} (status: {status})")
            
    return violations, allowed_all, changed

def main():
    if len(sys.argv) < 2:
        print("Usage: issue_scope_guard.py <path_to_task_card_md>", file=sys.stderr)
        sys.exit(2)
        
    card_path = sys.argv[1]
    violations, allowed_all, changed = run_scope_check(card_path)
    
    if violations:
        print("SCOPE VIOLATION DETECTED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Scope check passed. All modified files are within the allowed scope.")
        sys.exit(0)

if __name__ == "__main__":
    main()
