# Design System — @chicagobullsdata

The visual identity for the account's graphics. Established with the debut post
("The Shape of the Season," 2026-07-09); the reference implementation is
`scripts/prototypes/season_shape_post.py`. Reuse these decisions; don't re-litigate them
per post. When a decision here changes, update this file (noting it in the decision log at
the bottom), the executable layer (`bulls/graphics/house.py` / `craft.py`), and the rendered
companion `design-system.html` together — the token drift test only catches color mismatches.

Companion docs: `STRATEGY.md` (why the account exists), `bulls-content-playbook.html`
(what to post — the visual encyclopedia), `idea-catalog.html` (the idea shelf), and
`design-system.html` (a browsable visual companion). This file is the canonical record for
design decisions and their history.
This file is *how it should look*.

---

## 1. Brand Identity

> **Status: OPEN — rebrand in progress (started 2026-07-09).** Logo/profile-picture
> exploration is **parked** (candidate sheet generator:
> `scripts/prototypes/brand_logo_candidates.py`, kept for later). Non-logo brand
> decisions — positioning line, on-graphic brand presence, grid rules — are active.

- **Handle:** `@chicagobullsdata` · display name "Chicago Bulls + Data Viz"
- **Logo:** parked (three candidate directions sketched: season-shape glyph, data-bull
  concept mark, varsity wordmark; initials "CBD" ruled out as a lettermark)
- **Profile picture:** parked with the logo (a player photo is explicitly *not* the
  long-term direction; current avatar is a player headshot)
- **Watermark:** text-only (`@chicagobullsdata`, see §6 Footer); a logo lockup variant
  is parked with the logo.
- **Trademark guardrail:** never trace, recolor, or closely imitate the official Bulls
  mark — riffing on red/black as a fan account is fine, the logo itself is team IP.

### Reference accounts (surveyed 2026-07-09)

Three distinct branding models among accounts the user follows:

- **Half Court Mindset** (`halfcourtmindset`, ~4.3k) — *the template is the brand.*
  Concept-mark avatar (brain + basketball = "mindset") on a cream circle. Every graphic
  shares one look: paper texture, rust/orange type, account name printed top-left like a
  masthead, tagline ("For fans that see the game different") printed at the bottom.
- **Orange Ball** (`__orangeball`, small/new) — *design-studio identity.* Wordmark
  avatar ("ORANGE" in marker scrawl on white). Positioning line in bio: "an analytical
  product of sport and design." Grid: B&W halftone player cutouts, cream space, orange
  accents. High polish, low volume.
- **Owen Phillips / The F5** (`owenlhjphillips`, ~6.8k) — *person up front, product
  badge on the work.* Personal-photo avatar; the brand mark ("F5" badge, top corner)
  lives on the graphics, not the profile.

Takeaway for us: `@chicagobullsdata` is a thing, not a person → brand-mark avatar
(HCM/Orange Ball model), and the graphics' shared canvas (header pattern + footer
watermark) is already the masthead — consistency of the template is the brand.

## 2. Color

Red + black is the team palette. Avoid neutral grays for *meaningful* areas — gray reads
off-brand and flat. Grays are for scaffolding: gridlines, muted labels, separators.

| Token | Hex | Role |
|---|---|---|
| `RED` | `#CE1141` | Bulls red — positive/above/accent, one accent word in titles, payoff ring |
| `BULLS_BLACK` | `#141414` | Rich near-black — negative/below/heavy fills (never pure black) |
| `INK` | `#1A1A1A` | Primary text, data lines |
| `MUTED` | `#777777` | Secondary text, axis labels, event-line labels, watermark |
| `FAINT` | `#AAAAAA` | Footer/source credit, quietest text tier |
| `RULE` | `#DDDDDD` | Table rules, hairlines |
| — | `#CFCFCF` | Subtitle separator ticks |
| — | `#F0F0F0` | Chart gridlines |
| — | `#FFFFFF` | Canvas background |

**Magnitude colormap** (`craft.MAGNITUDE_CMAP`): light neutral `#F2EAE8` → Bulls red
`#CE1141` → deep red `#7E0C2B`. Use when a bar/cell's fill encodes stat magnitude.

### Canvas themes

The canvas is a **theme**, not a fixed background. Five sanctioned canvas themes exist
(`house.THEMES`), promoted from the design-system.html doc-chrome palettes on 2026-07-13;
**`jersey` (warm off-white `#FAF8F5`) is the default**, with `white` kept as a sanctioned
alternate. A theme is the full coordinated token set — a background
is a contract with every color on the page, so switching themes swaps ink, rules, gridlines,
and the jersey stripe together, never just the fill. The theme is chosen per post at mock
time (see `POSTING_WORKFLOW.md` Clarification Gate); no other backgrounds or textures.

| Token | `white` | `jersey` (default) | `newsprint` | `blackout` | `hardwood` |
|---|---|---|---|---|---|
| `canvas` | `#FFFFFF` | `#FAF8F5` | `#F3EDDF` | `#121214` | `#BE0E3B` |
| `ink` | `#1A1A1A` | `#141414` | `#191713` | `#F1EFEC` | `#FDF3EA` |
| `muted` | `#777777` | `#5F5B57` | `#5D5749` | `#A7A39E` | `#FBE8E0` |
| `faint` | `#AAAAAA` | `#A19B92` | `#948C79` | `#6F6B66` | `#E497A4` |
| `rule` | `#DDDDDD` | `#E6E2DB` | `#DCD3BF` | `#2B2B30` | `#D15370` |
| `tick` | `#CFCFCF` | `#D6D0C6` | `#CBC1A9` | `#3A3A40` | `#D76A81` |
| `grid` | `#F0F0F0` | `#F1EEE8` | `#EAE2CE` | `#1B1B1E` | `#A70C34` |
| `accent` | `#CE1141` | `#CE1141` | `#B5123C` | `#FF3355` | `#141414` |
| `contrast` | `#141414` | `#141414` | `#191713` | `#F1EFEC` | `#FDF3EA` |
| `band` | `#CE1141` | `#CE1141` | `#191713` | `#FF3355` | `#141414` |
| `trim_a` | `#FFFFFF` | `#FFFFFF` | `#F3EDDF` | `#121214` | `#FDF3EA` |
| `trim_b` | `#141414` | `#141414` | `#B5123C` | `#F1EFEC` | `#BE0E3B` |

Canvas/ink/muted/accent/band/trim values mirror the design-system.html doc themes exactly;
`faint`/`rule`/`tick`/`grid` are first-pass derivations (blends toward the canvas) and may be
tuned against real renders. On `hardwood` the accent flips to black — red is the ground, so
black is the one meaningful color; on `blackout` the accent brightens to `#FF3355` because
`#CE1141` lacks contrast on near-black. `jersey` is the warm off-white of the
design-system.html page itself (its default doc theme) with the standard red accent and
stripe; the user adopted it as the everyday default over plain white on 2026-07-13.

## 3. Typography

| Role | Face | File(s) | Notes |
|---|---|---|---|
| Titles | **Academic M54** | `assets/fonts/AcademicM54.ttf` | Collegiate slab. ALL CAPS. Auto-fit to width (see §5). One accent word in `RED`. |
| Body / labels / annotations | **Archivo** | `assets/fonts/Archivo-400/500/600.ttf` | Grotesque; 400 regular, 500 medium, 600 bold — always select weight **by file**. |
| Fallback title face | Bevan | `assets/fonts/Bevan.ttf` | OFL-licensed drop-in if Academic M54 must be replaced. |
| Legacy (don't use in new work) | Playfair Display + DM Sans | `assets/fonts/` | Remain only in `bulls/graphics/feed.py` zone builders. |

⚠️ **Academic M54 license:** free for **non-commercial use only**. If the account ever
goes commercial, license it or swap to Bevan.

⚠️ **matplotlib gotcha:** the `weight=` kwarg is silently ignored for single-file fonts
(DM Sans was single-weight for months without anyone noticing). Always pass the specific
weight's file via `FontProperties(fname=...)`. Instance more weights from the variable
font with `fontTools.varLib.instancer` if needed.

## 4. Canvas & Export

- **Format:** 1080×1350 px (Instagram portrait 4:5). Jersey off-white background
  (`#FAF8F5`) by default; a sanctioned canvas theme (§2) may be chosen per post —
  `house.new_canvas(theme)`.
- **Iterate at 150 DPI** (fast), **export final at 300 DPI** (2160×2700 — text survives
  Instagram compression). Prototype scripts take a `--final` flag for the 300-DPI render;
  current posts use `house.save_post(fig, path, final=...)` so draft/final dimensions are explicit.
- Full-bleed axes (`fig.add_axes([0, 0, 1, 1])`), data coords = pixel coords, equal aspect,
  no spines/ticks.
- **Side margins:** 60 px left and right (title, subtitle, kicker, footer all anchor here).

## 5. Header Pattern

Stacked tight, top-left anchored at x=60 (values from the reference implementation):

0. **Jersey stripe** — full-bleed 16 px band across the very top of the canvas: the
   theme's `band` color with two pinstripes (top-down: band 4 / trim_a 2 / band 4 /
   trim_b 2 / band 4). On the white default that is red with one white and one black
   pinstripe. Mirrors the `.band` element on design-system.html. Default-on via
   `house.draw_header(..., stripe=True)`; `house.draw_jersey_stripe(ax)` standalone.
1. **Title** — Academic M54, ALL CAPS, top at y = H−66. Auto-fit so the string fills
   W−120 exactly (balanced ~60 px margins regardless of copy length). One accent word
   in `RED`, rest in `INK`. **Jersey-lettering outline, default-on:** each glyph gets a
   red outer stroke (7 pt) and white gap (3.5 pt) via path effects, echoing the stripe.
   Switch back globally by flipping `house.OUTLINED_TITLE = False`, or per post with
   `draw_header(..., outlined=False)`.
2. **Subtitle** — y = H−168, 18 pt Archivo medium, `MUTED`. Segments (team · season ·
   record etc.) separated by thin light-gray **vertical ticks** (`#CFCFCF`, ~1.3 lw,
   ~16 px tall) — never "|" or "·" glyphs in rendered text.
3. **Kicker** — y = H−206, 14 pt Archivo medium italic, `RED`. States the metric in
   plain words ("Games over/under .500 through each game"). If the kicker explains the
   metric, don't repeat the explanation in a footer.

## 6. Footer Pattern (every graphic)

Both on the same baseline (y=40), quiet:

- **Bottom-left:** source credit — "Data via nba.com", 8.5 pt Archivo regular,
  `FAINT`. This is a fairness guardrail; it never comes off.
- **Bottom-right:** watermark — `@chicagobullsdata`, 10.5 pt Archivo medium, `MUTED`,
  right-aligned at x=1020. Authorship must survive reposts/screenshots.
- For stat boards with qualification rules, use `craft.threshold_footer(qualification,
  coverage, source)` — one line joining threshold + coverage window + source, e.g.
  "Min. 20 games | 2025-26 season through Jul 4 | data: stats.nba.com".

## 7. Annotation Grammar (two visual languages)

Every marker or callout must **explain a bend in the data** — if the line doesn't turn
there, it's trivia; cut it. Alternate emotional beats with factual anchors so the graphic
never reads as a rant or a spec sheet.

**Factual event markers** — budget: ~1 hero line, at most 1 supporting.
- Gray dashed vertical line: `MUTED`, 1.2 lw, dash pattern `(0, (4, 3))`.
- Label: stacked, dated, muted — e.g. "TRADE DEADLINE" (9 pt Archivo bold) over
  "Feb 5" (9 pt Archivo medium), right-aligned 8 px off the line.
- **Fact rule:** anything printed on a graphic (dates, picks, trades, injuries) must be
  verified — web-search anything past the model's knowledge cutoff; never draw a guessed
  date.

**Fan-voice callouts** — budget: 3–4.
- 11 pt Archivo bold, `INK`, with a thin straight connector (`arrowstyle="-"`, `MUTED`,
  1.0 lw) from text to the data point.
- Voice: "fan in the stands" — first-person, wry, a notch above meme-page
  ("5-0 start, we were so back", "Tank for Caleb begins"). Names/context/thesis live in
  the IG caption, not on the graphic.

## 8. Faces (headshots)

The highest-stopping-power object on a graphic — use sparingly.

- Circular crop via `craft._make_circular_headshot` / `craft.headshot_label`; a **red border
  ring** (`border_color=(206, 17, 65)`, `border_frac≈0.045`) means "the payoff."
- Position so geometry does the pointing (e.g. the data line ends at the face); the
  payoff face can go unlabeled.
- Missing headshots render as a neutral placeholder disc — builders never break.
- **Image rule:** NBA CDN headshots for new rookies are often the gray silhouette
  (~12 KB file = silhouette; real ones are 50–200 KB) — check visually. Fall back to the
  team's own CDN (nba.com/bulls article images are clean/unwatermarked); crop square
  around the face for the circular helper. Flag wire-photo licensing to the user before
  using non-NBA sources.

## 9. Executable House Layer and Component Library

### House foundation (`bulls/graphics/house.py`)

`DESIGN.md` is the human-readable north star; `house.py` is the small Matplotlib implementation
of the rules every current post shares. It owns the palette and canvas themes (`house.THEMES`;
every draw function takes an optional `theme` and defaults to white), Academic M54/Archivo font files,
1080×1350 canvas, 60 px margins, fitted segmented title, tick-separated subtitle, optional kicker,
source/watermark footer pair, and 150/300-DPI export contract.

Use the house layer for new posts before drawing format-specific content. Do not put charts, tables,
story copy, or post-specific layout in it. Those stay with the prototype until a second real post
proves that the grammar repeats.

### Craft components (`bulls/graphics/craft.py`)

Shared F5-derived helpers — reach for these before hand-rolling:

- `gradient_bar(ax, y, value, vmin, vmax, ...)` — horizontal stat bar, fill sampled from
  `MAGNITUDE_CMAP` at the value's normalized position.
- `stacked_label(ax, x, y, primary, secondary, ...)` — bold name over muted context line;
  names >16 chars collapse to "F. Lastname" everywhere.
- `threshold_footer(fig, qualification, coverage, source)` — the fairness-guardrail footer.
- `headshot_label(ax, image_path, x, y, radius, border_color)` — circular headshot with
  placeholder fallback.

### Report-card component values

The Summer League report established the current component dimensions used by
`scripts/prototypes/summer_league_report.py`:

- Standard stat chip: 118×52 px, radius 10 px.
- Supporting rail card: 250×80 px, radius 12 px; neutral profile and distribution cards use the
  stronger borderless blush `#F3E1E7` against the pale panel. Profile values sit lower in the card
  at 21 pt so their top padding and label spacing remain balanced.
- Player story row: `PLAYER_ROW_HEIGHT = 173` px.
- Full-slide player identity: 58 px headshot radius with warm-neutral stat chips; the evidence panel
  uses a borderless pale blush field so the jersey canvas remains the dominant surface.
- Featured-player tables use 52 px headshots, 16 px body type, and 11 px row padding through four
  rows. A five-player table compacts to 46 px headshots, 15 px body type, and 7 px row padding so it
  preserves footer clearance rather than shrinking the full table after composition.
- Court lines: `#CFCFCF` on white, `#C6C6C6` at slide scale, and `COURT_LINE`
  (`#C9A8B5`) on pale panels.

These are component defaults, not reasons to force every post into the report-card format.
Promote the prototype helpers into `craft.py` only when a second post needs the same grammar.

Table-format posts render via `plottable` (see `scripts/prototypes/f5_lineup_table.py`).
F5 technique references: `docs/reference/f5-technique-notes.html`.

## 10. Grid Rules (what every post must share)

The grid viewed as a whole is the brand (the Half Court Mindset lesson: the template
*is* the identity). Every feed post shares:

1. A sanctioned canvas theme (§2), 4:5 portrait (§4) — jersey (warm off-white) is the
   default; white, newsprint, blackout, and hardwood are the only alternates. No other
   colors, no textures. The theme is a per-post choice made at mock time, not a
   per-element decoration.
2. The header pattern (§5): Academic M54 ALL-CAPS title with exactly one red accent
   word, tick-separated muted subtitle, red italic kicker.
3. Red/black as the only *meaningful* colors (§2) — a thumbnail should read as
   red + black + white even before the title is legible.
4. The footer pair (§6): source credit bottom-left, watermark bottom-right.
5. One idea per post — the title states it; if the title needs "and," it's two posts.

## 11. Voice & Caption

- On-graphic copy is minimal and in the fan voice (§7). The analytical thesis, player
  names, and context live in the **IG caption**, which the user writes or heavily owns.
- Captions sound like a knowledgeable person who watches the Bulls: simple, direct, and
  grounded in the actual basketball observation. A plain factual caption is a successful result.
- Do not add a hook, joke, fan slang, rhetorical question, or engagement bait merely to make the
  copy feel distinctive. Use humor only when it is natural to the post or explicitly comes from
  the user; never perform a social-media persona.
- Save the approved caption on the idea-catalog card when available. Hashtags, alt text, and Story
  copy are optional supporting pieces, not mandatory additions.

---

## Open Questions (rebrand — all parked 2026-07-09, resume any session)

Settled this round: grid rules codified (§10); on-graphic brand presence stays
footer-watermark-only (no masthead — the header already works hard; revisit when a
logo exists).

- [ ] Positioning line + bio — leading candidate: **"Chicago Bulls, charted."**
      (already the STRATEGY.md one-liner) with name field "Chicago Bulls Data" and a
      one-line descriptor; user deferred the decision, not the direction.
- [ ] Logo / avatar mark — three sketched directions (season-shape glyph, data-bull,
      varsity wordmark); candidate sheet: `scripts/prototypes/brand_logo_candidates.py`
- [ ] Profile picture — depends on the logo (player photo ruled out long-term)
- [ ] Watermark logo lockup — depends on the logo
- [ ] Story/reel variants of the canvas (9:16) — needed?

## Decision Log

- **2026-07-13** — Source credit standardized to `Data via nba.com`: a concise attribution
  to the official provider with only the opening `D` capitalized. Updated the shared footer
  default and rendered companion.
- **2026-07-13** — Fifth canvas theme `jersey` added and **adopted as the default** (§2): the
  design-system.html page's own warm off-white (`#FAF8F5`) with the standard red accent and
  stripe. User preferred it over plain white on the mock-post render; white stays a sanctioned
  alternate. All house draw functions now default to jersey (`house.DEFAULT_THEME`).
  `scripts/prototypes/mock_post_demo.py` gained `--theme <name>` to preview any canvas theme.
- **2026-07-13** — Outlined "jersey lettering" title adopted as the default (user pick from a
  side-by-side mock): red outer stroke + white gap path effects on the fitted Academic M54
  title (§5 item 1). `house.OUTLINED_TITLE` is the global switch; `outlined=False` per post.
  `scripts/prototypes/mock_post_demo.py` added as a fake-data design-preview harness that
  renders both variants.
- **2026-07-13** — Canvas themes promoted from doc chrome to render options: the white canvas
  became the default of four sanctioned themes (`white`, `newsprint`, `blackout`, `hardwood` —
  §2 Canvas themes), implemented as `house.Theme`/`house.THEMES` with every house draw function
  taking an optional `theme`. The theme is chosen per post during the Clarification Gate. §10
  rule 1 relaxed accordingly; "no other colors, no textures" still holds. Doc-chrome palettes on
  design-system.html supplied canvas/ink/muted/accent/stripe values; quiet-tier tokens
  (`faint`/`rule`/`tick`/`grid`) are first-pass blends open to visual tuning.
- **2026-07-13** — Jersey-trim stripe promoted from a design-system.html page decoration to
  part of the graphics themselves: a full-bleed 16 px red band with white/black pinstripes
  at the top of every canvas (§5 item 0, `house.draw_jersey_stripe`), default-on in
  `draw_header`.
- **2026-07-13** — Token-integrity pass: `tests/test_design_tokens.py` now fails the suite when
  the hex values in this file, `design-system.html`, or `bulls/config.py` diverge from
  `house.py` (the docs stay hand-authored; the test replaces manual sync discipline).
  `bulls/config.py` legacy RGB tuples aligned to house tokens (`BULLS_BLACK` was `#000000`;
  off-system green/red pair removed). `_make_circular_headshot` moved from legacy `feed.py`
  into `craft.py` so the current component layer no longer depends on the legacy module.
- **2026-07-12** — Python remains the center of the graphics pipeline. Added
  `bulls/graphics/house.py` as the executable implementation of settled cross-post rules; Season
  Shape and Summer League now consume it with pixel-identical final renders. Summer League also
  separates display-ready slide data from drawing so another renderer can be compared without
  changing the analysis. An HTML/CSS/SVG version of the team slide was tested and not adopted: the
  user preferred the original Matplotlib output, so the executable spike was removed. Revisit only
  if a future layout-heavy format provides a clearer reason.
- **2026-07-12** — `design-system.html` enhancement completed: fitted masthead, jersey-trim
  chrome, proportional/copyable palette, sticky section navigation, interactive component
  demonstrations, side-gutter anatomy callouts, varied documentation rhythm, and mobile/
  accessibility fixes. These are documentation-interface treatments; the two-layer rule
  remains unchanged and graphic-spec demos still use fixed tokens on white.
- **2026-07-12** — Design-system enhancement decisions: retain all four documentation
  themes; use side-gutter callout lines instead of solid floating pins on real-render
  anatomies; absorb durable report-card component values into this canonical document.
- **2026-07-12** — `design-system.html` rebuilt as a hand-authored static page (v2) after a
  Claude Design exploration round. Doc-chrome themes adopted (Jersey default + Newsprint,
  Blackout, Hardwood Red switcher) — chrome-only: spec demos always render on white with the
  real tokens and fonts. **Archivo confirmed as the graphics body face**; Barlow Semi Condensed
  is the Jersey theme's page font only (a Claude Design export had wrongly documented it as the
  graphics face). §09 anatomies now embed the real renders from `docs/mocks/`. The loose
  Claude Design exports ("Bulls Design System.html", "Direction Options.html") are absorbed
  and slated for removal.
- **2026-07-16** — Summer League Report stat ladder settled: the cover table closes with the
  basic +/- while the detailed player slides carry NETRTG (the "advanced" stat belongs with the
  deeper view), and TS% was replaced by plain FG% on both surfaces (cover table column placed
  right after FGM/A) — FG% ignores free throws, so the 2026 one-free-throw rule cannot inflate
  a shooting number on the graphic. Player-slide shot charts gained fuller court geometry
  (free-throw circle with dashed lower half, restricted-area arc, backboard) and sit closer
  under the SHOT CHART label.
- **2026-07-13** — Strong card-rail emphasis became optional and meaning-driven rather than
  automatic. The Summer League player slide keeps every shot-profile card neutral; TS% remains
  visible but does not receive a solid-red payoff treatment. A red payoff card is still available
  when a future composition has a deliberately chosen headline number.
- **2026-07-11** — F5 emphasis grammar refined on the first live Summer League Report: it can hold
  for **card rails** (at most one solid-red payoff card while siblings stay quiet) but was
  **rejected for dense stat tables** — the user removed the magnitude-colored column entirely, and
  the shipped table is a clean zebra-striped box score sorted by the story stat (points, so the
  headline player tops the table) with no emphasized column. Embedded tables may be rendered with
  Great Tables to a cropped PNG and composited onto the white canvas; the canvas stays white
  (F5's cream background considered and not adopted — §10 grid rule).
- **2026-07-10** — Caption voice clarified: knowledgeable Bulls observer, simple and direct;
  manufactured hooks, humor, slang, and engagement bait ruled out. Supporting posting copy is optional.
- **2026-07-09** — Rebrand round closed: grid rules codified (§10); footer watermark
  confirmed as the only on-graphic brand element for now. Tagline/bio parked with
  "Chicago Bulls, charted." as the leading candidate. Logo work parked earlier same day.
- **2026-07-09** — Reference-account survey (Half Court Mindset, Orange Ball, Owen
  Phillips) captured in §1. Logo/profile-pic/watermark-lockup exploration parked;
  rebrand continues on positioning line, bio, on-graphic brand presence, grid rules.
  "CBD" initials ruled out as a lettermark; trademark guardrail added.
- **2026-07-09** — File created: design system extracted from AGENTS.md and expanded with
  exact values from `season_shape_post.py` + `craft.py`. Rebrand exploration opened.
- **2026-07-09** — Debut post shipped; type (Academic M54 + Archivo), palette, header/footer
  patterns, annotation grammar, and voice established with the user.
