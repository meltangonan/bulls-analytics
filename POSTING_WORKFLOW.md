# Posting Workflow

The operating guide for turning Bulls analysis into an Instagram post. Read this before creating,
revising, or preparing a visual post. For the account's purpose, read `STRATEGY.md`; for its visual
system, read `DESIGN.md`; for the editorial north star and fairness principles, read
`bulls-content-playbook.html`.

## Core Rules

- Work one post idea at a time: clarify it, mock it, then stop for feedback.
- Prefer boards, tables, grids, and shared-scale comparisons. Use a court only when location is the
  actual question.
- Keep qualification thresholds, coverage windows, and sources visible on every graphic.
- The user posts manually. Never post, comment, like, follow, or change account settings without
  explicit per-action approval.

## Clarification Gate

Before creating a new visual, clarify the request. Ask one focused question at a time; use the
runtime's question tool when available. Do not start implementation until these fields are clear:

- `insight_goal` — what the post should prove
- `scope` — team/player and season or last-N-games window
- `visual_type` — chart or card style
- `style_direction` — clean, bold, editorial, and so on
- `output_text` — exact title, subtitle, and footnote copy

If the user says “pick for me,” default to a 1080×1350 Instagram-feed PNG. Once the brief is clear,
restate it in 3–6 bullets, then make any data or analysis changes, add tests, and generate the draft.

## Draft Refinement Gate

Once a draft exists, work through these rounds in order. Each round is one focused question:

1. **Voice dial** — set the amount of fan voice for every annotation.
2. **Event lines** — add a real-world marker only when it explains a bend in the data; verify the
   date before drawing it.
3. **Copy deck** — show each annotation as a before→after table and get approval or redlines.
4. **Title and subtitle** — confirm or revise them.
5. **Caption and hashtags** — add a copy-paste block to the catalog card unless the user provides it.
6. **Render** — iterate at 150 DPI, then export the approved post at 300 DPI using the prototype's
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
3. Add a copy-paste caption and hashtag block.

After the user confirms it is live, update the card to `Posted`.

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
- Keep the thresholds and sources visible regardless of entry point.
- At the start of a new NBA season, update `CURRENT_SEASON` and `LAST_SEASON` in `bulls/config.py`.
  Fetchers otherwise keep serving the previous season's frozen data.
