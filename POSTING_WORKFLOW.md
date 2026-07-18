# Posting Workflow

The operating guide for turning Bulls analysis into an Instagram post. Read this before creating,
revising, or preparing a visual post. For the account's purpose, read `STRATEGY.md`; for its visual
system, read `DESIGN.md`; for the editorial north star and fairness principles, read
`bulls-content-playbook.html`.

## Core Rules

- Work one post idea at a time: clarify it, mock it, then stop for feedback.
- Prefer boards, tables, grids, and shared-scale comparisons. Use a court only when location is the
  actual question.
- Keep applicable qualification thresholds, coverage windows, and sources visible on every graphic.
- The user posts manually. Never post, comment, like, follow, or change account settings without
  explicit per-action approval.

## Clarification Gate

Before creating a new visual, complete the brief below. Treat it as an internal completeness check,
not a fixed questionnaire. Use the conversation, catalog card, and project documents as already-settled
context; ask one focused question at a time only for decisions that remain unresolved. Use the runtime's
question tool for clear choices when available and normal conversation for nuanced questions.

1. **Objective** — the basketball question, intended insight, and why a Bulls fan should care.
2. **Analytical scope** — team or player, timeframe, metrics, filters, and sample.
3. **Comparison logic** — the baseline, peers, eras, or before/after framing that gives the number meaning.
4. **Evidence and qualifications** — sources, thresholds, uncertainty, fairness, and what the data can support.
5. **Visual communication** — visual form, information hierarchy, title, annotations, required
   footnotes, and the canvas theme. Always ask which canvas theme the post uses (jersey default,
   white, newsprint, blackout, or hardwood — DESIGN.md §2) unless the user already chose one
   for this post; recommend jersey and note when the story argues for an alternate.
6. **Deliverable** — feed or carousel format, prototype expectations, and what constitutes an approved draft.

Every area must be answered by the user, inferred from existing context, filled with a recommended default,
or explicitly deferred because it does not affect the first draft. If the user says “pick for me,” choose a
reasonable project-consistent default; use a 1080×1350 feed PNG when no other output format is implied.
Once every area has a state, restate the settled brief in 3–6 bullets and give the user a chance to correct it
before making data or analysis changes, adding tests, and generating the draft.

## Prepare, Then Render

For a data-heavy repeat format, convert fetched/validated data into display-ready post content before
drawing: the chosen claim, labels, supporting metrics, image paths, shot marks, and qualifications.
Renderers should consume that prepared content rather than fetch data or interpret raw NBA API columns.
This keeps analytical truth and visual composition independently testable without forcing every post into
one schema. Simple one-off prototypes can stay direct when a preparation layer would add ceremony without
clarity.

New Matplotlib posts use `bulls.graphics.house` for the shared canvas, fonts, header/footer, and
draft/final export behavior.

## Draft Refinement Gate

Once a draft exists, cover the checks below before calling it approved. They are exit criteria, not six
mandatory conversational rounds: review only what changed or remains unresolved, in the order that best fits
the draft, and ask one focused question when a user decision is actually needed.

- **Voice** — annotations match the settled amount of fan voice.
- **Event lines** — a real-world marker appears only when it explains the data; its date is verified.
- **Copy deck** — every annotation is accurate, concise, and approved or redlined.
- **Title and subtitle** — both are accurate, legible, and approved.
- **Posting copy** — either approved copy is saved with the catalog card or the user has chosen to write it.
- **Render** — drafts iterate at 150 DPI; the approved post exports at 300 DPI using the prototype's
  `--final` pattern when available.

### Fact and Image Rules

- Verify every fact printed on a graphic—dates, picks, trades, injuries, and similar claims. Search
  the web for facts past the model's knowledge cutoff; never use a guessed date.
- NBA CDN headshots for new rookies can be gray silhouettes. Check the image visually: a roughly
  12 KB file is usually a silhouette, while a real headshot is commonly 50–200 KB.
- When needed, use an unwatermarked team-CDN image, crop it square around the face for the circular
  helper, and flag wire-photo licensing before using a non-NBA source.

## Session Entry Points

### “I want to post X from the catalog.”

Open the card in `idea-catalog.html` and treat it as a pre-filled brief. Run an abbreviated
clarification gate: ask only about fields the card leaves open, usually timeframe and exact
title/subtitle/footnote copy. Refresh data, run or adapt the prototype, render at 300 DPI, and
iterate with the user.

When the user approves a post for publishing:

1. Copy the final PNG to `docs/mocks/`.
2. Update the catalog card to `Mocked`.
3. Add the approved caption or note that the user is supplying it. Add hashtags only when requested.

After the user confirms it is live, update the card to `Posted`.

## Promotion and Distribution

Base final posting copy on the approved graphic and its underlying analysis. Prefer simple, direct,
basketball-literate language; a plain factual caption is a valid result. Do not force a hook, humor, fan slang,
rhetorical questions, or engagement bait. Preserve material qualifiers and verify any current fact before use.

Durable caption rules (user-confirmed 2026-07-11, after the account's first two published data-viz posts):

- **The user writes the caption.** Offer at most one short line as raw material — never a
  multi-sentence draft. The first two data-viz posts both used the user's own one-liner plus hashtags.
- **Always provide a ready-to-paste hashtag block** (user rule, 2026-07-18). Build it as:
  1. The standing generic reach set, on every post: `#chicagobulls #bulls #nba #nbastats #dataviz`,
     plus the seasonal context tag when one applies (currently `#summerleague`).
  2. One tag per player featured in the final graphic.
  3. Deliberate reach tags the user designates, allowed even when the player is not in the post —
     currently `#calebwilson`, as the roster's most popular player.
- **Verify hashtags and named players against the posted content.** Run this check on the actual
  final caption immediately before posting, not only on an earlier draft, and do not reuse a prior
  hashtag block unchanged. The check guards against *accidental* carryover — `#matas` rode into two
  Summer League reports despite Matas not appearing in either carousel. A deliberate reach tag from
  the rule above is not a violation; anything else tagging an absent player is.

Provide caption help, alt text, hashtags, Story copy, or distribution guidance only when useful or requested.
Keep distribution guidance to a few post-specific actions grounded in the actual subject and relevant Bulls
community; do not produce a generic engagement checklist. Draft and advise only. The user publishes and
interacts manually unless they give explicit per-action approval.

## Post Review and Learning

A review may use creative feedback alone or combine it with the final graphic, actual caption, audience
response, and Instagram Insights. Ask for the most important missing feedback or evidence rather than requiring
every input. Classify each lesson as:

- **Observation** — something seen in one post or session.
- **Working hypothesis** — a possible pattern to surface to the user and watch in later work.
- **Durable rule** — an explicitly stated user preference, a user-confirmed hypothesis, or a pattern supported
  by repeated evidence.

Record post-specific evidence compactly on the catalog card. Surface hypotheses to the user for confirmation;
do not silently turn a single performance result into a rule. Route confirmed durable knowledge to its owner
document: visual and voice decisions to `DESIGN.md`, production behavior to this file, strategy and distribution
principles to `STRATEGY.md`, and clear new post ideas to `idea-catalog.html`. Revise stale guidance rather than
appending duplicate history.

### “I have a new idea / question.”

Run the full clarification gate, then follow the prototype-first flow: create one script under
`scripts/prototypes/`, write the PNG to `output/feed/`, and add a card to `idea-catalog.html`.

### “I have no ideas but need to post.”

Offer 2–3 concrete candidates as a short reaction round. Prefer, in order:

1. Parked catalog cards with data ready today.
2. Guided Idea Bank lanes in `bulls-content-playbook.html`.
3. Timely opportunities: the latest game, roster news, dates, or anniversaries.

Give each candidate a one-line pitch. Once the user picks one, continue through the matching flow
above. Do not invent a new format when a Parked card already fits.

## Catalog and Season Maintenance

- Card lifecycle: `Parked` → `Mocked` → `Posted`. `Generated` is legacy, pre-playbook terminology.
- Keep applicable qualification thresholds, coverage windows, and sources visible regardless of entry point.
- At the start of a new NBA season, update `CURRENT_SEASON` and `LAST_SEASON` in `bulls/config.py`.
  Fetchers otherwise keep serving the previous season's frozen data.
