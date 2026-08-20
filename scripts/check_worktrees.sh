#!/usr/bin/env bash
# Report what is unsaved in each post worktree. Read-only: this script never
# removes, stashes, or modifies anything.
#
# "Is the branch merged?" and "is the work done?" are different questions. A
# merged branch means the *code* landed; it says nothing about renders sitting in
# ignored output/ or a cache/ that took fifty minutes to fetch. Both have been
# destroyed by a cleanup that asked only the first question. This asks the second.
set -euo pipefail

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
WORKTREES="$(dirname "$ROOT")/$(basename "$ROOT")-worktrees"

if [ ! -d "$WORKTREES" ]; then
    echo "No worktree directory at $WORKTREES — nothing to check."
    exit 0
fi

printf '%-44s %7s %8s %7s  %s\n' "WORKTREE" "EDITS" "RENDERS" "CACHE" "STATUS"
printf '%s\n' "$(printf '%.0s-' {1..100})"

removable=0
for w in "$WORKTREES"/*/; do
    [ -d "$w" ] || continue
    name="$(basename "$w")"

    edits="$(git -C "$w" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    renders="$(find "$w/output" -type f ! -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ')"
    cache="$(du -sh "$w/cache" 2>/dev/null | cut -f1 || echo '-')"
    branch="$(git -C "$w" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"

    if git -C "$ROOT" merge-base --is-ancestor "$branch" main 2>/dev/null; then
        merged="merged"
    else
        merged="unmerged"
    fi

    if [ "$edits" -gt 0 ] || [ "$renders" -gt 0 ]; then
        status="LIVE — unsaved work, leave alone"
    elif [ "$merged" = "unmerged" ]; then
        status="LIVE — branch has commits main lacks"
    else
        status="safe to remove (branch $branch is merged, nothing unsaved)"
        removable=$((removable + 1))
    fi

    printf '%-44s %7s %8s %7s  %s\n' "$name" "$edits" "$renders" "${cache:--}" "$status"
done

echo
if [ "$removable" -eq 0 ]; then
    echo "Nothing is safe to remove. Every worktree holds unsaved work or unmerged commits."
else
    echo "$removable worktree(s) look removable."
fi
cat <<'NOTE'

Before removing any worktree, regardless of what this says:
  - promote anything in output/ that carries a decision (scripts/save_visual_version.py)
  - copy cache/ back to the primary checkout if the fetch was expensive
  - `git worktree remove <path>` first; it refuses when scratch is present, which is a
    warning worth reading rather than a reason to reach for `rm -rf`
NOTE
