# Shot-chart design

Read with [DESIGN.md](../../DESIGN.md) only for court-based work. This file describes the visual
contract. Source classification, units, coverage, and analytical derivation belong in the development
references and the post's Notion provenance. Shared court geometry lives in
[`bulls/graphics/court.py`](../../bulls/graphics/court.py); the main zone renderer is
[`current_roster_zone_charts.py`](../../scripts/prototypes/current_roster_zone_charts.py).

## Court geometry and labels

All shot courts share the complete landmark set: six-foot backboard 1.25 feet behind the center of
an 18-inch rim, connector ending at the rim's rear edge, restricted-area D, lane-space ticks, sideline
hashes, free-throw circle, and full three-point line. Physical dimensions follow NBA regulation:
four-foot restricted radius, 16-foot lane, free-throw line 15 feet from the backboard, 23-foot-nine-inch
arc, and 22-foot corner lines. Change contrast for the data layer, not physical geometry.

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
where text actually sits on a fill. The standard pill's cream background lets text colors keep a
consistent meaning across regions.

Separate neighboring fills with cream geometry-derived seams only where the floor has no black
marking: mid-range rays, above-the-arc rays, and corner break. Never trace seam lines from the
classified grid; that creates stray contour closures and doubled borders. Filled masks can be
smoothed before contouring. Extend sidelines through the drawn depth and close the cropped top;
that top edge is a chart boundary, not the half-court line. Draw only as deep as the labels require,
roughly 33.5–34 feet.

Zone blocks omit zone names; position supplies the attribution. Use four lines in one column:

1. Makes/attempts and FG%, such as `11/32 FG (34.4%)`.
2. Signed shooting gap ending in `vs LA`.
3. Share of all subject FGA.
4. Signed gap to league shot share, also ending in `vs LA`.

Shooting leads because the fill encodes shooting. Both primary figure lines share a size. Shooting
gaps within ±2.5 points stay neutral, matching the fill; shot-share gaps use the signed directional
grammar. Use a true minus and decide the sign after rounding so zero carries no false direction.
Sentence case applies to labels (`11.6% of FGA`, `Below`, `Above`, `Under 400 FGA`); retain acronyms.

Under-floor zones are gray, with all descriptive figures retained in muted pills. Zero attempts
print only `0 FGA`; unavailable data must not become zero. The legend prints the actual qualification
as `Under N FGA`. Use the post's floor rather than silently inheriting another post's number.

Measure card height and line spacing in the renderer's coordinate system: point sizes and canvas
units differ. Space the two figure/comparison pairs distinctly. An optional large pill uses 10-point
primary figures, 7.5-point comparisons, expanded spacing, and measured padding. Keep the rim's type
scale equal to the other zones, even if its card slightly crosses the eight-foot disc. Tight
mid-range placement may need compact cards; do not shrink only the most important figure to fit.

Optional verified summary cards below the legend contain total FGA, eFG%, and 3PT%, without league
comparisons. PPG may lead when needed and must come from official box-score points and games—the
shot log contains no free throws. Below 20 total 3PA, print the attempt count instead of 3PT%.
These one-line cards use a `#B5123C` → `#7E0C2B` vertical gradient and white type.

## Covers and season grids

Distinguish decorative previews from data-bearing colors:

| Form | Contract |
|---|---|
| Neutral silhouette | Same zones, semitransparent gray, black landmarks, white seams; no numbers or legend |
| Illustrative color teaser | Seeded shuffle of the five-band palette; no adjacent identical shades or analytical claims |
| Reusable single-red court | Opaque `#CE1141` or `#E67C96`; player-neutral name and content |
| Actual data-color cover | Same subject window, league baseline, palette, and floor as the detail chart; suppress pills and legend |
| Season grid | One actual data-color court per season, compared with that season's league; label season and attempt count |

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
indistinct mass. Court markings over saturated bands use thinner lines and approximately 0.68 alpha.
