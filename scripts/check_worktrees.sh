#!/usr/bin/env bash
# Read-only inventory. A clean or merged tree is not permission to delete it.
set -euo pipefail
python3 - "$(dirname "${BASH_SOURCE[0]}")" <<'PY'
from pathlib import Path
import subprocess
import sys


def git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


common = Path(git(sys.argv[1], "rev-parse", "--path-format=absolute", "--git-common-dir"))
primary = common.parent
siblings = primary.parent / f"{primary.name}-worktrees"
# -z preserves spaces, newlines, and other characters in registered paths.
records = {}
record = None
for field in git(primary, "worktree", "list", "--porcelain", "-z").split("\0"):
    if field.startswith("worktree "):
        path = Path(field[9:])
        record = records.setdefault(path, {})
    elif field and record is not None:
        key, _, value = field.partition(" ")
        record[key] = value
if siblings.is_dir():
    for path in siblings.iterdir():
        if path.is_dir():
            records.setdefault(path, {"orphan": ""})
records.pop(primary, None)


def file_count(path):
    if not path.is_dir():
        return 0
    return sum(p.is_file() and p.name != ".gitkeep" for p in path.rglob("*"))


print("WORKTREE\tEDITS\tOUTPUT FILES\tCACHE FILES\tSTATUS")
for path, metadata in sorted(records.items()):
    if not path.exists():
        state = "PRUNABLE" if "prunable" in metadata else "MISSING"
        print(f"{path}\t-\t-\t-\t{state} — registered path is absent; inspect metadata")
        continue
    output_count = file_count(path / "output")
    cache_count = file_count(path / "cache")
    if "orphan" in metadata:
        print(f"{path}\t?\t{output_count}\t{cache_count}\tORPHAN — unregistered sibling directory; inspect contents")
        continue
    try:
        edits = len(git(path, "status", "--porcelain").splitlines())
        head = git(path, "rev-parse", "HEAD")
        merged = subprocess.run(
            ["git", "-C", str(primary), "merge-base", "--is-ancestor", head, "refs/heads/main"],
            capture_output=True,
        ).returncode == 0
    except subprocess.CalledProcessError:
        print(f"{path}\t?\t{output_count}\t{cache_count}\tUNKNOWN — Git inspection failed")
        continue
    label = "detached HEAD" if "detached" in metadata else metadata.get("branch", "unknown branch")
    if edits or output_count or cache_count:
        status = "LIVE — edits, output, or cached data require review"
    elif not merged:
        status = "LIVE — HEAD not confirmed contained in main"
    else:
        status = "REVIEW — clean tracked tree, HEAD contained in main"
    if "locked" in metadata:
        status += "; worktree is locked"
    print(f"{path}\t{edits}\t{output_count}\t{cache_count}\t{status} ({label})")
if not records:
    print("No linked worktrees or orphan sibling directories found.")
print("\nThis inventory does not establish that a worktree is safe to remove.")
print("Review ignored files, preserve shown renders and post data, and compare cache contents before cleanup.")
print("Historical assets are not evidence that the current post was saved. Use git worktree remove only after review.")
PY
