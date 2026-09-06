---
name: create-bulls-post
description: Build or revise a selected Bulls post's verified graphic for user review; assemble or review Canva pages when requested.
---

# Create Bulls Post

Use the settled conversation and matching Notion post. Read `DESIGN.md` for a chart change and only
the relevant family/helper; consult `DEVELOPMENT.md` for code or verification. `POSTING_WORKFLOW.md`
owns production and status. Don't load every guide or repeat a settled brief for a small adjustment.

Resolve only missing scope, comparison, qualification, visual form or deliverable decisions that
materially change the first draft. For a new editorial choice, consult Notion editorial direction
(linked in `STRATEGY.md`). Loose ideation stays conversational until a concept is chosen.

Reuse the established chart family and shared table/card/portrait elements. Python owns calculations,
selection, labels and chart assets; Canva owns the composed page. Keep substantial preparation
separate from rendering so visual iterations reuse verified data. Verify printed claims and source
coverage, and save the source/reconciliation/selection tables with the post.

Before showing each render, save it with `scripts/save_visual_version.py --project <slug> <files>`.
Complete the user's requested adjustments; stop inventing polish when the brief is satisfied.
Run only affected checks, repeating them when relevant code or data changes.

Deliver the inspected, saved graphic for user review and approval. Follow `POSTING_WORKFLOW.md`
for the Canva handoff and recent-Posted page references; Canva work is a separate requested stage.
Keep Notion's brief and provenance current. Use `Mocked` only after design approval;
`Posted` requires live-publication confirmation. Record sources using `docs/reference/provenance.md`.

Summarize the result, verification and meaningful limitations. Commit/push need explicit approval
per `AGENTS.md`. Continue into promotion when requested; don't generate unsolicited posting copy.
