# Design System Page Enhancement Handoff

**Status: ACTIVE — ready to start in a fresh session**

## Task

Enhance and polish `design-system.html` (the rendered companion to DESIGN.md, rebuilt
2026-07-12 as hand-authored static HTML). The goal set by the user: eye candy and
distinctiveness without losing the page's job as a faithful spec — "make the page perform
its system, not just document it."

The complete work brief is
`docs/handoffs/2026-07-12-design-system-enhancement-analysis.md`. Read it in full before
touching the file. It contains:

1. **Ten detailed opportunities** in three tiers (fitted masthead title, anatomy pin
   coupling, jersey-trim band, palette-board recomposition; copy-hex, scrollspy,
   interactive gradient bar, load moment; card-rhythm variance, favicon) with
   implementation notes and watch-outs per item.
2. **A dual-agent critique** (34/40) with seven confirmed defects (two P1: anatomy pins
   occluding render titles, mobile overflow at ~390px), judgment findings to fold into the
   tiers, and three owner-level open questions.
3. **Hard constraints** — most importantly the two-layer rule (doc chrome themes; the
   `--g-*` graphic constants and white canvas cards never theme) and spec fidelity (never
   change a documented value while polishing).

## Suggested order

Fix the P1/P2 defects first (they overlap opportunities #2 and #6), then Tier 1, then
Tier 2/3 as approved. Work one tier at a time and show the user results between tiers;
verify in all four themes and at 390px each round. `/impeccable polish design-system.html`
will pick up the persisted critique snapshot
(`.impeccable/critique/2026-07-12T21-39-12Z__design-system-html.md`) as its backlog;
re-run `/impeccable critique design-system.html` after fixes to track the score.

## Owner decisions still open (ask, don't assume)

- Keep four doc themes or commit to Jersey only.
- DESIGN.md absorbs §08's component-only values (chip/rail dimensions,
  PLAYER_ROW_HEIGHT, court-line trio) vs. formally delegating component truth to the page.
- Anatomy annotation style: floating pins vs. side-gutter callout lines.
- Unverified caveat from the rebuild session: whether Academic M54/Archivo load when the
  file is opened via `file://` (verified over HTTP only). If fonts fail on double-click,
  base64-embed the four faces.

## Durable Pointers

- `DESIGN.md` — canonical spec + decision log (2026-07-12 entry covers the v2 rebuild).
- `PRODUCT.md` — register (brand), personality, design principles; written 2026-07-12.
- `.impeccable/config.json` — detector suppression: `numbered-section-markers` is a
  confirmed convention; em-dash spec glyphs ("—" swatch names, missing-value rule) are
  intentional content, prose em dashes are not to be reintroduced.
- Viewing: `python3 -m http.server 8899` from the repo root, then
  `http://127.0.0.1:8899/design-system.html`.

## On close

Move durable outcomes to DESIGN.md (decision log) and delete or compact both this file and
the analysis document per the AGENTS.md handoff policy.
