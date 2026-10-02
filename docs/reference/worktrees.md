# Worktrees and integration

A branch names a Git history; a worktree gives it a separate working folder. Keep primary `main`
as the integration checkout. Use one worktree per active post and for substantial shared changes
or concurrent work. Read-only work needs none. Small maintenance can use clean `main` when no
other task is editing it. If the current task already has a suitable worktree, reuse it.
Cloud tasks are already isolated; reuse their checkout unless the user requests another worktree.

## Start

Check `git status --short --branch` and `git worktree list`. Run `scripts/check_worktrees.sh` when
starting an isolated task or preparing cleanup. Fetch `origin` before starting or resuming work;
fast-forward a clean primary `main` to `origin/main`. Preserve unexpected work; do not auto-stash
or reset it. If access fails, report that freshness is unverified. Create from the updated main:

```bash
git -C /Users/meltangonan/projects/bulls-analytics worktree add -b codex/<slug> \
  /Users/meltangonan/projects/bulls-analytics-worktrees/<slug> main
```

Use the primary checkout's Python environment. Do not copy all of `cache/` automatically; copy
only the selected chart's required shared inputs when needed. Keep worktree writes isolated and
post-specific source data in that post's tracked `data/` directory.

When switching between local and cloud, resume the same task branch and fast-forward from its
remote branch when safe. Inspect divergence before reconciling it; do not replace unfinished work.
At handoff, report the branch, last pushed commit, and anything still local (including ignored
assets/data). Git transfers only committed and pushed files, not `output/`, caches, or environments.

## Integrate

After the user approves committing/pushing the reviewed change, inspect the diff, stage explicit
paths and make one Conventional Commit per logical post or cleanup. Fetch again before integration
or pushing; reconcile with latest `origin/main` and check affected code after any conflict resolution.
Do not rewrite a shared task branch without agreement. Fast-forward primary main, push only when approved,
and verify local/remote SHA parity. Never force-push `main`; if it advanced, fetch and reconcile again.
Update the compact renderer index in the same change when its
entry point changes; do not require a separate index-maintenance commit.

## Remove

Delete merged local branch names that no worktree uses when cleaning up. An unmerged branch or a
dirty worktree needs inspection of its unique work, not forced deletion. A parked post stays parked
until the user resumes or abandons it; record an abandonment reason on its Notion page.

Before removing an integrated worktree, verify its intended changes reached `origin/main` and no
unique unpushed commits remain. Inspect tracked changes, untracked files, ignored outputs,
and caches. Preserve shown/approved assets and unique expensive inputs; compare scratch with the
tracked assets before discarding it. The checker inventories candidates, not authorization to delete.

Use `git worktree remove <absolute-path>` after preserving unique files. A modified/untracked-files
refusal means investigate. A post-removal `Directory not empty` can be macOS residue, but verify
the remaining files before removing them. Prune a missing worktree's Git registration only after
confirming that its directory is gone; keep its branch unless merged or explicitly abandoned.
Do not run broad force-clean, reset, branch deletion, or cache deletion against active work.
