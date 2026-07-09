# Design System — @chicagobullsdata

The visual identity for the account's graphics. Established with the debut post
("The Shape of the Season," 2026-07-09); the reference implementation is
`scripts/prototypes/season_shape_post.py`. Reuse these decisions; don't re-litigate them
per post. When a decision here changes, update this file and note it in the decision log
at the bottom.

Companion docs: `STRATEGY.md` (why the account exists), `bulls-content-playbook.html`
(what to post — the visual encyclopedia), `idea-catalog.html` (the idea shelf).
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

- **Format:** 1080×1350 px (Instagram portrait 4:5), white background.
- **Iterate at 150 DPI** (fast), **export final at 300 DPI** (2160×2700 — text survives
  Instagram compression). Prototype scripts take a `--final` flag for the 300-DPI render;
  pass `dpi=300` to `save_feed_post`.
- Full-bleed axes (`fig.add_axes([0, 0, 1, 1])`), data coords = pixel coords, equal aspect,
  no spines/ticks.
- **Side margins:** 60 px left and right (title, subtitle, kicker, footer all anchor here).

## 5. Header Pattern

Stacked tight, top-left anchored at x=60 (values from the reference implementation):

1. **Title** — Academic M54, ALL CAPS, top at y = H−66. Auto-fit so the string fills
   W−120 exactly (balanced ~60 px margins regardless of copy length). One accent word
   in `RED`, rest in `INK`.
2. **Subtitle** — y = H−168, 18 pt Archivo medium, `MUTED`. Segments (team · season ·
   record etc.) separated by thin light-gray **vertical ticks** (`#CFCFCF`, ~1.3 lw,
   ~16 px tall) — never "|" or "·" glyphs in rendered text.
3. **Kicker** — y = H−206, 14 pt Archivo medium italic, `RED`. States the metric in
   plain words ("Games over/under .500 through each game"). If the kicker explains the
   metric, don't repeat the explanation in a footer.

## 6. Footer Pattern (every graphic)

Both on the same baseline (y=40), quiet:

- **Bottom-left:** source credit — "Data via NBA.com/Stats", 8.5 pt Archivo regular,
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

- Circular crop via `_make_circular_headshot` / `craft.headshot_label`; a **red border
  ring** (`border_color=(206, 17, 65)`, `border_frac≈0.045`) means "the payoff."
- Position so geometry does the pointing (e.g. the data line ends at the face); the
  payoff face can go unlabeled.
- Missing headshots render as a neutral placeholder disc — builders never break.
- **Image rule:** NBA CDN headshots for new rookies are often the gray silhouette
  (~12 KB file = silhouette; real ones are 50–200 KB) — check visually. Fall back to the
  team's own CDN (nba.com/bulls article images are clean/unwatermarked); crop square
  around the face for the circular helper. Flag wire-photo licensing to the user before
  using non-NBA sources.

## 9. Component Library (`bulls/graphics/craft.py`)

Shared F5-derived helpers — reach for these before hand-rolling:

- `gradient_bar(ax, y, value, vmin, vmax, ...)` — horizontal stat bar, fill sampled from
  `MAGNITUDE_CMAP` at the value's normalized position.
- `stacked_label(ax, x, y, primary, secondary, ...)` — bold name over muted context line;
  names >16 chars collapse to "F. Lastname" everywhere.
- `threshold_footer(fig, qualification, coverage, source)` — the fairness-guardrail footer.
- `headshot_label(ax, image_path, x, y, radius, border_color)` — circular headshot with
  placeholder fallback.

Table-format posts render via `plottable` (see `scripts/prototypes/f5_lineup_table.py`).
F5 technique references: `docs/reference/f5-technique-notes.html`.

## 10. Grid Rules (what every post must share)

The grid viewed as a whole is the brand (the Half Court Mindset lesson: the template
*is* the identity). Every feed post shares:

1. White canvas, 4:5 portrait (§4) — no colored or textured backgrounds.
2. The header pattern (§5): Academic M54 ALL-CAPS title with exactly one red accent
   word, tick-separated muted subtitle, red italic kicker.
3. Red/black as the only *meaningful* colors (§2) — a thumbnail should read as
   red + black + white even before the title is legible.
4. The footer pair (§6): source credit bottom-left, watermark bottom-right.
5. One idea per post — the title states it; if the title needs "and," it's two posts.

## 11. Voice & Caption

- On-graphic copy is minimal and in the fan voice (§7). The analytical thesis, player
  names, and context live in the **IG caption**, which the user writes or heavily owns.
- Ship-ready caption + hashtag block goes on the idea-catalog card when a post is
  approved (so posting from the phone is trivial).

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
