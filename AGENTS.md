# Working Guide

Bulls analysis and social-graphics production for `@chicagobullsdata`. **Posts are assembled in
Canva**; Python owns the analysis and produces the verified chart assets that go into the page.
Canva is a layout surface, never an analytical source — this repo stays the editor of record for
metrics, qualifications, sources, and the final downloaded pages.

## Read the Right Document

| Working on… | Read… |
| --- | --- |
| Audience, metrics, distribution | `STRATEGY.md` |
| Any visual, mock, or post iteration | `DESIGN.md`, then `POSTING_WORKFLOW.md` |
| Editorial direction and fairness guardrails | `bulls-content-playbook.html` |
| The shelf of post ideas | the Notion `chicagobullsdata posts` database, then `idea-catalog.html` |
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
4. `output/` is disposable only after approved finals are preserved in `docs/mocks/`.
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
re-derive it to answer "where did this come from?" months later. `idea-catalog.html` remains the repo-side shelf of
worked-up briefs; Notion is where an idea starts and where its status stays current.

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
Python. `DESIGN.md` owns the chart layer, and a chart-layer change must land in `DESIGN.md` and
`bulls/graphics/house.py` together. `tests/test_design_tokens.py` catches color drift only.
`design-system.html` documents the legacy full-layout system and has not been rebuilt for the
Canva-first model.

Record an explicitly stated user preference as a durable rule immediately. Keep a conclusion inferred
from results as a hypothesis until the user confirms it or repeated evidence supports it.

`docs/handoffs/` holds temporary transfer notes marked `ACTIVE` or `CLOSED`. When work closes, move
anything reusable into its owner document and compact the handoff to its outcome.

## Cross-Tool Skills

Canonical skills live in `.agents/skills/<name>/SKILL.md`. `.claude/skills/<name>/SKILL.md` is a
relative symlink to it — never a copy. Update both paths when adding, renaming, or removing one.
