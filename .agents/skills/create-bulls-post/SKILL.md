---
name: create-bulls-post
description: Turn a selected Chicago Bulls post idea into a clarified brief, tested analysis, and reviewable graphic. Use when the user wants to create, mock up, build, or develop a specific @chicagobullsdata post, including an existing idea-catalog card. Do not use for loose ideation, promotion of an approved post, or post-performance review.
---

# Create Bulls Post

Move one selected idea from intent to an approved visual without making the user repeat settled context.

## Load Project Context

1. Read `AGENTS.md`, `DESIGN.md`, and `POSTING_WORKFLOW.md`.
2. Read the matching card in `idea-catalog.html` when the idea already exists.
3. Read the relevant sections of `bulls-content-playbook.html` when the editorial angle or fairness standard is unclear.
4. Read `DEVELOPMENT.md` before changing analysis, fetchers, graphics code, scripts, or tests.

Treat these files and the current conversation as the source of truth. Do not duplicate their rules in a separate planning artifact.

## Complete the Brief

Use the six-area Clarification Gate in `POSTING_WORKFLOW.md` as an internal coverage check. For each area, determine whether it is:

- answered by the user;
- inferred from the conversation, catalog, or project documents;
- filled with a recommended project-consistent default; or
- explicitly deferred because it does not affect the first draft.

Ask only about blocking gaps. Ask one focused question at a time, use the runtime's question tool for clear choices when available, and explain the recommended option and meaningful tradeoff. Use normal conversation for nuanced questions. Never ask the user to repeat a settled decision.

If the user says “pick for me,” make the choice and state it plainly. For an existing catalog card, run an abbreviated gate covering only what remains open.

Do not begin implementation while a blocking area is unresolved. When coverage is complete, restate the settled brief in 3–6 bullets and give the user a chance to correct it.

## Build One Draft

Follow the prototype-first workflow in `POSTING_WORKFLOW.md` and `DEVELOPMENT.md`.

- Reuse the established design system and existing helpers before creating a new visual grammar.
- Verify the analysis, thresholds, coverage window, sources, and any current factual claims.
- Add or update tests for reusable data or analysis behavior.
- Generate one reviewable draft and explain the important analytical and visual choices in plain language.
- Update the affected owner documents and catalog card as decisions change; revise stale guidance instead of appending duplicates.

Do not prepare promotional copy unless the user asks for it; `promote-bulls-post` owns that stage.

## Refine to the Exit Criteria

Use the Draft Refinement Gate in `POSTING_WORKFLOW.md` as a coverage check, not a fixed series of rounds. Review only what changed or remains unresolved and ask for a decision only when one is needed.

After the user approves the post:

1. Produce the final 300 DPI export.
2. Copy the approved graphic to `docs/mocks/`.
3. Update the matching catalog card to `Mocked` and preserve its supporting context.
4. Run the relevant tests and `git diff --check`.
5. Summarize the practical result, verification, risks, and all changed files.
6. Stop for explicit approval before committing or pushing.

Never mark a post `Posted` until the user confirms it is live. Never publish or interact with Instagram without explicit per-action approval.
