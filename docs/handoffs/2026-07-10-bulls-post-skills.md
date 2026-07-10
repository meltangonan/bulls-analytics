# Bulls Analytics Post Skills Handoff

Created: 2026-07-10
Updated: 2026-07-10

## Objective

Build three small, repo-scoped skills that cover the recurring post lifecycle without duplicating the
repository's owner documents:

1. `create-bulls-post` — clarify, build, and refine one selected post.
2. `promote-bulls-post` — prepare an approved post and offer restrained, post-specific distribution advice.
3. `review-bulls-post` — turn creative feedback and performance evidence into compounding project knowledge.

## Decisions

- Keep loose idea exploration in the global `brainstorming` skill. The creation skill begins only after a
  direction is selected and the user wants to make it.
- Use `.agents/skills/` at the repository root, the documented Codex location for checked-in repo skills.
- Keep `.agents/skills/` canonical and expose each `SKILL.md` to Claude Code through a relative symlink inside
  the matching `.claude/skills/<skill-name>/` discovery directory; never maintain copied implementations.
- Keep all three skills instruction-only. The repository already owns the scripts, data, graphics helpers,
  and tests they route into.
- Make the creation gate exhaustive but adaptive: cover all six areas in `POSTING_WORKFLOW.md`, ask only about
  unresolved decisions, and treat the post-draft checks as exit criteria rather than six mandatory rounds.
- Use simple, direct, basketball-literate caption language. Do not force hooks, humor, slang, rhetorical
  questions, novelty, or engagement bait. The user's voice is primary.
- Keep distribution recommendations optional, limited to 1–3 actions, and specific to the actual post.
- Classify review learning as observation, working hypothesis, or durable rule. Explicit user preferences are
  durable immediately; performance-derived conclusions remain hypotheses until confirmed or repeated.
- Update affected owner documents automatically as part of completing work, while revising stale guidance and
  avoiding duplicate history.
- Work on local `main`, but wait for explicit user approval before both committing and pushing.
- Never post, comment, like, follow, message, or change Instagram settings without explicit per-action approval.

## Implemented Files

- `.agents/skills/create-bulls-post/`
- `.agents/skills/promote-bulls-post/`
- `.agents/skills/review-bulls-post/`
- `.claude/skills/` — Claude Code discovery wrappers linked to the three canonical skill entrypoints.
- `POSTING_WORKFLOW.md` — clarification, refinement, promotion, and learning behavior.
- `DESIGN.md` — durable caption-voice rule.
- `STRATEGY.md` — evidence-aware learning loop and distribution boundary.
- `AGENTS.md` — skill routing, automatic owner-document maintenance, hypothesis handling, and git approval gate.
- `README.md` — repo-scoped skill location in the project map.

The skills route into `DESIGN.md`, `POSTING_WORKFLOW.md`, `STRATEGY.md`, `DEVELOPMENT.md`,
`bulls-content-playbook.html`, and `idea-catalog.html` instead of restating those documents.

## Verification

- All three skill folders pass the skill creator's `quick_validate.py` structural check.
- Each `.claude/skills/<skill-name>/SKILL.md` resolves through a one-way relative symlink to the
  canonical `.agents/skills/<skill-name>/SKILL.md`; no skill implementation is duplicated.
- Claude Code command lookup no longer reports the linked skill as unknown. A full live invocation remains
  unverified because the installed Claude CLI is not logged in.
- `create-bulls-post` passed independent clarification tests for a vague new idea and a partially settled
  catalog idea.
- `promote-bulls-post` passed an independent test that produced simple copy and restrained distribution advice
  for “The Shape of the Season.”
- `review-bulls-post` passed an independent test that separated a strong one-post result from an unproven causal
  hypothesis and requested the missing reach comparison.
- The full repository suite passes: `129 passed` via `./run_tests.sh`.
- `git diff --check` passes.

## Current State

The implementation is local, verified, and uncommitted. Present the diff to the user and wait for explicit
approval before committing or pushing to `main`.
