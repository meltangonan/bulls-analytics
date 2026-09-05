# Working Guide

Python verifies the data and renders chart assets for `@chicagobullsdata`; Canva assembles the page.
Notion owns editorial direction, ideas, briefs, post status, and publishing history.

## Load only what the task needs

Use guidance already in the conversation; don't reread it on every turn. Search the relevant
section or function before opening a whole file. A caption edit doesn't need graphics code;
a chart adjustment doesn't need the full post history.

| Task | Starting point |
| --- | --- |
| Choose an idea, editorial direction, captions, performance | [Notion editorial direction](https://www.notion.so/3d2e1c13abe681e586b4c44762261fab) and the relevant post |
| Build or adjust a chart | `DESIGN.md`, then only the matching family reference/helper |
| Build, approve, or record a post | `POSTING_WORKFLOW.md` or the matching create/promote/review skill |
| Change Python or run checks | `DEVELOPMENT.md`; endpoint references only for the data being used |
| Find an existing renderer | `scripts/prototypes/README.md` |
| Create, integrate, or remove a worktree | `docs/reference/worktrees.md` |

## Working defaults

- Reuse settled chart formats and shared table, card, and portrait helpers. Keep calculations and
  qualification in Python; never recompute them in Canva. Extract repeated operations after real
  consumers exist, without inventing a universal post framework.
- Verify source coverage, units, scope, and qualifications. Missing/unavailable data is not zero.
  Preserve source snapshots and the trail from raw rows to the published figure.
- Save each render before showing it with `scripts/save_visual_version.py --project <slug> <files>`.
  Before committing, prune superseded cosmetic adjustments; retain decision-bearing versions and
  approved publish-resolution assets. Post-specific data belongs in that post's tracked `data/`.
- Run checks matched to the change using `DEVELOPMENT.md`. Repeat or broaden only after relevant
  changes, failures, or unresolved concerns. Finish requested adjustments; stop proposing polish
  once the brief is satisfied.
- Use a worktree for a post, substantial shared-code changes, or concurrent work. Small maintenance
  may use a clean primary `main` when no other task is editing it. Never switch primary `main` to a
  task branch. One logical post or cleanup is one reviewed commit; commit/push need explicit approval.
- Preserve dirty worktrees, unique scratch, and unmerged work. Remove only reviewed, integrated work;
  consult `docs/reference/worktrees.md` at closeout.
- Use bounded sub-agents when independent work can progress alongside useful local work: source
  audits, separate code areas, or an independent review. Assign file ownership and ask for compact
  findings with evidence. Routine edits stay local; don't delegate merely to add reviewers.

## Notion and external actions

The [posts database](https://www.notion.so/3a6e1c13abe6809ab16bfe33edb233cf) is the live catalog.
Read the matching record when starting/resuming a post or checking its state, not on every adjustment.
Keep working details and provenance there as decisions land; store the Canva edit link in `Canva`.
`POSTING_WORKFLOW.md` defines the status transitions and publication check.

Instagram and X are read-only without explicit per-action approval for posting, commenting,
liking, following, messaging, or settings. The in-app browser may already be signed into
`@chicagobullsdata` and `@bullsdata`; verify live state rather than assuming it.

## Maintain one owner

Update the owner of a changed rule, replacing stale guidance instead of appending an incident log.
Notion owns strategy, voice, ideas and post-specific lessons; the repo owns code, reproducibility,
chart contracts and execution. Record explicit user preferences there; inferred lessons remain
hypotheses until confirmed. Keep supporting references conditional, and preserve useful contrary evidence.

Canonical skills are `.agents/skills/<name>/SKILL.md`; `.claude/skills/<name>/SKILL.md` is a one-way
relative symlink. Keep both discovery paths valid. Closed handoffs contain only outcomes and pointers.
