# Bulls Analytics Post Skills Handoff

**Status: CLOSED — implemented and committed 2026-07-10**

## Outcome

The repository now has three small skills covering the recurring post lifecycle:

1. `create-bulls-post` — clarify, build, and refine one selected post.
2. `promote-bulls-post` — prepare an approved post for manual release.
3. `review-bulls-post` — turn feedback and results into durable project learning.

Canonical skill files live under `.agents/skills/`. Claude Code discovers the same implementations
through one-way `SKILL.md` symlinks under `.claude/skills/`; there are no copied skill bodies.

## Durable Pointers

- `AGENTS.md` — skill routing, owner-document maintenance, and approval defaults.
- `POSTING_WORKFLOW.md` — creation, promotion, and review behavior.
- `DESIGN.md` — visual and caption-voice rules.
- `STRATEGY.md` — audience, success measures, and evidence-aware learning.
- `.agents/skills/<skill-name>/SKILL.md` — canonical recurring workflows.

The skills and shared workflow were committed in `56ca895`. Their folders passed structural
validation and the full repository suite passed at close. Live Claude execution was not tested in
that session because its CLI was logged out; the one-way symlink structure itself was verified.

There is no remaining implementation work in this handoff. Future skill changes belong directly in
the canonical skill and its affected owner documents.
