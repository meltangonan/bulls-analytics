# CLOSED — 2025–26 Bulls on-court performance landscape

## Outcome

The user confirmed the Canva-composed post was published on **2026-07-22**. The post uses the
verified NBA.com chart asset, a 500-Bulls-minute qualification, Bulls-only minutes for traded
players, flat Sticky Stats-style chart treatment, and square-crop headshots. It remains a
backward-looking 2025–26 on-court team-efficiency view, not an isolated player-impact metric.

The final downloaded 1080×1350 Canva page and exact posted caption were not returned to the
repository before publication. If the user supplies them later, inspect the PNG, copy it to
`docs/mocks/`, and record the actual caption on the matching `idea-catalog.html` card. This is
optional artifact housekeeping; no production work remains open.

## Objective

Create and refine a backward-looking Instagram post that recaps how the 2025–26 Chicago Bulls
performed offensively and defensively during each qualifying player's minutes. The visual starting
point is Basketball University's roster impact landscape, adapted into an NBA.com-based Bulls season
recap rather than a predictive DARKO post.

Reference post: [Basketball University — 2026–27 Charlotte Hornets Impact Landscape](https://x.com/UofBasketball/status/2079719750964318415)

## Settled decisions

- This is a **2025–26 regular-season recap**, not a forecast of the roster under construction.
- Do not use DARKO or another forward-looking projection metric for the primary analysis.
- Make an **on-court performance landscape**:
  - X-axis: Bulls offensive rating while the player was on the court.
  - Y-axis: Bulls defensive rating while the player was on the court, oriented so moving upward
    means better defense (lower points allowed per 100 possessions).
  - Use Bulls full-season offensive and defensive ratings as the initial crosshairs/reference lines.
- Include players based on minutes logged for Chicago in 2025–26, not membership on the current
  2026–27 roster. Multi-team players must use their Bulls-only split.
- Use NBA.com/NBA Stats as the analytical source through the repo's existing `nba_api` setup.
- Describe the numbers as **team performance during each player's minutes**, not isolated individual
  offensive or defensive impact.
- Start with roughly a 500-Bulls-minute qualification threshold, but inspect the real minutes
  distribution before locking it. If an important part of the season falls just below the line,
  evaluate a 350–500 minute threshold or a clearly labeled limited-sample treatment rather than
  silently making an exception.
- Keep the first version simple. Do not build APM/RAPM for this post.

## Metric interpretation

NBA.com defines player-level offensive rating as the points a player's team scored per 100
possessions while he was on the court. Player-level defensive rating is the points his team allowed
per 100 possessions while he was on the court. Net rating is `OffRtg - DefRtg`.

These are shared lineup outcomes. Teammates, opponents, role, substitution patterns, injuries, and
garbage time affect them. The post should therefore use language such as:

> How the Bulls performed with each player on the court

Avoid claims such as "best player," "individual offensive rating," or "defensive impact" unless
separate evidence supports them.

Official definition: [NBA Stats glossary](https://www.nba.com/stats/help/glossary?hidenav=true)

## Implemented data path

`bulls.data.get_team_player_advanced_stats()` joins two Chicago-filtered NBA Stats responses:

- `LeagueDashPlayerStats` with `MeasureType=Base` supplies total Bulls minutes.
- `LeagueDashPlayerStats` with `MeasureType=Advanced` supplies OffRtg, DefRtg, NetRtg, and possessions.

This join is necessary because the Advanced response reports minutes per game even when
`PerMode=Totals`. The selected team's games, minutes, and ratings remain correctly scoped, but a
traded player's returned team abbreviation can show his later/current team. Do not use that
abbreviation to infer the stint scope.

`bulls.data.get_team_advanced_stats()` fetches the Bulls team row separately for the reference
lines. The validated full-season team values are 112.1 OffRtg, 117.4 DefRtg, and -5.3 NetRtg.

The player result includes:

- `PLAYER_ID`, `PLAYER_NAME`, `GP`, `MIN`
- `OFF_RATING`, `DEF_RATING`, `NET_RATING`
- `POSS`, plus optional contextual measures such as `TS_PCT`, `USG_PCT`, and `PIE`

The prototype is `scripts/prototypes/bulls_on_court_landscape.py`; generated review artifacts stay
under `output/feed/` until the user approves a final render. Mocked coverage lives in
`tests/test_data.py`.

## Current visual/content direction

The production path is now a verified Python chart asset plus external page assembly, matching the
2026-07-21 Sticky Stats chart rather than a complete Python poster. The chart uses its warm rounded
panel, Helvetica, heavy left/bottom axes, faint grid, plain two-line quadrant keys without legend
dots, metric-only axis titles (`OFF RTG` and `DEF RTG`), unoutlined player and team-reference
labels, equal-size square-crop cutout headshots, and dashed reference lines. Both team-reference labels sit
inside the panel. Page title, subtitle, source, watermark, and any closing copy belong to the
eventual assembled page.

The Basketball University reference uses a four-color field that preserves all four axis
combinations: yellow for defense-led, green for above average on both axes, red for below average on
both, and purple for offense-led. A localized green/red adaptation was tested and removed. Reducing
four quadrants to two colors required an additional overall-good/overall-bad score, blurred the
mixed-quadrant distinction, and made the background more interpretive than the chart needs.

The settled draft therefore keeps the Sticky Stats panel flat. The axes, team crosshairs, and plain
quadrant keys already explain direction without adding a third encoding. Do not revive a gradient
unless the user explicitly chooses the full four-color quadrant logic and accepts that departure
from the repo's normal Bulls palette.

Promising starting copy:

- Working title: **HOW THE BULLS PERFORMED WITH EACH PLAYER**
- Subtitle: Chicago's offensive and defensive rating during each player's minutes · 2025–26 regular season
- X-axis cue: **Better Bulls offense with him on court →**
- Y-axis cue: **↑ Better Bulls defense with him on court**
- Footer concept: Minimum X Bulls minutes · Regular season · Team ratings during each player's
  minutes · Source: NBA.com/stats

Equal-size headshots are the cleanest initial treatment. If playing time needs a visual encoding,
prefer a subtle supporting label or ring rather than dramatically different headshot sizes that
could look like a quality ranking.

## Open creative and analytical questions

- Is the Bulls team average the best crosshair, or would league-average context add useful meaning
  without clutter? The approved chart uses the Bulls average; do not add league context unless the
  user reopens it during Canva assembly.
- The 500-Bulls-minute threshold is confirmed. It yields 14 players and a clean 176.6-minute gap
  between Leonard Miller (623.8) and Nick Richards (447.2).
- Which 2–3 placements are genuinely useful to annotate? The strongest candidates from the first
  read are Jalen Smith, Coby White, and either Patrick Williams or Isaac Okoro.
- Should a second carousel page explain selected placements with supporting stats such as TS%, usage,
  assist rate, deflections, or contested shots? Do not add this unless the first-page findings need it.
- The chart-only Sticky Stats treatment is approved for external page assembly. The gradient is
  removed and the portraits use square crops rather than circular masks.

## Work completed and verification

- Confirmed the user prefers a descriptive 2025–26 recap over DARKO's forward-looking projections.
- Confirmed NBA.com exposes player-level advanced OffRtg, DefRtg, and NetRtg and defines them as team
  performance during the player's on-court minutes.
- Confirmed `nba_api` documents both advanced player statistics and team player on/off endpoints.
- Reviewed the linked Basketball University post in the logged-in X session. Its graphic plots
  offensive and defensive DARKO DPM for a roster landscape and explicitly credits `darko.app`; it
  is a visual reference only for this post.
- Fetched 28 Chicago-filtered player rows and validated a 14-player population at 500 Bulls minutes.
  The qualifying OffRtg range is 103.8–116.4; DefRtg is 113.0–120.6, so the scatter has enough
  separation to tell a story despite several shared-lineup clusters.
- Verified traded-player stint handling by comparing Chicago-filtered and all-team rows. Examples:
  Coby White has 843.4 Chicago minutes at 115.5/115.8 versus 1,249.8 all-team minutes at
  117.2/114.0; Nikola Vučević has 1,480.3 Chicago minutes at 113.2/117.5 versus 1,818.1 all-team
  minutes at 113.1/114.8.
- Cross-checked representative rows in NBA.com's rendered 2025–26 Chicago Players Advanced and
  Traditional tables: Matas Buzelis, Josh Giddey, Jalen Smith, Coby White, and Nikola Vučević all
  match the fetched values, including total Chicago minutes from the Traditional Totals view.
- Added reusable player/team advanced fetchers and mocked tests. The focused data suite passes.
- Added a Parked idea-catalog card and revised the render into a transparent 1080×1030 chart-only
  asset using the Sticky Stats formatting grammar. Plain quadrant keys and unoutlined player names
  now match the reference format. The background is flat after testing and rejecting both a
  full-panel four-corner wash and a localized green/red field.
- User approved the chart asset, 500-Bulls-minute threshold, and square-crop headshots on 2026-07-22
  and moved the page into Canva assembly. This approves the chart, not the final post.
- Review artifacts:
  - `output/feed/2026-07-22-bulls-on-court-landscape-min-500.csv`
  - `output/feed/2026-07-22-bulls-on-court-landscape-chart.png`

## Clearest next action

Wait for the user's downloaded 1080×1350 Canva page, then inspect it against the Canva checklist in
`POSTING_WORKFLOW.md`. Confirm the title/subtitle, visible `Minimum 500 Bulls minutes` qualification,
2025–26 regular-season coverage, NBA.com source, account attribution, and any player annotations.
Only after the downloaded page passes review should it be copied to `docs/mocks/` and the catalog card
move from Parked to Mocked. Do not add league-average context or a second carousel page unless the
user reopens those choices.
