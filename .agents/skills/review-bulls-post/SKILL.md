---
name: review-bulls-post
description: Review Bulls creative feedback or published results and update the relevant post or confirmed guidance.
---

# Review Bulls Post

Use the actual graphic, caption, relevant Notion post and available feedback/Insights. A review can
proceed without Insights; don't invent missing metrics or infer remembered performance. Consult
Notion editorial direction (linked in `STRATEGY.md`) only when its principles affect the review.
Read analysis code when checking a data claim, not automatically for every piece of feedback.

Distinguish observed results, hypotheses about why they happened, and durable rules. Explicit user
preferences are durable; explanations inferred from one post remain hypotheses until confirmed or
supported repeatedly. Preserve contrary evidence and identify the missing evidence that would help.

Update the existing Notion post with its feedback and results. Editorial direction/voice lessons go
to Notion; reusable chart changes go to `DESIGN.md` or its family reference and the owning helper;
data/execution changes go to the relevant `DEVELOPMENT.md` reference. Replace stale guidance instead
of adding transcripts, separate decision logs or a rule for every incident.

Create a future idea only when the user selects it or asks to save it. Don't turn a review into
unrequested production. State what was observed, what remains uncertain, and what guidance changed.
Use `DEVELOPMENT.md` to select checks only if the review changed code; documentation changes need
relevant reference checks and `git diff --check`, not historical render tests.
