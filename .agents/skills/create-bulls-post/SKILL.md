---
name: create-bulls-post
description: Build or revise a selected Bulls post, from its brief to verified chart assets and Canva review.
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

For a chart-only adjustment, deliver and inspect the saved chart asset; a Canva round-trip is
needed only when assembling or reviewing the composed page. A complete post draft includes the
inspected downloaded Canva page, preserved publish-resolution chart, and updated Notion
brief/provenance/Canva link. Use `Mocked` only after design approval;
`Posted` requires live-publication confirmation. The downloaded page is QA scratch; the archive
helper has no `--final` flag. Record source details using `docs/reference/provenance.md`.

Summarize the result, verification and meaningful limitations. Commit/push need explicit approval
per `AGENTS.md`. Continue into promotion when requested; don't generate unsolicited posting copy.
