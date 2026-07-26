# Design System — @chicagobullsdata

**This file owns the chart layer.** Canva's Brand Kit owns post typography and page layout.

Posts are assembled in Canva. Python's job is a verified chart asset that drops into a Canva page
and looks native there. That means this document specifies colors, chart typography, mark grammar,
and the export contract — not headers, titles, or page furniture.

| Surface | Owner |
|---|---|
| Post title, subtitle, headers, body copy, page layout | **Canva Brand Kit** |
| Chart colors, chart typography, marks, annotations, export | **This file** + `bulls/graphics/house.py` |
| Which post to make and how it ships | `POSTING_WORKFLOW.md` |

When a chart-layer decision changes, update this file, `house.py`/`craft.py`, and
`design-system.html` together — `tests/test_design_tokens.py` catches color drift only.

---

## 1. Typography

**Canva Brand Kit (posts):**

| Role | Face |
|---|---|
| Titles | **Clarendon Narrow** |
| Subtitles and section headers | **Yearbook Solid** |
| Body | **Helvetica Bold** |

Clarendon Narrow and Yearbook Solid are Canva faces — they aren't installed locally and Python never
renders them. Don't try to approximate them in a chart; if a chart seems to need a title, that title
belongs on the Canva page.

**Charts (Python):** Helvetica, matching the Canva body face so labels read as part of the page.
Use `house.helvetica()` / `house.helvetica("bold")`.

⚠️ **matplotlib registers only the Regular face of `Helvetica.ttc`**, so asking for bold by family
name silently renders regular. `house.helvetica()` splits the requested face out of the system
collection into `cache/fonts/` and loads it by filename. The extraction stays in `cache/` so the
licensed system font is never committed. On non-macOS it falls back to Archivo.

## 2. Color

Red + black is the palette, unchanged. Avoid neutral grays for *meaningful* areas — gray reads
off-brand and flat. Grays are scaffolding: gridlines, muted labels, separators.

| Token | Hex | Role |
|---|---|---|
| `RED` | `#CE1141` | Bulls red — positive/above/accent, payoff emphasis |
| `BULLS_BLACK` | `#141414` | Rich near-black — negative/below/heavy fills (never pure black) |
| `INK` | `#1A1A1A` | Primary text, data lines |
| `MUTED` | `#777777` | Secondary text, axis labels, annotation labels |
| `FAINT` | `#AAAAAA` | Quietest text tier |
| `RULE` | `#DDDDDD` | Table rules, hairlines |
| `SUBTITLE_RULE` | `#CFCFCF` | Separator ticks |
| `GRIDLINE` | `#F0F0F0` | Chart gridlines |
| `WHITE` | `#FFFFFF` | The `white` theme's canvas — not the post default |

**Post canvas is `#FAF8F5`** (warm off-white — the `jersey` theme). Charts are exported transparent
and sit on that Canva background, so chart colors must be chosen to read against it.

**Magnitude colormap** (`craft.MAGNITUDE_CMAP`): light neutral `#F2EAE8` → `#CE1141` → deep red
`#7E0C2B`. Use when a bar or cell fill encodes magnitude.

⚠️ The table diverging colormap (`NET_CMAP`) runs red-to-green — colorblind-unsafe. Mitigated by
always printing the sign (`force_sign`). Revisit if a table post ever leans on color alone.

### Alternate themes (parked)

`house.THEMES` carries four alternates beyond `jersey`. **None are in active use** — the account runs
on `#FAF8F5`. They're kept because the tokens may be reimplemented in Canva later to vary the look.
A theme is a coordinated set, never just a background swap: changing the canvas changes ink, rules,
gridlines, and accents together.

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

Two deliberate inversions if these are ever revived: `hardwood` flips the accent to black (red is the
ground, so black becomes the meaningful color), and `blackout` brightens it to `#FF3355` because
`#CE1141` lacks contrast on near-black.

## 3. Chart Asset Contract

- **Export transparent.** The chart carries no background; the Canva page supplies `#FAF8F5`.
- **Export larger than the placed size.** Canva-rendered output is judged from the downloaded page at
  feed size, and an undersized asset can't be recovered by DPI metadata.
- **The chart carries data, not framing.** Axis labels, value labels, player names, medians, and
  annotations belong in the chart. Titles, subtitles, kickers, source lines, watermark, and editorial
  copy belong on the Canva page.
- Prototypes print a Canva copy block — the exact strings to paste — so the page's numbers come from
  the same run as the chart. Never retype a number from a chart into Canva by eye.
- Chart labels use `house.helvetica()`; pull colors from the theme tokens (`theme.ink`,
  `theme.accent`, `theme.grid`) rather than the white-canvas module constants.

## 4. Mark and Annotation Grammar

Every marker or callout must **explain a bend in the data**. If the line doesn't turn there, it's
trivia — cut it.

- **Reference lines** (medians, league average) in `MUTED`, dashed `(0, (4, 3))`, 1.2 lw, with a
  short label stating what the line is ("MEDIAN 34.1%").
- **Event markers** — budget ~1 hero, at most 1 supporting. Stacked dated label: name (Helvetica
  bold, 9 pt) over the date (9 pt regular), right-aligned 8 px off the line.
- **Callouts** — budget 3–4. Bold label with a thin straight connector (`arrowstyle="-"`, `MUTED`,
  1.0 lw) to the point. Names and context can live on the Canva page instead when the chart is dense.
- **Emphasis is meaning-driven, never decorative.** At most one payoff element per chart.

## 5. Faces (headshots)

The highest-stopping-power object on a chart — use sparingly.

Two crops, and the difference carries meaning:

- **Circular, red-ringed** — `craft._make_circular_headshot` / `craft.headshot_label`. The ring
  (`border_color=(206, 17, 65)`, `border_frac≈0.045`) means "this is the payoff." At most one.
- **Bare square** — `house.square_headshot_label(ax, path, x, y, half_size, zorder=…)`, the
  landscape scatter family's plot marker. No ring: every plotted player is equal, so a ring would
  read as an emphasis the layer does not intend. Use `half_size=36` for a roster landscape.
  `house.ensure_headshots(nba_ids)` warms `house.HEADSHOT_CACHE` first; pass the ids in draw order
  and set each returned artist's `zorder` so overlapping faces stack predictably.

`bulls_on_court_landscape.py` and `current_roster_hot_spots.py` still carry their own square-crop
copies that differ (top-anchored crop, and a non-returning variant); fold them in when either post
is next touched.
- Position so geometry does the pointing — the data line ends at the face.
- Missing headshots render as a neutral placeholder disc; builders never break.
- ⚠️ **NBA CDN headshots for new rookies are often a gray silhouette.** Check visually: ~12 KB is
  usually the silhouette, a real headshot is 50–200 KB. Fall back to the team's own CDN
  (nba.com/bulls article images are clean and unwatermarked), crop square around the face, and flag
  wire-photo licensing before using a non-NBA source.

## 6. Working From F5 and Other Tutorials

When building from `docs/reference/f5-technique-notes.html` or a similar tutorial, **reproduce the
source's styling and structure closely.** Swap in our palette and Helvetica; keep its layout,
proportions, mark choices, and visual logic.

Do not redesign it toward "our own direction" — the reason to work from a tutorial is that its
composition already works. Divergence should be a deliberate, stated choice, not a drift.

## 7. What Every Post Shares

Visual outcomes, whichever tool composes the page:

1. `#FAF8F5` canvas, 1080×1350 (4:5). No other backgrounds, no textures.
2. Red/black as the only *meaningful* colors — a thumbnail should read red + black + off-white before
   the title is legible.
3. Clarendon Narrow title, Yearbook Solid supporting headers, Helvetica Bold body, with deliberate
   red emphasis.
4. Visible authorship on every page; visible source, qualification, and coverage on every
   data-bearing page. These may move to fit the composition but never disappear — analytical honesty
   has to survive reposts and screenshots.
5. **One idea per post.** The title states it; if the title needs "and," it's two posts.
6. **Pretty *and* instantly legible.** The two-second bar rules out both ugly stat-dumps and
   beautiful-but-inscrutable analytics. When a detail would help a nerd but confuse a casual fan, the
   casual fan wins.
7. **Take the structure, not the look.** Adopt formats from the best accounts, rendered in our
   palette and type.

## 8. Voice & Caption

The single owner of how the account sounds.

**On-graphic copy** is minimal. The analytical thesis, player names, and context live in the caption.
On-chart annotations may carry a light "fan in the stands" voice — first-person, wry, a notch above
meme-page — but the chart stays clean.

**The user writes the caption.** Offer at most one short line as raw material; never a multi-sentence
draft unless asked. Both of the account's first two data-viz posts used the user's own one-liner plus
hashtags (confirmed 2026-07-11).

Captions sound like a knowledgeable person who watches the Bulls: simple, direct, grounded in the
actual basketball observation. **A plain factual caption is a successful result.** Preserve material
qualifiers without turning the caption into methodology notes.

Never add a hook, joke, fan slang, rhetorical question, or engagement bait to make copy feel
distinctive. Use humor only when it's natural to the post or comes from the user. Never perform a
social-media persona.

## 9. Brand Identity

- **Handle:** `@chicagobullsdata` · display name "Chicago Bulls + Data Viz"
- **Watermark:** text-only (`@chicagobullsdata`), set in Canva.
- **Trademark guardrail:** never trace, recolor, or closely imitate the official Bulls mark. Riffing
  on red/black as a fan account is fine; the logo itself is team IP.
- **Ruled out:** "CBD" as a lettermark; a player photo as the long-term profile picture.
- **Parked (2026-07-09):** positioning line and bio — leading candidate "Chicago Bulls, charted.";
  logo/avatar mark; profile picture; 9:16 Story variants.

**Why the template carries the brand.** A survey of three branding models — Half Court Mindset (the
template *is* the brand), Orange Ball (design-studio identity), Owen Phillips / The F5 (person up
front, product badge on the work) — landed on the first. `@chicagobullsdata` is a thing, not a
person, so a consistent page template is the identity.

---

## Legacy: Python Full-Layout Posts

`house.py` still contains the full-page system used by earlier posts: `new_canvas`, `draw_header`,
`draw_fitted_title`, `draw_subtitle`, `draw_jersey_stripe`, `draw_footer`, `save_post`, with Academic
M54 titles and Archivo body (`display_font()` / `body_font()`). Reference implementation:
`scripts/prototypes/season_shape_post.py`.

**This is not the path for new posts.** It's documented so existing prototypes stay maintainable:

- 1080×1350, 60 px side margins, full-bleed axes, iterate 150 DPI / export 300 DPI.
- Jersey stripe: full-bleed 16 px band, pinstripes band 4 / trim_a 2 / band 4 / trim_b 2 / band 4.
- Title auto-fits to W−120 with a red outer stroke (7 pt) and white gap (3.5 pt); subtitle at
  y = H−168 with drawn tick separators; kicker at y = H−206.
- Footer pair on the y=40 baseline: `Data via nba.com` bottom-left (`FAINT`), `@chicagobullsdata`
  bottom-right (`MUTED`, x=1020).
- ⚠️ Academic M54 is licensed **non-commercial only** — license it or swap to Bevan if that changes.

Report-card component values from the Summer League report (`PLAYER_ROW_HEIGHT = 173` px, 118×52 stat
chips, 250×80 rail cards, `COURT_LINE` `#C9A8B5` on pale panels) live with that prototype.

`design-system.html` documents this legacy system and has not been rebuilt for the Canva-first model.

---

## Settled — Don't Re-Litigate

- **HTML/CSS/SVG rendering was tested and rejected** (2026-07-12) for composing graphics; the user
  preferred the Matplotlib output and the spike was removed. Distinct from the *live* Great Tables
  path, which legitimately renders HTML through `nokap.from_html` and composites the PNG.
- **F5 magnitude-colored columns were rejected for dense stat tables** (2026-07-11) — the shipped
  table is clean zebra stripes sorted by the story stat. Emphasis stays available for a single
  deliberate payoff element (2026-07-13: strong emphasis became optional and meaning-driven).
- **TS% was replaced by plain FG%** on Summer League surfaces (2026-07-16). FG% ignores free throws,
  so the 2026 one-free-throw rule can't inflate a shooting number.
- **"CBD" was ruled out as a lettermark** (2026-07-09).
- **Canva became the assembly surface** (adopted 2026-07-22 after the Sticky Stats pilot; Brand Kit
  took over post typography 2026-07-25). Python stays the source of analytical truth.
