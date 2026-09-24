# Shot-chart design

Read with [DESIGN.md](../../DESIGN.md) only for court-based work. This file describes the visual
contract. Source classification, units, coverage, and analytical derivation belong in the development
references and the post's Notion provenance. Shared court geometry lives in
[`bulls/graphics/court.py`](../../bulls/graphics/court.py); the main zone renderer is
[`current_roster_zone_charts.py`](../../scripts/prototypes/current_roster_zone_charts.py).

## Court geometry and labels

All newly rendered Bulls shot courts use black markings and the same visible landmark positions:
six-foot backboard 1.25 feet behind the center of an 18-inch rim, connector ending at the rim's rear
edge, restricted-area D, lane-space ticks, sideline hashes, free-throw circle, and full three-point line.
Physical dimensions follow NBA regulation:
four-foot restricted radius, 16-foot lane, free-throw line 15 feet from the backboard, 23-foot-nine-inch
arc, and 22-foot corner lines. The [NBA Rule No. 1 court diagram](https://official.nba.com/rule-no-1-court-dimensions-equipment/)
also sets the six-inch lane-space ticks and nearby hashes, the one-foot neutral-zone blocks,
and the three-foot sideline hashes. The selected chart treatment uses two ticks at 7 and 8 feet
from the baseline, singles at 11 and 14 feet, and no filled neutral-zone blocks. It is a visual
choice, not the complete regulation marking set. `draw_chart_court` and `chart_court_segments`
in the shared helper own the black ink and selected marks across standard, ring, ladder, and
scoring-by-location renderers. The helper also retains the complete official markings for a
regulation diagram. Different chart crops show different amounts of the court; only a crop reaching
the actual half-court line shows the center-circle semicircles. Older exported images do not change
until re-rendered. Change contrast for the data layer, not physical geometry.

**NBA Left appears on the viewer's right in our basket-at-bottom view.** Keep NBA's source label,
counts, and league comparison intact; mirror x exactly once through `nba_to_basket_bottom_px`.
Do not mirror already transformed coordinates. This matters for both zone placement and annotation.

Draw the restricted-area marking as a D. The source classification uses the full four-foot circle,
including behind the board. Merge rim into the paint mask before tracing a painted outline so the
classification circle does not become an extra court line. The production source's zone family owns
restricted area, paint, mid-range, corner three, above-the-break three, and backcourt; custom angles
only subdivide mid-range into five and above-the-break into three. Backcourt is excluded from the
twelve half-court fills and reported as coverage.

Court figures sit on text-measured cream cards, with restrained padding and a warm hairline when
needed. Size from rendered extents, not a guessed character count. Keep each zone label's anchor
inside its classified region; narrow rim/corner cards may cross boundaries while their centers
identify their zones. Avoid leader lines when positioning or adjacency can do the job. Scoring by
location uses pale red floor `#F6DCE1`, paint `#EFC6D0`, restricted area `#E5A9B8`, and black geometry
and figures. Do not carry that illustrative floor into a chart whose fills encode efficiency.

## Twelve-zone charts

Use five fixed bands for **FG% minus league FG% in the same zone**: dark red at −5 percentage points
or worse, light red between −5 and −2.5, yellow around zero (±2.5), light green between +2.5 and +5,
and dark green at +5 or better. Preserve renderer boundary handling at exact cut points. These
symmetric cuts compare performance at the same location; raw FG% must not use this better/worse
interpretation. `--palette hex` is a comparison option, not the default.

Signed figures repeat direction so the red/green palette remains interpretable without distinguishing
those hues. Preserve lightness differences between its ends. Compute ink contrast from fill luminance
where text actually sits on a fill. Figures sit on an opaque zone tag rather than on the fill, so
text colors keep one meaning across regions and a tag centred on a narrow corner strip still reads as
belonging to it. The house tag (`tagged` style, the default since 2026-09-22) is the page colour
`#FAF8F5` with near-square corners (3-unit radius) and a 1.1-weight `#242424` rule. Text set straight
on the fills with a white outline was tried and rejected: it reads as stickers and loses attribution.

Separate neighboring fills with cream geometry-derived seams only where the floor has no black
marking: mid-range rays, above-the-arc rays, and corner break. Never trace seam lines from the
classified grid; that creates stray contour closures and doubled borders. Filled masks can be
smoothed before contouring. Extend sidelines through the drawn depth and close the cropped top;
that top edge is a chart boundary, not the half-court line. Draw only as deep as the labels require,
roughly 33.5–34 feet.

Zone blocks omit zone names; position supplies the attribution. Use four lines in one column:

1. Makes/attempts and FG%, such as `11/32 FG (34.4%)`.
2. Signed shooting gap ending in `vs NBA`.
3. Share of all subject FGA.
4. Signed gap to league shot share, also ending in `vs NBA`. (`vs LA` read as Los Angeles.)

Shooting leads because the fill encodes shooting. Both primary figure lines share a size. Shooting
gaps within ±2.5 points stay neutral, matching the fill; shot-share gaps use the signed directional
grammar. Use a true minus and decide the sign after rounding so zero carries no false direction.
Sentence case applies to labels (`11.6% of FGA`, `Below`, `Above`, `Under 400 FGA`); retain acronyms.

Under-floor zones are gray, with all descriptive figures retained in muted, faded tags. Zero attempts
print only `0 FGA`; unavailable data must not become zero. The legend prints the actual qualification
as `Under N FGA`, under a `FG% vs. NBA avg` heading in `#242424`. Use the post's floor rather than silently inheriting another post's number.

`--merge-mid` pools the five mid-range regions into one zone, leaving eight. Use it only when the
subject barely shoots there and the band would otherwise spend most of the court's type on figures
too thin to read. The merged region is exactly NBA's own Mid-Range family, so merging removes our
angular subdivision and invents no new boundary: drop the internal mid-range seams, paint the band
one colour, and place the single pill above the paint inside the arc. Pool both the subject and the
league from raw attempts so the merged FG% is attempt-weighted rather than an average of five rates.
The merged zone faces the same floor as any other; pooling buys a readable figure, never a colour.

Measure card height and line spacing in the renderer's coordinate system: point sizes and canvas
units differ. Space the two figure/comparison pairs distinctly. An optional large pill uses 10-point
primary figures, 7.5-point comparisons, expanded spacing, and measured padding. Keep the rim's type
scale equal to the other zones, even if its card slightly crosses the eight-foot disc. Tight
mid-range placement may need compact cards; do not shrink only the most important figure to fit.

Optional verified summary cards below the legend contain total FGA, eFG%, and 3PT%, without league
comparisons. PPG may precede them and must come from official box-score points and games, because the
shot log contains no free throws. GP may lead (`summary_gp`, official games for the scoped team) so a
short or injury-shortened sample reads as short; print plain `N GP`, never `N of 82`, since a trade or
shortened season makes any denominator a claim about missed games. Below 20 total 3PA, print the
attempt count instead of 3PT%. The cards are rounded (14-unit radius) flat Bulls red `#CE1141` with
white type, sitting 40 units closer to the legend than the classic layout. Four cards keep their
210-unit width; five shrink to 172 so the row spans the court's own 920 units.

The earlier `classic` style (cream `#F5EFE2` bubbles, `vs LA`, red legend heading, `#B5123C` →
`#7E0C2B` gradient cards) is how every zone post through Hinrich was published. Pass
`"style": "classic"` only to reproduce one of those exactly; `ZONE12_STYLES` in
`scripts/make_shot_chart.py` owns both.

## Covers and season grids

Distinguish decorative previews from data-bearing colors:

| Form | Contract |
|---|---|
| Neutral silhouette | Same zones, semitransparent gray, black landmarks, white seams; no numbers or legend |
| Illustrative color teaser | Seeded shuffle of the five-band palette; no adjacent identical shades or analytical claims |
| Reusable single-red court | Opaque `#CE1141` or `#E67C96`; player-neutral name and content |
| Actual data-color cover | Same subject window, league baseline, palette, and floor as the detail chart; suppress pills and legend |
| Season grid | One actual data-color court per season, compared with that season's league; label the season only (per-season counts belong on the season slides) |

Bare courts crop to the court baseline, rather than retaining the detail chart's empty legend space.
For a tenure grid on a portrait page, use three columns, fit scale to available rows and labels,
center a short last row, and scale court-line weights down with the court. Gray must remain
explainable by the visible attempts and qualification. Actual data-color covers and grids still
need source, coverage, and qualification on the Canva page.

## Hex efficiency

Use five fixed **FG%-versus-NBA** bands: dark blue below −7.5 points, light blue to −2.5, yellow
within ±2.5, orange to +7.5, dark red above +7.5. The wider outer cuts reflect noisier local
neighborhood estimates. Preserve source/renderer exact-boundary behavior. Relative eFG% would mostly
multiply the three-point comparison by 1.5; use plain relative FG% for this spatial comparison.

Maximum hex radius is 96% of nominal bin radius, minimum 25% of that maximum. Area grows with
attempts and caps at the 97.5th percentile. Draw high-volume marks first and small marks above them,
with a restrained subpixel shadow and 0.30-point white seam. Clip marks to baseline and sidelines
without moving edge-bin centers.

Use a compact two-column key: **Volume** with small/large hexes labeled **Less/More**, and
**FG% vs. NBA Avg** with five chips labeled **Below/Above**. Place it close below the baseline and
crop around actual shots plus key, retaining the full 1080-pixel court width. Subject names,
headshots, headline totals, and qualification copy belong in Canva, not inside this key.

## Rings and ladders

Concentric bands use thin tinted sub-annuli to distinguish adjoining bands; ladder charts add a
soft stepped shadow outside each ring. Do not flatten an established many-band chart into one
indistinct mass. Court markings over saturated bands use thin, opaque black lines.
