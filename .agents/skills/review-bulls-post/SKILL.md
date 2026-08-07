---
name: review-bulls-post
description: Review creative feedback, a published Bulls post, its actual caption, or Instagram Insights and carry the learning into future @chicagobullsdata work. Use when the user wants to debrief a mock or post, explain performance, incorporate feedback, identify hypotheses, or compound project knowledge. Do not use to create or promote the post.
---

# Review Bulls Post

Turn feedback and results into compact reusable project knowledge rather than a one-off conversation.

## Evidence

Read `AGENTS.md` and `STRATEGY.md`. Inspect the actual final graphic, the actual caption, the
matching `idea-catalog.html` card, the relevant analysis, and any Insights or qualitative feedback.
For Canva work, use the published pages in the post folder's `final/`, and its `assets/` for the
chart versions that produced them, highest version number first
(`docs/mocks/` for posts predating 2026-08). Earlier versions in that folder show how the post
evolved, which is often what explains a piece of feedback.

A review can proceed without Insights. Never rely on remembered performance or invent missing
metrics. Compare against prior catalog evidence when it's relevant.

## Classify Each Lesson

- **Observation** — seen in one post or session. Record as post-specific context.
- **Working hypothesis** — a plausible pattern. Explain the evidence and the uncertainty, then bring
  it to the user.
- **Durable rule** — an explicitly stated user preference, a hypothesis the user confirms, or a
  pattern with repeated evidence behind it.

User preferences are durable immediately. Conclusions inferred from performance stay hypotheses until
confirmed. If the user is unsure, give a recommendation and say what evidence would strengthen or
weaken it — then leave it as a hypothesis rather than forcing a decision.

## Update the System

Make the smallest set of updates that keeps the project current:

- Post-specific feedback and results go compactly on the catalog card.
- Confirmed visual or voice rules → `DESIGN.md`. Confirmed production behavior →
  `POSTING_WORKFLOW.md`. Confirmed audience, metric, or distribution learning → `STRATEGY.md`.
- A clear, distinct future idea → a new `Parked` catalog card.

Note production mechanics (chart export, Canva assembly) only when they materially affected
accuracy, comprehension, effort, or results — tooling alone is not a performance lesson.

**Two failure modes to avoid:** don't create a transcript, a new knowledge file, or a decision log
merely because the skill ran; and preserve important contrary evidence so the project doesn't overfit
to a single post.

## Close

Say what was observed, which hypotheses still need evidence, which durable rules changed, which files
you updated, and the clearest implication for the next post. Run `git diff --check`.
