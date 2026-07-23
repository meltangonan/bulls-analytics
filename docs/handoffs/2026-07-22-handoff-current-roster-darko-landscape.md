# CLOSED — Current Bulls roster DARKO landscape parked for possible monthly reuse

## Parked outcome — 2026-07-23

- The verified roster-only working table, tested Python chart generator, generated chart assets,
  and Canva draft are retained.
- The user chose not to publish the July edition after Basketball University posted a substantially
  overlapping Bulls/DARKO impact landscape at 12:19 p.m. CT on July 23:
  <https://x.com/UofBasketball/status/2080342151305507156>.
- Keep the catalog card `Parked`, not `Mocked` or `Posted`. No approved 1080×1350 Canva export was
  returned to the repository, so nothing belongs in `docs/mocks/` yet.
- The Canva starting point is `2026-07-23 Bulls Impact`, design ID `DAHQODG5o7E`
  (<https://www.canva.com/design/DAHQODG5o7E>). The full edit-share token is intentionally not
  stored in the repository.
- Possible restart: treat this as a manual monthly roster/DARKO check-in. Re-fetch the official
  NBA.com roster and full-precision DARKO data on the same date, preserve unavailable players as
  missing, and proceed only when the new snapshot offers a timely change or a distinct Bulls angle.
  Do not schedule automated publication.

**Status:** The July draft is intentionally held and should not resume automatically. The remaining
sections are retained as implementation and analytical context; any earlier “next session”
instructions are superseded by the parked outcome above.

## Objective

Create a separate, forward-looking `@chicagobullsdata` post showing the current/upcoming Chicago
Bulls roster on a player-impact scatter:

- X-axis: DARKO Offensive DPM (`ODPM`), with better offense to the right.
- Y-axis: DARKO Defensive DPM (`DDPM`), with better defense upward.
- Population: the official current Bulls roster, frozen and labeled with an explicit as-of date.

This is the forward-looking companion to the backward-looking NBA.com post documented in
`docs/handoffs/2026-07-22-handoff-bulls-on-court-landscape.md`. The posts may share a visual family,
but their metrics, claims, population logic, reference lines, qualifications, and source language
must remain separate.

Structural inspiration: [Basketball University — 2026–27 Charlotte Hornets Impact Landscape](https://x.com/UofBasketball/status/2079719750964318415)

## Finalized brief

- Use the **official current Bulls roster**, not everyone who played for Chicago in 2025–26 and not
  the team field on DARKO's leaderboard.
- Use the current headline DARKO components: **ODPM on X** and **DDPM on Y**. Do not substitute
  NBA.com OffRtg/DefRtg, single-season on/off, Box DPM, or a home-built APM/RAPM model.
- Frame the post as a **current forward-looking estimate**, not a recap of Bulls performance, a
  depth chart, a rotation forecast, or a guarantee of 2026–27 results.
- Both axes use the intuitive orientation **higher is better**: right is better projected offense;
  up is better projected defense.
- Use zero lines as unlabeled neutral visual references. Do not label zero “league average” or print
  a points-per-100 unit unless a current first-party DARKO surface explicitly supports that wording.
- Plot the 12 roster players with a live DARKO value. Do not assign fake values to the four missing
  rookies or place them at `(0, 0)`.
- Handle the four missing rookies with the finalized Canva footnote below, not a separate roster
  rail.
- Start from the approved chart-only visual family in
  `scripts/prototypes/bulls_on_court_landscape.py`: warm rounded panel, simple axes and grid,
  equal-size square-crop headshots, clean labels, and a flat jersey/warm background.
- Start without annotations. Inspect the real spacing and clusters first; add a callout only if the
  draft shows a placement that genuinely benefits from explanation.
- Produce a verified Python chart/data asset for Canva assembly. The user will add the page framing
  and rookie footnote in Canva.
- Credit DARKO prominently and print the roster/data snapshot date because the ratings update
  nightly and the offseason roster can change.

## Finalized copy deck

Use these as the starting words for the Canva page:

- **Title:** `HOW DARKO SEES THE CURRENT BULLS`
- **Subtitle:** `DARKO's current estimate of each player's offensive and defensive impact`
- **X-axis:** `ODPM` with a restrained cue that right is better.
- **Y-axis:** `DDPM` with a restrained cue that up is better.
- **Source line:** `Current roster via NBA.com · Player impact via DARKO · Snapshot: [actual date]`
- **Rookie footnote:** `DARKO ratings are not yet available for 2026 rookies Tobe Awaka, Jaylin Sellers, Dailyn Swain, and Caleb Wilson.`

The rookie footnote is settled. The next agent should give the user the exact sentence with the chart
asset, but should not try to typeset it into the Python chart because the user will add it in Canva.

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
- Positive is favorable on both components. The live leaderboard labels its largest positive values
  “Best Offensive DPM” and “Best Defensive DPM.”

Use plain-language framing such as:

> DARKO's current estimate of each player's offensive and defensive impact

Avoid calling these values 2025–26 Bulls performance, Bulls-only impact, observed team ratings, or
an isolated record of what happened in Chicago. DARKO is a stabilized projection built from a
player's broader history and updates after team changes; an acquired player's value is not based
only on Bulls possessions.

## Official roster snapshot — 2026-07-23

The [official NBA Bulls roster page](https://www.nba.com/team/1610612741/roster) showed these 16
players when refreshed on **2026-07-23**:

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

This is an offseason roster and can change. Re-fetch it immediately before analysis, use the same
date for the DARKO snapshot, and print that date on the final page. Note that DARKO lists Nic
Claxton as **Nicolas Claxton**.

## Validated DARKO snapshot — 2026-07-23

Twelve of the 16 official roster entries had a live DARKO row. These values were read from the
full-precision data powering DARKO's public leaderboard; the one-decimal columns are the intended
display values:

| NBA ID | Player | DARKO team field | ODPM | DDPM | DPM |
| ---: | --- | --- | ---: | ---: | ---: |
| 1630188 | Jalen Smith | Chicago Bulls | +0.4 | +0.7 | +1.2 |
| 1626181 | Norman Powell | Miami Heat | +1.4 | -0.9 | +0.5 |
| 1630581 | Josh Giddey | Chicago Bulls | +0.7 | -0.5 | +0.2 |
| 1628380 | Zach Collins | Chicago Bulls | -1.2 | +1.2 | +0.0 |
| 1630200 | Tre Jones | Chicago Bulls | +0.6 | -0.9 | -0.3 |
| 1641824 | Matas Buzelis | Chicago Bulls | -0.2 | -0.7 | -0.8 |
| 1631159 | Leonard Miller | Chicago Bulls | -0.1 | -0.8 | -0.9 |
| 1630171 | Isaac Okoro | Chicago Bulls | -0.6 | -0.6 | -1.2 |
| 1629651 | Nicolas Claxton | Brooklyn Nets | -1.6 | -0.1 | -1.7 |
| 1642855 | Noa Essengue | Chicago Bulls | -1.4 | -0.3 | -1.7 |
| 1630172 | Patrick Williams | Chicago Bulls | -2.2 | -0.5 | -2.7 |
| 1642265 | Rob Dillingham | Chicago Bulls | -2.1 | -0.7 | -2.8 |

Treat this table as a reproducibility and sanity-check reference, not permission to skip the
same-day refresh. DARKO updates nightly.

Four official-roster rookies had no live DARKO row:

- Tobe Awaka
- Jaylin Sellers
- Dailyn Swain
- Caleb Wilson

DARKO's documentation says it presently has no NCAA, Summer League, or preseason data and begins
learning about rookies as they play. Do not place these players at `(0, 0)`, estimate their values,
or import another metric onto the DARKO axes.

## Data-access findings and implementation boundary

The 2026-07-23 live check resolved how to obtain usable values:

1. DARKO's `CHI` team filter is **not** a valid roster source. It returned 18 names and reflected
   stale team assignments; most importantly, Powell remained assigned to Miami and Claxton to
   Brooklyn.
2. DARKO's first-party `Download CSV` control works, but the downloaded impact columns were rounded
   to whole numbers even though the live table displays tenths. That precision loss is unacceptable
   for this scatter because it would create false overlaps.
3. The public leaderboard response contains the full-precision records powering the table,
   including `nba_id`, `player_name`, `team_name`, `dpm`, `o_dpm`, and `d_dpm`.
4. The appropriate solution is a small, post-specific extractor that reads the current public
   leaderboard response, retains only the official Bulls roster, and saves a date-stamped working
   snapshot. Do not build scheduled automation, a permanent general-purpose scraper, or a mirror of
   the full DARKO dataset.
5. No stable documented public API or explicit reuse license was identified. Keep the extract
   roster-sized, attribute DARKO prominently, and do not redistribute the complete source data.

The next session should:

- Use the official NBA roster as the membership source.
- Join DARKO values by NBA player ID when the roster surface exposes it. If a name fallback is
  temporarily necessary, make the `Nic Claxton` → `Nicolas Claxton` alias explicit and validate all
  16 rows.
- Retain `nba_id`, official roster name, DARKO name/team field, `o_dpm`, `d_dpm`, total `dpm`, data
  availability, roster source, and snapshot timestamp in the post-specific working table.
- Confirm `dpm` approximately equals `o_dpm + d_dpm` before rounding.
- Compare the rounded working values with the visible first-party DARKO table for representative
  players.
- Save the working table and chart asset with the snapshot date so the post remains reproducible
  after the live values change.

## What the 2026-07-23 snapshot suggests

The chart has enough separation and a coherent tradeoff story:

- Jalen Smith is the only current Bull clearly positive on both displayed components.
- Norman Powell, Josh Giddey, and Tre Jones form an offense-positive/defense-negative group.
- Zach Collins occupies the opposite defense-positive/offense-negative profile.
- Several younger or lower-rated players cluster in the negative/negative region.
- Claxton's placement may attract attention because DARKO currently estimates strongly negative
  offense and roughly neutral defense. Show the placement without turning it into a categorical
  claim that he is a bad defender.

These are model estimates, not player grades. Defense is harder to estimate cleanly than offense,
and small DDPM differences should be treated as directional rather than ranked aggressively.

## Why this cannot be mixed with the NBA.com landscape

| Question | NBA.com on-court landscape | DARKO current-roster landscape |
| --- | --- | --- |
| Time direction | Backward-looking 2025–26 recap | Forward-looking current estimate |
| Population | Players with qualifying 2025–26 Bulls minutes | Official current roster as of a stated date |
| Metric | Bulls team OffRtg/DefRtg during a player's Chicago minutes | Projected player ODPM/DDPM |
| Team scope | Chicago stint only | Player history across teams, stabilized by DARKO |
| Interpretation | Shared five-player team outcome | Model-estimated player scoreboard impact |
| Source | NBA.com/stats | darko.app, plus NBA.com for roster membership |
| Qualification | Minimum Bulls minutes | Available current DARKO value; four missing rookies disclosed |

Do not reuse the 500-Bulls-minute threshold, Bulls team-rating crosshairs, “above team average”
quadrants, or “with him on the court” language. Those are correct only for the retrospective
NBA.com chart.

## Build direction

Before changing code, read `DEVELOPMENT.md` as required by the `create-bulls-post` skill.

- Create a separate idea-specific prototype rather than changing the meaning of
  `scripts/prototypes/bulls_on_court_landscape.py`.
- Reuse its chart geometry, square headshot treatment, collision-offset approach, and approved
  Sticky Stats visual grammar where practical.
- Use a flat jersey/warm panel with house ink, muted grid, and restrained Bulls red. Do not copy
  Basketball University's four-color field or revive the rejected gradient.
- Use equal-size square-crop player cutouts. Equal size avoids implying that minutes, contract size,
  or total DPM controls portrait size.
- Use plain quadrant language based on positive/negative offensive and defensive components, or
  omit quadrant labels if the draft is clearer without them. Do not call the quadrants above/below
  league average.
- Render a compact chart-only asset for Canva assembly.
- Add or update the matching `idea-catalog.html` card when implementation begins.
- Give the user one reviewable draft, the validated working table, the exact rookie footnote, and a
  short explanation of what the refreshed data shows.
- Stop for review before final export, catalog status changes, commit, or push.

## Risks and honesty checks

- DARKO changes nightly; values can drift between analysis, Canva assembly, and posting.
- The official Bulls roster can change during the offseason.
- A DARKO current-team label is not a Bulls-only data filter and may lag recent transactions.
- New or low-experience players have less evidence. Availability is not the same as equal
  confidence for every player.
- Defense is generally harder to estimate cleanly than offense. Avoid ranking claims from tiny
  DDPM differences.
- Do not describe the chart as a depth chart, rotation forecast, season projection, expected team
  record, or record of Bulls-only performance.
- Do not use the rounded first-party CSV as the final analytical input.

## Work completed and verification

- Read the original handoff and the relevant `create-bulls-post`, brainstorming, design, and posting
  workflow guidance.
- Refreshed the official NBA Bulls roster on 2026-07-23 and confirmed the same 16-player population.
- Inspected DARKO's current live leaderboard, metric labels, team filter, and `Download CSV` action.
- Confirmed the `CHI` filter does not match the official roster and documented the stale Powell and
  Claxton team fields.
- Downloaded and inspected a first-party CSV; confirmed that it rounds ODPM/DDPM to whole numbers
  and is therefore unsuitable for the scatter.
- Confirmed the public leaderboard response contains full-precision data and NBA player IDs.
- Extracted and validated the 12 available roster rows, confirmed the four missing rookies, and
  checked that each player's total DPM equals the offensive and defensive components within
  rounding.
- Reviewed `output/feed/2026-07-22-bulls-on-court-landscape-draft.png` and
  `scripts/prototypes/bulls_on_court_landscape.py` so this post can remain a deliberate visual
  companion.
- Finalized the scope, copy deck, production path, source language, zero-line treatment, and rookie
  footnote with the user.

## Open questions or blockers

There are no blocking planning questions. Do not ask the user to choose the roster boundary, rookie
treatment, title, subtitle, theme, reference-line interpretation, or production path again.

The only later choices should be evidence from the first draft: collision offsets, whether plain
quadrant labels help, and whether one genuinely useful annotation is warranted.

## Clearest next action

Take no action until the user intentionally revives the monthly check-in. On revival, start from the
catalog card and retained Canva design, re-fetch the official Bulls roster and full-precision DARKO
snapshot on the same date, compare the new snapshot with the July baseline, and confirm there is a
timely change or distinct Bulls-specific angle before preparing another edition.
