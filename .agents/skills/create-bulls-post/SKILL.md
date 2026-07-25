---
name: create-bulls-post
description: Turn a selected Chicago Bulls post idea into a clarified brief, tested analysis, and reviewable graphic. Use when the user wants to create, mock up, build, or develop a specific @chicagobullsdata post, including an existing idea-catalog card. Do not use for loose ideation, promotion of an approved post, or post-performance review.
---

# Create Bulls Post

Move one selected idea from intent to an approved visual without making the user repeat settled
context.

## Context

Read `AGENTS.md`, `DESIGN.md`, and `POSTING_WORKFLOW.md`. Read the matching card in
`idea-catalog.html` when the idea already exists, `bulls-content-playbook.html` when the editorial
angle or fairness standard is unclear, and `DEVELOPMENT.md` before touching analysis, fetchers,
graphics code, or tests.

These files and the conversation are the source of truth. Don't restate their rules in a separate
planning artifact.

## Brief

Cover the six areas in `POSTING_WORKFLOW.md`, then restate the settled brief so the user can correct
it. Ask only about gaps that block the first draft; for an existing catalog card, that's usually just
timeframe and exact title/subtitle/footnote copy. Never ask the user to re-decide
something already settled.

If the user says "pick for me," choose and state the choice plainly.

## One Draft

Build a single reviewable draft, not a set of options. Python builds the **chart**; the Canva page
carries the title, headers, and framing.

- Reuse the established design system and existing helpers before inventing a new visual grammar.
- When working from an F5 or similar tutorial, reproduce its styling and structure closely and swap
  in our palette and type (`DESIGN.md` §6). Don't redesign it toward a different direction.
- Verify the analysis, thresholds, coverage window, sources, and every factual claim that will be
  printed.
- Add or update tests for reusable data or analysis behavior.
- Explain the analytical, production-path, and visual choices in plain language.

Don't prepare promotional copy — `promote-bulls-post` owns that stage.

## After Approval

1. Produce the final artifact: the downloaded 1080×1350 Canva page(s).
2. **Inspect the actual downloaded files.** Run the checks in `POSTING_WORKFLOW.md` — approving the
   editable Canva design or the chart asset alone is the recurring failure here.
3. Copy every approved final page to `docs/mocks/` and update the catalog card to `Mocked`.
4. Run the relevant tests and `git diff --check`.
5. Update any owner document whose decision changed.
6. Summarize the result, verification, risks, and changed files.

Never mark a post `Posted` until the user confirms it's live.

Then offer — don't assume — continuing into `promote-bulls-post` in the same session so it inherits
the settled context.
