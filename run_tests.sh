#!/bin/bash
# Run tests using the virtual environment's Python
# This ensures all dependencies and mocks work correctly. Linked worktrees reuse
# the primary checkout's environment but explicitly import code from this tree.

set -euo pipefail

repo_dir="$(cd "$(dirname "$0")" && pwd)"
python_path="$repo_dir/venv/bin/python"

if [[ ! -x "$python_path" ]]; then
    common_git_dir="$(git -C "$repo_dir" rev-parse --path-format=absolute --git-common-dir)"
    primary_repo_dir="$(dirname "$common_git_dir")"
    python_path="$primary_repo_dir/venv/bin/python"
fi

if [[ ! -x "$python_path" ]]; then
    echo "Python environment not found. Expected venv/bin/python in the primary checkout." >&2
    exit 1
fi

cd "$repo_dir"
PYTHONPATH="$repo_dir${PYTHONPATH:+:$PYTHONPATH}" \
    "$python_path" -m pytest tests/ -v "$@"
