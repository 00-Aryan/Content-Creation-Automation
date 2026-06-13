#!/usr/bin/env bash
# issue-runner.sh — Entrypoint for local issue-driven automation runner
set -euo pipefail

# Ensure working directory is the repository root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Ensure UV cache directory is set
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
mkdir -p "$UV_CACHE_DIR"

# Run Python runner controller
exec python3 scripts/issue_runner.py "$@"
