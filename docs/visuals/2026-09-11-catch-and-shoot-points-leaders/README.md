# Bulls catch-and-shoot points season leaders

Approved top-15 chart assets for all catch-and-shoot points and three-point catch-and-shoot points,
2013–14 through 2025–26 regular season, Chicago production only. Reuses the published
pull-up table-bar layout with PTS/G and FGA/G comparisons beneath their columns. Parentheses carry signed
differences; one page-level legend replaces repeated “vs. LA” labels.
Notion: https://www.notion.so/3d1e1c13abe680e0bffcec602a9720b3

The note “add FGA vs LA” is interpreted as attempts per game minus league attempts per
official NBA player appearance. The user also requested PTS/G versus the same league average. All players
are included in the denominator, including appearances with no catch-and-shoot attempt.
Volume comparisons are neutral gray; above-average attempts do not imply better shooting.

## Reproduce

Use the primary checkout's Python environment in this worktree:

```sh
python scripts/prototypes/catch_and_shoot_points_data.py
python scripts/prototypes/pull_up_points_bars.py --data docs/visuals/2026-09-11-catch-and-shoot-points-leaders/data/top15.csv --output output/catch-and-shoot-points-leaders/all.png --volume-comparisons --final
python scripts/prototypes/pull_up_points_bars.py --data docs/visuals/2026-09-11-catch-and-shoot-points-leaders/data/top15_three_point.csv --output output/catch-and-shoot-points-leaders/threes.png --efficiency-label 3P% --volume-comparisons --final
./run_tests.sh tests/test_catch_and_shoot_points_data.py tests/test_pull_up_points_data.py -q
```

Preparation reuses raw snapshots; `--refresh` fetches new data. Raw JSON records endpoint,
parameters and retrieval time. Official Chicago snapshots were reused from yesterday's
post, with their original timestamps; catch-and-shoot and league official rows were fetched
on September 11. No claim of full tracking observation coverage follows from GP matching.

## Metric contract

Source: NBA.com `LeagueDashPtStats`, `player_or_team=Player`, `pt_measure_type=CatchShoot`,
`per_mode_simple=Totals`, `season_type_all_star=Regular Season`, each season individually.
Chicago uses `team_id_nullable=1610612741`; league player baseline has no team filter.
Team queries are audit comparisons. `LeagueDashPlayerStats` provides official GP and count
bounds with matching regular-season/team scope. Raw team identifiers on traded-player rows
may show their later team; the query's Chicago filter and official stint counts establish scope.

One row is a player's season production for the specified team scope. Provider counts are
CATCH_SHOOT_FGM, FGA, PTS, FG3M and FG3A. Derived 3PM = PTS − 2×FGM, checked against every
available raw FG3M. Total-board eFG% = 50×PTS/FGA; three-board 3P% = 100×3PM/3PA.
Points exclude free throws. PTS/G and FGA/G divide by official Chicago GP.
Efficiency comparisons subtract pooled same-season league shooting efficiency, not an
unweighted mean of player percentages. PTS/G and FGA/G comparisons subtract pooled points or attempts per
all official player appearances. No minimum-games or attempts filter is applied.

Worked examples: Nikola Vučević 2022–23: 204 makes, 509 attempts, 121 threes, 529 points,
82 GP: 52.0% eFG and 6.5 PTS/G. Coby White 2023–24: 145 threes in 397 attempts,
435 three-point points, 79 GP: 36.5% 3P and 5.5 PTS/G.

`all_player_seasons.csv` and `all_three_point_seasons.csv` preserve the population;
`top15.csv` and `top15_three_point.csv` are chart selections. The three-point CSV uses the
renderer-compatible `efg_pct` and `league_efg_pct` fields for **3P%**, not eFG%; its renderer
must receive `--efficiency-label 3P%`. Point ties sort by makes, then season and player ID.
All three seasons tied at the three-point cutoff of 330 points are included.

## Coverage and source limitations

All 13 seasons have saved player, team and official data. Chicago GP matches official GP;
Chicago tracking counts are bounded by official counts. Historical tracking is unavailable
before 2013–14. The alternate shots-general dashboard is not blended into this source.

- Chicago player/team differences: 2013–14 to 2016–17 attempts differ by +25, +28, +18,
  +25 despite equal makes/points. In 2024–25 player totals are −5 FGM, −25 FGA and −10 PTS
  relative to the team response. Counts are retained as supplied.
- 2017–18 league player/team baselines differ: player eFG 54.3611% vs team 53.9668%;
  player three-point attempts are 305 below team totals. This is separate from missing
  field uncertainty. Charts consistently use the player-level source, as yesterday's post did.
- Missing 3PA is retained as an interval, bounded by official total 3PA and catch-and-shoot
  FGA. Most blanks resolve to zero because one of those independently supplied totals is
  zero. Seven attempts remain unresolved across four seasons (2013–14: 2; 2014–15: 1;
  2017–18: 2; 2023–24: 2). All selected rows have resolved 3PA. Both league bounds yield
  identical one-decimal displayed comparisons for every selected row. This does not resolve
  the larger player/team disagreement. See `missing_three_point_attempts.csv` and
  `season_audit.csv`.
- Jon Leuer 2018–19 has 12 tracking catch-and-shoot 3PA versus 11 official total 3PA.
  The league source discrepancy is retained and audited, not silently corrected.

Transparent 300-DPI chart assets and warm-background review previews are in `assets/`.
User approved the chart assets and authorized integration on September 11.
Canva: https://www.canva.com/design/DAHU7p3aMnA/tfma3d9u-_buqQLT6W5V5g/edit
The downloaded three-page PNG export was reviewed at 1080×1350. Chart values, row order,
portraits and supporting comparisons match the approved assets without clipping.
Canva copy corrections remain: cover “cactch” typo; cover scope should specify a single season
and 2013–14; three-point subtitle should explicitly say three-point points. The crowded
single-line footer should identify parentheses as differences and name the catch-and-shoot
league baseline. Detailed recommendations and promotion draft live in Notion. Final composed
page approval remains pending those copy decisions; no publication is recorded.
