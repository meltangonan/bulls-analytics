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

printf '%-40s %6s %8s %6s %6s  %s\n' "WORKTREE" "EDITS" "RENDERS" "SAVED" "CACHE" "STATUS"
printf '%s\n' "$(printf '%.0s-' {1..104})"

removable=0
unsaved_renders=()
for w in "$WORKTREES"/*/; do
    [ -d "$w" ] || continue
    name="$(basename "$w")"

    edits="$( { git -C "$w" status --porcelain 2>/dev/null || true; } | wc -l | tr -d ' ')"
    # ⚠️ `set -euo pipefail` is on, so a `find` over a directory that does not
    # exist fails the whole pipeline and kills the run. A worktree with no
    # output/ or no docs/visuals/ is normal, not an error — count it as zero.
    renders="$( { find "$w/output" -type f ! -name '.gitkeep' 2>/dev/null || true; } | wc -l | tr -d ' ')"
    # Renders in output/ with nothing in assets/ means nothing was ever saved.
    # Every render shown to the user should already be here (AGENTS.md default 4).
    saved="$( { find "$w/docs/visuals" -path '*/assets/*' -type f 2>/dev/null || true; } | wc -l | tr -d ' ')"
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

    if [ "$renders" -gt 0 ] && [ "$saved" -eq 0 ]; then
        unsaved_renders+=("$name")
    fi

    printf '%-40s %6s %8s %6s %6s  %s\n' \
        "$name" "$edits" "$renders" "$saved" "${cache:--}" "$status"
done

echo
if [ ${#unsaved_renders[@]} -gt 0 ]; then
    echo "⚠️  Renders in output/ but nothing in assets/: ${unsaved_renders[*]}"
    echo "    output/ overwrites on every re-run, so an unsaved render is one run from gone."
    echo "    Save with scripts/save_visual_version.py --project <slug>, then prune at commit."
    echo
fi
if [ "$removable" -eq 0 ]; then
    echo "Nothing is safe to remove. Every worktree holds unsaved work or unmerged commits."
else
    echo "$removable worktree(s) look removable."
fi
cat <<'NOTE'

Before removing any worktree, regardless of what this says:
  - save anything in output/ the user has seen (scripts/save_visual_version.py); prune the
    adjustments before the post's commit, not before the render is safe
  - copy cache/ back to the primary checkout if the fetch was expensive
  - `git worktree remove <path>` first; it refuses when scratch is present, which is a
    warning worth reading rather than a reason to reach for `rm -rf`
NOTE
