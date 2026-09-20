# Posting workflow

[Notion editorial direction](https://www.notion.so/3d2e1c13abe681e586b4c44762261fab) owns what the
account says and who it serves. This file owns production, fairness and completion.

## Start or resume

Read the matching Notion post and use the settled conversation. Resolve only missing decisions:
basketball question, scope, comparison, evidence/qualification, visual form, and deliverable.
State reasonable defaults; ask only when the answer materially changes the result. Do not repeat
the brief for an already-scoped adjustment.

Choose an existing chart family from `DESIGN.md` and `scripts/prototypes/README.md`. One selected
idea gets one working post; loose brainstorming does not trigger fetching, artifacts, or Notion writes.

## Data and chart

Python owns calculations, selection, labels, and chart assets. Canva owns the page and its framing.
Keep the coverage window, qualification and source visible on each data-bearing composed page.
Use era, opportunity, pace or league context when the comparison needs it. Financial comparisons
need same-season/cap-share context; composite metrics need honest component definitions.

Verify every printed factual claim, including dates and roster membership. A source's structural
limits constrain the headline. `docs/reference/provenance.md` defines the source trail that belongs
on the Notion post; relevant endpoint traps are routed from `DEVELOPMENT.md`.

Render into `output/`, then save each image before showing it. Keep data-bound Canva copy from the
same calculation as the chart; never transcribe a value by eye. Reuse verified data during styling
changes. Run only the checks appropriate to the change (`DEVELOPMENT.md`).

Complete requested visual changes. If further self-directed polish has no clear benefit, present
the result instead of inventing another round. Spacing, cropping and label readability inside a
chart remain Python's responsibility; page layout belongs in Canva.

## Canva and approval

Default handoff: verified graphic → user review and approval → user assembles in Canva.
Create or edit a Canva page only when requested; selecting a post idea isn't graphic approval.
For Canva assembly, use a copy of a recent design in `Posted` as the starting point for page
typography, colors, spacing and framing. That reference does not determine the new chart type;
keep the graphic matched to the selected brief.

For substantive edits to an existing Canva design, use a separate QA copy or duplicated draft pages
unless the user authorizes edits to the original. When reviewing the composed page, inspect the
actual downloaded page at feed size:

- correct dimensions (1080×1440 or 1080×1350, matching what the page was built for), readable
  labels and no cropping;
- numbers, names, coverage, thresholds, source and handle agree with Python;
- no stale template copy, placeholders, duplicate frames or draft notes;
- printed components make sense together. Independently rounded components may not sum to a
  printed total; preserve true values and choose a clear note or presentation when needed.

The chart asset or editable design alone does not establish final-page approval. Keep the approved
publish-resolution chart in the post's `assets/`. The downloaded Canva page is temporary QA;
do not create a new `final/` archive. Older final-page archives remain historical records.

Before the logical post commit, prune saved versions that became cosmetic adjustments. Keep every
approved version and every change in metric, cohort, threshold, chart type, sorting or claim.
When uncertain, keep the asset. Commit and push only with explicit user approval.

## Notion record

Update the existing page as decisions land, without waiting for a separate documentation request.
Use these headings in order for a built post; ideas need only the sections supported so far:

- **Brief and final scope** — the question, coverage, comparison, qualification and final selection.
- **Results and decisions** — published findings, meaningful rejected approaches and why.
- **Data provenance** — the complete source trail in `docs/reference/provenance.md`, including
  the worked example, reconciliation, limitations and saved-file/renderer paths.
- **Publication** — Canva edit link in the `Canva` property; body holds the confirmed publication
  URL/date and approved caption, or notes that the user supplies it.

Use real headings, code blocks for calls/formulas, and tables where they clarify results. Preserve
useful existing detail when reorganizing; replace stale statements without reducing the page to a
status summary. Add feedback/results when available; don't create empty placeholder sections.

The live database currently supports `Not started`, `In progress`, `Parked`, `Mocked`, and `Posted`.
Use `In progress` for an active build; `Parked` for a paused idea with a reason; `Mocked` after a
verified approved design and a Notion source trail that meets
[provenance](docs/reference/provenance.md) for the final scope. On resuming a post, fetch its current
state rather than treating this list as proof of that post's state. Keep the Canva edit URL in the
`Canva` property.

Only mark `Posted` after the user confirms it is live. At publication closeout, check the whole
record against the final published scope and the provenance checklist, filling verified gaps.
Re-fetch after substantive updates to verify the body, formatting, links and properties, not just
the status. State any unresolved documentation gaps. A dropped concept gets its reason on the
same page; don't delete unique work until its disposition is established.

## Caption, distribution and review

Use the matching promote/review skill and the relevant section of Notion editorial direction.
Read current guidance when entering that stage; use context already loaded during ongoing edits.
Save the user's approved caption on the post, or note that they supply it. Never infer performance
or publication. Social actions remain subject to the per-action approval rule in `AGENTS.md`.
