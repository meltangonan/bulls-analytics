# Shot analysis contracts

Read for shot-data or court-family changes. `DESIGN.md` routes visual styling; source/coordinate
truth lives in `bulls/analysis/shot_maps.py` and `bulls/graphics/court.py`.

## Source labels and geometry

NBA shot coordinates are integer tenths of a foot, hoop at the origin. Use shared court geometry:
backboard y = −12.5, baseline y = −52.5, free-throw line y = 137.5. Integer coordinates may round
across an edge; production rows use NBA's basic `shot_zone` to adjudicate physical families.
`shot_distance` was verified as `floor(hypot(loc_x, loc_y)/10)` across 219,160 rows.

Keep `shot_zone`, `shot_zone_area`, `shot_type`, coordinates and distance in cached extracts.
`shot_zone` defines physical families; `shot_type` defines official 2/3-point value. They can disagree
at the arc: the DeRozan audit found five conflicts in 4,193 attempts, confirmed with play-by-play.
Use `source_zone_value_conflicts` to expose them. Never derive points, 3PA or eFG% from zone names.

`zone12_of_shots` retains NBA Restricted Area, Paint, Mid-Range, Corner 3, Above-the-Break 3 and
Backcourt families, applying custom rays only within Mid-Range and Above-the-Break 3. Coordinate-only
`zone_of` is for synthetic/non-NBA inputs. For ordinary NBA zone tables, group by NBA's own labels.
`detailed_zones` recognizes `Back Court(BC)` even when the basic label is Above the Break 3; exclude
and report backcourt attempts from the twelve half-court zones.

NBA area sectors vary with distance: one inside 8 ft, three from 8–16 ft (60°/120°), five beyond
16 ft (36°/72°/108°/144°). Our continuous twelve-zone rays differ deliberately. The baseline ray
runs through the corner break (`CORNER_BREAK_DEG`, ~22.13°); central cuts divide the remainder
into thirds (`MID_SECTOR_CUTS`). Rays through the paint corners were rejected because they made
the central above-the-break area disproportionately large.

Validate both physical-family totals and left/right attribution against independent source labels.
Family totals alone cannot catch swapped mid-range wings. The DeRozan source-family and area
crosstabs in `tests/test_demar_derozan_bulls_zone_charts.py` are the worked regression.

## Orientation

NBA names Left/Right from a basket-at-the-top view. A basket-bottom rendering reverses horizontal
placement. Use `nba_to_basket_bottom_px`; never swap stored labels or mutate the source coordinates.
The 2021-22 DeRozan Left Corner 3 (11/29) appears on the viewer's right; Right Corner 3 (7/28) on
the viewer's left. Center zones stay centered.

Angle-based wedges need the same transform: `180 − theta`, reversed interval endpoints, mirrored
label anchors/rotation/stacking. Test a real point inside each wedge against the shared coordinate
mapping. `polar_cells` keeps NBA angular cuts but moves the three-to-five-sector change to the
three-point line; classification and drawing use the same coordinates and shot type.

## Twelve-zone and tenure charts

Zone fill compares FG% against the league; shot share compares zone FGA / all subject FGA against
the same league fraction. Raw makes/attempts remain visible. Each season in `render_zonegrid` uses
its own season's league baseline, not one pooled comparison for every year.

The existing colour floors are display contracts:

| Subject | Floor | Reason |
| --- | --- | --- |
| Team | 400, `colour_floor(2.5)` | One standard error cannot move a band |
| Player | 20, `single_shot_floor(5.0)` | One make changes FG% by at most the full 5-point neutral span |
| Pooled player tenure | 20 × included seasons | Same per-season colour qualification |

The player floor is not a confidence claim: a shot can cross a narrower 2.5-point outer band.
At/above the floor show the efficiency colour; below it retain the full muted descriptive pill;
zero attempts show `0 FGA`. Report rated share so a visually grey chart can be interpreted honestly.
Do not substitute shares of player/league attempts for this colour floor: they give different
precision to identical percentages. An earlier 45-attempt player floor greyed 71% of zones.

A *leader within a bucket* is a different question from colouring a player's zone. In
`scoring_by_location.py`, 15% of the team's zone attempts is the qualification; top-N volume and
flat floors produced tiny or unrepresentative candidates when bucket sizes differed greatly.
Preserve the distinction rather than applying one threshold to both purposes.

Tenure pulls are Bulls-only, including trade seasons; reconcile official totals before any filtering.
Name seasons spent elsewhere rather than implying uninterrupted coverage. Pool league season frames
by concatenation; weighting by Hinrich's attempts changed no colour band (largest FG% change 0.21
points), so it added complexity without changing that result. Shared raw league baselines stay in
`cache/shot_charts`; save subject shots, official totals and printed splits with the post.

Historical feeds can contain legitimate shots missing every location field. Keep them in official
scoring totals, exclude/report them from spatial charts, and raise on partially missing location
fields or unknown zone labels. Reconciliation precedes this exclusion.

Summary cards use official PTS/GP for PPG, `(FGM + 0.5 × 3PM) / FGA` for eFG%, and `3PM / 3PA`
for 3PT%. Shot detail cannot reconstruct free throws. Cards are descriptive; zone values provide
the league comparison. Under normal consistent shot values, PPS within a zone repeats FG% scaled
by 2 or 3, so it is not an additional comparison signal.

## Distance ladder

The ladder compares distance bands; `pps` answers shot value, while `fg-rel` and `pps-rel` compare
with the league at that distance. A league chart rejects relative-to-itself metrics. Existing
rating floors are 40 attempts for team/league and 15 for player; overrides require a stated reason.
`--blank` is a neutral data-free cover, never a player's result.

Bands split at 24 ft: two-point attempts inside, threes outside. Separate the corner-three pocket;
otherwise distance-only bins give the inner band mostly corner threes or paint them with an
above-the-break value. Use `corner_mask`/`corner_split`; ring clipping must tile the same geometry.

Default bands are 2 ft: 21 of 29 adjacent league 1-ft bands were statistically indistinguishable.
Band widths must divide `LADDER_MAX_FT` (30) and `LADDER_TWO_MAX_FT` (24); exclude/report beyond
30 ft instead of making a catch-all outer band. `ladder_edges` must not readmit heaves under an
overridden width. Historical reference comparisons used a different 30+ outer bucket; don't force
agreement between differing coverage contracts.

Use fixed, clamped, symmetric scales. PPS centres on 1.00 and spans 0.80–1.20 in 0.05 steps;
centring on the league mean changes the claim. Preserve the glyph-ink/band alignment regression
rather than replacing measured positioning with cosmetic constants.
