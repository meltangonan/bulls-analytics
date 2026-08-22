# Working Guide

Bulls analysis and social-graphics production for `@chicagobullsdata`. **Posts are assembled in
Canva**; Python owns the analysis and produces the verified chart assets that go into the page.
Canva is a layout surface, never an analytical source — this repo stays the editor of record for
metrics, qualifications, sources, and the verified chart assets.

## Read the Right Document

| Working on… | Read… |
| --- | --- |
| Audience, editorial direction, metrics, distribution | `STRATEGY.md` |
| Any visual, mock, or post iteration | `DESIGN.md`, then `POSTING_WORKFLOW.md` |
| Analytical scope and fairness guardrails | `POSTING_WORKFLOW.md` |
| Caption voice, hashtags, what a post says | `POSTING_WORKFLOW.md` |
| The shelf of post ideas and post log | the Notion `chicagobullsdata posts` database |
| A create / promote / review stage | the matching skill in `.agents/skills/` |
| Fetchers, analysis, graphics code, scripts, tests | `DEVELOPMENT.md` |

## Defaults

1. One post idea per task and working tree. Favor analysis quality over presentation polish, and
   keep solutions simple — no speculative architecture, heavy export pipelines, or new frameworks
   unless asked.
2. Python builds the chart, Canva builds the page. Don't add titles, headers, or page furniture to a
   chart asset; don't recompute anything in Canva. The Python full-layout system is legacy
   (`DESIGN.md`) — maintain it, don't build new posts on it.
3. Applicable thresholds, coverage windows, and sources stay visible on every data-bearing graphic.
   The user usually adds them manually in Canva.
4. **Promote decisions, not renders.** Renders go to `output/` — scratch, gitignored, disposable.
   A render is promoted into `docs/visuals/YYYY-MM-DD-<slug>/assets/` when it carries a *decision*:
   a different metric, cohort, threshold, chart type, sort or claim. Always promote what the user
   approves. Adjustments — moved, resized, recolored, re-cropped — are overwritten in `output/` and
   never promoted. Promote at publish DPI, as it happens.
   **When in doubt, promote** — over-promoting costs 300 KB, under-promoting loses the only copy.
   **Saving is continuous; committing is not.** One post is one commit, made at the end once the
   final graphic is settled, then pushed. Never commit a post's work in pieces — thirty iterations
   are one piece of work, not thirty. Promoted files sit uncommitted in the worktree until then,
   which is safe: `git worktree remove` refuses a dirty or untracked worktree, and
   `scripts/check_worktrees.sh` reports what is unsaved before anything is removed.
   The numbers behind the render go in `data/`. Save with `scripts/save_visual_version.py`
   (`--data`). The repo does not archive the composed Canva page: Canva holds the editable design,
   Instagram holds the published post, and the publish-DPI chart is already in `assets/`. QA still
   works from a real export — download it, check it, don't file it.
   **A graphic's data ships with the graphic.** Scope decides where a dataset lives: a dataset with
   exactly one consuming post belongs in that post's `data/` from the start, whether or not it was
   expensive to fetch, because that is what makes the numbers auditable later without refetching.
   Only genuinely shared material stays in ignored `cache/` — portraits, the licensed font
   extraction, the league shot baseline, season game logs.
   `scripts/save_visual_version.py` and `bulls/visuals.py` own the full rules and the reasons;
   `tests/test_data_locations.py` enforces the data half.
5. After completing and verifying work, show the user the result and wait for explicit approval
   before committing or pushing. Approval covers the work under review, not later work.
6. Any post task that changes repo files automatically gets a temporary branch and linked worktree;
   the user does not need to request it or report parallel work. Keep the primary checkout on `main`
   at all times — never switch it to a post branch. Follow `DEVELOPMENT.md` for the fixed worktree
   location, shared environment, integration, and safe cleanup. Preserve and report any dirty or
   unmerged worktree; remove only work already represented on `main`.

## Notion

The user's Notion `chicagobullsdata posts` database is the live idea catalog and post log — one page
per post, `Status` moving `Not started → In progress → Mocked → Posted`, and a `Canva` URL property
holding the design's edit link. Read it when picking up or scoping an idea, and check it before
assuming a post's state. The page body carries the working detail — what the chart shows, thresholds,
what was rejected and why, build notes — so record those there as work lands, and keep the Canva link
in the property rather than as a bookmark block.

**Every data-bearing post page also carries a data provenance section, written without being asked.**
Findings age well; the trail back to them does not. Record where the numbers came from and how a raw
record becomes the published figure — endpoint and exact call parameters, what one raw row is, units
and coordinate systems, which fields are derived rather than measured, what the source structurally
cannot contain, and one worked example tracing a single record end to end. `DEVELOPMENT.md` defines
what the section must answer. The user should never have to ask for it, and should never have to
re-derive it to answer "where did this come from?" months later. Notion owns the idea, working brief,
status, and post history; the repository owns code, verified artifacts, and durable system rules.

## Instagram and X Access

Read-only on both platforms: never post, comment, like, follow, or change settings without explicit
per-action approval.

The user is logged into `@chicagobullsdata` (Instagram) and `@bullsdata` (X) in the runtime's in-app
browser, falling back to Chrome. X follows a curated set of basketball data/analytics accounts and is
the better surface for narratives and beat-reporter news (K.C. Johnson, `@chicagobulls`). Useful
Instagram references: the grid, the saved `Basketball` collection, Basketball University, Kirk
Goldsberry, WNBA Viz Wiz, datakabas. Treat live state as best-effort and session-specific, and verify
any fact independently before it reaches a caption or a graphic.

## Documentation Ownership

Update the document that owns a changed decision. Revise stale guidance instead of appending history.
This is part of completing the work, not a separate request.

**Design ownership is split.** Canva's Brand Kit owns post typography and page layout — that's
upstream of this repo, so record changes in `DESIGN.md` rather than trying to reproduce them in
Python. `DESIGN.md` owns the chart layer — how a chart looks — and a chart-layer change must land in
`DESIGN.md` and `bulls/graphics/house.py` together. It does not own what a post *says*: caption
voice and hashtags live in `POSTING_WORKFLOW.md`, and the analytical reasoning behind the shot-chart
family lives in `DEVELOPMENT.md` under Chart Family Notes. `tests/test_design_tokens.py` catches color drift only.
The legacy full-layout HTML design-system companion has been retired; `DESIGN.md` and
`bulls/graphics/house.py` retain only the code and rules needed to maintain older renderers.

Record an explicitly stated user preference as a durable rule immediately. Keep a conclusion inferred
from results as a hypothesis until the user confirms it or repeated evidence supports it.

`docs/handoffs/` holds temporary transfer notes marked `ACTIVE` or `CLOSED`. When work closes, move
anything reusable into its owner document and compact the handoff to its outcome.

## Cross-Tool Skills

Canonical skills live in `.agents/skills/<name>/SKILL.md`. `.claude/skills/<name>/SKILL.md` is a
relative symlink to it — never a copy. Update both paths when adding, renaming, or removing one.
