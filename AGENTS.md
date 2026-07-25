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
| The shelf of post ideas | `idea-catalog.html` |
| A create / promote / review stage | the matching skill in `.agents/skills/` |
| Fetchers, analysis, graphics code, scripts, tests | `DEVELOPMENT.md` |

## Defaults

1. One post idea at a time. Favor analysis quality over presentation polish, and keep solutions
   simple — no speculative architecture, heavy export pipelines, or new frameworks unless asked.
2. Python builds the chart, Canva builds the page. Don't add titles, headers, or page furniture to a
   chart asset; don't recompute anything in Canva. The Python full-layout system is legacy
   (`DESIGN.md`) — maintain it, don't build new posts on it.
3. Applicable thresholds, coverage windows, and sources stay visible on every data-bearing graphic.
   The user usually adds them manually in Canva.
4. `output/` is disposable only after approved finals are preserved in `docs/mocks/`.
5. After completing and verifying work, show the user the result and wait for explicit approval
   before committing or pushing. Approval covers the work under review, not later work. Work on
   `main` unless the user asks for a branch.

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
