# Worktrees and integration

A branch names a Git history; a worktree gives it a separate working folder. Keep primary `main`
as the integration checkout. Use one worktree per active post and for substantial shared changes
or concurrent work. Read-only work needs none. Small maintenance can use clean `main` when no
other task is editing it. If the current task already has a suitable worktree, reuse it.

## Start

Check `git status --short --branch` and `git worktree list`. Run `scripts/check_worktrees.sh` when
starting an isolated task or preparing cleanup. Fetch and fast-forward a clean primary `main`;
preserve unexpected work. Create from current main:

```bash
git -C /Users/meltangonan/projects/bulls-analytics worktree add -b codex/<slug> \
  /Users/meltangonan/projects/bulls-analytics-worktrees/<slug> main
```

Use the primary checkout's Python environment. Do not copy all of `cache/` automatically; copy
only the selected chart's required shared inputs when needed. Keep worktree writes isolated and
post-specific source data in that post's tracked `data/` directory.

## Integrate

After the user approves committing/pushing the reviewed change, inspect the diff, stage explicit
paths and make one Conventional Commit per logical post or cleanup. Rebase on current main if
needed; resolve and check affected shared code. Fast-forward primary main, push only when approved,
and verify local/remote SHA parity. Update the compact renderer index in the same change when its
entry point changes; do not require a separate index-maintenance commit.

## Remove

Delete merged local branch names that no worktree uses when cleaning up. An unmerged branch or a
dirty worktree needs inspection of its unique work, not forced deletion. A parked post stays parked
until the user resumes or abandons it; record an abandonment reason on its Notion page.

Before removing an integrated worktree, inspect tracked changes, untracked files, ignored outputs,
and caches. Preserve shown/approved assets and unique expensive inputs; compare scratch with the
tracked assets before discarding it. The checker inventories candidates, not authorization to delete.

Use `git worktree remove <absolute-path>` after preserving unique files. A modified/untracked-files
refusal means investigate. A post-removal `Directory not empty` can be macOS residue, but verify
the remaining files before removing them. Prune a missing worktree's Git registration only after
confirming that its directory is gone; keep its branch unless merged or explicitly abandoned.
Do not run broad force-clean, reset, branch deletion, or cache deletion against active work.
