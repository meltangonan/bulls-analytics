# Bulls Analytics Post Skills Handoff

Created: 2026-07-10

## Objective

Create two small, repo-scoped skills for the Bulls Analytics project:

1. A clarification-gate skill for turning a selected post idea into a clear mockup brief.
2. A promotion skill for turning an approved Bulls analysis or graphic into accurate, on-brand posting copy.

Do not put Bulls-specific behavior in the global `promote` or `brainstorming` skills. Keep the Bulls workflow close to the repository and its source documents.

## Decisions Already Made

- Keep early idea exploration in the global lightweight `brainstorming` skill.
- Trigger the clarification skill only when the user wants to mock, create, or develop a specific Bulls post.
- Keep clarification and promotion as separate skills because they operate at different moments and need different context.
- Treat the repository documents as the source of truth. Skills should route into them rather than duplicate a second full rulebook.
- Keep both skills conversational and narrow. No subagents, formal research pipelines, saved planning artifacts, or automatic next-step menus.
- Never post, comment, like, follow, or change Instagram settings without explicit per-action approval.

## Current Global Skill State

- The global `brainstorming` skill now handles both quick idea generation and collaborative exploration. It stays conversational and creates no artifact by default.
- The global `promote` skill is intentionally universal. It adapts to project guidance but contains no Bulls-specific rules.
- The global `strategy` skill maintains rigorous, gap-aware `STRATEGY.md` documents. The Bulls-specific skills should read the existing account strategy rather than recreate it.
- The global `handoff` skill is available for transferring the next session, but neither Bulls skill should generate handoffs as part of its normal workflow.

## Project Sources to Read

- `AGENTS.md` — repository map and durable defaults.
- `STRATEGY.md` — account purpose, audience, success signals, priorities, boundaries, and marketing direction.
- `DESIGN.md` — established visual system; do not re-litigate it for each post.
- `POSTING_WORKFLOW.md` — clarification fields, draft refinement, fact rules, catalog workflow, and publishing boundaries.
- `bulls-content-playbook.html` — editorial north star and fairness guidance.
- `idea-catalog.html` — existing post ideas and pre-filled context.

## Skill 1: Bulls Post Brief

Working name: `bulls-post-brief`.

Trigger when the user says things such as:

- “Let’s mock up this Bulls post.”
- “Turn this idea into a graphic.”
- “Let’s build the post from the catalog.”

Expected behavior:

- Read `DESIGN.md` and the relevant parts of `POSTING_WORKFLOW.md` before starting the mockup.
- Use the conversation and catalog card as already-settled context. Do not ask the user to repeat decisions.
- Ask only for important missing clarification, one focused question at a time.
- Cover the clarification gate’s intent: what the post should show, scope/timeframe, suitable visual form, any post-specific style direction, and necessary on-graphic text.
- Treat those fields as a coverage check, not five mandatory questions. Infer settled answers from context and combine or skip questions when no decision remains.
- If the user says “pick for me,” choose reasonable defaults consistent with the project instead of forcing an answer.
- For an existing catalog card, use the abbreviated gate and ask only about fields that remain open.
- Restate the settled brief in a few bullets, then proceed into the normal prototype-first project workflow.
- Do not trigger during loose ideation. Brainstorming ends when the user selects a direction; this skill begins when they want to make it.

## Skill 2: Bulls Post Promotion

Working name: `bulls-post-promote`.

Trigger when a Bulls analysis, mock, or approved graphic exists and the user asks for a caption, hashtags, posting copy, or help preparing it for Instagram.

Expected behavior:

- Read the actual graphic, analysis, catalog card, and relevant project guidance rather than drafting from a generic summary.
- Lead with the real basketball finding or question.
- Preserve important qualifications such as season, timeframe, sample, threshold, and comparison basis.
- Verify current statistics, roster facts, dates, transactions, injuries, or news before using them.
- Use a natural Bulls-aware voice with restrained fan energy. Do not manufacture certainty, outrage, controversy, or hype.
- Produce one strong Instagram caption by default. Include a small relevant hashtag block when the user asks or the project workflow requires it.
- Stay focused on Instagram posting copy. Do not create a cross-channel campaign unless the user explicitly asks.
- Draft only. Never publish or interact with the account.

If the skill is later allowed to update `idea-catalog.html`, preserve the current lifecycle exactly: `Parked` → `Mocked` only after approval; `Posted` only after the user confirms the post is live. Never infer that publishing occurred.

## Workflow Boundary

```text
Explore possibilities
    -> global brainstorming
Choose a post and start making it
    -> bulls-post-brief
Build and refine the graphic
    -> repository posting workflow
Prepare approved work for Instagram
    -> bulls-post-promote
User publishes manually
```

## Open Decisions for the Next Session

- Verify the supported repo-scoped skill directory and discovery behavior before creating either skill.
- Confirm the final skill names.
- Decide whether `bulls-post-promote` only drafts copy or may also update the catalog card when explicitly requested.
- Decide whether the caption should be drafted only after visual approval or may be developed alongside late-stage refinement.
- Decide whether `AGENTS.md` should explicitly route mockup and caption requests to the new skills.
- Reconcile the current six-round Draft Refinement Gate in `POSTING_WORKFLOW.md` with the low-ceremony intent. The new skills should not force six separate rounds when decisions are already settled, but changing the authoritative workflow should be explicit rather than silently contradicted.

## Suggested Next Session

1. Use the global `skill-creator` guidance and verify the repo-scoped skill location.
2. Create and validate `bulls-post-brief` first.
3. Test it against one new idea and one existing catalog card.
4. Create and validate `bulls-post-promote` second.
5. Test it against an approved graphic with known qualifiers and a current fact that requires verification.
6. Update the repository routing documentation only after the skill behavior is settled.
