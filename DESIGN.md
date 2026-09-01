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
`bulls/graphics/house.py` together — `tests/test_design_tokens.py` catches color drift.

---

## 1. Typography

**Canva Brand Kit (posts):** the page's faces are chosen in Canva and change as the look evolves.
Recent posts have used Clarendon Narrow titles, Yearbook Solid headers and Helvetica Bold body, but
that is a record of what was used, not a rule to check a page against. The typography of a finished
page is the user's call at assembly time.

Canva faces such as Clarendon Narrow and Yearbook Solid aren't installed locally, and Python never
renders them. Don't try to approximate them in a chart; if a chart seems to need a title, that title
belongs on the Canva page.

**Charts (Python):** Helvetica, matching the Canva body face so labels read as part of the page.
Use `house.helvetica()` / `house.helvetica("bold")`.

⚠️ **matplotlib registers only the Regular face of `Helvetica.ttc`**, so asking for bold by family
name silently renders regular. `house.helvetica()` splits the requested face out of the system
collection into `cache/fonts/` and loads it by filename. The extraction stays in `cache/` so the
licensed system font is never committed. On non-macOS it falls back to an installed sans-serif.

`helvetica()` accepts `regular`, `bold`, `oblique` and `bold_oblique`. Helvetica has no true
italic — **Oblique is its slanted face**, and it is what "italic" means for this account. The same
trap as bold applies: matplotlib registers only Regular from `Helvetica.ttc`, so asking for
`style="italic"` by family name silently renders upright. Ask for the face by name instead.

**Slant is available as a row-level qualifier.** The height ladder sets a whole row in oblique to
mark a row that met a weaker standard than the rest, in place of an asterisk on one field: the
slant marks every field at once and leaves the footnote to the Canva page. Use it that way — as a
property of an entire row — rather than as emphasis on a single label.

⚠️ **Helvetica has no arrow glyph.** `→` (U+2192) renders as an empty box and matplotlib does not
warn. En dashes, middle dots and accented Latin characters are all present, so only the arrows bite.
Spell the transition (`13.1 to 20.0`) or draw a real `FancyArrowPatch`.

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

**⚠️ Black in a graphic is `#242424`.** Nothing the account publishes uses pure or near-pure black —
not text, not marks, not rules. Stated by the user 2026-09-01 as a standing rule covering charts and
graphics alike, so it applies to every new chart regardless of what the legacy `INK` and
`BULLS_BLACK` tokens below say. Those two remain only because the legacy full-layout renderers were
built on them; do not reach for them in new work.

**⚠️ New charts take no theme.** The page canvas changes from post to post — it is whatever the user
picks in Canva that day, and has ranged at least `#FAF8F5` to `#E9E5E1`. Chart assets are always
exported transparent, and the only meaningful colours in them are Bulls red and `#242424`, so a
canvas-dependent theme buys nothing and actively misleads: the `jersey` theme's `ink`, `muted` and
`grid` tokens describe a background the post is not using. State the handful of colours a chart needs
as named constants in the chart module instead. `three_point_leaders.py` is the reference for this.

The theme machinery in `house.py` (`THEMES`, `get_theme`, `DEFAULT_THEME`) is therefore **retired in
practice and slated for removal**; the user has confirmed they have never used an alternate theme.
It still has 47 referencing modules, so removing it is its own task rather than something a post
picks up in passing.

**Post canvas is chosen in Canva and varies.** It has usually been a warm off-white near `#FAF8F5`
(the `jersey` theme), and has been as dark as `#E9E5E1`. Charts are exported transparent and sit on
whatever background the page uses, so chart colors need to read against a light, low-saturation
ground — that constraint is real; the exact hex is not. Don't fail a page for missing a specific
canvas value.

⚠️ **The quietest chart grey has to survive the whole canvas range, not the lightest end of it.**
A gridline picked to look right against `#FAF8F5` can disappear entirely one page later. The
three-point-leaders chart shipped `#E6E2DB` gridlines that were invisible on an `#E9E5E1` page —
a contrast ratio of **1.03**, which is the same colour to a reader, and the failure looks like the
lines were never drawn rather than like a colour that needs adjusting. Check the faintest element
against the *darkest* canvas in use: `#D8D2CA` holds at 1.20 there while staying light at 1.42 on
`#FAF8F5`. Ordering is what carries a grey hierarchy, so move the whole ladder together rather than
darkening one rule.

The same failure recurs one level up, in Canva type. The three-point-leaders page shipped its title
and footer in `#A19B92` — contrast **2.20** on an `#E9E5E1` canvas, against 14.7 for the chart's own
labels, so the headline was seven times weaker than the data it introduced. **Page text carrying
source, coverage or qualification should clear roughly 4.5:1 on whatever canvas is in use**, because
§7 requires those lines to survive reposts and screenshots and Instagram's compression eats faint
small type first.

Settled values for the `#E9E5E1` canvas: **subtitle `#5F5B57`** (5.37) and **footer `#7A736C`**
(3.73), chosen by the user 2026-09-01. The footer sits under the 4.5:1 guide by deliberate choice —
it is a legibility-for-quietness trade the user made with the numbers in front of them, not an
oversight, so don't re-raise it per post. `#948D86` (2.61) and `#A19B92` (2.20) were both rejected as
too faint.

**Get a quieter tier from size and weight, not from a paler grey.** Lighter and legible are the same
dial, so tone-only hierarchy has nowhere to go before it becomes unreadable — and tone is exactly the
signal that breaks when the canvas moves. The chart's own reference lines separate by dash length and
line weight for this reason, and the same applies to a subtitle against a footer.

**Magnitude colormap** (`craft.MAGNITUDE_CMAP`): light neutral `#F2EAE8` → `#CE1141` → deep red
`#7E0C2B`. Use when a bar or cell fill encodes magnitude.

⚠️ The table diverging colormap (`NET_CMAP`) runs red-to-green — colorblind-unsafe. Mitigated by
always printing the sign (`force_sign`). Revisit if a table post ever leans on color alone.

### Alternate themes (retired)

`house.THEMES` carries four alternates beyond `jersey`. **None has ever been used**, confirmed by the
user 2026-09-01, and the account does not run on a fixed canvas at all — see the rule above. The
table is retained only as a record for the legacy renderers still importing it.
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

- **Export transparent.** The chart carries no background; the Canva page supplies the canvas.
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
- **A quadrant key names an archetype, never a verdict.** A player in a low-volume, low-reward
  corner is doing a different job, not failing at this one. "DRIVES A LOT, NO WHISTLE" describes a
  pattern; "CAN'T FINISH" grades a player the data cannot grade.
- **Size a quadrant panel from the data, not the data range.** A key pinned to a panel corner covers
  the outlier that corner exists to describe — the league's most extreme foul-drawer once rendered
  underneath his own quadrant pill and disappeared. The fix is axis headroom past the extreme point,
  not moving the key somewhere it means less.
- **Figures over a court diagram sit on a card, sized to the text it holds.** Page-coloured fill
  (`#FAF8F5`) with a hairline warm-grey edge, so the label reads as resting on the floor rather than
  as a second block of colour. Three treatments were tried on `scoring_by_location.py` before this
  one: a text halo (invisible on the page but it fought the geometry), bare text over unbroken lines
  (a court line runs straight through the digits), and cutting a gap in the line behind each label
  (the broken boundary looked like a rendering fault). Size the card from the *measured* text extent
  after layout, never a guess — the widest string differs per slide (`1.40 PPS` against `351 FGA`)
  and shrinks again wherever chips are compacted. Faces stay above the card and may cover a line;
  an opaque crop hides it cleanly.

**Court diagrams** (`scoring_by_location.py`): a light Bulls-red floor (`#F6DCE1`), one step deeper
for the paint (`#EFC6D0`) and deeper again for the restricted area (`#E5A9B8`), with every line —
painted court geometry and analytical zone divider alike — in near-black. The red floor is what
carries the red/black/off-white thumbnail read, so figures on it stay black rather than red.

**Every shot-chart court uses the same complete landmark set:** a thick six-foot backboard sitting
1.25 feet behind the center of the correctly sized 18-inch rim, with its short connector stopping
at the rim's rear edge, plus the restricted-area D,
lane-space ticks, sideline hashes, the free-throw circle, and the full three-point line. Contrast may
change with the data layer — light over saturated ladder bands and Bulls black over the pale hex map
— but the court geometry does not.

**Hex efficiency uses five fixed FG%-versus-NBA bands, not a gradient:** well below (dark blue,
below −7.5 percentage points), below (light blue, −7.5 to −2.5), approximately average (yellow,
−2.5 to +2.5), above (orange, +2.5 to +7.5), and well above (dark red, above +7.5). Fixed,
symmetric cuts make “average” stable across teams and players and avoid presenting shade-level
precision that the smoothed neighborhood estimate cannot support. Location already distinguishes
two-point and three-point areas, so relative eFG% would mostly amplify the same three-point result
by 1.5 rather than add new information.

Hex marks use the fuller, deliberately overlapping scale: maximum radius is 96% of the nominal hex
bin radius, with a 25%-of-maximum floor so qualified three- to seven-attempt cells grow along with
the rest of the map instead of remaining pinpricks. Area grows with attempts through the middle of
the scale and caps at the 97.5th percentile. Draw high-volume marks first and smaller marks above
them, with a restrained sub-pixel shadow and a 0.30-point white hairline. The layering and seam keep
overlapping colors distinct without turning the map into a white grid. Clip the entire mark layer
to the sidelines and baseline; edge-bin centers remain in their true locations, but no part of a
shot mark may appear outside the court.

**The twelve-zone chart reuses the same five-band grammar as area fills, but tightens the outer
cuts to ±5 percentage points and runs them red → yellow → green.** Dark red is −5 or worse, light
red is −5 to −2.5, yellow is −2.5 to +2.5, light green is +2.5 to +5, and dark green is +5 or
better. Five points within one named zone is already substantial: about 10 points per 100 attempts
for a two-point zone and 15 for a three-point zone. The symmetric cuts keep praise and criticism at
the same bar. Hexes retain their ±7.5 outer cuts because smoothed local cells are a different,
noisier mark; zones pool an entire named region and print the exact gap and raw count.

**Left and right follow NBA's source labels, not the viewer's screen.** NBA defines those labels in
its basket-at-the-top shot-chart view. Our conventional court puts the basket at the bottom, which
is the same court turned around: NBA Left therefore appears on the viewer's right, and NBA Right
appears on the viewer's left. Keep the source label, makes, attempts, and league comparison intact;
mirror the horizontal coordinate only once, at the shared render boundary in
`bulls.graphics.court.nba_to_basket_bottom_px`. Tests pin all four left/right zone pairs so a future
renderer cannot quietly restore the unmirrored shortcut.

Green-means-better is only honest because every figure on that chart is measured against the league
*in the same zone*. On a raw FG% map it would be nonsense — the rim would always be green and the
arc always red. It also settles a clash the hex scale created: the zone chart already prints each
gap in green or red beneath its figure, so a blue fill sat above a red delta with both meaning
"below league". `--palette hex` still renders the blue scale for comparison.

The cost is real and accepted: red and green are the common colour-blindness pair. It survives here
because direction is carried redundantly in text — every rated zone prints a signed number — and
because the two ends differ in lightness as well as hue. Keep that if the palette is ever retuned;
equal-lightness ends would leave a dichromat unable to tell which extreme they were looking at.

Three rules keep filled zones legible where floating marks needed none. **Type colour is computed
from the fill's luminance, not chosen by hand**, because the scale runs dark blue → pale blue →
yellow → orange → dark red and the readable ink therefore flips twice across it; a hand-kept list
rots the moment a colour moves. **Neighbouring zones are separated by a cream hairline**, because two
adjacent zones can land in the same band and would otherwise read as one region.
Those hairlines are **solved from geometry, never traced from the classified
grid** — tracing is right for a fill and wrong for a line, and it left white
stubs hanging mid-zone where a contour closed on itself, plus a faint second
edge beside every black court line it ran along. Only the dividers the floor
does not already paint get a hairline: the mid-range rays, the two above-the-arc
rays, and the corner break. The arc, corner lines, paint edges and free-throw
line are drawn in black already, and a white seam beside them is a duplicate. And **the sidelines
run the full drawn depth** on this chart alone: `draw_half_court` stops them at 11 ft, which is fine
under floating marks and reads as a colour bleed under fills.

**Zone blocks carry no zone name.** A court is a diagram the reader already knows, so a caption over
the top of the key spends a line of type restating the picture — twelve times over. Position is the
attribution instead, which makes position load-bearing: **every block must sit inside the region it
reports**, and `tests/test_zone_charts.py` asserts it by running each anchor back through the
classifier. The rim and the two corner blocks used to sit below the baseline, which only worked while
they were captioned; removing the captions moved them onto their own zones.

**Figures sit on cream pills, four lines:** makes over attempts with the shooting percentage in
brackets (`11/32 FG (34.4%)`), its gap to league average in green above / red below ending in
"vs LA", then the zone's share of all subject FGA and its signed gap to the NBA share, also ending
in "vs LA". Both figures take
the same size, so neither shooting nor shot diet outranks the other — but **shooting leads, because
the fill is shooting.** A zone's colour is its FG% against the league, so the first line of the pill
has to be the figure that colour is about; leading with shot share made the reader hunt past it for
the number the region was already shouting. Shot share is the better complement here because it
isolates location preference; attempts per 75 mixed that preference with the player's overall usage.

The makes and attempts sit in front of the percentage rather than behind a floor. "11/32 FG
(34.4%)" lets a reader see how much to trust the 34.4% themselves, which is what makes a grey
zone informative instead of something they have to take on faith — the count explains why the zone
did not earn an efficiency colour. A
compact two-line variant (`--pill counts`) drops to the shooting pair alone for a simpler chart that
gives up the shot-diet comparison.

For a chart placed smaller inside a carousel page, the optional **large pill** keeps the same four
lines but increases the first and third figure lines to 10 points while leaving both comparison
lines at 7.5 points. The comparison lines sit slightly farther from the figures above them, and the
four-line text block receives a small downward optical correction so its visible top and bottom
padding read as balanced.
Its vertical spacing grows with the type, and the card is measured from the rendered strings before
drawing, so larger figures never sacrifice padding. The standard four-line pill remains the default.

An optional overall-summary row may sit below the legend when the page needs the player's headline
line carried by the verified asset rather than retyped in Canva. It contains total FGA, eFG%, and
3PT%, with no league comparisons. A post may add PPG as a leading fourth card when scoring context
belongs in that summary; it must come from official box-score points and games because the shot log
contains no free throws. When a player has fewer than 20 total three-point attempts, the 3PT card
prints the 3PA count instead; a percentage on that sample would add false precision and prints `nan`
for a player with no threes. The one-line cards use the national-TV chart's darker Bulls-red vertical
gradient (`#B5123C` to `#7E0C2B`) and white type.

Gaps use a **true minus** (−, not a hyphen) and carry **no sign at all when they round to zero** —
`+.0f` renders a −0.4% gap as "−0%", a direction the printed number contradicts, so the sign is
decided after rounding rather than before.

The pill is what makes one ink and one colour set possible. Type laid straight on the fill had to be
recoloured per zone to stay legible, and the same figure changing colour zone to zone read as though
the colour meant something. On cream, colour means direction and nothing else. Pills **stack** into
one column rather than the rings chart's two: the four lines need less width than side-by-side pairs,
and three wide pills above the arc would need more room than the court has. A corner strip is 3 ft
wide, so its pill overhangs onto the neighbouring zone and is attributed by being centred on the
strip.

**A shooting gap only earns a colour when it is bigger than the doubt around it**, otherwise it
prints grey. Shooting borrows the fill scale's own ±2.5-point neutral band, so a zone painted
"about average" never carries a coloured gap — colour cannot contradict colour. Shot share uses the
same signed comparison grammar and green/red direction (`−10.6 vs LA`) because the comparison itself
is the point of the second pair.

Line spacing is set against line height, not by eye. Spacing is in canvas units and type in points,
and at this canvas's 150 dpi one point is 2.08 units, so a gap smaller than the type is an overlap —
which is exactly what three drafts shipped. The gap under a figure is deliberately tighter than the
gap to the next pair, so four lines read as two statements rather than one list.

**A zone below the colour floor is grey**, while its pill keeps all four figures at muted ink and
alpha. The pill preserves the descriptive result and exposes the sample; the ground declines to make
an efficiency judgement the sample cannot support. A zone with zero attempts uses the same grey but
prints only `0 FGA`, so it remains distinct from "measured and unrated." The legend keys the actual
floor as `Under N FGA`, making the rule checkable against every pill rather than hiding it behind a
verdict.

A **data-free cover silhouette** may reuse the exact twelve-zone geometry with every region in
semi-transparent neutral grey. It carries no pills, values, legend, or summary cards: its only job
is to preview the chart form before the next slide reveals the data. Court landmarks use solid
`#242424`, matching cover typography, while the analytical zone seams remain white. The silhouette
therefore reads as the same chart switching on, not as a different illustration.

A **data-free colour teaser** is the more energetic cover variant. It uses opaque fills sampled
from the established five-band zone palette in a seeded, illustrative shuffle, with the same
`#242424` court landmarks and white zone seams. Neighboring regions may not share a shade, because
they would visually merge into one zone. It carries no analytical labels or legend because the
placement does not represent player results; the fixed seed keeps the asset stable across reruns
while previewing how the completed chart will feel.

A reusable **single-colour cover court** may instead fill all twelve zones with one opaque Bulls
family red while retaining white seams and `#242424` court landmarks. The canonical options are
Bulls red (`#CE1141`) and its established light-red companion (`#E67C96`). These assets stay
player-neutral: filenames and the chart itself carry no player identity, values, or analytical
meaning, so Canva can reuse them as framing across future zone-chart posts.

A player-specific **data-colour cover** may use the real qualified zone fills while suppressing
every pill, value, legend, and summary card. Unlike the decorative teasers, its colors remain an
analytical claim: use the same player window, league baseline, palette, and low-volume floor as the
corresponding detail chart. It previews the actual pattern while reserving its interpretation and
supporting numbers for the data page.

Zone-chart labels use sentence case rather than all caps: `11.6% of FGA`, `Below`, `Above`, and
`Under 400 FGA`. Basketball acronyms remain uppercase (`FG`, `FGA`, `NBA`).

The filled court is closed across the top of its cropped depth. That horizontal rule is a chart
boundary, not a claim that the 33.5-foot analytical crop is the literal half-court line.

The **rim disc is 8 ft across**, but its pill uses the same type scale as every other zone. Earlier
drafts shrank it until the whole card fit inside the disc; the team chart fell to roughly 60% of the
standard size and became the hardest figure to read. The cream card may now cross the restricted-area
boundary slightly, just as corner pills overhang their narrow strips. Tight padding limits the
overlap, while the pill centre still attributes the figures to the rim.

Keep the hex-chart key visual and sparse in one two-column row: **Volume** on the left, with one
small and one large hex labeled **Less** and **More** beneath it; **FG% vs. NBA Avg** on the right,
with the five efficiency colors labeled **Below** and **Above** beneath it. Do not print subject
names, headshots, FGA, FG%, eFG%, 3PT%, or gray-cell qualification notes inside the chart asset;
those details belong in the accompanying Canva copy.
Place the key close beneath the baseline and crop the transparent export vertically around the
outermost shots and key. A chart asset is not a 4:5 post page: retain the full 1080-pixel court width,
but do not make Canva carry hundreds of pixels of empty transparent space above and below it.
Keep both sets of legend icons compact: the two volume examples and the five color chips should read
as continuous left-to-right scales, not as isolated symbols spread across the chart width.

Draw the court **only as deep as the furthest chip needs** — about 34 ft, a little past the
above-the-break labels — and crop the rest. Stopping right at the arc leaves a squat shape; running
all the way to the half-court line is honest but hands back a third of the frame as empty floor.
Trace zone dividers from the classifier rather than by hand, and blur the mask before contouring: a
raw 0/1 mask leaves every diagonal divider visibly stair-stepped next to the true arcs.

Two zone facts drive the layout, and both cost a rebuild to learn. The **mid-range band is shallow**
between the paint and the arc, so a full-size chip there covers a border — shrink those chips
instead. And **no chip needs a leader line** — three zones are too narrow to hold one (the rim and
the two 3 ft corner strips), but each can sit hard against its own zone instead: the corners just
past their sideline, where a chip still satisfies the corner zone's own rule, and the rim directly
above the basket with its face across the baseline and its figures tucked between the backboard and
the baseline. Adjacency points more cleanly than a line does, and it costs no ink. Reach for a
leader only when a chip can be neither in its zone nor against it.

**Draw the restricted area as the painted D, not as a disc** — a semicircle closing onto the
backboard with two short straight sides. Two traps: NBA *classifies* it as the full 4 ft circle, so
the sliver behind the board still counts (26 of 2,226 roster shots) though the D does not shade it;
and because the paint is a ring around it, tracing the paint's own mask redraws that full circle as
an inner edge. Merge the rim into the paint's mask before tracing, or the D arrives with a circle
stamped over it.

**Physical court families are NBA-owned; only the angular cuts are custom.** The black markings and
the coloured shapes share the regulation 4 ft restricted radius, 16 ft lane, free-throw line 15 ft
from the backboard, 23 ft 9 in arc, and 22 ft corner lines. For production rows, NBA.com's
`shot_zone` decides whether an attempt is restricted-area, paint, mid-range, corner three,
above-the-break three, or backcourt. Our continuous straight rays only subdivide Mid-Range into five
sectors and Above the Break 3 into three. This keeps the readable custom angles without moving a
shot across a real physical boundary. Backcourt attempts are excluded from the twelve half-court
fills and reported as coverage rather than silently assigned to the top of the key.

### Conditional cell fill in tables

`bulls/graphics/house.py` owns the red-white-green cell scale used by the Assist Leaders, Most
Impactful and rookie tables: `heat_fill(value, red_at, neutral_low, neutral_high, green_at)` plus
`HEAT_RED` / `HEAT_MID` / `HEAT_GREEN` and `heat_text_color`. Three rules make it behave.

**The midpoint is the canvas, not a yellow.** `HEAT_MID` is `#FAF8F5`, so a cell that says nothing
remarkable disappears into the page. A yellow midpoint made every ordinary value shout.

**Neutral is a band, not a point.** Everything between `neutral_low` and `neutral_high` stays blank.
With a single midpoint every cell except an exact tie takes some tint, and the middle of a table
shimmers pink and green at values that carry no meaning. The band is how a chart declines to comment.
Collapse the band onto `red_at` to make a column sequential — no red end at all, which is right for
counting stats where a low number is a role rather than a failure. A guard with 0.1 blocks is a
guard.

**Calibrate from the population, never from the chart's own range.** Min-to-max scaling hands the
midpoint to whichever single row happens to be extreme, so the colour ends up describing that outlier
instead of the field. Anchor on percentiles of the population the chart is about, or on a published
basketball reference (replacement level, league average). Where a statistic has a meaningful zero,
neutral belongs at zero; a negative number must never read as green.

**Where a statistic has drifted across eras, colour on the gap to that season's league value.** What
the cell *prints* is a separate decision, and both answers are in use:

- **Print the raw number** when the raw number is the one a reader recognises. The rookie table's
  `TS%` does this — 57.1% means something on sight, and the colour carries the era adjustment
  silently.
- **Print the gap itself** when the comparison *is* the point. `clutch_seasons_table.py` prints
  `RTS` — points above or below that season's league clutch average — because two identical 62.5%
  seasons twenty years apart were different achievements, and a table whose whole subject is
  cross-era ranking should say so rather than leave it to the shading.

**A column that already expresses a difference changes what its scale should be.** Percentile anchors
suit a raw measure with no natural midpoint; anything already relative pivots on zero, and its dead
band must straddle zero evenly. Swapping a cell from raw to relative therefore obliges you to
recalibrate — the old anchors keep *working*, which is exactly what hides the problem. Colouring
`RTS` on the population's own 25th/75th (−3.5 to +4.9) left an off-centre band where a −3 read as
unremarkable.

**The two ends need not match, and forcing them to can flatter one side.** The band straddles zero;
the ends are a separate question, each anchored at the same percentile of the real distribution. Clutch
plus-minus has a median of +12, not 0, because the players who take 100+ clutch shots are mostly on
winning teams — so its ends sit at −41.7 and +67.0, the 10th and 90th. Symmetric ends had graded every
negative season against a spread the field does not have, leaving a −25 at an 8% tint.

The ends may sit on either side of the band, so a column where low is good runs green downward with
no separate inverted code path.

### The accent card behind a ranking column

A table sorted by one metric marks that column with a single continuous rounded card in the accent
red — `draw_accent_card` in `bulls/graphics/house.py`. It tells a reader what the ranking means
before they read a header. Used by the game-score decade tables (Game Score) and the rookie
leaderboard (PRA/75).

Three details carry it. The card **outsets** past its column on every side and further at the top, so
it overlaps the header rule and reads as an object resting on the table rather than another cell in
it. No rule may **cross** the card — a line ruled over it cuts the shape back into cells and undoes
the point of drawing it as one block. And the fill is **flat accent**: what reads as a gradient is a
drop shadow offset down-right in a deeper red (`#8A1737` at 22%), which lifts the card without
introducing a second colour.

**The overlap needs the stacking order and the broken rule together, and one without the other is a
defect rather than depth.** The card must win the z-order against the header rule, *and* that rule
must stop at the card's edges (`ACCENT_CARD_OUTSET_X`, 8 px) — otherwise the black line shows through
the rounded corners the overlap exists to display. `clutch_seasons_table.py` shipped three wrong
combinations before the right one: card under the rule (a black line ruled straight across the pill),
then the card tucked entirely beneath the rule (no overlap at all), then the card raised without
breaking the rule. `bulls_rookie_leaderboard.py` is the reference implementation.

Row rules are the one line that may run **behind** the card rather than stopping at it, drawn below it
in the z-order so the card hides the covered segment. Two stubs dying a few pixels short of a rounded
corner read as a rendering fault; an unbroken rule under an opaque card looks identical where it
shows and is simpler where it does not.

**A column may claim a fixed margin off the card.** `clutch_seasons_table.py` reserves 22 px between
the pill and the first ordinary column, subtracted before the width weights are shared out — so
widening that margin narrows the ordinary columns instead of pushing the last one off the canvas.

One card per table. If two columns both look like the answer, the table has not decided what it
argues.

## 5. Faces (headshots)

The highest-stopping-power object on a chart — use sparingly.

⚠️ **The NBA CDN serves a player's *current* portrait, not the one from the season being charted.**
A post spanning several eras arrives with players in the uniform of a team they joined years later —
an all-time Bulls chart renders Butler in Warriors blue, Caruso in Thunder colors, Gibson and White
in Hornets teal. Nothing warns you; every id resolves. **Portraits stay full colour on their
transparent background** (confirmed 2026-08-05; desaturating them onto a warm tile was tried and
rejected the same day). Anchor the crop to the top to keep the jersey small, and expect the
off-brand colours rather than being surprised by them.

Three crops, and the difference carries meaning:

- **Circular, red-ringed** — `craft._make_circular_headshot` / `craft.headshot_label`. The ring
  (`border_color=(206, 17, 65)`, `border_frac≈0.045`) means "this is the payoff." At most one.
- **Bare square** — `house.square_headshot_label(ax, path, x, y, half_size, zorder=…)`, the
  landscape scatter family's plot marker. No ring: every plotted player is equal, so a ring would
  read as an emphasis the layer does not intend. Use `half_size=36` for a roster landscape.
  `house.ensure_headshots(nba_ids)` warms `house.HEADSHOT_CACHE` first; pass the ids in draw order
  and set each returned artist's `zorder` so overlapping faces stack predictably.
- **Top-anchored square** — `scoring_leaps.top_anchored_headshot_label`, for a ranked list of
  player-seasons. Same equal treatment as the bare square, but the crop is anchored to the top and
  tightened to the head and shoulders rather than the full portrait frame. This keeps current-team
  jerseys from becoming a distracting colour block on an all-time Bulls chart.

`bulls_on_court_landscape.py` and `current_roster_hot_spots.py` still carry their own square-crop
copies that differ (top-anchored crop, and a non-returning variant); fold them in — along with
`scoring_leaps.top_anchored_headshot_label`, which is a third copy of the same idea — when any of
these posts is next touched.
- Position so geometry does the pointing — the data line ends at the face.
- Missing headshots render as a neutral placeholder disc; builders never break.
- ⚠️ **NBA CDN headshots for new rookies are often a gray silhouette.** Check visually: ~12 KB is
  usually the silhouette, a real headshot is 50–200 KB. Fall back to the team's own CDN
  (nba.com/bulls article images are clean and unwatermarked), crop square around the face, and flag
  wire-photo licensing before using a non-NBA source.

## 6. Working From External References

When building from an external tutorial or visual reference, **reproduce the source's styling and
structure closely.** Swap in our palette and Helvetica; keep its layout, proportions, mark choices,
and visual logic.

Do not redesign it toward "our own direction" — the reason to work from a tutorial is that its
composition already works. Divergence should be a deliberate, stated choice, not a drift.

**Concentric-band charts get depth, not flat fills.** Where many bands abut — the `rings` and
`ladder` shot charts — each band is drawn as a stack of thin sub-annuli tinted lighter at its inner
edge, and `ladder` adds a soft cast shadow just outside each ring onto the larger one behind it.
Matplotlib has no blur, so both gradients are built from a handful of steps. This is not decoration:
30 flat abutting bands read as one mass, and the lift-plus-shadow is what separates them into
countable steps. Court markings on these charts drop to ~0.68 alpha and a thinner line, since they
sit on top of saturated data and should locate the reader rather than compete.

## 7. What Every Post Shares

Visual outcomes, whichever tool composes the page:

1. A light, low-saturation canvas at 1080×1350 (4:5). The exact background is Canva's to choose.
2. Red/black as the only *meaningful* colors — a thumbnail should read red + black + off-white before
   the title is legible.
3. A consistent type hierarchy with deliberate red emphasis. The faces themselves are set in Canva
   and may change between posts.
4. Visible authorship on every page; visible source, qualification, and coverage on every
   data-bearing page. These may move to fit the composition but never disappear — analytical honesty
   has to survive reposts and screenshots.
5. **One idea per post.** The title states it; if the title needs "and," it's two posts.
6. **Pretty *and* instantly legible.** The two-second bar rules out both ugly stat-dumps and
   beautiful-but-inscrutable analytics. When a detail would help a nerd but confuse a casual fan, the
   casual fan wins.
7. **Take the structure, not the look.** Adopt formats from the best accounts, rendered in our
   palette and type.

## 8. Brand Identity

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
`draw_fitted_title`, `draw_subtitle`, `draw_jersey_stripe`, `draw_footer`, `save_post`. Its compatibility
font helpers now resolve to Helvetica, matching the current chart layer. Reference implementation:
`scripts/prototypes/season_shape_post.py`.

**This is not the path for new posts.** It's documented so existing prototypes stay maintainable:

- 1080×1350, 60 px side margins, full-bleed axes, iterate 150 DPI / export 300 DPI.
- Jersey stripe: full-bleed 16 px band, pinstripes band 4 / trim_a 2 / band 4 / trim_b 2 / band 4.
- Title auto-fits to W−120 with a red outer stroke (7 pt) and white gap (3.5 pt); subtitle at
  y = H−168 with drawn tick separators; kicker at y = H−206.
- Footer pair on the y=40 baseline: `Data via nba.com` bottom-left (`FAINT`), `@chicagobullsdata`
  bottom-right (`MUTED`, x=1020).

Report-card component values from the Summer League report (`PLAYER_ROW_HEIGHT = 173` px, 118×52 stat
chips, 250×80 rail cards, `COURT_LINE` `#C9A8B5` on pale panels) live with that prototype.

The browsable HTML companion for this legacy system was retired after the move to Canva-first posts.

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
