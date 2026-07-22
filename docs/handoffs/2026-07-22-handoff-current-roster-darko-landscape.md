# ACTIVE — Current Bulls roster DARKO landscape

## Objective

Create a separate, forward-looking `@chicagobullsdata` post showing the current/upcoming Chicago
Bulls roster on a player-impact scatter:

- X-axis: DARKO Offensive DPM (`ODPM`), with better offense to the right.
- Y-axis: DARKO Defensive DPM (`DDPM`), with better defense upward.
- Population: the current Bulls roster, frozen and labeled with an explicit as-of date.

This is analytically distinct from the active backward-looking NBA.com post in
`docs/handoffs/2026-07-22-handoff-bulls-on-court-landscape.md`. The two posts may share a visual
family, but their metrics, claims, population logic, and source language must remain separate.

Structural inspiration: [Basketball University — 2026–27 Charlotte Hornets Impact Landscape](https://x.com/UofBasketball/status/2079719750964318415)

## Settled direction

- Use the **current/upcoming Bulls roster**, not everyone who played for Chicago in 2025–26.
- Use the current headline DARKO components: **ODPM on X** and **DDPM on Y**. Do not substitute
  NBA.com OffRtg/DefRtg, single-season on/off, Box DPM, or a home-built APM/RAPM model.
- Frame this as a **forward-looking current-player projection/estimate**, not a recap of Bulls team
  performance and not a guarantee of 2026–27 results.
- Both axes use the intuitive orientation **higher is better**: right is better projected offense;
  up is better projected defense. DARKO's current leaderboard treats positive ODPM and positive
  DDPM as better and its displayed DPM equals the offensive and defensive components added together.
- Start from the already approved chart-only visual family used by
  `scripts/prototypes/bulls_on_court_landscape.py`: warm rounded panel, simple axes and grid,
  player-centered marks, clean labels, and likely equal-size square-crop cutout headshots. Page
  framing can remain a Python chart/data asset plus Canva assembly.
- Keep the background flat and in the house system by default. The Basketball University gradient
  is structural inspiration, not a palette to copy. Do not revive a gradient unless a later review
  explicitly reopens it and the meaning of all four quadrants is clear.
- Credit DARKO prominently and include the data snapshot date because its ratings update nightly.
- Do not build the chart in this handoff session.

## What DARKO means

The official [DARKO About page](https://www.darko.app/about) describes DARKO as a machine-learning
player projection system designed to update daily. It is Bayesian, weights older games through
stat-specific decay, uses a modified Kalman filter and gradient-boosted model, and responds to new
information without an arbitrary last-X-games endpoint.

For this post, use the headline **DPM** components, not Box DPM:

- The site's metric tooltip defines **ODPM** as projected offensive impact on scoreboard
  differential.
- It defines **DDPM** as projected defensive impact on scoreboard differential.
- The headline DPM includes on/off evidence; Box DPM is the separate box-score-only flavor.
- Positive is favorable on both components. For example, the live leaderboard labels its largest
  positive values as “Best Offensive DPM” and “Best Defensive DPM.”

Use plain-language copy such as:

> DARKO's current estimate of each player's offensive and defensive impact

Avoid calling these values 2025–26 Bulls performance, Bulls-only impact, observed team ratings, or
an isolated record of what happened in Chicago. DARKO is a stabilized projection built from a
player's broader history and updates after team changes; an acquired player's value is not based
only on Bulls possessions.

The official page describes DPM as projected scoreboard impact but does not spell out the full unit
and baseline in the visible tooltip. Before printing “points per 100 possessions above average” or
labeling zero “league average,” verify that exact wording from a current DARKO first-party surface.
It is safe to use zero as an unlabeled neutral visual reference in an exploratory draft, but do not
attach an unverified baseline claim to it.

## Current roster check — 2026-07-22

The [official NBA Bulls roster page](https://www.nba.com/team/1610612741/roster) showed these 16
players when checked on **2026-07-22**:

- Tobe Awaka
- Jaylin Sellers
- Josh Giddey
- Dailyn Swain
- Rob Dillingham
- Caleb Wilson
- Nic Claxton
- Leonard Miller
- Zach Collins
- Matas Buzelis
- Norman Powell
- Noa Essengue
- Jalen Smith
- Tre Jones
- Isaac Okoro
- Patrick Williams

This is an offseason roster and can change. Re-fetch it immediately before analysis and print the
as-of date on the graphic or source line. Do not silently use the team field on DARKO's leaderboard
as the roster source; use the official NBA roster and join DARKO values to it by NBA player ID when
possible. Note that DARKO lists Nic Claxton as **Nicolas Claxton**, so name-only joins need an alias
or, preferably, should be avoided.

## Preliminary DARKO coverage check

The official [DARKO active leaderboard](https://www.darko.app/) was checked on 2026-07-22. It says
the data update nightly, supplies a `Download CSV` action, and exposes NBA player IDs in the live
data. Twelve of the 16 NBA.com roster entries had a current DARKO row:

- Josh Giddey, Rob Dillingham, Nicolas Claxton, Leonard Miller, Zach Collins, Matas Buzelis,
  Norman Powell, Noa Essengue, Jalen Smith, Tre Jones, Isaac Okoro, and Patrick Williams.

Four 2026 rookies did not have a live row:

- Tobe Awaka
- Jaylin Sellers
- Dailyn Swain
- Caleb Wilson

Do **not** place missing rookies at `(0, 0)`, estimate their values, or import NCAA/Summer League
metrics onto the same axes. DARKO's own documentation says it presently has no NCAA, Summer League,
or preseason data and begins learning about rookies as they play. The first draft should either:

1. plot the 12 players with DARKO values and carry a concise “DARKO not yet available for four 2026
   rookies” note; or
2. add a small separate `NO DARKO YET` roster rail outside the coordinate field if excluding those
   names makes the current-roster framing feel incomplete.

The first option is the cleaner recommended default. The missing-player treatment remains a user
decision before rendering.

## Data access and attribution constraints

- Prefer DARKO's first-party `Download CSV` action or live first-party table over a third-party
  mirror. Save a date-stamped working snapshot so the analysis remains reproducible after nightly
  updates.
- No stable documented public API or explicit reuse license was identified in this check. Avoid
  building a permanent scraper or redistributing a full DARKO dataset. A small, post-specific,
  attributed roster extract is the appropriate scope unless the site's terms or creator guidance
  establish broader permission.
- Retain `nba_id`, player name, current team, `o_dpm`, `d_dpm`, total `dpm`, and snapshot timestamp
  in the validated working table. Confirm `dpm` approximately equals `o_dpm + d_dpm` after rounding.
- The on-graphic source should say **Data via DARKO · darko.app** and include the snapshot date. Do
  not use the NBA.com source credit from the other landscape.
- Use the official NBA roster page as the roster-membership source and DARKO as the metric source.

## Why this cannot be mixed with the NBA.com landscape

| Question | NBA.com on-court landscape | DARKO current-roster landscape |
| --- | --- | --- |
| Time direction | Backward-looking 2025–26 recap | Forward-looking current estimate |
| Population | Players with qualifying 2025–26 Bulls minutes | Current Bulls roster as of a stated date |
| Metric | Bulls team OffRtg/DefRtg during a player's Chicago minutes | Projected player ODPM/DDPM |
| Team scope | Chicago stint only | Player history across teams, stabilized by DARKO |
| Interpretation | Shared five-player team outcome | Model-estimated player scoreboard impact |
| Source | NBA.com/stats | darko.app, plus NBA.com for roster membership |
| Qualification | Minimum Bulls minutes | Available current DARKO value; missing rookies disclosed |

Do not reuse the 500-Bulls-minute threshold, Bulls team-rating crosshairs, or “with him on the
court” language. Those are correct only for the retrospective NBA.com chart.

## Visual starting point

- Build a compact chart-only asset first, visually related to the approved Sticky Stats treatment.
- Use short axis labels `ODPM` and `DDPM`, with unobtrusive cues that right/up are better.
- Use equal-size square-crop player cutouts unless the user changes that choice. Equal size avoids
  implying that minutes, contract size, or total DPM controls portrait size.
- Keep quadrant labels plain and dot-free; keep player names readable without white outlines unless
  the actual background requires a deliberate contrast treatment.
- Use a flat jersey/warm panel with house ink, muted grid, and restrained Bulls red. Do not copy
  Basketball University's four-color field.
- Start without annotations. First inspect the actual spacing, clusters, and outliers; annotate only
  placements that remain genuinely interesting after understanding the model and current roster.
- If the four missing rookies are named, place them outside the scatter in a clearly separate
  treatment so “no model value yet” cannot be mistaken for average or zero impact.

## Open decisions

1. **Roster boundary:** all 16 names on NBA.com's roster page, or only standard/two-way players once
   training-camp contract status is settled? Recommended default: official NBA roster page as of the
   data snapshot, with the date printed.
2. **Missing rookies:** concise footnote or separate `NO DARKO YET` rail? Recommended default:
   footnote for the first draft.
3. **Reference lines:** unlabeled zero lines are the safest starting point. Confirm DARKO's exact
   baseline/unit before calling zero “league average.”
4. **Title:** likely direction is `HOW DARKO SEES THE CURRENT BULLS`, but title/subtitle should not
   imply certainty about final opening-night roster or actual 2026–27 results.
5. **Timing:** build now with an explicit 2026-07-22 snapshot, or wait until the roster is closer to
   opening night? The concept works now, but offseason roster churn should be visible in the date.

## Risks and honesty checks

- DARKO changes nightly; values can drift between analysis, Canva assembly, and posting.
- The current NBA roster can change during the offseason.
- Defense is generally harder to estimate cleanly than offense. Treat close DDPM placements as
  directional rather than creating a ranking claim from tiny differences.
- New or low-experience players have less evidence. DARKO explicitly says it learns about rookies as
  they play; availability is not the same as equal certainty for every player.
- A current team label is not a Bulls-only data filter. DARKO carries a player's prior history and
  accounts for changing teams.
- Do not describe the chart as a depth chart, rotation forecast, season projection, or expected team
  record. It is a roster map of current player-impact estimates.

## Clearest next action

In a fresh `create-bulls-post` session, re-fetch the official Bulls roster and DARKO snapshot on the
same date. Join by NBA player ID, reconcile the four missing rookies without assigning fake values,
and prepare a compact validation table with player, roster status/source, ODPM, DDPM, total DPM, and
snapshot date. Then inspect the real ranges and clustering before deciding zero-line labels,
annotations, or whether the scatter has enough separation for square headshots. Build one flat,
chart-only draft only after reporting what the data actually shows and confirming the missing-rookie
treatment with the user.
