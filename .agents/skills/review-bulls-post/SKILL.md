---
name: review-bulls-post
description: Review creative feedback, a published Bulls post, its actual caption, or Instagram Insights and carry the learning into future @chicagobullsdata work. Use when the user wants to debrief a mock or post, explain performance, incorporate feedback, identify hypotheses, or compound project knowledge. Do not use to create or promote the post.
---

# Review Bulls Post

Turn feedback and results into current, compact, reusable project knowledge rather than a one-off conversation.

## Reconstruct the Evidence

1. Read `AGENTS.md`, the Post Review and Learning section of `POSTING_WORKFLOW.md`, and `STRATEGY.md`.
2. Inspect the actual final graphic, actual caption, matching `idea-catalog.html` card, relevant
   analysis, and any available Insights or qualitative feedback. For Canva-composed work, use the
   downloaded pages preserved in `docs/mocks/`, not only the editable design or Python asset.
3. Read the relevant owner document before proposing a durable change: `DESIGN.md` for visual or voice decisions, `POSTING_WORKFLOW.md` for production behavior, and `STRATEGY.md` for audience, distribution, or success principles.
4. Compare with prior catalog evidence when it is relevant; do not rely on remembered performance or invent missing metrics.

A review can proceed without Insights. Ask for the most important missing feedback or evidence one focused question at a time; do not require a complete retrospective form.

## Classify Each Lesson

Use three evidence levels:

- **Observation** — something seen in one post or session. Record it as post-specific context.
- **Working hypothesis** — a plausible pattern worth watching. Explain the evidence and uncertainty, then bring it to the user for confirmation.
- **Durable rule** — an explicitly stated user preference, a hypothesis the user confirms, or a pattern supported by repeated evidence.

Treat explicit user preferences as durable immediately. Treat conclusions inferred from performance as hypotheses until the user confirms them or repeated evidence supports them.

If the user is unsure whether to confirm a hypothesis, give a recommendation and explain what evidence would strengthen or weaken it. Keep it as a hypothesis when uncertainty remains; do not force a decision.

## Update the System

Documentation maintenance is part of the review. Make the smallest set of updates that keeps the project current:

- Record post-specific feedback, results, and unresolved hypotheses compactly on the matching catalog card.
- Record whether the post was Python- or Canva-composed only when the production path materially
  affected accuracy, comprehension, effort, or results; renderer choice alone is not a performance lesson.
- Revise `DESIGN.md` for confirmed visual or voice rules.
- Revise `POSTING_WORKFLOW.md` for confirmed creation, approval, promotion, or review behavior.
- Revise `STRATEGY.md` for confirmed audience, metric, distribution, or strategic learning.
- Add a `Parked` catalog card only when the review reveals a clear, distinct future post idea.

Edit or replace stale guidance instead of appending duplicate rules. Do not create a transcript, a new knowledge file, or a long decision log merely because the skill ran. Preserve important contrary evidence so the project does not overfit to one post.

## Close the Review

Summarize:

1. what was observed;
2. which hypotheses need future evidence or user confirmation;
3. which durable rules changed;
4. which project files were updated; and
5. the clearest implication for the next post.

Run `git diff --check`. Never alter the catalog lifecycle without the required user confirmation, and stop for explicit approval before committing or pushing.
