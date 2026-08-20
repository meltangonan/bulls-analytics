# Posting Workflow

How a Bulls analysis becomes an Instagram post. `STRATEGY.md` owns what's worth posting;
`DESIGN.md` owns how it looks and sounds; this document owns the production and fairness checks.

## The Brief

Before building, the brief needs a state for each area below — answered by the user, inferred from
the Notion page or conversation, filled with a stated default, or explicitly deferred as
not-yet-relevant. Then restate it and let the user correct it.

1. **Objective** — the basketball question and why a Bulls fan should care.
2. **Analytical scope** — team or player, timeframe, metrics, filters, sample.
3. **Comparison logic** — the baseline, peers, eras, or before/after framing that gives the number
   meaning. A number without a comparison is not a post.
4. **Evidence and qualifications** — sources, thresholds, uncertainty, and what the data can
   actually support.
5. **Visual communication** — chart form, information hierarchy, annotations, and what the Canva
   page needs to say around the chart (title, subtitle, footnotes).
6. **Deliverable** — feed or carousel, and what counts as an approved draft.

Default to a 1080×1350 feed page when nothing else is implied.

## Data & Fairness Guardrails

- **Name the coverage window.** Say “since 2000” or “shot-location era” when the source does not
  cover full franchise history.
- **Adjust when eras distort the comparison.** Use pace, league efficiency, role, or opportunity
  context when raw totals would reward the environment more than the player.
- **Normalize financial comparisons.** Prefer salary-cap share, payroll share, or same-season
  context over nominal dollars across decades.
- **Show the qualification rule.** Keep minimum games, minutes, possessions, attempts, or seasons
  visible on the graphic.
- **Expose important metric components.** A named composite can help, but readers should see its
  inputs and not mistake editorial weighting for objective truth.
- **Keep sources and dates attached.** Posts should remain auditable after the season changes and
  the graphic recirculates.

## How a Post Gets Built

**Python builds the chart; Canva builds the page.** Python owns verified calculations, display-ready
content, and a transparent chart asset (see `DESIGN.md` §3 for the export contract). Canva owns the
`#FAF8F5` page, all typography, and editorial copy.

**Preserve the original during Canva iteration.** When making substantive edits to an existing
design, work in a clearly labeled separate QA copy or on duplicated draft pages by default. Do not
overwrite the user's original pages or design unless they explicitly ask to promote the approved
draft into it. The user should not need to request this isolation on each revision.

The approved artifact is the **downloaded 1080×1350 page** — never the editable Canva design or the
chart asset alone.

Prototypes print a Canva copy block with the exact strings to paste, so page numbers and chart
numbers come from the same run. Never retype a value from a chart into Canva by eye.

The Python full-layout system (`house.draw_header` and friends) is legacy — maintain existing
prototypes on it, don't start new posts there.

**Know when the chart is done.** Three consecutive rounds that change only presentation — spacing,
label placement, color, crop — mean the analysis is settled. Say so and ask whether to ship instead
of opening a fourth. Polish is Canva's job: a chart asset carries no page furniture by contract
(`DESIGN.md` §3), so presentation rounds in Python are usually redone by the layout surface anyway.
Rounds that change what the chart *claims* are not polish and are not capped.

## Before Calling a Draft Approved

- Every annotation, title, and subtitle is accurate, legible, and approved or redlined.
- Event lines appear only where they explain a bend in the data, with verified dates.
- Fan voice matches the settled amount for this post.
- Posting copy is either saved on the Notion page or the user has chosen to write it.

**Verify every fact printed on a graphic** — dates, picks, trades, injuries, records. Web-search
anything past the model's knowledge cutoff. Never draw a guessed date.

**Check the downloaded pages, not the Canva design:**

- every page is exactly 1080×1350 on the `#FAF8F5` canvas;
- charts aren't cropped and labels stay readable at feed size;
- typography is the Brand Kit set — Clarendon Narrow title, Yearbook Solid headers, Helvetica Bold
  body;
- thresholds, coverage, sources, attribution, names, dates, and handles match the latest Python
  output;
- no placeholder, duplicate frame, draft note, or previous-post copy survived.

Canva-rendered text is judged from the downloaded page at feed size — DPI metadata does not improve
it. Fix resolution problems by exporting a larger source asset.

## After Approval

1. Save the actual final page or carousel pages with
   `scripts/save_visual_version.py --project <slug> --final` and commit them. They land in
   `docs/visuals/YYYY-MM-DD-<slug>/final/`, beside the `assets/` versions that produced them. You have
   already exported the page for the QA checks above, so this is the same file.
2. Update the Notion page to `Mocked` and save the approved caption (or note the user supplies it).
3. After the user confirms it is live, update the page to `Posted`. Never infer that a post is live.

Card lifecycle: `Parked` → `Mocked` → `Posted`. `Generated` is legacy, pre-playbook terminology.

## Hashtags

Always provide a ready-to-paste block (user rule, 2026-07-18), built from three parts:

1. **Standing reach set, every post:** `#chicagobulls #bulls #nba #nbastats #dataviz #analytics`,
   plus a seasonal tag only while the post's own subject is in that season (`#summerleague`). Never
   carry a seasonal tag past the window it describes.
2. **One tag per featured player worth tagging.** Draft with every player in the final graphic and
   expect the user to cut the low-reach names — searched-for players earn the tag, deep-bench names
   dilute it (confirmed 2026-07-24, after the scoring landscape shipped without Claxton, Okoro,
   Miller, and Dillingham).
3. **Deliberate reach tags the user designates**, allowed even when the player isn't in the post —
   currently `#calebwilson`, the roster's most popular player.

**Check the block against the actual final caption immediately before posting**, not against an
earlier draft, and never reuse a prior block unchanged. This guards against accidental carryover:
`#matas` rode into two Summer League reports despite Matas appearing in neither carousel. A
deliberate reach tag is fine; anything else tagging an absent player is not.

## "I need to post but have no idea"

Offer 2–3 concrete candidates with one-line pitches, preferring in order:

1. Parked Notion ideas with data ready today.
2. Timely hooks: the latest game, roster news, dates, or anniversaries.
3. A new brainstorm only when no existing Notion idea fits.

Don't invent a new format when a Parked card already fits.

## Season Rollover

At the start of a new NBA season, update `CURRENT_SEASON` and `LAST_SEASON` in `bulls/config.py`.
Fetchers otherwise keep serving the previous season's frozen data with no error.
