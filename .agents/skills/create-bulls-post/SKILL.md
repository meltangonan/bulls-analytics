---
name: create-bulls-post
description: Turn a selected Chicago Bulls post idea into a clarified brief, tested analysis, and reviewable graphic. Use when the user wants to create, mock up, build, or develop a specific @chicagobullsdata post, including an existing Notion idea. Do not use for loose ideation, promotion of an approved post, or post-performance review.
---

# Create Bulls Post

Move one selected idea from intent to an approved visual without making the user repeat settled
context.

## Context

Read `AGENTS.md`, `DESIGN.md`, and `POSTING_WORKFLOW.md`. Read the matching page in the Notion
`chicagobullsdata posts` database when the idea already exists, `STRATEGY.md` when the editorial
angle is unclear, and `DEVELOPMENT.md` before touching analysis, fetchers, graphics code, or tests.

These files and the conversation are the source of truth. Don't restate their rules in a separate
planning artifact.

## Brief

Cover the six areas in `POSTING_WORKFLOW.md`, then restate the settled brief so the user can correct
it. Ask only about gaps that block the first draft; for an existing Notion page, that's usually just
timeframe and exact title/subtitle/footnote copy. Never ask the user to re-decide
something already settled.

If the user says "pick for me," choose and state the choice plainly.

## One Draft

Build a single reviewable draft, not a set of options (`AGENTS.md` default 2 splits chart from
page).

- Reuse the established design system and existing helpers before inventing a new visual grammar.
- When working from an F5 or similar tutorial, reproduce its styling and structure closely and swap
  in our palette and type (`DESIGN.md` §6). Don't redesign it toward a different direction.
- Verify the analysis, thresholds, coverage window, sources, and every factual claim that will be
  printed.
- Add or update tests for reusable data or analysis behavior.
- Explain the analytical, production-path, and visual choices in plain language.

Two rules govern the iteration loop, and this is the stage where both bite:

- **Save every render you show the user** — `AGENTS.md` default 4. Saving is part of showing, not a
  later batch: run `scripts/save_visual_version.py --project <slug>` before the render goes out.
  Prune the ones that turned out to be adjustments before the post's single commit.
- **Know when to stop** — `POSTING_WORKFLOW.md` caps presentation-only rounds at three.

Don't prepare promotional copy — `promote-bulls-post` owns that stage.

## After Approval

1. Produce the final artifact: the downloaded 1080×1350 Canva page(s).
2. **Inspect the actual downloaded files.** Run the checks in `POSTING_WORKFLOW.md` — approving the
   editable Canva design or the chart asset alone is the recurring failure here.
3. Save every approved final page with
   `scripts/save_visual_version.py --project <slug> --final` — it joins the post's single commit,
   made once at the end (`AGENTS.md` default 4). Update the Notion page to `Mocked`.
4. Update the post's Notion page: the working detail, and the **data provenance** section defined in
   `DEVELOPMENT.md` — where the numbers came from and how a raw record becomes the published figure.
   Write it without being asked; the user should not have to request the trail back to a finding.
5. Run the relevant tests and `git diff --check`.
6. Update any owner document whose decision changed.
7. Summarize the result, verification, risks, and changed files.

Never mark a post `Posted` until the user confirms it's live.

Then offer — don't assume — continuing into `promote-bulls-post` in the same session so it inherits
the settled context.
