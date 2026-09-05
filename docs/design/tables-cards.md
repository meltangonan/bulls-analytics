# Tables, ranking cards, and portraits

Read with [the current chart contract](../../DESIGN.md) when changing these components. Reuse the
small helpers below; the post still chooses its columns, thresholds, dimensions, and story.

## Existing components

| Component | Shared code | Working examples |
|---|---|---|
| Centered table cell, optional fill | `craft.draw_table_cell` in [craft.py](../../bulls/graphics/craft.py) | [Rookie leaderboard](../../scripts/prototypes/bulls_rookie_leaderboard.py), [chronological rookie table](../../scripts/prototypes/bulls_rookie_chronological_table.py) |
| Two-line metric box | `craft.draw_metric_badge` in [craft.py](../../bulls/graphics/craft.py) | [Lineup rORTG](../../scripts/prototypes/bulls_lineup_rortg.py), [rDRTG](../../scripts/prototypes/bulls_lineup_rdrtg.py) |
| Continuous ranking-column card | `house.draw_accent_card`, `accent_card_bounds` in [house.py](../../bulls/graphics/house.py) | [Rookie leaderboard](../../scripts/prototypes/bulls_rookie_leaderboard.py), [clutch seasons](../../scripts/prototypes/clutch_seasons_table.py) |
| Conditional cell color | `house.heat_fill`, `heat_text_color` | Same table examples |
| Square portrait | `house.square_headshot_label` | [Lineup rORTG](../../scripts/prototypes/bulls_lineup_rortg.py) |
| Top-anchored portrait | `house.top_anchored_headshot_label` | [Scoring leaps](../../scripts/prototypes/scoring_leaps.py), [three-point leaders](../../scripts/prototypes/three_point_leaders.py) |
| One emphasized portrait | `craft.headshot_label` | Circular red-ringed crop; at most one payoff |

Call signatures and geometry defaults live in the helpers. Choose the closest example and reuse its
component, rather than importing a helper from another post or copying its drawing loop. Keep a
post-specific layout local until it has real repeat users.

## Table grammar

Dense stat tables use clean alternating rows, sorted by the story metric. Do not color every column
by magnitude. `craft.MAGNITUDE_CMAP` (`#F2EAE8` → `#CE1141` → `#7E0C2B`) remains available for a mark
whose magnitude genuinely is the point. Print signs where color expresses a difference; the existing
red/green scales must never carry direction alone.

Conditional fills have a **neutral band**, not a single midpoint. `heat_fill` blends red `#D64545`
and green `#3FAE63` toward cream `#FAF8F5`; values inside the band stay neutral. That cream is a cell
fill, not a requirement for the Canva background. Use `heat_text_color` for readable text.

Calibrate from the eligible population or a meaningful basketball reference, never just the displayed
rows' minimum and maximum. For counting stats, a low value may describe a role rather than failure;
a sequential scale can omit the red end by collapsing its band onto `red_at`. Low-is-good measures
can reverse the endpoint values without a separate rendering path.

For a relative metric, center the neutral band on zero. The ends may be asymmetric when equal
population percentiles are asymmetric; a zero-centered band does not require equal endpoints.
Recalibrate when switching a printed metric from raw to relative. For era-sensitive values, color
on the gap to that season's league baseline. Print raw values when familiar units help the reader
(e.g. TS%); print the gap when cross-era comparison is itself the claim (e.g. rTS).

## Cards and boxes

A ranking table may use **one continuous red card** behind its defining column. It outsets past the
column and overlaps the header boundary. Draw it above the header rule and break that rule at the
card's outer bounds: either measure alone leaves a visible line through the rounded corners.
Row rules may run behind the opaque card. The fill is flat red; its restrained deeper-red shadow
provides depth. Use the helper's measured bounds to reserve a gap before neighboring columns, then
allocate remaining widths within the canvas.

A two-line metric badge is for a ranked list's main number and its short qualifier. Reuse
`draw_metric_badge`; it does not choose the metric or convert units. Keep different text structures
local until they have a second real consumer. Court-label pills are measured to their rendered text;
see [shot charts](shot-charts.md) for their four-line grammar.

## Portraits

Keep portraits full color on a transparent background. The NBA CDN supplies a player's **current**
portrait, so historical charts may show another team's jersey. A top-anchored crop limits that
jersey without recoloring it. Equal-ranked players get equal unringed crops; a circular red ring
means deliberate emphasis. Position portraits so geometry identifies the associated row or mark,
and set draw order explicitly when faces overlap.

Warm `house.HEADSHOT_CACHE` with `ensure_headshots`, then use the appropriate shared crop. Missing
portraits must not break a builder. Inspect new-rookie images visually: a successful CDN response can
still be a silhouette. A Bulls article image can provide an alternative; preserve source attribution
and check rights before adopting a non-NBA wire photo.
